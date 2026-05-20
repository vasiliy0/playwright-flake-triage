# AI agent and CI integration

This CLI is safe for agent workflows that need a first-pass summary of flaky Playwright failures before proposing fixes.

## When an agent should run it

Run `pw-flake-triage` after Playwright tests have produced JSON/JUnit reports, trace-adjacent logs, or CI logs. Use it to group likely failure causes; do not treat the output as proven root cause.

## Safe commands

```bash
pw-flake-triage ./test-results ./ci.log --format json --output triage-report.json --quiet --no-color
pw-flake-triage ./test-results ./ci.log --format markdown --github-step-summary
pw-flake-triage ./test-results ./ci.log --fail-on-severity high
```

## Machine contract

- JSON schema: `schemas/report.schema.json`.
- `schema_version`: `1.0`.
- Findings include `file`, `test`, `signal`, `category`, `severity`, `confidence`, `why`, `fixes`, and `fingerprint`.
- Duplicate retry groups are exposed as `duplicate_groups`.

## Exit codes

- `0`: scan completed; report-only mode or no configured gate was tripped.
- `1`: scan completed and `--fail-on-findings` or `--fail-on-severity` matched.
- `2`: usage, config, filter, or GitHub step summary environment error.
- `3`: reserved for future runtime/tool errors.

## Agent loop

1. Collect Playwright JSON/JUnit/log artifacts locally.
2. Run JSON mode and parse `findings` plus `duplicate_groups`.
3. Summarize the top recurring high-confidence categories.
4. Propose a patch plan; ask before editing or pushing.
5. After approved edits, rerun and compare `fingerprint` values.

## Safety

The tool reads local files only. It makes no network calls and uploads nothing. Generated reports may contain snippets from logs, including internal URLs, user data, or secrets; review before sharing.
