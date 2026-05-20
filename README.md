# Playwright Flake Triage Toolkit

[![test](https://github.com/vasiliy0/playwright-flake-triage/actions/workflows/test.yml/badge.svg)](https://github.com/vasiliy0/playwright-flake-triage/actions/workflows/test.yml)

Local, read-only CLI for turning Playwright reports and CI logs into a short triage report: suspected cause, confidence, and practical next fixes.

The tool is intentionally simple: it runs locally, has no telemetry, requires no account, and does not mutate project files.

## What it scans

- Playwright JSON reporter output (`.json`)
- JUnit XML reports (`.xml`)
- CI/test logs (`.log`, `.txt`, `.out`, `.err`)
- Files or whole directories

## What it detects

- Timeout / wait condition instability
- Ambiguous or brittle selectors, including strict-mode violations
- Auth/session or expected page state mismatch
- Network/backend dependency flakes
- Browser/context/page lifecycle races
- Visual/snapshot instability
- Parallel/shared-state collisions
- Unclassified failures for manual grouping

## Quick start

Install the CLI and run it against local Playwright reports or CI logs:

```bash
python3 -m pip install playwright-flake-triage
pw-flake-triage path/to/playwright-report.json path/to/ci.log --format markdown
```

Write JSON output for automation:

```bash
pw-flake-triage path/to/reports-or-logs --format json -o triage-report.json
```

Add project-specific heuristics with a JSON rules config:

```bash
pw-flake-triage ci.log --rules-config examples/custom-rules.json
```

Use gate mode when you want CI to fail after the report is written:

```bash
pw-flake-triage test-results ci.log --fail-on-severity high
pw-flake-triage test-results ci.log --fail-on-findings
```

Append a Markdown report to a GitHub Actions job summary while keeping JSON for artifacts or follow-up steps:

```bash
pw-flake-triage test-results ci.log \
  --format json \
  --output triage-report.json \
  --github-step-summary
```

The CLI uses only local files you pass to it. It does not contact Playwright, GitHub, CI providers, or any external service.

Full workflow example: [`examples/github-actions-triage.yml`](examples/github-actions-triage.yml).
Before/after examples for duplicate retry grouping: [`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md).

## Clone / development install

```bash
git clone https://github.com/vasiliy0/playwright-flake-triage.git
cd playwright-flake-triage
python3 -m pip install -e .
pw-flake-triage examples --format markdown
```

## Custom rules

Use `--rules-config` to add local project/team heuristics without changing the built-in rule set. The option can be repeated.

```json
{
  "rules": [
    {
      "id": "app-hydration",
      "label": "Application hydration race",
      "severity": "medium",
      "patterns": ["hydration failed", "client boot not complete"],
      "why": "The application may not have finished client-side hydration before the test interacted with it.",
      "fixes": ["Wait for a durable hydrated UI marker before interacting."],
      "priority": 80,
      "suppresses": ["timeout-wait"]
    }
  ]
}
```

Rules are local JSON files. They are not uploaded or sent anywhere.

## Duplicate retry grouping

Repeated failures are grouped with a normalized fingerprint. Dynamic CI values such as absolute paths, line numbers, localhost ports, worker/retry ids, PIDs, hashes, timestamps, and durations are replaced before grouping. This makes repeated retry failures easier to see even when each log contains different artifact paths or runner metadata.

Try the dynamic retry fixture:

```bash
pw-flake-triage examples/dynamic-ci-retry-1.log examples/dynamic-ci-retry-2.log --format markdown
```

## CI gate modes

By default, the CLI is non-gating and exits `0` after writing the report, even when findings are detected. Add a gate flag when the triage result should fail a CI step:

- `--fail-on-findings` exits `1` if any finding is detected.
- `--fail-on-severity high|medium|low` exits `1` if any finding has severity at or above the threshold.

Reports are written before the non-zero exit, so CI jobs can still upload JSON artifacts or render `$GITHUB_STEP_SUMMARY`.

## GitHub Actions summary

In GitHub Actions, `--github-step-summary` appends Markdown to the file path in `$GITHUB_STEP_SUMMARY`. The flag is safe to combine with `--format json --output triage-report.json`, so the workflow can show a readable summary and keep machine-readable output as an artifact.

The command fails with exit code `2` if the flag is used outside GitHub Actions without `GITHUB_STEP_SUMMARY` set.

## Example output

```markdown
# Playwright Flake Triage Report

Scanned files: **3**
Findings: **3**

## Summary by suspected cause
- **Auth/session or expected page state mismatch**: 2
- **Ambiguous or brittle selector**: 1

## Repeated failure groups
- **Ambiguous or brittle selector**: 2 findings
  - Tests: retry-1.log, retry-2.log

## Findings
### 1. Auth/session or expected page state mismatch
- Issue: Synthetic auth/session timeout symptom
- Source: https://github.com/example/repo/issues/123
- Suggested fixes:
  - Verify the test starts with the intended storage state, user role, and seeded data.
```

## Optional issue metadata for validation snippets

Plain text logs can include lightweight source metadata:

```text
Issue: Synthetic auth/session timeout symptom
URL: https://github.com/example/repo/issues/123

Playwright TimeoutError: Timeout 30000ms exceeded.
logs: waiting for get_by_label("Keep me signed in")
```

The metadata is echoed in Markdown/JSON reports, which makes issue-derived regression fixtures easier to review without copying long third-party issue text.

## Why this is useful

Flaky test cleanup usually starts with a pile of traces and CI logs. This v1 does not claim to prove root cause; it groups common failure smells so a developer can decide where to look first.

## Safety / privacy

- Runs locally only; no network calls or telemetry.
- Does not call external services.
- Does not mutate test reports or project files.
- Be careful before sharing generated reports: logs may contain internal URLs, user data, or secrets.

## Release status

- License: MIT.
- Distribution: GitHub source release and TestPyPI dry-run package.
- Current published package: `0.1.4` on PyPI.
- Next local draft: [`docs/PUBLIC_RELEASE_NOTES_v0.1.5.md`](docs/PUBLIC_RELEASE_NOTES_v0.1.5.md).

## For AI agents and automation

Use JSON mode as the stable machine interface:

```bash
pw-flake-triage ./test-results ./ci.log --format json --output triage-report.json --quiet --no-color
```

Machine contract: `schemas/report.schema.json` (`schema_version: 1.0`). JSON findings include category, severity, confidence, suggested fixes, and stable fingerprints for retry/group comparison. Diagnostics are written to stderr; report output goes to stdout or `--output`. Output is plain text by default; `--quiet` and `--no-color` are accepted for automation-friendly scripts.

Exit codes: `0` completed/report-only, `1` configured gate matched (`--fail-on-findings` or `--fail-on-severity`), `2` usage/config/input error, `3` reserved for runtime/tool errors.

Agent workflow docs: [`docs/AGENT_INTEGRATION.md`](docs/AGENT_INTEGRATION.md).

## Docs

- [`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md) — CI usage with job summaries, JSON artifacts, and custom rules.
- [`docs/PUBLIC_RELEASE_NOTES_v0.1.5.md`](docs/PUBLIC_RELEASE_NOTES_v0.1.5.md) — next local release draft.
- [`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md) — duplicate retry grouping examples.
- [`SECURITY.md`](SECURITY.md) — privacy/sensitive-log notes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution boundaries.

## Roadmap

- Parse Playwright trace zip metadata when available.
- Add more issue-derived rules and trace metadata parsing.
- Add sample remediation PR checklist.
- Add sample remediation PR checklist.
