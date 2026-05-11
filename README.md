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

From the repository root:

```bash
PYTHONPATH=src python3 -m pw_flake_triage.cli examples --format markdown
PYTHONPATH=src python3 -m pw_flake_triage.cli examples --format json -o triage-report.json
```

Optional editable install:

```bash
python3 -m pip install -e .
pw-flake-triage path/to/playwright-report.json path/to/ci.log
```

## Example output

```markdown
# Playwright Flake Triage Report

Scanned files: **3**
Findings: **3**

## Summary by suspected cause
- **Auth/session or expected page state mismatch**: 2
- **Ambiguous or brittle selector**: 1
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

- Runs locally only.
- Does not call external services.
- Does not mutate test reports or project files.
- Be careful before sharing generated reports: logs may contain internal URLs, user data, or secrets.

## Release status

- License: MIT.
- Distribution: GitHub source release.
- Current release notes: [`docs/PUBLIC_RELEASE_NOTES_v0.1.0.md`](docs/PUBLIC_RELEASE_NOTES_v0.1.0.md).

## Docs

- [`docs/PUBLIC_RELEASE_NOTES_v0.1.0.md`](docs/PUBLIC_RELEASE_NOTES_v0.1.0.md) — release notes.
- [`SECURITY.md`](SECURITY.md) — privacy/sensitive-log notes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution boundaries.

## Roadmap

- Parse Playwright trace zip metadata when available.
- Add configurable custom rules.
- Group duplicate failures across retries/workers.
- Emit GitHub Actions step summary markdown.
- Add sample remediation PR checklist.
