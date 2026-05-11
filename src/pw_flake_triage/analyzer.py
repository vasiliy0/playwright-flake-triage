from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

from .rules import classify

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


@dataclass
class Analysis:
    scanned_files: int
    findings: list[Finding]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_files": self.scanned_files,
            "finding_count": len(self.findings),
            "findings": [asdict(f) for f in self.findings],
            "notes": self.notes,
        }


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


def analyze_paths(paths: list[str]) -> Analysis:
    files = discover([Path(p) for p in paths])
    findings: list[Finding] = []
    notes: list[str] = []
    for file in files:
        try:
            suffix = file.suffix.lower()
            if suffix in JSON_EXTENSIONS:
                findings.extend(analyze_json(file))
            elif suffix in XML_EXTENSIONS:
                findings.extend(analyze_junit_xml(file))
            elif suffix in TEXT_EXTENSIONS:
                findings.extend(analyze_text(file))
        except Exception as exc:  # keep CLI useful on mixed report dirs
            notes.append(f"Skipped {file}: {exc}")
    if not files:
        notes.append("No supported report/log files found. Supported: .json, .xml, .log, .txt, .out, .err")
    return Analysis(scanned_files=len(files), findings=findings, notes=notes)


def _make_findings(file: Path, test: str, status: str, text: str, metadata: dict[str, str] | None = None) -> list[Finding]:
    metadata = metadata or {}
    found = []
    for rule, count in classify(text):
        found.append(
            Finding(
                file=str(file),
                test=test or "(unknown test/log)",
                status=status or "unknown",
                signal=_snippet(text),
                category=rule.label,
                severity=rule.severity,
                confidence=min(100, 55 + count * 15),
                why=rule.why,
                fixes=list(rule.fixes),
                issue_title=metadata.get("issue_title", ""),
                issue_url=metadata.get("issue_url", ""),
            )
        )
    if not found and text.strip():
        found.append(
            Finding(
                file=str(file),
                test=test or "(unknown test/log)",
                status=status or "unknown",
                signal=_snippet(text),
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
            )
        )
    return found


def analyze_text(file: Path) -> list[Finding]:
    text = file.read_text(errors="replace")
    metadata, body = _extract_text_metadata(text)
    return _make_findings(file, file.name, "log", body, metadata)


def analyze_junit_xml(file: Path) -> list[Finding]:
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
            findings.extend(_make_findings(file, name, status, "\n".join(chunks)))
    return findings


def analyze_json(file: Path) -> list[Finding]:
    data = json.loads(file.read_text(errors="replace"))
    candidates: list[tuple[str, str, str]] = []
    _walk_json(data, [], candidates)
    findings: list[Finding] = []
    for name, status, text in candidates:
        if status.lower() not in {"passed", "expected", "skipped"} or text.strip():
            findings.extend(_make_findings(file, name, status, text))
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
