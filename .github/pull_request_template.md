## Title

[Feature] Short description

## Checklist

- [ ] Core paths untouched (see `.github/core-protected-paths.txt`) — or label `allow-core-change` applied with justification
- [ ] Feature flag implemented / documented (default `false`) if user-visible behavior added
- [ ] Backward-compatible API (additive optional fields only)
- [ ] Unit or integration tests added where applicable
- [ ] No unintended JSON schema / response shape break (see `schemas/`)
- [ ] Rollback documented (env flag or revert path)

## Description

- What was added
- Why it is safe for existing users
- How to roll back (e.g. set `FEATURE_*=false`)

## Notes

- PDF pipeline + LaTeX generator may share code paths; if both change, describe each concern in the PR body.
