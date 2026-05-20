from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any

from . import __version__
from .rules import RULES, Rule, classify

TEXT_EXTENSIONS = {".log", ".txt", ".out", ".err"}
JSON_EXTENSIONS = {".json"}
XML_EXTENSIONS = {".xml"}


@dataclass
class Finding:
    file: str
    test: str
    status: str
    signal: str
    category: str
    severity: str
    confidence: int
    why: str
    fixes: list[str]
    issue_title: str = ""
    issue_url: str = ""
    fingerprint: str = ""


@dataclass
class Analysis:
    scanned_files: int
    findings: list[Finding]
    notes: list[str]

    def duplicate_groups(self) -> list[dict[str, Any]]:
        groups: dict[str, list[Finding]] = defaultdict(list)
        for finding in self.findings:
            groups[finding.fingerprint].append(finding)
        repeated = []
        for fingerprint, findings in groups.items():
            if len(findings) < 2:
                continue
            repeated.append(
                {
                    "fingerprint": fingerprint,
                    "category": findings[0].category,
                    "count": len(findings),
                    "tests": sorted({f.test for f in findings}),
                    "files": sorted({f.file for f in findings}),
                }
            )
        return sorted(repeated, key=lambda item: (-item["count"], item["category"], item["fingerprint"]))

    def to_dict(self) -> dict[str, Any]:
        severity_counts = Counter(f.severity for f in self.findings)
        category_counts = Counter(f.category for f in self.findings)
        report = {
            "schema_version": "1.0",
            "tool": "playwright-flake-triage",
            "tool_version": __version__,
            "status": "warning" if self.findings else "ok",
            "scanned_files": self.scanned_files,
            "finding_count": len(self.findings),
            "summary": {
                "scanned_files": self.scanned_files,
                "finding_count": len(self.findings),
                "summary_by_severity": dict(sorted(severity_counts.items())),
                "summary_by_category": dict(sorted(category_counts.items())),
            },
            "summary_by_severity": dict(sorted(severity_counts.items())),
            "summary_by_category": dict(sorted(category_counts.items())),
            "findings": [asdict(f) for f in self.findings],
            "duplicate_groups": self.duplicate_groups(),
            "metadata": {
                "privacy": "local-only; no telemetry, network calls, or source uploads",
                "determinism": "fingerprints normalize common CI retry/run noise",
            },
            "notes": self.notes,
        }
        return report


