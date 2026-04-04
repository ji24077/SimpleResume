# Golden / regression tests

## Layout

- `fixtures/` — frozen inputs (e.g. `minimal_resume_data.json`).
- `expected/` — expected hashes or snapshots (e.g. `structured_minimal_document_body.sha256`).
- `test_regression_*.py` — pytest modules run via `pytest tests/golden` in CI.

## Policy

If a golden assertion fails after a **deliberate** change to preamble or deterministic body rendering, update the matching file under `expected/` in the **same PR** and note the reason in the PR description.
