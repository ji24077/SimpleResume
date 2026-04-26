# AI-Safe Development Governance (SimpleResume)

Rules — for both AI and humans — for adding features **without breaking existing behavior**.

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-stable |
| `dev` | (Optional) integration branch |
| `feature/*` | New features — **one branch and one PR per feature, recommended** |

For our standard branch names and roles (PDF / first- vs second-pass generation / error recovery, etc.), see **[`docs/FEATURE_BRANCHES.md`](./FEATURE_BRANCHES.md)**.

### PDF rendering + LaTeX generator (the realistic take)

Docker TeX compilation and LLM LaTeX generation **share many of the same implementation paths** (`api/features/pdf_rendering/`, `api/features/generation/`). Splitting them cleanly into **completely separate branches** can be hard, so:

- Allow them to **share a branch / PR** when needed,
- But in the PR / commit description, **separate** “PDF pipeline” vs “prompts / generation logic”,
- And where possible design changes so they can be **toggled with a feature flag**.

## Protected paths (Core)

The files below should not be changed except as **intentional maintenance**.
If a PR touches anything in this list, the [Core protection](../.github/workflows/core-protection.yml) workflow will fail.
**Exception:** if the PR carries the `allow-core-change` label, that check is skipped (maintainers only).

Source of truth: [`.github/core-protected-paths.txt`](../.github/core-protected-paths.txt)

Currently includes, for example:

- `api/features/pdf_rendering/compile_pdf.py` — Docker / latexmk, sanitize, compile loop
- `api/features/pdf_rendering/dhruv_preamble.tex` — Dhruv template body

The team can **add** lines to `.github/core-protected-paths.txt` to widen the protected set. (Removing lines should be done carefully.)

## Extension architecture

Where possible, isolate new features under **`extensions/`**.

- **Core / protected paths** must **not depend on** `extensions`.
- **Extensions** may **import** existing API / compile / utility code.
- Allowed dependency direction: `extensions → (existing modules)` only. The reverse is forbidden.

For details: [`extensions/README.md`](../extensions/README.md).

## Feature flags

Put new features behind an env-var flag that **defaults to `false`**. Examples:

- `FEATURE_PDF_ANNOTATIONS=false`
- `FEATURE_ADVANCED_DIAGNOSTICS=false`

See `api/.env` / `api/.env.example`. It must be possible to roll back simply by turning the flag off.

## API contracts

Avoid **renaming, retyping, or removing** existing fields in JSON responses; only **adding optional fields** is allowed.
Reference schema draft: [`schemas/generate_response_v1.json`](../schemas/generate_response_v1.json) (agree on a versioning strategy if you need to extend it).

## Recommended prompt header for AI requests

```
------------------------------------------------------------
DO NOT MODIFY existing core logic (see .github/core-protected-paths.txt).
DO NOT refactor unrelated files.
DO NOT change public API contracts except additive optional fields.
Only ADD new files or optional fields. Preserve backward compatibility.
------------------------------------------------------------
```

If a core change is genuinely required, **don’t patch the code directly** — propose it as a design issue.

## Golden / regression

Sample inputs and expected hashes live under `tests/golden/` and are validated in **GitHub Actions** (`.github/workflows/ci.yml`) via `pytest tests/golden`.
For the policy, see [tests/golden/README.md](../tests/golden/README.md).

## PRs

- Aim for diffs **under 500 lines** when feasible.
- Checklist: [`.github/pull_request_template.md`](../.github/pull_request_template.md)
- CI: `pytest tests/unit`, `tests/integration`, `tests/golden` (`.github/workflows/ci.yml`).

## Monitoring

For users / traffic where a flag is on, watch failure rate and latency, and **flip the flag off** immediately if anything goes wrong.

---

**Principle:** change Core only when unavoidable; isolate new features as **additive + flagged + extensions**.
