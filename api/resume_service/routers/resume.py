"""POST /generate, /generate-stream, /generate-json, /generate-json-stream."""

import json
import logging
from typing import Any, Iterator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openai import OpenAI

from compile_pdf import (
    compile_latex_to_pdf,
    count_pdf_pages_from_bytes,
    pdf_bottom_strip_mean_luminance,
    sanitize_latex_for_overleaf,
    sanitize_unicode_for_latex,
)
from resume_service.config import settings
from features.resume_pipeline.pipeline.ats_check import ats_smoke_test, should_autofix_ats
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
    revision_user_fix_compile,
    revision_user_fix_compile_structured,
    revision_user_one_page,
    revision_user_fit_one_page_structured,
    structured_densify_system,
    structured_fixer_compile_system,
    structured_fixer_system,
    structured_generator_system,
)
from resume_service.routers._helpers import (
    _coerce_any_response,
    _coerce_generate_response,
    _inject_preview_coaching_from_previous,
    _parse_page_policy,
    repair_json,
)
from resume_service.models import (
    GenerateJsonBody,
    GenerateResponse,
    PagePolicy,
)
from resume_service.services.pdf_service import extract_text

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    return count_pdf_pages_from_bytes(pdf_bytes)


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


def _progress_event(log_ko: list[str], log_en: list[str]) -> dict[str, Any]:
    return {
        "type": "progress",
        "message": log_ko[-1],
        "message_en": log_en[-1],
        "log_ko": list(log_ko),
        "log_en": list(log_en),
    }


# ---------------------------------------------------------------------------
# Core generation pipeline (iterator)
# ---------------------------------------------------------------------------


def iterate_generate_progress(raw: str, page_policy: PagePolicy) -> Iterator[dict[str, Any]]:
    """Yields progress dicts and a final {"type":"result","data": ...}."""
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


# ---------------------------------------------------------------------------
# Route helpers
# ---------------------------------------------------------------------------


def _append_contact_hints(
    raw: str,
    *,
    contact_email: str | None = None,
    contact_linkedin: str | None = None,
    contact_phone: str | None = None,
) -> str:
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


# ---------------------------------------------------------------------------
# Route endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=GenerateResponse)
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


@router.post("/generate-stream")
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


@router.post("/generate-json", response_model=GenerateResponse)
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


@router.post("/generate-json-stream")
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


# ---------------------------------------------------------------------------
# New /resume/* routes (backward-compatible aliases + future endpoints)
# ---------------------------------------------------------------------------


@router.post("/resume/generate")
async def resume_generate_stream(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    page_policy: str = Form("strict_one_page"),
    contact_email: str | None = Form(None),
    contact_linkedin: str | None = Form(None),
    contact_phone: str | None = Form(None),
):
    """Alias for /generate-stream with the new /resume/* path prefix."""
    return await generate_stream(
        file=file, text=text, page_policy=page_policy,
        contact_email=contact_email, contact_linkedin=contact_linkedin,
        contact_phone=contact_phone,
    )


@router.get("/resume/preview/{resume_id}")
def resume_preview(resume_id: str):
    """Placeholder for future result persistence and preview by ID."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
