from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from .analyzer import analyze_paths, Analysis
from .rules import RULES, load_rules_config


def render_markdown(analysis: Analysis) -> str:
    lines: list[str] = []
    lines.append("# Playwright Flake Triage Report")
    lines.append("")
    lines.append(f"Scanned files: **{analysis.scanned_files}**")
    lines.append(f"Findings: **{len(analysis.findings)}**")
    lines.append("")
    if analysis.notes:
        lines.append("## Notes")
        for note in analysis.notes:
            lines.append(f"- {note}")
        lines.append("")
    if not analysis.findings:
        lines.append("No failure signals found in supported files.")
        return "\n".join(lines) + "\n"

    by_category = Counter(f.category for f in analysis.findings)
    lines.append("## Summary by suspected cause")
    for category, count in by_category.most_common():
        lines.append(f"- **{category}**: {count}")
    lines.append("")

    duplicate_groups = analysis.duplicate_groups()
    if duplicate_groups:
        lines.append("## Repeated failure groups")
        for group in duplicate_groups:
            lines.append(f"- **{group['category']}**: {group['count']} findings")
            lines.append(f"  - Tests: {', '.join(group['tests'][:5])}")
            if len(group["tests"]) > 5:
                lines.append(f"  - Additional tests: {len(group['tests']) - 5}")
        lines.append("")

    lines.append("## Findings")
    for i, f in enumerate(analysis.findings, 1):
        lines.append(f"### {i}. {f.category}")
        lines.append(f"- File: `{f.file}`")
        lines.append(f"- Test: `{f.test}`")
        lines.append(f"- Status: `{f.status}`")
        if f.issue_title:
            lines.append(f"- Issue: {f.issue_title}")
        if f.issue_url:
            lines.append(f"- Source: {f.issue_url}")
        lines.append(f"- Severity: **{f.severity}**; confidence: **{f.confidence}%**")
        lines.append(f"- Signal: {f.signal}")
        lines.append(f"- Why this happens: {f.why}")
        lines.append("- Suggested fixes:")
        for fix in f.fixes:
            lines.append(f"  - {fix}")
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pw-flake-triage",
        description="Read-only heuristic triage for Playwright JSON/JUnit reports and CI logs.",
    )
    parser.add_argument("paths", nargs="+", help="Report/log files or directories to scan")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--output", "-o", help="Write report to file instead of stdout")
    parser.add_argument(
        "--github-step-summary",
        action="store_true",
        help="Append a Markdown report to the GitHub Actions step summary file from $GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--rules-config",
        action="append",
        default=[],
        help="Load additional heuristic rules from a JSON config file. Can be repeated.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = _load_rules(args.rules_config)
    except Exception as exc:
        sys.stderr.write(f"Failed to load rules config: {exc}\n")
        return 2
    analysis = analyze_paths(args.paths, rules=rules)
    if args.format == "json":
        output = json.dumps(analysis.to_dict(), indent=2)
    else:
        output = render_markdown(analysis)
    if args.github_step_summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_path:
            sys.stderr.write("--github-step-summary requires GITHUB_STEP_SUMMARY to be set.\n")
            return 2
        _write_text(summary_path, render_markdown(analysis), mode="a")

    if args.output:
        _write_text(args.output, output)
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def _load_rules(config_paths: list[str]) -> tuple:
    rules = list(RULES)
    for path in config_paths:
        rules.extend(load_rules_config(path))
    return tuple(rules)


def _write_text(path: str, output: str, mode: str = "w") -> None:
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(output)
        if not output.endswith("\n"):
            fh.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
