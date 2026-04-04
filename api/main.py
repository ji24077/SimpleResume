import io
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Iterator, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from compile_pdf import (
    compile_latex_to_pdf,
    compiler_available,
    count_pdf_pages_from_bytes,
    normalize_to_dhruv_template,
    pdf_bottom_strip_mean_luminance,
    sanitize_latex_for_overleaf,
    sanitize_unicode_for_latex,
)
from prompts import (
    build_checker_user,
    build_generation_user_message,
    build_structured_generation_user_message,
    checker_system,
    densify_system,
    fixer_compile_system,
    fixer_system,
    generator_system,
    revision_user_densify,
    revision_user_densify_structured,
    revision_user_fix_ats,
    revision_user_fix_ats_structured,
    revision_user_fix_schema,
    revision_user_fix_compile,
    revision_user_fix_compile_structured,
    revision_user_one_page,
    revision_user_fit_one_page_structured,
    structured_densify_system,
    structured_fixer_compile_system,
    structured_fixer_system,
    structured_generator_system,
)
from structured_resume import (
    ResumeSchemaError,
    build_latex_document,
    format_resume_validation_errors,
    parse_resume_data,
)
from features.resume_pipeline.pipeline.ats_check import ats_smoke_test, should_autofix_ats

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

    # PDF = Docker TeX Live full + latexmk only (host latexmk/pdflatex/TinyTeX are not used).
    latex_docker_image: str = Field(default="simpleresume-texlive:full")
    latex_docker_network: str = "none"
    # 1 = strip fullpage + glyphtounicode for a portable preamble retry inside Docker (rare).
    latex_portable_preamble: bool = Field(default=False)

    # After generate: compile PDF and re-prompt if >1 page (0 = disable).
    resume_one_page_max_revisions: int = Field(default=3, ge=0, le=8)

    # When strict 1-page PDF still has a large bottom whitespace (measured via pdftoppm + Pillow),
    # ask the model to densify up to this many times (0 = skip density loop).
    resume_density_expand_max: int = Field(default=2, ge=0, le=6)
    # Sample mean luminance in this bottom fraction of page 1; bright strip ⇒ underfull (empty).
    # 0.15 ≈ “하단 15%가 거의 흰색이면 덜 찬 페이지”로 보는 실무 기본값.
    resume_underfull_bottom_frac: float = Field(default=0.15, ge=0.08, le=0.45)
    # Slightly below 237 so one-page PDFs with visible bottom whitespace trigger densify a bit more often.
    resume_underfull_mean_threshold: float = Field(default=233.0, ge=210.0, le=252.0)
    resume_underfull_dpi: int = Field(default=100, ge=72, le=150)
    # Optional: run scripts/measure_pdf_bottom_mean.py on your Overleaf "full 1 page" PDF, paste value here.
    # When set, underfull = measured_mean > golden_mean + golden_margin (absolute threshold ignored).
    resume_underfull_golden_mean: float | None = Field(default=None)
    resume_underfull_golden_margin: float = Field(default=12.0, ge=0.5, le=80.0)

    # After 1-page PDF succeeds: pdftotext/pypdf smoke test; auto-fix via LLM up to N times (0 = off).
    resume_ats_fix_max: int = Field(default=2, ge=0, le=4)
    # Optional post-pass: checker LLM returns issues JSON only (extra API cost).
    resume_quality_checker: bool = Field(default=False)

    # True: model returns resume_data + preview + coaching; server builds LaTeX deterministically.
    resume_structured_latex: bool = Field(default=False)
    # Structured mode: LLM retries after SCHEMA_ERROR (0 = fail immediately on invalid resume_data).
    resume_schema_heal_max: int = Field(default=2, ge=0, le=8)

    # Governance (docs/AI_GOVERNANCE.md): new features default off; wire in feature PRs.
    feature_pdf_annotations: bool = Field(default=False)
    feature_advanced_diagnostics: bool = Field(default=False)

    # env는 위에서 load_dotenv로만 주입 (cwd/이중 로드 이슈 방지)
    model_config = SettingsConfigDict(extra="ignore")

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def strip_api_key(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("latex_docker_image", mode="before")
    @classmethod
    def strip_docker_image(cls, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return v

settings = Settings()

# compile_pdf.py 는 os.environ 만 읽음 — Settings 와 동기화
if settings.latex_docker_image.strip():
    os.environ["LATEX_DOCKER_IMAGE"] = settings.latex_docker_image.strip()
else:
    os.environ.pop("LATEX_DOCKER_IMAGE", None)
if settings.latex_docker_network.strip():
    os.environ["LATEX_DOCKER_NETWORK"] = settings.latex_docker_network.strip()
os.environ.pop("LATEX_DOCKER_ONLY", None)
os.environ.pop("LATEX_DOCKER_ALLOW_FALLBACK", None)
if settings.latex_portable_preamble:
    os.environ["LATEX_PORTABLE_PREAMBLE"] = "1"
else:
    os.environ.pop("LATEX_PORTABLE_PREAMBLE", None)

if not settings.openai_api_key:
    logger.warning(
        "OPENAI_API_KEY is empty. Add it to %s or %s then restart the API.",
        _API_DIR / ".env",
        _API_DIR.parent / ".env",
    )
else:
    logger.info("OpenAI API key loaded (%d chars). Model: %s", len(settings.openai_api_key), settings.openai_model)

if settings.resume_structured_latex:
    logger.info(
        "RESUME_STRUCTURED_LATEX: model outputs resume_data only; LaTeX is server-rendered "
        "(schema self-heal max=%s).",
        settings.resume_schema_heal_max,
    )

_has_docker_cli = bool(shutil.which("docker"))
logger.info(
    "PDF compile: Docker-only | LATEX_DOCKER_IMAGE=%r | docker CLI=%s | LATEX_DOCKER_NETWORK=%r",
    settings.latex_docker_image or None,
    "yes" if _has_docker_cli else "NO (PDF will fail until Docker is available)",
    settings.latex_docker_network,
)
if settings.latex_docker_image.strip() and not _has_docker_cli:
    logger.warning(
        "LATEX_DOCKER_IMAGE is set but `docker` is not in PATH — PDF compile will fail. "
        "Start Docker Desktop and ensure `docker` is on PATH."
    )

_comp = compiler_available()
if settings.latex_docker_image.strip() and not _comp.get("latex_docker_ready"):
    logger.warning(
        "PDF requires Docker for %s. From repo root: docker compose build texlive — "
        "then start Docker Desktop and restart the API.",
        settings.latex_docker_image,
    )

app = FastAPI(title="SimpleResume API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    """Page count for one-page enforcement: pdfinfo / qpdf if available, else pypdf."""
    return count_pdf_pages_from_bytes(pdf_bytes)


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


PagePolicy = Literal["strict_one_page", "allow_multi"]


class GenerateResponse(BaseModel):
    latex_document: str
    preview_sections: list[PreviewSection]
    coaching: list[CoachingSection]
    pdf_page_count: int | None = None
    """Server-side page count after compile; None if compile was skipped or failed."""
    one_page_enforced: bool = False
    """True if multi-page output was detected and successfully revised to one page."""
    page_policy_applied: PagePolicy = "strict_one_page"
    revision_log: list[str] = Field(default_factory=list)
    """English timeline of server steps (1-page enforcement, compile, etc.)."""
    revision_log_ko: list[str] = Field(default_factory=list)
    """Korean timeline (same steps as revision_log)."""
    pdf_layout_underfull: bool | None = None
    """True if bottom of page looked empty (heuristic); None if density check skipped or unavailable."""
    density_expand_rounds: int = 0
    """How many LLM densify passes ran after PDF layout check."""
    ats_issue_code: str | None = None
    """Last ATS smoke-test issue code after pipeline; None if check passed or skipped."""
    quality_issues: list[dict[str, Any]] | None = None
    """Optional checker LLM output (issues only); None if disabled or failed."""


def repair_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _parse_preview_coaching(data: dict[str, Any]) -> tuple[list[PreviewSection], list[CoachingSection]]:
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

    while len(coaching) < len(preview_sections):
        coaching.append(CoachingSection(section_why="", items=[]))
    for i, prev in enumerate(preview_sections):
        while len(coaching[i].items) < len(prev.bullets):
            coaching[i].items.append(CoachingItem(why_better=""))
        coaching[i].items = coaching[i].items[: len(prev.bullets)]

    return preview_sections, coaching


def _coerce_latex_document_response(data: dict[str, Any]) -> GenerateResponse:
    """Validate model JSON and build GenerateResponse (normalized LaTeX)."""
    latex = data.get("latex_document") or data.get("latex") or ""
    if not latex or "\\documentclass" not in latex:
        raise HTTPException(
            status_code=502,
            detail="Model did not return a valid latex_document.",
        )
    latex = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(latex))
    )
    preview_sections, coaching = _parse_preview_coaching(data)
    return GenerateResponse(
        latex_document=latex,
        preview_sections=preview_sections,
        coaching=coaching,
    )


def _coerce_structured_attempt(
    data: dict[str, Any],
) -> tuple[GenerateResponse, dict[str, Any]]:
    """Single structured pass; raises ResumeSchemaError for LLM self-heal loop."""
    rd_raw = data.get("resume_data")
    if not isinstance(rd_raw, dict):
        raise ResumeSchemaError(
            ["- resume_data: must be a JSON object"],
            data,
        )
    try:
        rd = parse_resume_data(rd_raw)
    except ValidationError as e:
        raise ResumeSchemaError(format_resume_validation_errors(e), data) from e
    try:
        latex = build_latex_document(rd)
    except ValueError as e:
        raise ResumeSchemaError([f"- document: {e}"], data) from e
    latex = sanitize_latex_for_overleaf(sanitize_unicode_for_latex(latex))
    preview_sections, coaching = _parse_preview_coaching(data)
    return (
        GenerateResponse(
            latex_document=latex,
            preview_sections=preview_sections,
            coaching=coaching,
        ),
        rd_raw,
    )


def _llm_fix_resume_schema(
    client: OpenAI,
    fixer_sys: str,
    model_response: dict[str, Any],
    schema_errors: list[str],
) -> dict[str, Any]:
    user = revision_user_fix_schema(
        model_response=model_response,
        schema_errors=schema_errors,
    )
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": fixer_sys},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.15,
        max_tokens=16_384,
    )
    raw = completion.choices[0].message.content or "{}"
    return repair_json(raw)


def _structured_coerce_pipeline(
    client: OpenAI | None,
    data: dict[str, Any],
    fixer_sys: str,
    log_en: list[str],
    log_ko: list[str],
) -> tuple[GenerateResponse, dict[str, Any]]:
    work = data
    max_h = settings.resume_schema_heal_max if client is not None else 0
    for attempt in range(max_h + 1):
        try:
            return _coerce_structured_attempt(work)
        except ResumeSchemaError as e:
            if attempt >= max_h:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "resume_data_schema_failed",
                        "schema_errors": e.errors,
                    },
                ) from None
            log_en.append(
                f"resume_data failed validation; schema self-heal ({attempt + 1}/{max_h})…"
            )
            log_ko.append(
                f"스키마 검증 실패 — resume_data 자동 수정 중 ({attempt + 1}/{max_h})…"
            )
            work = _llm_fix_resume_schema(
                client, fixer_sys, e.model_response, e.errors
            )
    raise AssertionError("structured coerce pipeline unreachable")


def attempt_llm_latex_compile_fix(
    client: OpenAI,
    *,
    tex_for_prompt: str,
    err_snippet: str,
) -> tuple[str | None, str | None]:
    """
    Single LLM call: REVISION_SIGNAL fix_compile_error with numbered source context.
    Returns (normalized_tex_or_none, optional_reason).
    """
    user = revision_user_fix_compile(latex=tex_for_prompt, error_snippet=err_snippet)
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": fixer_compile_system()},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=16_384,
    )
    raw = completion.choices[0].message.content or "{}"
    try:
        data = repair_json(raw)
    except json.JSONDecodeError:
        logger.warning("compile heal: model returned invalid JSON")
        return None, None
    reason = data.get("reason") if isinstance(data.get("reason"), str) else None
    latex_out = (data.get("latex_document") or data.get("latex") or "").strip()
    if not latex_out or "\\documentclass" not in latex_out:
        return None, reason
    latex_out = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(latex_out))
    )
    return latex_out, reason


def _inject_preview_coaching_from_previous(
    data: dict[str, Any],
    prev: GenerateResponse | None,
) -> None:
    """Compile-fix JSON may omit UI fields; keep preview/coaching from the last response."""
    if prev is None:
        return
    ps = data.get("preview_sections")
    ch = data.get("coaching")
    if not ps:
        data["preview_sections"] = [p.model_dump() for p in prev.preview_sections]
    if not ch:
        data["coaching"] = [c.model_dump() for c in prev.coaching]


def _coerce_any_response(
    data: dict[str, Any],
    *,
    client: OpenAI | None = None,
    fixer_sys: str = "",
    log_en: list[str] | None = None,
    log_ko: list[str] | None = None,
) -> tuple[GenerateResponse, dict[str, Any] | None]:
    if not settings.resume_structured_latex:
        return _coerce_latex_document_response(data), None
    fs = fixer_sys.strip() or structured_fixer_system()
    le, lk = log_en or [], log_ko or []
    return _structured_coerce_pipeline(client, data, fs, le, lk)


def _coerce_generate_response(data: dict[str, Any]) -> GenerateResponse:
    """Backward-compatible: LaTeX or structured → GenerateResponse (drops resume_data blob)."""
    r, _ = _coerce_any_response(data)
    return r


def _run_checker_llm(
    client: OpenAI, checker_sys: str, latex: str
) -> list[dict[str, Any]] | None:
    """Diagnostic-only checker; returns issues list or None on failure."""
    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": checker_sys},
                {"role": "user", "content": build_checker_user(latex=latex)},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
            max_tokens=4096,
        )
        raw = completion.choices[0].message.content or "{}"
        data = repair_json(raw)
        issues = data.get("issues")
        if isinstance(issues, list):
            return [x for x in issues if isinstance(x, dict)]
    except Exception as e:
        logger.warning("Checker LLM failed: %s", e)
    return None


def _append_one_page_done_notes(
    log_en: list[str],
    log_ko: list[str],
    *,
    raw: str,
    layout_underfull: bool | None,
    density_max: int,
) -> None:
    """Explain sparse/short output when source or tooling limits density (user-facing logs)."""
    if density_max <= 0:
        log_en.append("Full-page density expand is off (RESUME_DENSITY_EXPAND_MAX=0).")
        log_ko.append("한 페이지 밀도 자동 보강이 꺼져 있습니다 (RESUME_DENSITY_EXPAND_MAX=0).")
    if layout_underfull is True:
        log_en.append(
            "Bottom may still look empty: if the draft had little to add (bullets, metrics, projects), "
            "the resume stays shorter or relaxed on purpose — we do not invent achievements."
        )
        log_ko.append(
            "원문에 추가할 불릿·수치·프로젝트가 없으면 짧게·여유 있게 끝난 것일 수 있습니다. 허위 내용은 넣지 않습니다."
        )
    elif layout_underfull is None and density_max > 0:
        log_en.append(
            "PDF bottom density was not measured; install Poppler (pdftoppm) + Pillow and set "
            "pdf_density_check_ready true in /health."
        )
        log_ko.append(
            "PDF 하단 밀도를 재지 못했습니다. Poppler(pdftoppm)·Pillow 설치 후 /health 에서 pdf_density_check_ready 를 확인하세요."
        )
    if len(raw.strip()) < 1200:
        log_en.append("Source text is short; richer input usually fills one page better.")
        log_ko.append("원문이 짧습니다. 내용을 더 넣으면 한 페이지가 더 자연스럽게 채워집니다.")


def _parse_page_policy(value: str | None) -> PagePolicy:
    if (value or "").strip().lower() in ("allow_multi", "multi", "allow_multiple"):
        return "allow_multi"
    return "strict_one_page"


def _progress_event(log_ko: list[str], log_en: list[str]) -> dict[str, Any]:
    return {
        "type": "progress",
        "message": log_ko[-1],
        "message_en": log_en[-1],
        "log_ko": list(log_ko),
        "log_en": list(log_en),
    }


def iterate_generate_progress(raw: str, page_policy: PagePolicy) -> Iterator[dict[str, Any]]:
    """Yields progress dicts and a final {\"type\":\"result\",\"data\": ...}."""
    if len(raw) > 120_000:
        raw = raw[:120_000] + "\n\n[truncated]"

    client = OpenAI(api_key=settings.openai_api_key)
    structured = settings.resume_structured_latex
    generator_sys = (
        structured_generator_system() if structured else generator_system()
    )
    fixer_sys = structured_fixer_system() if structured else fixer_system()
    compile_fixer_sys = (
        structured_fixer_compile_system() if structured else fixer_compile_system()
    )
    densify_sys = (
        structured_densify_system() if structured else densify_system()
    )
    checker_sys = checker_system()
    user_msg = (
        build_structured_generation_user_message(raw)
        if structured
        else build_generation_user_message(raw)
    )
    user_msg += (
        "\n=== SERVER PIPELINE NOTE ===\n"
        "First pass: **maximize** grounded detail from RESUME SOURCE—**100%** of metrics/tech names/scope must stay in the output (rephrase OK, omit never). "
        "Experience **4–5** sentence-level bullets per role when material exists; mix **1- and 2-line** depth. "
        "If PDF >1 page, server asks for **fit_one_page**: remove filler words only—**not** facts—then densify may refill bottom whitespace from existing facts.\n"
    )
    if settings.resume_density_expand_max > 0:
        user_msg += (
            "If the PDF is one page but the bottom looks empty, the server may **densify** (more detail from existing facts only).\n"
        )
    if structured:
        user_msg += "Structured mode: revisions adjust **resume_data** JSON only; never output LaTeX.\n"

    log_ko: list[str] = []
    log_en: list[str] = []

    log_en.append("Calling the model (first pass)…")
    log_ko.append("AI가 이력서 초안을 생성하고 있습니다…")
    yield _progress_event(log_ko, log_en)

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": generator_sys},
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

    resp, resume_data_state = _coerce_any_response(
        data,
        client=client,
        fixer_sys=fixer_sys,
        log_en=log_en,
        log_ko=log_ko,
    )
    latex = resp.latex_document

    log_en.append("Draft ready; applying checks…")
    log_ko.append("초안이 준비되었습니다. 검사를 진행합니다…")
    yield _progress_event(log_ko, log_en)

    if page_policy == "allow_multi":
        log_en.append("Multiple pages allowed — skipping strict 1-page enforcement.")
        log_ko.append("여러 페이지 허용 모드입니다. 1페이지 강제를 적용하지 않습니다.")
        yield _progress_event(log_ko, log_en)
        pdf, err_detail = compile_latex_to_pdf(latex)
        am_compile_budget = 2
        if not pdf:
            err_snippet = (
                json.dumps(err_detail, ensure_ascii=False) if err_detail else ""
            )
            while not pdf and am_compile_budget > 0:
                am_compile_budget -= 1
                log_en.append(
                    f"PDF compile failed; asking model to fix LaTeX "
                    f"({2 - am_compile_budget}/2)…"
                )
                log_ko.append(
                    "PDF 컴파일 실패 — 모델에 LaTeX 오류 수정을 요청합니다… "
                    f"({2 - am_compile_budget}/2)"
                )
                yield _progress_event(log_ko, log_en)
                rev_user = (
                    revision_user_fix_compile_structured(
                        resume_data=resume_data_state,
                        error_snippet=err_snippet,
                        rendered_latex=latex,
                    )
                    if structured and resume_data_state is not None
                    else revision_user_fix_compile(
                        latex=latex, error_snippet=err_snippet
                    )
                )
                try:
                    completion = client.chat.completions.create(
                        model=settings.openai_model,
                        messages=[
                            {"role": "system", "content": compile_fixer_sys},
                            {"role": "user", "content": rev_user},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                        max_tokens=16_384,
                    )
                except Exception as e:
                    logger.exception("OpenAI compile-fix error (allow_multi)")
                    raise HTTPException(status_code=502, detail=str(e)) from e
                rev_content = completion.choices[0].message.content or "{}"
                try:
                    data = repair_json(rev_content)
                except json.JSONDecodeError:
                    logger.warning(
                        "Compile-fix JSON parse failed (allow_multi): %s",
                        rev_content[:500],
                    )
                    break
                reason = data.get("reason")
                if isinstance(reason, str) and reason.strip():
                    log_en.append(f"Compile-fix note: {reason.strip()[:500]}")
                    log_ko.append(f"컴파일 수정: {reason.strip()[:500]}")
                _inject_preview_coaching_from_previous(data, resp)
                resp, blob = _coerce_any_response(
                    data,
                    client=client,
                    fixer_sys=fixer_sys,
                    log_en=log_en,
                    log_ko=log_ko,
                )
                if blob is not None:
                    resume_data_state = blob
                latex = resp.latex_document
                pdf, err_detail = compile_latex_to_pdf(latex)
                err_snippet = (
                    json.dumps(err_detail, ensure_ascii=False)
                    if err_detail
                    else ""
                )
        pc = _count_pdf_pages(pdf) if pdf else None
        if not pdf:
            log_en.append("Server PDF compile failed; page count unknown.")
            log_ko.append("서버에서 PDF 컴파일에 실패했습니다. 페이지 수를 확인하지 못했습니다.")
        else:
            log_en.append(f"Server PDF: {pc} page(s).")
            log_ko.append(f"서버 PDF 기준 {pc}페이지입니다.")
        yield _progress_event(log_ko, log_en)
        ats_ic = ats_smoke_test(pdf) if pdf else None
        if ats_ic:
            log_en.append(f"ATS smoke (informational): {ats_ic}")
            log_ko.append(f"ATS 스모크(참고): {ats_ic}")
            yield _progress_event(log_ko, log_en)
        q_issues: list[dict[str, Any]] | None = None
        if pdf and settings.resume_quality_checker:
            log_en.append("Running quality checker (diagnostic only)…")
            log_ko.append("품질 점검(진단만)을 실행합니다…")
            yield _progress_event(log_ko, log_en)
            q_issues = _run_checker_llm(client, checker_sys, latex)
        final = resp.model_copy(
            update={
                "pdf_page_count": pc,
                "one_page_enforced": False,
                "page_policy_applied": page_policy,
                "revision_log": list(log_en),
                "revision_log_ko": list(log_ko),
                "pdf_layout_underfull": None,
                "density_expand_rounds": 0,
                "ats_issue_code": ats_ic,
                "quality_issues": q_issues,
            }
        )
        yield {"type": "result", "data": final.model_dump()}
        return

    max_rev = settings.resume_one_page_max_revisions
    if max_rev <= 0:
        log_en.append("1-page enforcement is off (RESUME_ONE_PAGE_MAX_REVISIONS=0).")
        log_ko.append("1페이지 강제가 설정에서 꺼져 있습니다.")
        yield _progress_event(log_ko, log_en)
        final = resp.model_copy(
            update={
                "pdf_page_count": None,
                "one_page_enforced": False,
                "page_policy_applied": page_policy,
                "revision_log": list(log_en),
                "revision_log_ko": list(log_ko),
                "pdf_layout_underfull": None,
                "density_expand_rounds": 0,
            }
        )
        yield {"type": "result", "data": final.model_dump()}
        return

    expand_left = settings.resume_density_expand_max
    density_rounds = 0
    density_max = settings.resume_density_expand_max
    compile_fix_budget = 2

    def _finish_fields(
        *,
        pdf_page_count: int | None,
        one_page_enforced: bool,
        layout_underfull: bool | None,
        ats_issue_code: str | None = None,
        quality_issues: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "pdf_page_count": pdf_page_count,
            "one_page_enforced": one_page_enforced,
            "page_policy_applied": page_policy,
            "revision_log": list(log_en),
            "revision_log_ko": list(log_ko),
            "pdf_layout_underfull": layout_underfull,
            "density_expand_rounds": density_rounds,
            "ats_issue_code": ats_issue_code,
            "quality_issues": quality_issues,
        }

    while True:
        for attempt in range(max_rev + 1):
            log_en.append("Compiling PDF to verify page count…")
            log_ko.append("PDF를 컴파일해 페이지 수를 확인하는 중입니다…")
            yield _progress_event(log_ko, log_en)

            pdf, err_detail = compile_latex_to_pdf(latex)
            if not pdf:
                err_snippet = (
                    json.dumps(err_detail, ensure_ascii=False)
                    if err_detail
                    else ""
                )
                while not pdf and compile_fix_budget > 0:
                    compile_fix_budget -= 1
                    log_en.append(
                        f"PDF compile failed; asking model to fix LaTeX (compile-fix "
                        f"{2 - compile_fix_budget}/2)…"
                    )
                    log_ko.append(
                        "PDF 컴파일 실패 — 모델에 LaTeX 오류 수정을 요청합니다… "
                        f"({2 - compile_fix_budget}/2)"
                    )
                    yield _progress_event(log_ko, log_en)
                    rev_user = (
                        revision_user_fix_compile_structured(
                            resume_data=resume_data_state,
                            error_snippet=err_snippet,
                            rendered_latex=latex,
                        )
                        if structured and resume_data_state is not None
                        else revision_user_fix_compile(
                            latex=latex, error_snippet=err_snippet
                        )
                    )
                    try:
                        completion = client.chat.completions.create(
                            model=settings.openai_model,
                            messages=[
                                {"role": "system", "content": compile_fixer_sys},
                                {"role": "user", "content": rev_user},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.1,
                            max_tokens=16_384,
                        )
                    except Exception as e:
                        logger.exception("OpenAI compile-fix error")
                        raise HTTPException(status_code=502, detail=str(e)) from e

                    rev_content = completion.choices[0].message.content or "{}"
                    try:
                        data = repair_json(rev_content)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Compile-fix JSON parse failed: %s", rev_content[:500]
                        )
                        break

                    reason = data.get("reason")
                    if isinstance(reason, str) and reason.strip():
                        log_en.append(f"Compile-fix note: {reason.strip()[:500]}")
                        log_ko.append(f"컴파일 수정: {reason.strip()[:500]}")
                    _inject_preview_coaching_from_previous(data, resp)
                    resp, blob = _coerce_any_response(
                        data,
                        client=client,
                        fixer_sys=fixer_sys,
                        log_en=log_en,
                        log_ko=log_ko,
                    )
                    if blob is not None:
                        resume_data_state = blob
                    latex = resp.latex_document
                    pdf, err_detail = compile_latex_to_pdf(latex)
                    err_snippet = (
                        json.dumps(err_detail, ensure_ascii=False)
                        if err_detail
                        else ""
                    )

            if not pdf:
                logger.warning(
                    "One-page check: compile failed (attempt %s), skipping enforcement: %s",
                    attempt,
                    (err_detail or {}).get("code", err_detail),
                )
                log_en.append("PDF compile failed on server; cannot verify or enforce 1 page.")
                log_ko.append("서버 PDF 컴파일 실패 — 1페이지 여부를 확인·강제할 수 없습니다.")
                yield _progress_event(log_ko, log_en)
                final = resp.model_copy(
                    update=_finish_fields(
                        pdf_page_count=None,
                        one_page_enforced=False,
                        layout_underfull=None,
                    )
                )
                yield {"type": "result", "data": final.model_dump()}
                return

            pages = _count_pdf_pages(pdf)
            if pages > 1:
                if attempt >= max_rev:
                    logger.warning(
                        "One-page check: still %s page(s) after %s revision(s); returning best effort",
                        pages,
                        max_rev,
                    )
                    log_en.append(f"Still {pages} page(s) after maximum revisions.")
                    log_ko.append(f"최대 수정 후에도 {pages}페이지입니다.")
                    yield _progress_event(log_ko, log_en)
                    final = resp.model_copy(
                        update=_finish_fields(pdf_page_count=pages, one_page_enforced=False, layout_underfull=None)
                    )
                    yield {"type": "result", "data": final.model_dump()}
                    return

                line_en = (
                    f"Detected {pages} page(s) — lightly tightening to fit 1 page "
                    f"(keep all source facts; revision {attempt + 1}/{max_rev})…"
                )
                line_ko = (
                    f"{pages}페이지입니다. 원본 정보는 유지한 채 문장·여백만 조여 1페이지에 맞춥니다… "
                    f"({attempt + 1}/{max_rev}차)"
                )
                log_en.append(line_en)
                log_ko.append(line_ko)
                yield _progress_event(log_ko, log_en)

                log_en.append("Asking the model for a mild trim (wording / spacing; preserve all source content)…")
                log_ko.append("모델에 문장·여백 위주로 살짝 줄이기를 요청합니다 (원본 정보 삭제·누락 지양)…")
                yield _progress_event(log_ko, log_en)

                rev_user = (
                    revision_user_fit_one_page_structured(
                        resume_data=resume_data_state, pages=pages
                    )
                    if structured and resume_data_state is not None
                    else revision_user_one_page(latex=latex, pages=pages)
                )
                try:
                    completion = client.chat.completions.create(
                        model=settings.openai_model,
                        messages=[
                            {"role": "system", "content": fixer_sys},
                            {"role": "user", "content": rev_user},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.25,
                        max_tokens=16_384,
                    )
                except Exception as e:
                    logger.exception("OpenAI revision error")
                    raise HTTPException(status_code=502, detail=str(e)) from e

                rev_content = completion.choices[0].message.content or "{}"
                try:
                    data = repair_json(rev_content)
                except json.JSONDecodeError as e:
                    logger.warning("One-page revision JSON parse failed: %s", rev_content[:500])
                    raise HTTPException(
                        status_code=502,
                        detail="Model returned invalid JSON on one-page revision. Retry.",
                    ) from e

                resp, blob = _coerce_any_response(
                    data,
                    client=client,
                    fixer_sys=fixer_sys,
                    log_en=log_en,
                    log_ko=log_ko,
                )
                if blob is not None:
                    resume_data_state = blob
                latex = resp.latex_document
                continue

            layout_underfull: bool | None = None
            if density_max > 0:
                log_en.append("Checking PDF for underfull bottom (layout density)…")
                log_ko.append("PDF 하단 여백(밀도)을 검사하는 중입니다…")
                yield _progress_event(log_ko, log_en)
                mean_lum = pdf_bottom_strip_mean_luminance(
                    pdf,
                    bottom_fraction=settings.resume_underfull_bottom_frac,
                    dpi=settings.resume_underfull_dpi,
                )
                if mean_lum is not None:
                    log_en.append(
                        f"Bottom strip mean luminance (0-255, bottom {settings.resume_underfull_bottom_frac:.0%}): "
                        f"{mean_lum:.1f}"
                    )
                    log_ko.append(
                        f"하단 {settings.resume_underfull_bottom_frac:.0%} 구간 평균 밝기(0-255): {mean_lum:.1f}"
                    )
                    yield _progress_event(log_ko, log_en)
                if mean_lum is None:
                    layout_underfull = None
                elif settings.resume_underfull_golden_mean is not None:
                    gm = settings.resume_underfull_golden_mean
                    margin = settings.resume_underfull_golden_margin
                    layout_underfull = mean_lum > gm + margin
                else:
                    layout_underfull = mean_lum >= settings.resume_underfull_mean_threshold

                if layout_underfull is None:
                    log_en.append("Density check unavailable (install poppler `pdftoppm` + Pillow).")
                    log_ko.append("밀도 검사 생략: `pdftoppm`(Poppler)과 Pillow를 설치하면 하단 여백을 감지합니다.")
                    yield _progress_event(log_ko, log_en)
                elif layout_underfull:
                    log_en.append("Layout looks underfull (large bottom whitespace).")
                    log_ko.append("하단에 빈 공간이 많아 보입니다.")
                    yield _progress_event(log_ko, log_en)
                else:
                    log_en.append("Layout density OK on one page.")
                    log_ko.append("1페이지 밀도가 적당해 보입니다.")
                    yield _progress_event(log_ko, log_en)

            if layout_underfull is not True:
                ats_issue_code = ats_smoke_test(pdf)
                if ats_issue_code and not should_autofix_ats(ats_issue_code):
                    log_en.append(
                        f"ATS smoke: {ats_issue_code} (no auto-fix for this code)."
                    )
                    log_ko.append(f"ATS 스모크: {ats_issue_code} (이 코드는 자동 수정 안 함).")
                    yield _progress_event(log_ko, log_en)
                if (
                    settings.resume_ats_fix_max > 0
                    and should_autofix_ats(ats_issue_code)
                ):
                    if structured and resume_data_state is None:
                        log_en.append(
                            "ATS auto-fix skipped: missing structured resume_data state."
                        )
                        log_ko.append(
                            "ATS 자동 수정 생략: 구조화 resume_data 상태가 없습니다."
                        )
                        yield _progress_event(log_ko, log_en)
                    else:
                        ats_left = settings.resume_ats_fix_max
                        latex_snap, pdf_snap, resp_snap = latex, pdf, resp
                        cur_issue = ats_issue_code
                        fix_idx = 0
                        while cur_issue and ats_left > 0:
                            ats_left -= 1
                            fix_idx += 1
                            mode = "JSON" if structured else "LaTeX"
                            log_en.append(
                                f"ATS auto-fix ({mode}) ({fix_idx}/{settings.resume_ats_fix_max}): "
                                f"{cur_issue}…"
                            )
                            log_ko.append(
                                f"ATS 자동 수정 ({mode}) ({fix_idx}/{settings.resume_ats_fix_max}): "
                                f"{cur_issue}…"
                            )
                            yield _progress_event(log_ko, log_en)
                            if structured:
                                rev_user = revision_user_fix_ats_structured(
                                    resume_data=resume_data_state,
                                    ats_issue=cur_issue,
                                )
                            else:
                                rev_user = revision_user_fix_ats(
                                    latex=latex, ats_issue=cur_issue
                                )
                            try:
                                completion = client.chat.completions.create(
                                    model=settings.openai_model,
                                    messages=[
                                        {"role": "system", "content": fixer_sys},
                                        {"role": "user", "content": rev_user},
                                    ],
                                    response_format={"type": "json_object"},
                                    temperature=0.22,
                                    max_tokens=16_384,
                                )
                            except Exception as e:
                                logger.warning("ATS fix LLM error: %s", e)
                                resp, latex, pdf = resp_snap, latex_snap, pdf_snap
                                break

                            rev_content = completion.choices[0].message.content or "{}"
                            try:
                                data = repair_json(rev_content)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "ATS fix JSON parse failed: %s", rev_content[:500]
                                )
                                resp, latex, pdf = resp_snap, latex_snap, pdf_snap
                                break
                            try:
                                if structured:
                                    resp_try, blob_try = _coerce_any_response(
                                        data,
                                        client=client,
                                        fixer_sys=fixer_sys,
                                        log_en=log_en,
                                        log_ko=log_ko,
                                    )
                                    if blob_try is not None:
                                        resume_data_state = blob_try
                                else:
                                    resp_try = _coerce_generate_response(data)
                            except HTTPException:
                                resp, latex, pdf = resp_snap, latex_snap, pdf_snap
                                break
                            latex_try = resp_try.latex_document
                            pdf_try, _e2 = compile_latex_to_pdf(latex_try)
                            if not pdf_try:
                                resp, latex, pdf = resp_snap, latex_snap, pdf_snap
                                break
                            try:
                                if _count_pdf_pages(pdf_try) != 1:
                                    resp, latex, pdf = resp_snap, latex_snap, pdf_snap
                                    break
                            except Exception:
                                resp, latex, pdf = resp_snap, latex_snap, pdf_snap
                                break
                            resp, latex, pdf = resp_try, latex_try, pdf_try
                            latex_snap, pdf_snap, resp_snap = latex, pdf, resp
                            cur_issue = ats_smoke_test(pdf)
                            if cur_issue is None:
                                break
                            if not should_autofix_ats(cur_issue):
                                log_en.append(
                                    f"ATS after fix: {cur_issue} (stopping auto-fix)."
                                )
                                log_ko.append(
                                    f"ATS 수정 후: {cur_issue} (자동 수정 중단)."
                                )
                                yield _progress_event(log_ko, log_en)
                                break

                ats_issue_code = ats_smoke_test(pdf)
                q_issues: list[dict[str, Any]] | None = None
                if settings.resume_quality_checker:
                    log_en.append("Running quality checker (diagnostic only)…")
                    log_ko.append("품질 점검(진단만)을 실행합니다…")
                    yield _progress_event(log_ko, log_en)
                    q_issues = _run_checker_llm(client, checker_sys, latex)

                try:
                    pages = _count_pdf_pages(pdf)
                except Exception:
                    pass

                log_en.append(f"PDF fits on {pages} page(s). Done.")
                log_ko.append(f"PDF는 {pages}페이지입니다. 완료되었습니다.")
                yield _progress_event(log_ko, log_en)
                _n = len(log_en)
                _append_one_page_done_notes(
                    log_en,
                    log_ko,
                    raw=raw,
                    layout_underfull=layout_underfull,
                    density_max=density_max,
                )
                if len(log_en) > _n:
                    yield _progress_event(log_ko, log_en)
                final = resp.model_copy(
                    update=_finish_fields(
                        pdf_page_count=pages,
                        one_page_enforced=attempt > 0,
                        layout_underfull=layout_underfull,
                        ats_issue_code=ats_issue_code,
                        quality_issues=q_issues,
                    )
                )
                yield {"type": "result", "data": final.model_dump()}
                return

            if expand_left <= 0:
                log_en.append("Underfull but max density-expand rounds reached; returning as-is.")
                log_ko.append("하단이 비었지만 추가 채움 횟수를 모두 썼습니다. 현재 버전으로 마칩니다.")
                yield _progress_event(log_ko, log_en)
                _n = len(log_en)
                _append_one_page_done_notes(
                    log_en,
                    log_ko,
                    raw=raw,
                    layout_underfull=True,
                    density_max=density_max,
                )
                if len(log_en) > _n:
                    yield _progress_event(log_ko, log_en)
                ats_ic = ats_smoke_test(pdf)
                q_done: list[dict[str, Any]] | None = None
                if settings.resume_quality_checker:
                    q_done = _run_checker_llm(client, checker_sys, latex)
                final = resp.model_copy(
                    update=_finish_fields(
                        pdf_page_count=pages,
                        one_page_enforced=attempt > 0,
                        layout_underfull=True,
                        ats_issue_code=ats_ic,
                        quality_issues=q_done,
                    )
                )
                yield {"type": "result", "data": final.model_dump()}
                return

            expand_left -= 1
            density_rounds += 1
            log_en.append(f"Densifying layout (round {density_rounds}/{density_max})…")
            log_ko.append(f"한 페이지를 꽉 채우도록 내용을 보강합니다… ({density_rounds}/{density_max}차)")
            yield _progress_event(log_ko, log_en)

            rev_user = (
                revision_user_densify_structured(resume_data=resume_data_state)
                if structured and resume_data_state is not None
                else revision_user_densify(latex=latex)
            )
            try:
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": densify_sys},
                        {"role": "user", "content": rev_user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.28,
                    max_tokens=16_384,
                )
            except Exception as e:
                logger.exception("OpenAI density-expand error")
                raise HTTPException(status_code=502, detail=str(e)) from e

            rev_content = completion.choices[0].message.content or "{}"
            try:
                data = repair_json(rev_content)
            except json.JSONDecodeError as e:
                logger.warning("Density-expand JSON parse failed: %s", rev_content[:500])
                raise HTTPException(
                    status_code=502,
                    detail="Model returned invalid JSON on density expand. Retry.",
                ) from e

            resp, blob = _coerce_any_response(
                data,
                client=client,
                fixer_sys=fixer_sys,
                log_en=log_en,
                log_ko=log_ko,
            )
            if blob is not None:
                resume_data_state = blob
            latex = resp.latex_document
            break

        else:
            raise AssertionError("one-page inner loop should return or break")


def _run_generate(raw: str, page_policy: PagePolicy = "strict_one_page") -> GenerateResponse:
    last: GenerateResponse | None = None
    for event in iterate_generate_progress(raw, page_policy):
        if event["type"] == "result":
            last = GenerateResponse.model_validate(event["data"])
    if last is None:
        raise HTTPException(status_code=500, detail="Generate produced no result.")
    return last


@app.get("/health")
def health():
    comp = compiler_available()
    return {
        "ok": True,
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model if settings.openai_api_key else None,
        "resume_structured_latex": settings.resume_structured_latex,
        "resume_schema_heal_max": settings.resume_schema_heal_max,
        "env_hint": str(_API_DIR / ".env"),
        "pdf_compile": comp.get("pdf_compile", comp.get("pdflatex") or comp.get("tectonic")),
        "compiler": comp,
    }


def _append_contact_hints(
    raw: str,
    *,
    contact_email: str | None = None,
    contact_linkedin: str | None = None,
    contact_phone: str | None = None,
) -> str:
    """Append explicit contact lines so the model can fill the header when the source is ambiguous."""
    e = (contact_email or "").strip()
    l = (contact_linkedin or "").strip()
    p = (contact_phone or "").strip()
    if not (e or l or p):
        return raw
    block = ["--- USER-SUPPLIED CONTACT (put in center header; use real mailto: and https:// hrefs) ---"]
    if p:
        block.append(f"Phone: {p}")
    if e:
        block.append(f"Email: {e}")
    if l:
        block.append(f"LinkedIn: {l}")
    return f"{raw.rstrip()}\n\n" + "\n".join(block)


async def _read_resume_source(
    file: UploadFile | None,
    text: str | None,
) -> str:
    if file and file.filename:
        data = await file.read()
        if len(data) > 12 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 12MB)")
        return extract_text(file.filename, data)
    if text and text.strip():
        return text.strip()
    raise HTTPException(
        status_code=400,
        detail="Upload a .pdf, .txt, or .tex file, or paste resume text.",
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    page_policy: str = Form("strict_one_page"),
    contact_email: str | None = Form(None),
    contact_linkedin: str | None = Form(None),
    contact_phone: str | None = Form(None),
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Copy api/.env.example to api/.env.",
        )

    raw = await _read_resume_source(file, text)
    raw = _append_contact_hints(
        raw,
        contact_email=contact_email,
        contact_linkedin=contact_linkedin,
        contact_phone=contact_phone,
    )
    return _run_generate(raw, _parse_page_policy(page_policy))


@app.post("/generate-stream")
async def generate_stream(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    page_policy: str = Form("strict_one_page"),
    contact_email: str | None = Form(None),
    contact_linkedin: str | None = Form(None),
    contact_phone: str | None = Form(None),
):
    """NDJSON stream: `progress` events (Korean `message`, English `message_en`) then `result` or `error`."""
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Copy api/.env.example to api/.env.",
        )

    raw = await _read_resume_source(file, text)
    raw = _append_contact_hints(
        raw,
        contact_email=contact_email,
        contact_linkedin=contact_linkedin,
        contact_phone=contact_phone,
    )
    policy = _parse_page_policy(page_policy)

    def ndjson_iter():
        try:
            for ev in iterate_generate_progress(raw, policy):
                yield (json.dumps(ev, ensure_ascii=False) + "\n").encode("utf-8")
        except HTTPException as he:
            err = {"type": "error", "detail": str(he.detail), "status_code": he.status_code}
            yield (json.dumps(err, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(ndjson_iter(), media_type="application/x-ndjson; charset=utf-8")


class GenerateJsonBody(BaseModel):
    text: str
    page_policy: PagePolicy = "strict_one_page"
    contact_email: str = ""
    contact_linkedin: str = ""
    contact_phone: str = ""


@app.post("/generate-json", response_model=GenerateResponse)
def generate_json_body(body: GenerateJsonBody):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text required")
    raw = _append_contact_hints(
        body.text.strip(),
        contact_email=body.contact_email or None,
        contact_linkedin=body.contact_linkedin or None,
        contact_phone=body.contact_phone or None,
    )
    return _run_generate(raw, body.page_policy)


@app.post("/generate-json-stream")
def generate_json_stream(body: GenerateJsonBody):
    """NDJSON stream for JSON clients (paste flow)."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text required")

    raw = _append_contact_hints(
        body.text.strip(),
        contact_email=body.contact_email or None,
        contact_linkedin=body.contact_linkedin or None,
        contact_phone=body.contact_phone or None,
    )

    def ndjson_iter():
        try:
            for ev in iterate_generate_progress(raw, body.page_policy):
                yield (json.dumps(ev, ensure_ascii=False) + "\n").encode("utf-8")
        except HTTPException as he:
            err = {"type": "error", "detail": str(he.detail), "status_code": he.status_code}
            yield (json.dumps(err, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(ndjson_iter(), media_type="application/x-ndjson; charset=utf-8")


class CompilePdfBody(BaseModel):
    latex_document: str
    """If True (default), on compile failure call the compile-only LLM fixer up to 2× (needs OPENAI_API_KEY)."""

    heal_with_llm: bool = True


@app.post("/compile-pdf")
def compile_pdf_endpoint(body: CompilePdfBody):
    """LaTeX → PDF; normalizes to the repo Dhruv preamble/body split (app default)."""
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


class CompileTexBody(BaseModel):
    """Full `.tex` source, compiled as-is (no Dhruv normalization)."""

    tex: str


@app.post("/compile")
def compile_raw_tex_endpoint(body: CompileTexBody):
    """
    LaTeX → PDF without Dhruv normalization (Overleaf-style main.tex compile).
    Prefer Docker TeX Live (`LATEX_DOCKER_IMAGE`) for reproducible builds.
    """
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
