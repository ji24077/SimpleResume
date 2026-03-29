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
from pydantic import BaseModel, Field, field_validator, model_validator
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

    # Overleaf-grade default: TeX Live full in Docker + latexmk only (no silent TinyTeX).
    # Opt out in api/.env: LATEX_DOCKER_IMAGE=  LATEX_DOCKER_ONLY=0  LATEX_DOCKER_ALLOW_FALLBACK=1
    latex_docker_image: str = Field(default="simpleresume-texlive:full")
    latex_docker_only: bool = Field(default=True)
    latex_docker_allow_fallback: bool = Field(default=False)
    latex_docker_network: str = "none"
    # 1 = strip fullpage + glyphtounicode from canonical preamble before compile (friendlier to TinyTeX / some web paths).
    latex_portable_preamble: bool = Field(default=False)

    # After generate: compile PDF and re-prompt if >1 page (0 = disable).
    resume_one_page_max_revisions: int = Field(default=3, ge=0, le=8)

    # When strict 1-page PDF still has a large bottom whitespace (measured via pdftoppm + Pillow),
    # ask the model to densify up to this many times (0 = skip density loop).
    resume_density_expand_max: int = Field(default=2, ge=0, le=6)
    resume_underfull_bottom_frac: float = Field(default=0.22, ge=0.08, le=0.45)
    resume_underfull_mean_threshold: float = Field(default=237.0, ge=210.0, le=252.0)
    resume_underfull_dpi: int = Field(default=100, ge=72, le=150)
    # Optional: run scripts/measure_pdf_bottom_mean.py on your Overleaf "full 1 page" PDF, paste value here.
    # When set, underfull = measured_mean > golden_mean + golden_margin (absolute threshold ignored).
    resume_underfull_golden_mean: float | None = Field(default=None)
    resume_underfull_golden_margin: float = Field(default=12.0, ge=0.5, le=80.0)

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

    @model_validator(mode="after")
    def empty_image_disables_docker_only(self):
        """빈 이미지면 Docker-only를 끄지 않으면 PDF가 영원히 불가능해짐."""
        if not self.latex_docker_image.strip():
            return self.model_copy(update={"latex_docker_only": False})
        return self


settings = Settings()

# compile_pdf.py 는 os.environ 만 읽음 — Settings 와 동기화
if settings.latex_docker_image.strip():
    os.environ["LATEX_DOCKER_IMAGE"] = settings.latex_docker_image.strip()
else:
    os.environ.pop("LATEX_DOCKER_IMAGE", None)
if settings.latex_docker_network.strip():
    os.environ["LATEX_DOCKER_NETWORK"] = settings.latex_docker_network.strip()
if settings.latex_docker_only:
    os.environ["LATEX_DOCKER_ONLY"] = "1"
else:
    os.environ.pop("LATEX_DOCKER_ONLY", None)
if settings.latex_docker_allow_fallback:
    os.environ["LATEX_DOCKER_ALLOW_FALLBACK"] = "1"
else:
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

_has_docker_cli = bool(shutil.which("docker"))
logger.info(
    "PDF compile env: LATEX_DOCKER_IMAGE=%r | docker CLI=%s | LATEX_DOCKER_ONLY=%s | "
    "LATEX_DOCKER_ALLOW_FALLBACK=%s | LATEX_DOCKER_NETWORK=%r",
    settings.latex_docker_image or None,
    "yes" if _has_docker_cli else "NO (host TeX would be used only if allowed)",
    settings.latex_docker_only,
    settings.latex_docker_allow_fallback,
    settings.latex_docker_network,
)
if settings.latex_docker_image.strip() and not _has_docker_cli and not settings.latex_docker_allow_fallback:
    logger.warning(
        "LATEX_DOCKER_IMAGE is set but `docker` is not in PATH — compiles will fail until Docker is available "
        "or you set LATEX_DOCKER_ALLOW_FALLBACK=1 (TinyTeX/MacTeX)."
    )

