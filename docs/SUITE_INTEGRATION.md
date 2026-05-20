# Suite integration: Playwright Flake Triage Toolkit

Role in Engineering Risk Preflight suite: test reliability and CI flake diagnosis.

## Standalone value

Use this tool when frontend/QA/platform teams need to summarize Playwright failures from CI logs, JUnit XML, or Playwright JSON before opening traces manually.

## Relationship to repo-hygiene-ci-risk-preflight

- Repo Hygiene identifies CI/repo process risks.
- Playwright Flake Triage analyzes concrete test failure evidence.
- Future combined reports can include this as the `test-reliability-risk` section.

## Alignment targets

- Preserve Playwright-specific depth; do not turn it into a generic repo scanner.
- Align report field names and severity language where practical.
- Keep local/no-secret processing as default.

## Local next improvements

- Add more CI log/JUnit/JSON regression fixtures.
- Improve duplicate/flaky grouping docs.
- Add a short machine-readable summary for suite aggregation.
- Prepare local release notes for next v0.1.x; publish/outreach only with approval.
