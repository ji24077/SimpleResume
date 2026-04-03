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

**PDF requires Docker:** there is no host TeX fallback. Use `docker compose build texlive` and keep `LATEX_DOCKER_IMAGE=simpleresume-texlive:full` in `api/.env`.

## Flow

1. Upload PDF / .tex / .txt or paste text  
2. **Generate** (30–90s typical)  
3. Tabs: **Preview** · **Coaching** · **LaTeX**  
4. **Download .tex** · **Download coaching (.md)**

**PDF preview:** The API compiles **only** inside **Docker** (`latexmk` in the `simpleresume-texlive:full` image). Without Docker / image / `docker` CLI, PDF compile fails until `compiler.latex_docker_ready` is true.

Check `GET http://127.0.0.1:8000/health` → `pdf_compile`, `compiler.latex_docker_ready`.

## Docs (구현·엣지케이스)

- **[docs/ENGINEERING_NOTES.md](docs/ENGINEERING_NOTES.md)** — 지금까지 구현된 동작, 엣지케이스, 건드리면 안 되는 연관(프롬프트·sanitize·스트림 등).  
- **[api/OPS_CHECKLIST.md](api/OPS_CHECKLIST.md)** — 운영 시 Poppler/Pillow·밀도 루프 확인용 체크리스트.

## Env

| Variable | Where | Purpose |
|----------|--------|---------|
| `OPENAI_API_KEY` | `api/.env` | OpenAI (required) |
| `OPENAI_MODEL` | `api/.env` | Default `gpt-4o`; optional `gpt-4o-mini` |
| `API_BACKEND_URL` | `web/.env.local` | FastAPI URL for proxy |
| `LATEX_DOCKER_IMAGE` | `api/.env` | Required for PDF: `simpleresume-texlive:full` (after `docker compose build texlive`) |
| `LATEX_DOCKER_NETWORK` | `api/.env` | Default `none`; `bridge` if packages must fetch at compile time |
| `LATEX_PORTABLE_PREAMBLE` | `api/.env` | Optional `1` — preamble retry variant inside Docker |

---

I spent a year learning what actually works in hiring. After Tesla + NVIDIA, I helped 30+ candidates and ~13 landed offers. This repo automates that guidance.
