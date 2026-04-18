"""POST /compile, POST /compile-pdf — LaTeX to PDF compilation."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from openai import OpenAI
from pydantic import BaseModel

from compile_pdf import (
    compile_latex_to_pdf,
    normalize_to_dhruv_template,
    sanitize_latex_for_overleaf,
    sanitize_unicode_for_latex,
)
from resume_service.config import settings
from resume_service.routers._helpers import attempt_llm_latex_compile_fix

logger = logging.getLogger(__name__)

router = APIRouter()


class CompilePdfBody(BaseModel):
    latex_document: str
    heal_with_llm: bool = True


class CompileTexBody(BaseModel):
    tex: str


@router.post("/compile-pdf")
def compile_pdf_endpoint(body: CompilePdfBody):
    tex = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(body.latex_document.strip()))
    )
    pdf, err_detail = compile_latex_to_pdf(tex)
    if pdf:
        return Response(content=pdf, media_type="application/pdf")

    if body.heal_with_llm and (settings.openai_api_key or "").strip():
        err_snippet = json.dumps(err_detail, ensure_ascii=False) if err_detail else ""
        client = OpenAI(api_key=settings.openai_api_key)
        for attempt in range(2):
            fixed, note = attempt_llm_latex_compile_fix(
                client, tex_for_prompt=tex, err_snippet=err_snippet
            )
            if note:
                logger.info(
                    "compile-pdf LLM heal attempt %s: %s", attempt + 1, note[:400]
                )
            if not fixed:
                break
            tex = fixed
            pdf, err_detail = compile_latex_to_pdf(tex)
            if pdf:
                return Response(content=pdf, media_type="application/pdf")
            err_snippet = json.dumps(err_detail, ensure_ascii=False) if err_detail else ""

    raise HTTPException(status_code=422, detail=err_detail or {"code": "COMPILE_FAILED", "message": "Compile failed"})


@router.post("/compile")
def compile_raw_tex_endpoint(body: CompileTexBody):
    raw = body.tex.strip()
    if not raw or "\\documentclass" not in raw:
        raise HTTPException(
            status_code=400,
            detail="tex must be a full document including \\documentclass{...}.",
        )
    tex = sanitize_latex_for_overleaf(sanitize_unicode_for_latex(raw))
    pdf, err_detail = compile_latex_to_pdf(tex)
    if pdf:
        return Response(content=pdf, media_type="application/pdf")
    raise HTTPException(status_code=422, detail=err_detail or {"code": "COMPILE_FAILED", "message": "Compile failed"})
