import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from compile_pdf import (
    compile_latex_to_pdf,
    compiler_available,
    normalize_to_dhruv_template,
    sanitize_latex_for_overleaf,
    sanitize_unicode_for_latex,
)
from prompts import build_system_prompt

# .env는 api/ 우선, 없으면 레포 루트 (cwd와 무관)
_API_DIR = Path(__file__).resolve().parent
load_dotenv(_API_DIR / ".env")
if not (os.environ.get("OPENAI_API_KEY") or "").strip():
    load_dotenv(_API_DIR.parent / ".env", override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # env는 위에서 load_dotenv로만 주입 (cwd/이중 로드 이슈 방지)
    model_config = SettingsConfigDict(extra="ignore")

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def strip_api_key(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


settings = Settings()
if not settings.openai_api_key:
    logger.warning(
        "OPENAI_API_KEY is empty. Add it to %s or %s then restart the API.",
        _API_DIR / ".env",
        _API_DIR.parent / ".env",
    )
else:
    logger.info("OpenAI API key loaded (%d chars). Model: %s", len(settings.openai_api_key), settings.openai_model)
app = FastAPI(title="SimpleResume API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip() or "(empty PDF text)"


def extract_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf_text(data)
    if lower.endswith(".tex"):
        return data.decode("utf-8", errors="replace")
    return data.decode("utf-8", errors="replace")


class PreviewSection(BaseModel):
    kind: str
    title: str
    subtitle: str | None = None
    bullets: list[str] = Field(default_factory=list)


class CoachingItem(BaseModel):
    why_better: str


class CoachingSection(BaseModel):
    section_why: str
    items: list[CoachingItem]


class GenerateResponse(BaseModel):
    latex_document: str
    preview_sections: list[PreviewSection]
    coaching: list[CoachingSection]


def repair_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


@app.get("/health")
def health():
    comp = compiler_available()
    return {
        "ok": True,
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model if settings.openai_api_key else None,
        "env_hint": str(_API_DIR / ".env"),
        "pdf_compile": comp["pdflatex"] or comp["tectonic"],
        "compiler": comp,
    }


def _run_generate(raw: str) -> GenerateResponse:
    if len(raw) > 120_000:
        raw = raw[:120_000] + "\n\n[truncated]"

    client = OpenAI(api_key=settings.openai_api_key)
    system = build_system_prompt()
    user_msg = f"--- RESUME SOURCE ---\n\n{raw}"

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.35,
            max_tokens=16_384,
        )
    except Exception as e:
        logger.exception("OpenAI error")
        raise HTTPException(status_code=502, detail=str(e)) from e

    content = completion.choices[0].message.content or "{}"
    try:
        data = repair_json(content)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s", content[:500])
        raise HTTPException(
            status_code=502,
            detail="Model returned invalid JSON. Retry or shorten input.",
        ) from e

    latex = data.get("latex_document") or data.get("latex") or ""
    if not latex or "\\documentclass" not in latex:
        raise HTTPException(
            status_code=502,
            detail="Model did not return a valid latex_document.",
        )
    latex = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(latex))
    )

    preview_raw = data.get("preview_sections") or []
    coaching_raw = data.get("coaching") or []

    preview_sections: list[PreviewSection] = []
    for p in preview_raw:
        if isinstance(p, dict):
            preview_sections.append(
                PreviewSection(
                    kind=str(p.get("kind", "experience")),
                    title=str(p.get("title", "")),
                    subtitle=p.get("subtitle"),
                    bullets=list(p.get("bullets") or []),
                )
            )

    coaching: list[CoachingSection] = []
    for c in coaching_raw:
        if isinstance(c, dict):
            items = []
            for it in c.get("items") or []:
                if isinstance(it, dict):
                    items.append(CoachingItem(why_better=str(it.get("why_better", ""))))
                else:
                    items.append(CoachingItem(why_better=str(it)))
            coaching.append(
                CoachingSection(
                    section_why=str(c.get("section_why", "")),
                    items=items,
                )
            )

    # Pad coaching to match preview if model miscounted
    while len(coaching) < len(preview_sections):
        coaching.append(
            CoachingSection(section_why="", items=[])
        )
    for i, prev in enumerate(preview_sections):
        while len(coaching[i].items) < len(prev.bullets):
            coaching[i].items.append(CoachingItem(why_better=""))
        coaching[i].items = coaching[i].items[: len(prev.bullets)]

    return GenerateResponse(
        latex_document=latex,
        preview_sections=preview_sections,
        coaching=coaching,
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Copy api/.env.example to api/.env.",
        )

    raw = ""
    if file and file.filename:
        data = await file.read()
        if len(data) > 12 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 12MB)")
        raw = extract_text(file.filename, data)
    elif text and text.strip():
        raw = text.strip()
    else:
        raise HTTPException(
            status_code=400,
            detail="Upload a .pdf, .txt, or .tex file, or paste resume text.",
        )

    return _run_generate(raw)


class GenerateJsonBody(BaseModel):
    text: str


@app.post("/generate-json", response_model=GenerateResponse)
def generate_json_body(body: GenerateJsonBody):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text required")
    return _run_generate(body.text.strip())


class CompilePdfBody(BaseModel):
    latex_document: str


@app.post("/compile-pdf")
def compile_pdf_endpoint(body: CompilePdfBody):
    """Real LaTeX → PDF (Overleaf-style preview). Requires pdflatex or tectonic on server."""
    tex = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(body.latex_document.strip()))
    )
    pdf, err_detail = compile_latex_to_pdf(tex)
    if pdf:
        return Response(content=pdf, media_type="application/pdf")
    raise HTTPException(status_code=422, detail=err_detail or {"code": "COMPILE_FAILED", "message": "Compile failed"})
