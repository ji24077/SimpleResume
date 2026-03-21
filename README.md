# SimpleResume

Upload a resume (PDF / .tex / text) → **Dhruv-style SWE LaTeX** + **preview** + **per-section coaching** (why it’s stronger) → download `.tex` and coaching `.md`.

Stack: **Next.js** (UI + API proxy) · **FastAPI** · **OpenAI API**

## Prerequisites

- Node 20+
- Python 3.11+
- OpenAI API key

## Setup

### 1. API

```bash
cd api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-...  (must live in api/.env — loaded from api folder path, not cwd)
# Check: curl http://127.0.0.1:8000/health  → openai_configured: true
```

### 2. Web

```bash
cd web
npm install
cp .env.example .env.local
# Default API_BACKEND_URL=http://127.0.0.1:8000
```

## How to run (daily workflow)

**Prerequisites each time:** Docker Desktop running (for PDF preview), if you use `LATEX_DOCKER_IMAGE` in `api/.env`.

1. **Build the TeX image once** (or after Dockerfile changes), from repo root:
   ```bash
   docker compose build texlive
   ```
2. **Terminal 1 — FastAPI**
   ```bash
   cd api && source .venv/bin/activate
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   On startup, check logs for `PDF compile env:` — `LATEX_DOCKER_IMAGE` should match your image (e.g. `simpleresume-texlive:full`).
3. **Terminal 2 — Next.js**
   ```bash
   cd web && npm run dev
   ```
4. Open **[http://localhost:3000](http://localhost:3000)** — **Generate** or paste LaTeX, then **Compile** for PDF preview.

**First-time setup:** complete [Setup](#setup) above and copy `api/.env.example` → `api/.env` (add `OPENAI_API_KEY` and optional LaTeX Docker vars). Never commit `api/.env`.

**Without Docker:** omit `LATEX_DOCKER_IMAGE` or set `LATEX_DOCKER_ALLOW_FALLBACK=1` and use a full local TeX (MacTeX / TeX Live + `latexmk`); TinyTeX may miss packages (e.g. `fullpage`).

## Flow

1. Upload PDF / .tex / .txt or paste text  
2. **Generate** (30–90s typical)  
3. Tabs: **Preview** · **Coaching** · **LaTeX**  
4. **Download .tex** · **Download coaching (.md)**

**PDF preview (Overleaf-style):** Goal: **same TeX Live + `latexmk` as Overleaf**, not the user’s local TinyTeX.

1. **Docker image** (`docker/texlive-full/Dockerfile`): `FROM texlive/texlive:latest` + `latexmk`, `WORKDIR /work`.
2. **API** runs `docker run … latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -pdflatex='pdflatex … -no-shell-escape …' resume.tex` (default **`--network=none`**; override with `LATEX_DOCKER_NETWORK=bridge` if needed).
3. **Temp project dir**: `api/tex_assets/*` copied next to `resume.tex` (multi-file projects).

```bash
# From repo root (pull/build can be large)
docker compose build texlive

cd api && source .venv/bin/activate
# Prefer api/.env (loaded on startup) so uvicorn always sees Docker settings:
#   LATEX_DOCKER_IMAGE=simpleresume-texlive:full
#   LATEX_DOCKER_ONLY=1
# With LATEX_DOCKER_IMAGE set, host TinyTeX is NOT used unless LATEX_DOCKER_ALLOW_FALLBACK=1.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Endpoints**

| Method | Path | Body | Behavior |
|--------|------|------|----------|
| `POST` | `/compile-pdf` | `{ "latex_document": "..." }` | Dhruv template normalization + compile |
| `POST` | `/compile` | `{ "tex": "..." }` | Raw full `.tex` (Overleaf-style), no normalization |

**Engine order** (if `LATEX_DOCKER_ONLY` is not set): Docker **`latexmk`** → host **`latexmk`** → **`tectonic`** → **`pdflatex`**.

**Health:** `GET /health` → `compiler.latex_docker_ready`, `latex_docker_only`, `pdf_compile`.

**Web:** Preview uses **pdf.js** (`react-pdf`); Next proxies `/api/compile-pdf` and `/api/compile`.

**Not implemented yet:** S3 + presigned URLs, zip project upload, queue, full LaTeX sandbox beyond `-no-shell-escape` + Docker network isolation.

## Env

| Variable | Where | Purpose |
|----------|--------|---------|
| `OPENAI_API_KEY` | `api/.env` | OpenAI (required) |
| `OPENAI_MODEL` | `api/.env` | Default `gpt-4o`; optional `gpt-4o-mini` |
| `API_BACKEND_URL` | `web/.env.local` | FastAPI URL for proxy |
| `LATEX_DOCKER_IMAGE` | `api/.env` or shell | e.g. `simpleresume-texlive:full` |
| `LATEX_DOCKER_ONLY` | optional | `1` = compile **only** inside Docker (no host TinyTeX) |
| `LATEX_DOCKER_ALLOW_FALLBACK` | optional | `1` = if Docker fails or CLI missing, use host `latexmk`/TinyTeX (default: **off** when image is set) |
| `LATEX_DOCKER_NETWORK` | optional | default `none`; use `bridge` if the engine must reach the network |

---

I spent a year learning what actually works in hiring. After Tesla + NVIDIA, I helped 30+ candidates and ~13 landed offers. This repo automates that guidance.
