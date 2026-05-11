# Playwright Flake Triage Toolkit v0.1.0

Initial GitHub release of a local CLI for quickly triaging flaky Playwright test reports and CI logs.

## Included

- Markdown and JSON report output.
- Playwright JSON report scanning.
- JUnit XML scanning.
- Plain CI log scanning.
- Heuristic categories for:
  - waits/timeouts;
  - brittle selectors and strict-mode violations;
  - auth/session/page-state mismatches;
  - network/backend failures;
  - browser lifecycle races;
  - visual snapshot instability;
  - parallel/shared-state collisions.
- Synthetic examples and regression tests derived from public issue symptoms without copying long third-party issue text.
- Optional `Issue:` / `URL:` metadata headers for validation snippets.
- Public tests-only GitHub Actions workflow.

## Privacy

Runs locally and does not call external services. Review logs and generated reports before sharing because CI logs can contain sensitive data.

## Known limitations

- Heuristic triage only; not proof of root cause.
- Does not parse full Playwright trace zip contents yet.
- Custom rule configuration is not included in v0.1.0.
- Package registry publishing is deferred; GitHub source release only for now.
