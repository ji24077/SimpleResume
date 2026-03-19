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

## Run (two terminals)

**Terminal A — API**

```bash
cd api && source .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal B — Web**

```bash
cd web && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Flow

1. Upload PDF / .tex / .txt or paste text  
2. **Generate** (30–90s typical)  
3. Tabs: **Preview** · **Coaching** · **LaTeX**  
4. **Download .tex** · **Download coaching (.md)**

**PDF preview (Overleaf-style):** The API runs `pdflatex` (or `tectonic`) on your machine. Install TeX, then restart the API:

- **macOS:** MacTeX, or `brew install --cask basictex` then `sudo tlmgr install collection-latexextra`
- **Linux:** `sudo apt install texlive-latex-extra` (or full `texlive-full`)

Check `GET http://127.0.0.1:8000/health` → `"pdf_compile": true`. If `false`, Preview shows the error + you can still download `.tex` for Overleaf.

## Env

| Variable | Where | Purpose |
|----------|--------|---------|
| `OPENAI_API_KEY` | `api/.env` | OpenAI (required) |
| `OPENAI_MODEL` | `api/.env` | Default `gpt-4o`; optional `gpt-4o-mini` |
| `API_BACKEND_URL` | `web/.env.local` | FastAPI URL for proxy |

---

I spent a year learning what actually works in hiring. After Tesla + NVIDIA, I helped 30+ candidates and ~13 landed offers. This repo automates that guidance.
