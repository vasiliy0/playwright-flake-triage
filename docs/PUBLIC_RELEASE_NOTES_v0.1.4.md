# Playwright Flake Triage v0.1.4

Patch release with additional local triage controls.

## Added

- `--min-confidence` to include only findings at or above a chosen confidence threshold.
- `--category` filter, repeatable, to include only findings whose category contains matching text.
- Regression coverage for filter behavior and invalid confidence values.

## Included from recent development

- Navigation/frame detachment triage category and fixture.

## Safety posture

- Local-only, read-only scanner.
- No external service calls.
- No credentials or tokens required.
- Filters affect report output and CI gates only; they do not modify input artifacts.