_comp = compiler_available()
if settings.latex_docker_only and settings.latex_docker_image.strip() and not _comp.get("latex_docker_ready"):
    logger.warning(
        "Overleaf-grade PDF: LATEX_DOCKER_ONLY=1 but Docker is not ready for %s. "
        "From repo root run: docker compose build texlive — then ensure Docker Desktop is running. "
        "Or set LATEX_DOCKER_ONLY=0 and LATEX_DOCKER_ALLOW_FALLBACK=1 for host TeX.",
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


def repair_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _coerce_generate_response(data: dict[str, Any]) -> GenerateResponse:
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

    return GenerateResponse(
        latex_document=latex,
        preview_sections=preview_sections,
        coaching=coaching,
    )


def _revision_user_for_one_page(*, raw: str, latex: str, pages: int) -> str:
    raw_cap = raw if len(raw) <= 28_000 else raw[:14_000] + "\n\n[...truncated...]\n\n" + raw[-14_000:]
    return f"""The LaTeX resume below compiled to **{pages} pages**. It must fit **exactly ONE** U.S. letter page.

Return ONE JSON object with the same keys and schema as before: `latex_document`, `preview_sections`, `coaching`.
Follow the SAME system rules (Dhruv template, preamble lock, JSON shape).

**Tighten slightly — preserve ALL substantive facts from the ORIGINAL SOURCE.** Do not drop information to save space. That includes: **header contact** (phone, email, links as given), **Education** (schools, degrees, dates, honors, coursework, activities mentioned), **every employer / role / internship**, **every project or role-like block**, **Technical Skills** (every language/framework/tool named in the source should still appear somewhere in the three skill lines — abbreviate or cluster, do not delete a technology), certifications, awards, and other facts present in the source. You may **reword and compress** (same meaning, fewer words) and **merge** two short bullets into one line if no fact is lost.

**Do not remove a whole** `\\resumeSubheading` **or** `\\resumeProjectHeading` **that reflects content in the source.** If the source mentions something the template has no section for, keep it as a bullet under the closest section rather than omitting it.

**Order of edits (mild first, drastic last):**
1. Shorten bullet **wording** only (same facts, fewer words); merge clauses; drop filler adjectives.
2. **Merge** related bullets into a single `\\resumeItem` when both facts stay explicit — never merge in a way that hides an employer, date, or metric.
3. Tighten **Technical Skills** with shorter phrasing or grouping; **every tech term from the source must remain visible** (abbreviations OK if unambiguous).
4. Optional **small** negative `\\vspace` in the **document body only** (never change the required preamble).
5. Only if still over one page after the above: remove **at most one** lowest-redundancy bullet from the **single longest** list — and only if its facts are already stated elsewhere; otherwise keep trimming wording. Prefer another wording pass over deleting.
6. **Never** delete Education, a whole job, a whole project, or the skills block to fit the page.

Align `preview_sections` / `coaching` with the edited LaTeX.

--- ORIGINAL SOURCE (context) ---
{raw_cap}

--- CURRENT latex_document (slightly too long; replace entirely in your output) ---
{latex}
"""


def _revision_user_expand_density(*, raw: str, latex: str) -> str:
    raw_cap = raw if len(raw) <= 28_000 else raw[:14_000] + "\n\n[...truncated...]\n\n" + raw[-14_000:]
    return f"""The LaTeX resume compiles to **exactly ONE** U.S. letter page, but the **rendered PDF has too much empty space at the bottom** (underfull layout). Recruiters expect the page to be **well-filled** (~90-98%% vertical use of the body) when the source material supports it.

Return ONE JSON object with the same keys and schema as before: `latex_document`, `preview_sections`, `coaching`.
Follow the SAME system rules (Dhruv template, preamble lock, JSON shape).

**Densify using ONLY facts from the original source** — and **do not remove** any fact already in the current LaTeX (no invented employers, dates, or metrics):
1. Add **1-2 more** `\\resumeItem` bullets per Experience where the source still has unused details (hard cap **5** bullets per role).
2. Add or **expand** a Project block if the source lists projects not fully used.
3. **Expand** Technical Skills (Languages / Frameworks / Tools) with more comma-separated items from the source; keep everything already listed.
4. Prefer **one line per bullet**; if needed for metrics, up to **two lines**, target roughly **90-110 characters per line** where possible.
5. Priority: **Experience first**, then Projects, then Skills. Do **not** add a new section type that breaks the template.
6. The result must still compile to **one page**. You may use **small** negative `\\vspace` in the **document body only** (never change the required preamble).

--- ORIGINAL SOURCE (context) ---
{raw_cap}

--- CURRENT latex_document (too sparse at bottom; replace entirely in your output) ---
{latex}
"""


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
    system = build_system_prompt()
    user_msg = f"--- RESUME SOURCE ---\n\n{raw}"
    if settings.resume_density_expand_max > 0:
        user_msg += (
            "\n\n[Server pipeline] First pass: include **all** facts from the source (education, every job, projects, skills, contact). "
            "Use as many bullets per role as the source supports (typically 2-5). The server compiles to PDF, then may ask you to "
            "**densify** from the **same** source if the page looks underfull, or **tighten wording** (not drop facts) if over one page.\n"
        )

    log_ko: list[str] = []
    log_en: list[str] = []

    log_en.append("Calling the model (first pass)…")
    log_ko.append("AI가 이력서 초안을 생성하고 있습니다…")
    yield _progress_event(log_ko, log_en)

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

    resp = _coerce_generate_response(data)
    latex = resp.latex_document

    log_en.append("Draft ready; applying checks…")
    log_ko.append("초안이 준비되었습니다. 검사를 진행합니다…")
    yield _progress_event(log_ko, log_en)

    if page_policy == "allow_multi":
        log_en.append("Multiple pages allowed — skipping strict 1-page enforcement.")
        log_ko.append("여러 페이지 허용 모드입니다. 1페이지 강제를 적용하지 않습니다.")
        yield _progress_event(log_ko, log_en)
        pdf, _err = compile_latex_to_pdf(latex)
        pc = _count_pdf_pages(pdf) if pdf else None
        if not pdf:
            log_en.append("Server PDF compile failed; page count unknown.")
            log_ko.append("서버에서 PDF 컴파일에 실패했습니다. 페이지 수를 확인하지 못했습니다.")
        else:
            log_en.append(f"Server PDF: {pc} page(s).")
            log_ko.append(f"서버 PDF 기준 {pc}페이지입니다.")
        yield _progress_event(log_ko, log_en)
        final = resp.model_copy(
            update={
                "pdf_page_count": pc,
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

    def _finish_fields(
        *,
        pdf_page_count: int | None,
        one_page_enforced: bool,
        layout_underfull: bool | None,
    ) -> dict[str, Any]:
        return {
            "pdf_page_count": pdf_page_count,
            "one_page_enforced": one_page_enforced,
            "page_policy_applied": page_policy,
            "revision_log": list(log_en),
            "revision_log_ko": list(log_ko),
            "pdf_layout_underfull": layout_underfull,
            "density_expand_rounds": density_rounds,
        }

    while True:
        for attempt in range(max_rev + 1):
            log_en.append("Compiling PDF to verify page count…")
            log_ko.append("PDF를 컴파일해 페이지 수를 확인하는 중입니다…")
            yield _progress_event(log_ko, log_en)

            pdf, err_detail = compile_latex_to_pdf(latex)
            if not pdf:
                logger.warning(
                    "One-page check: compile failed (attempt %s), skipping enforcement: %s",
                    attempt,
                    (err_detail or {}).get("code", err_detail),
                )
                log_en.append("PDF compile failed on server; cannot verify or enforce 1 page.")
                log_ko.append("서버 PDF 컴파일 실패 — 1페이지 여부를 확인·강제할 수 없습니다.")
                yield _progress_event(log_ko, log_en)
                final = resp.model_copy(update=_finish_fields(pdf_page_count=None, one_page_enforced=False, layout_underfull=None))
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

                rev_user = _revision_user_for_one_page(raw=raw, latex=latex, pages=pages)
                try:
                    completion = client.chat.completions.create(
                        model=settings.openai_model,
                        messages=[
                            {"role": "system", "content": system},
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

                resp = _coerce_generate_response(data)
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
                final = resp.model_copy(
                    update=_finish_fields(
                        pdf_page_count=pages,
                        one_page_enforced=attempt > 0,
                        layout_underfull=True,
                    )
                )
                yield {"type": "result", "data": final.model_dump()}
                return

            expand_left -= 1
            density_rounds += 1
            log_en.append(f"Densifying layout (round {density_rounds}/{density_max})…")
            log_ko.append(f"한 페이지를 꽉 채우도록 내용을 보강합니다… ({density_rounds}/{density_max}차)")
            yield _progress_event(log_ko, log_en)

            rev_user = _revision_user_expand_density(raw=raw, latex=latex)
            try:
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": system},
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

            resp = _coerce_generate_response(data)
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


@app.post("/compile-pdf")
def compile_pdf_endpoint(body: CompilePdfBody):
    """LaTeX → PDF; normalizes to the repo Dhruv preamble/body split (app default)."""
    tex = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(body.latex_document.strip()))
    )
    pdf, err_detail = compile_latex_to_pdf(tex)
    if pdf:
        return Response(content=pdf, media_type="application/pdf")
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
