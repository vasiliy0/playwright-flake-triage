# Before / after examples

## Before: raw CI retry noise

Two retries for the same flaky selector can look different because CI adds paths,
ports, worker ids, retry ids, timestamps, screenshots, and durations:

```text
settings.spec.ts:47:13 worker-1 retry-1 duration 30124ms http://localhost:4173/settings
settings.spec.ts:93:21 worker-4 retry-2 duration 29876ms http://localhost:5173/settings
```

## After: stable duplicate group

`pw-flake-triage` normalizes dynamic values before grouping duplicate failures, so
both retries land in the same repeated failure group:

```markdown
## Repeated failure groups
- **Ambiguous or brittle selector**: 2 findings
  - Tests: dynamic-ci-retry-1.log, dynamic-ci-retry-2.log
```

Run it locally:

```bash
pw-flake-triage examples/dynamic-ci-retry-1.log examples/dynamic-ci-retry-2.log --format markdown
```

## Recommended adoption path

1. Run in report-only mode with `--github-step-summary`.
2. Upload JSON as an artifact for trend review.
3. Add `--fail-on-severity high` only after the team agrees on the signal/noise tradeoff.
