# SimpleResume

Upload a resume (PDF / .tex / text) → **Dhruv-style SWE LaTeX** + **preview** + **per-section coaching** (why it’s stronger) → download `.tex` and coaching `.md`.

Stack: **Next.js** (UI + API proxy) · **FastAPI** · **OpenAI API**

## Prerequisites

- Node 20+
- Python 3.11+
- OpenAI API key
- **Docker Desktop** (PDF 미리보기 — Overleaf와 같은 TeX Live full + `latexmk`; 기본 설정이 Docker 전용)

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

## Run (two terminals)

**Once — TeX Docker image (Overleaf-grade compile)**

```bash
# repo root
docker compose build texlive
```

**Terminal A — API**

```bash
cd api && source .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Startup logs should show `LATEX_DOCKER_IMAGE='simpleresume-texlive:full'` and Docker CLI `yes`. Check `GET http://127.0.0.1:8000/health` → `compiler.latex_docker_ready: true`.

**Terminal B — Web**

```bash
cd web && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). LaTeX-only compile: [http://localhost:3000/latex](http://localhost:3000/latex).

**Without Docker:** in `api/.env` set `LATEX_DOCKER_IMAGE=` (empty), `LATEX_DOCKER_ONLY=0`, `LATEX_DOCKER_ALLOW_FALLBACK=1`, then install full local TeX (not recommended — TinyTeX often misses `fullpage` etc.).

## Flow

1. Upload PDF / .tex / .txt or paste text  
2. **Generate** (30–90s typical)  
3. Tabs: **Preview** · **Coaching** · **LaTeX**  
4. **Download .tex** · **Download coaching (.md)**

**PDF preview:** By default the API compiles **only** inside **Docker** (`latexmk` in `texlive/texlive:latest` — same idea as Overleaf). No Docker → set env opt-out (see Run) or PDF compile stays unavailable until `latex_docker_ready` is true.

Check `GET http://127.0.0.1:8000/health` → `pdf_compile`, `compiler.latex_docker_ready`.

## Env

| Variable | Where | Purpose |
|----------|--------|---------|
| `OPENAI_API_KEY` | `api/.env` | OpenAI (required) |
| `OPENAI_MODEL` | `api/.env` | Default `gpt-4o`; optional `gpt-4o-mini` |
| `API_BACKEND_URL` | `web/.env.local` | FastAPI URL for proxy |
| `LATEX_DOCKER_IMAGE` | `api/.env` | Default `simpleresume-texlive:full`; empty = no Docker image |
| `LATEX_DOCKER_ONLY` | `api/.env` | Default `1` — host TinyTeX/MacTeX not used unless fallback |
| `LATEX_DOCKER_ALLOW_FALLBACK` | `api/.env` | `1` = if Docker fails, try host `latexmk` / `tectonic` |
| `LATEX_DOCKER_NETWORK` | `api/.env` | Default `none`; `bridge` if packages must fetch at compile time |

---

I spent a year learning what actually works in hiring. After Tesla + NVIDIA, I helped 30+ candidates and ~13 landed offers. This repo automates that guidance.
