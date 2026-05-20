# Playwright Flake Triage Toolkit v0.1.5 draft

Status: local draft, not published.

## Changes prepared locally

- Improved duplicate failure fingerprints by normalizing CI-specific noise: paths,
  line numbers, localhost ports, worker/retry ids, PIDs, hashes, timestamps, and durations.
- Added dynamic retry examples that demonstrate stable repeated failure grouping.
- Expanded docs with before/after output and a safer GitHub Actions adoption path.
- Kept the CLI local-only, read-only, and telemetry-free.

## Release checklist

- [x] Version bumped locally to `0.1.5`.
- [x] Unit tests cover duplicate normalization across dynamic CI values.
- [x] Docs updated locally.
- [ ] User approval for GitHub push.
- [ ] User approval for GitHub release/tag.
- [ ] User approval for TestPyPI/PyPI publish, if desired.
