# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### First-time setup
```bash
make setup          # uv sync --dev + npm install + docker build (all-in-one)
```

### Backend (FastAPI)
```bash
cd api && uv sync --dev
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Next.js)
```bash
cd web && npm install
npm run dev        # dev server with Turbopack
npm run build
npm run lint       # ESLint
```

### Docker (required for PDF compilation)
```bash
docker compose build texlive
```

### Tests
```bash
cd api && uv run pytest ../tests/unit                           # fast, no Docker or LLM
cd api && uv run pytest ../tests/integration                    # API schema/contract tests
cd api && uv run pytest ../tests/golden                         # frozen-fixture regression tests
cd api && uv run pytest ../tests                                # all

# Single test file or test case:
cd api && uv run pytest ../tests/unit/test_latex_sanitize.py
cd api && uv run pytest ../tests/unit/test_latex_sanitize.py -k "test_name"

# Or from repo root via Makefile:
make test-unit
make test
```

`pytest.ini` sets `pythonpath=api` so imports resolve without installing the package.

---

## Governance rules

- **Never edit `api/.env` or `web/.env.local`** — these are user-owned secrets files.
- **Never modify core-protected files** (`compile_pdf.py`, `dhruv_preamble.tex`) without an explicit user request and the `allow-core-change` CI label on the PR.
- **New user-facing behavior** must be gated by a `FEATURE_*` env var (default `false`) and live under `extensions/`.
- **Core must not import from `extensions/`** — dependency is one-way only.
- **Prefer `feature/*` branches** for new work.
- **`GenerateResponse` is additive-only** — never remove, rename, or change the type of existing fields; only add new optional ones.
- **Smallest diff wins** — avoid whole-file rewrites when editing existing modules.

---

## Architecture

SimpleResume is an AI-powered resume optimizer: users upload a PDF/`.tex`/text resume, the system rewrites it into a "Dhruv-style" LaTeX document, enforces one-page fit, and returns a downloadable PDF + coaching notes.

### Stack
- **Backend:** FastAPI + Uvicorn (Python 3.11+), managed by **uv** (`api/pyproject.toml`)
- **Frontend:** Next.js 15.5, React 19.1, TypeScript, Tailwind CSS 4
- **LLM:** OpenAI API (`gpt-4o` default, configurable via `OPENAI_MODEL`)
- **PDF Compilation:** Docker + TeX Live Full + `latexmk` — **no host-side TeX fallback**
- **PDF Extraction:** Poppler (`pdftotext`, `pdftoppm`) + pypdf + Pillow
- **Task runner:** `Makefile` at repo root (`make help` for all targets)

### Module layout

Real code lives under `api/resume_service/` and `api/features/`. Backward-compat shims in `api/routers/*.py`, `api/main.py`, `api/compile_pdf.py`, `api/prompts.py`, `api/structured_resume.py` are one-liner re-exports — do not add logic to shims.

### Request Pipeline (happy path)
```
User input (text / PDF upload)
  → Text extraction + contact-field injection
  → LLM generation (system prompt + dhruv_preamble.tex template)
  → JSON parsing + LaTeX sanitization
  → Docker compile (latexmk)
  → 1-page enforcement loop (re-prompt up to RESUME_ONE_PAGE_MAX_REVISIONS)
  → Density check loop (re-prompt if bottom whitespace > threshold, up to RESUME_DENSITY_EXPAND_MAX)
  → ATS smoke-test + auto-fix loop (up to RESUME_ATS_FIX_MAX)
  → Quality checker (optional diagnostic pass, no rewrite)
  → Streaming NDJSON response to client
```

### Key Files
| Path | Role |
|------|------|
| `api/resume_service/app.py` | FastAPI factory, CORS, router includes |
| `api/resume_service/config.py` | Settings class, env loading, startup diagnostics |
| `api/resume_service/routers/health.py` | GET /health |
| `api/resume_service/routers/compile.py` | POST /compile, /compile-pdf |
| `api/resume_service/routers/resume.py` | POST /generate, /generate-stream, /generate-json-stream + pipeline |
| `api/resume_service/routers/_helpers.py` | Shared models (GenerateResponse, etc.), coerce/repair helpers |
| `api/features/generation/prompts.py` | All LLM system/user prompts (generator, fixer, densify, ATS checker) |
| `api/features/generation/structured_resume.py` | Optional Pydantic schema + LaTeX builder (`RESUME_STRUCTURED_LATEX=true`) |
| `api/features/pdf_rendering/compile_pdf.py` | Docker compile, LaTeX sanitization, page count, density measurement |
| `api/features/pdf_rendering/dhruv_preamble.tex` | Canonical LaTeX template — **must stay in sync with `prompts.py`** |
| `api/features/resume_pipeline/orchestrator.py` | `run_machine_gate()`: lint → compile → pages → ATS (deterministic, no LLM) |
| `api/features/resume_pipeline/pipeline/` | Per-gate modules: `lint`, `compile`, `pdf_checks`, `ats_check`, `fixer_llm`, `checker_llm` |
| `web/src/app/page.tsx` | Main upload + generation UI |
| `web/src/app/latex/page.tsx` | LaTeX-only compile interface |
| `web/src/app/api/generate-stream/route.ts` | Streaming proxy to backend |
| `web/src/lib/types.ts` | `GenerateResponse` TypeScript type |

### Non-obvious design decisions

**Dhruv preamble sync** — `dhruv_preamble.tex` and the `=== TEMPLATE ===` block inside `prompts.py` must be identical. If they drift, the LLM generates macros that don't compile. Both are core-protected by CI.

**Docker-only PDF** — `compile_pdf.py` runs `latexmk` inside the `simpleresume-texlive:full` container. There is no host-path fallback. Any environment without Docker Desktop + `docker` CLI will get a graceful health-check failure, not a crash.

**Streaming protocol** — `/generate-stream` and `/generate-json-stream` return NDJSON. Each line is `{"type": "progress", "text": "..."}` or `{"type": "result", "data": {...}}`. Only the `result` event carries the final payload.

**Structured mode** — When `RESUME_STRUCTURED_LATEX=true`, the LLM returns a `resume_data` JSON object (Pydantic-validated) and the server builds LaTeX deterministically, avoiding malformed LLM LaTeX. The server heals bad JSON up to `RESUME_SCHEMA_HEAL_MAX` retries.

**LaTeX sanitization** — The sanitizer in `compile_pdf.py` fixes double-backslashes, empty `\href{}{}`, missing backslashes on macros, unmatched `\begin{center}`, and ensures `\resumeProjectHeading` is wrapped in `\resumeSubHeadingListStart`…`\resumeSubHeadingListEnd`. This logic is delicate — do not modify without running the full unit test suite.

**Extension architecture** — New optional features go under `extensions/` with `FEATURE_*` env-var gates. Core must not import extensions (one-way dependency enforced by convention).

### Core-protected paths (CI blocks PRs without `allow-core-change` label)
- `api/features/pdf_rendering/compile_pdf.py`
- `api/features/pdf_rendering/dhruv_preamble.tex`

### Environment variables (key ones)
| Var | Default | Effect |
|-----|---------|--------|
| `OPENAI_API_KEY` | — | Required |
| `OPENAI_MODEL` | `gpt-4o` | LLM model |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed origins |
| `LATEX_DOCKER_IMAGE` | `simpleresume-texlive:full` | PDF compile container |
| `LATEX_DOCKER_NETWORK` | `none` | Docker network mode |
| `LATEX_PORTABLE_PREAMBLE` | `0` | Strip `fullpage`/`glyphtounicode` for Docker retry |
| `RESUME_ONE_PAGE_MAX_REVISIONS` | `3` | Max 1-page re-prompt loops (0 = off) |
| `RESUME_DENSITY_EXPAND_MAX` | `2` | Max densify loops |
| `RESUME_UNDERFULL_BOTTOM_FRAC` | `0.15` | Bottom whitespace fraction threshold (8%–45%) |
| `RESUME_ATS_FIX_MAX` | `2` | Max ATS auto-fix loops (0 = off) |
| `RESUME_QUALITY_CHECKER` | `false` | Enable optional diagnostic checker pass |
| `RESUME_STRUCTURED_LATEX` | `false` | Use Pydantic-schema LaTeX builder |
| `RESUME_SCHEMA_HEAL_MAX` | `2` | Max schema self-heal retries (0–8) |
| `API_BACKEND_URL` | `http://127.0.0.1:8000` | Backend URL for frontend proxy (`web/.env.local`) |

API loads from `api/.env` first, then falls back to repo-root `.env`. Frontend uses `web/.env.local`.
