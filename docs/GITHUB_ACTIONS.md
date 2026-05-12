# GitHub Actions usage

Use `playwright-flake-triage` in CI to keep a readable Markdown summary in the job page and a machine-readable JSON report as an artifact.

## Minimal workflow step

```yaml
- name: Triage Playwright failures
  if: always()
  run: |
    python -m pip install playwright-flake-triage
    pw-flake-triage test-results ci.log --github-step-summary
```

`--github-step-summary` appends Markdown to `$GITHUB_STEP_SUMMARY`, which GitHub renders on the workflow run page.

## Recommended workflow with JSON artifact

```yaml
name: playwright-triage

on:
  workflow_dispatch:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # Run your normal app/test setup before this step.
      # Keep this example focused on triage output.

      - name: Install Playwright flake triage
        if: always()
        run: python -m pip install playwright-flake-triage

      - name: Triage Playwright reports and logs
        if: always()
        run: |
          pw-flake-triage \
            test-results \
            playwright-report \
            ci.log \
            --format json \
            --output triage-report.json \
            --github-step-summary

      - name: Upload triage JSON artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-flake-triage-report
          path: triage-report.json
          if-no-files-found: ignore
```

## Optional CI gate mode

By default, `pw-flake-triage` is report-only and exits `0` when findings exist. Add a gate flag if a workflow should fail after the report is written.

Fail only on high-severity findings:

```yaml
- name: Triage Playwright reports and fail on high severity
  if: always()
  run: |
    pw-flake-triage \
      test-results \
      ci.log \
      --format json \
      --output triage-report.json \
      --github-step-summary \
      --fail-on-severity high
```

Fail on any finding:

```yaml
- name: Triage Playwright reports and fail on any finding
  if: always()
  run: |
    pw-flake-triage test-results ci.log --github-step-summary --fail-on-findings
```

The report is written before the command exits `1`, so use `if: always()` on artifact upload steps if you need the JSON report after a gate failure.

## Add repo-specific custom rules

Create a local config such as `.github/pw-flake-rules.json`:

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

Then pass it to the CLI:

```yaml
- name: Triage Playwright reports and logs
  if: always()
  run: |
    pw-flake-triage \
      test-results \
      ci.log \
      --rules-config .github/pw-flake-rules.json \
      --format json \
      --output triage-report.json \
      --github-step-summary
```

## Privacy and safety notes

- The CLI runs locally in the job.
- It does not upload logs or call external services.
- It is read-only: it does not mutate Playwright reports, logs, or project files.
- Treat generated artifacts as sensitive if your logs contain internal URLs, user data, credentials, or tokens.
- Prefer uploading artifacts only on private repos or with retention/settings appropriate for your CI policy.