def discover(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix.lower() in TEXT_EXTENSIONS | JSON_EXTENSIONS | XML_EXTENSIONS:
                    files.append(child)
        elif path.is_file():
            files.append(path)
    return sorted(set(files))


def analyze_paths(paths: list[str], rules: tuple[Rule, ...] | None = None) -> Analysis:
    files = discover([Path(p) for p in paths])
    active_rules = rules or RULES
    findings: list[Finding] = []
    notes: list[str] = []
    for file in files:
        try:
            suffix = file.suffix.lower()
            if suffix in JSON_EXTENSIONS:
                findings.extend(analyze_json(file, active_rules))
            elif suffix in XML_EXTENSIONS:
                findings.extend(analyze_junit_xml(file, active_rules))
            elif suffix in TEXT_EXTENSIONS:
                findings.extend(analyze_text(file, active_rules))
        except Exception as exc:  # keep CLI useful on mixed report dirs
            notes.append(f"Skipped {file}: {exc}")
    if not files:
        notes.append("No supported report/log files found. Supported: .json, .xml, .log, .txt, .out, .err")
    return Analysis(scanned_files=len(files), findings=findings, notes=notes)


def _make_findings(
    file: Path,
    test: str,
    status: str,
    text: str,
    metadata: dict[str, str] | None = None,
    rules: tuple[Rule, ...] = RULES,
) -> list[Finding]:
    metadata = metadata or {}
    found = []
    signal = _snippet(text)
    for rule, count in classify(text, rules):
        found.append(
            Finding(
                file=str(file),
                test=test or "(unknown test/log)",
                status=status or "unknown",
                signal=signal,
                category=rule.label,
                severity=rule.severity,
                confidence=min(100, 55 + count * 15),
                why=rule.why,
                fixes=list(rule.fixes),
                issue_title=metadata.get("issue_title", ""),
                issue_url=metadata.get("issue_url", ""),
                fingerprint=_fingerprint(rule.id, signal),
            )
        )
    if not found and text.strip():
        found.append(
            Finding(
                file=str(file),
                test=test or "(unknown test/log)",
                status=status or "unknown",
                signal=signal,
                category="Unclassified failure",
                severity="low",
                confidence=35,
                why="The failure did not match v1 heuristic rules, but it is still worth grouping for manual review.",
                fixes=[
                    "Open the Playwright trace for this test and compare first failing action vs prior successful action.",
                    "Add the recurring error wording to a custom rule if this appears more than once.",
                ],
                issue_title=metadata.get("issue_title", ""),
                issue_url=metadata.get("issue_url", ""),
                fingerprint=_fingerprint("unclassified", signal),
            )
        )
    return found


def analyze_text(file: Path, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    text = file.read_text(errors="replace")
    metadata, body = _extract_text_metadata(text)
    return _make_findings(file, file.name, "log", body, metadata, rules)


def analyze_junit_xml(file: Path, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    root = ET.parse(file).getroot()
    findings: list[Finding] = []
    for case in root.iter("testcase"):
        name = ".".join(filter(None, [case.attrib.get("classname", ""), case.attrib.get("name", "")]))
        chunks = []
        status = "passed"
        for tag in ("failure", "error", "system-out", "system-err"):
            for node in case.findall(tag):
                if tag in {"failure", "error"}:
                    status = tag
                chunks.append(node.attrib.get("message", ""))
                chunks.append(node.text or "")
        if status != "passed" or any(chunks):
            findings.extend(_make_findings(file, name, status, "\n".join(chunks), rules=rules))
    return findings


def analyze_json(file: Path, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    data = json.loads(file.read_text(errors="replace"))
    candidates: list[tuple[str, str, str]] = []
    _walk_json(data, [], candidates)
    findings: list[Finding] = []
    for name, status, text in candidates:
        if status.lower() not in {"passed", "expected", "skipped"} or text.strip():
            findings.extend(_make_findings(file, name, status, text, rules=rules))
    return findings


def _walk_json(obj: Any, path: list[str], out: list[tuple[str, str, str]]) -> None:
    if isinstance(obj, dict):
        name = str(obj.get("title") or obj.get("name") or obj.get("file") or "")
        status = str(obj.get("status") or obj.get("outcome") or "")
        chunks: list[str] = []
        for key in ("message", "stack", "error", "stdout", "stderr"):
            val = obj.get(key)
            if isinstance(val, str):
                chunks.append(val)
            elif isinstance(val, list):
                chunks.extend(str(x) for x in val)
            elif isinstance(val, dict):
                chunks.extend(str(v) for v in val.values())
        for err in obj.get("errors", []) if isinstance(obj.get("errors"), list) else []:
            if isinstance(err, dict):
                chunks.extend(str(err.get(k, "")) for k in ("message", "stack", "value"))
            else:
                chunks.append(str(err))
        if chunks:
            out.append((" > ".join([*path, name]).strip(" >") or name, status, "\n".join(chunks)))
        for key, val in obj.items():
            if key in {"message", "stack", "error", "errors", "stdout", "stderr"}:
                continue
            next_path = [*path, name] if key in {"suites", "specs", "tests", "results"} and name else path
            _walk_json(val, next_path, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_json(item, path, out)


def _extract_text_metadata(text: str) -> tuple[dict[str, str], str]:
    """Read optional leading metadata from plain log snippets.

    Supported lines:
    Issue: <title>
    Title: <title>
    URL: https://github.com/owner/repo/issues/123
    Source: https://github.com/owner/repo/issues/123
    """
    metadata: dict[str, str] = {}
    body_lines: list[str] = []
    in_header = True
    for line in text.splitlines():
        stripped = line.strip()
        if in_header and not stripped:
            in_header = False
            continue
        if in_header:
            key, sep, value = stripped.partition(":")
            key_l = key.lower()
            if sep and key_l in {"issue", "title"}:
                metadata["issue_title"] = value.strip()
                continue
            if sep and key_l in {"url", "source"}:
                metadata["issue_url"] = value.strip()
                continue
            in_header = False
        body_lines.append(line)
    return metadata, "\n".join(body_lines) if body_lines else text


def _snippet(text: str, limit: int = 360) -> str:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _fingerprint(rule_id: str, signal: str) -> str:
    normalized = _normalize_dynamic_signal(signal)
    return f"{rule_id}:{normalized[:180]}"


def _normalize_dynamic_signal(signal: str) -> str:
    """Reduce CI/run-specific noise before duplicate grouping.

    Retry logs often contain different worker ids, line numbers, absolute temp paths,
    localhost ports, UUIDs, hashes, timestamps, and durations for the same underlying
    failure. Keep the semantic Playwright wording while replacing those values with
    stable placeholders so repeat groups are useful across retries and machines.
    """
    text = signal.lower()
    replacements = [
        (r"https?://[^\s)]+", " <url> "),
        (r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b", " <uuid> "),
        (r"\b[a-f0-9]{12,}\b", " <hash> "),
        (r"\b\d{4}-\d{2}-\d{2}[t\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?z?\b", " <timestamp> "),
        (r"\b\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds|m|min|minutes)\b", " <duration> "),
        (r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0):\d+\b", " <hostport> "),
        (r"(?:(?:/[\w.\-]+)+|[a-z]:\\(?:[^\\\s]+\\)+)[\w.\-]+", " <path> "),
        (r"\b(?:line|column|col)\s+\d+\b", " <position> "),
        (r"\b\w+\.(?:spec|test)\.(?:ts|tsx|js|jsx):\d+:\d+\b", " <test-file-position> "),
        (r"\b(?:worker|retry|attempt|shard|run|job|build)[-_ ]?\d+\b", " <ci-slot> "),
        (r"\bpid\s*[:=]?\s*\d+\b", " <pid> "),
        (r"\b\d+\b", " <n> "),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(r"[^a-z0-9<>]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
