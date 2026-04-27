"""Main orchestrator — combines parser, rule-based, and LLM scoring."""

import hashlib
import logging
import re
import threading
import time

from resume_service.models.resume_score import (
    AtsAudit,
    BulletAnalysis,
    Recommendation,
    RepairReadiness,
    ResumeScoreResponse,
    RoleAnalysis,
    RubricScore,
)
from resume_service.services.resume_score_llm import llm_score_resume
from resume_service.services.resume_score_parser import parse_resume
from resume_service.services.resume_score_rules import (
    compute_bullet_tags,
    compute_repair_readiness,
    score_bullet_heuristics,
    score_format_consistency,
    score_keyword_coverage,
    score_parseability,
    score_repetition,
    score_section_completeness,
)

logger = logging.getLogger(__name__)

_DEFAULT_RUBRIC = RubricScore(score=5.0, reason="LLM scoring unavailable.", suggestion="")

# In-process cache so /resume/review can reuse a recently-computed score from
# /resume/score (the frontend fires both in parallel; without this, we'd run the
# expensive LLM scoring twice and the second often hits a transient rate-limit).
_SCORE_CACHE: dict[str, tuple[float, "ResumeScoreResponse"]] = {}
_SCORE_CACHE_LOCK = threading.Lock()
_SCORE_CACHE_TTL_SEC = 600.0


def _score_cache_key(text: str, job_description: str) -> str:
    return hashlib.sha256(
        (text or "").encode("utf-8") + b"||" + (job_description or "").encode("utf-8")
    ).hexdigest()


def _score_cache_get(key: str) -> "ResumeScoreResponse | None":
    now = time.time()
    with _SCORE_CACHE_LOCK:
        entry = _SCORE_CACHE.get(key)
        if entry is None:
            return None
        ts, value = entry
        if now - ts > _SCORE_CACHE_TTL_SEC:
            _SCORE_CACHE.pop(key, None)
            return None
        return value


def _score_cache_put(key: str, value: "ResumeScoreResponse") -> None:
    with _SCORE_CACHE_LOCK:
        # bound size to prevent memory growth across long-lived dev sessions
        if len(_SCORE_CACHE) > 64:
            _SCORE_CACHE.clear()
        _SCORE_CACHE[key] = (time.time(), value)

_BULLET_NORM_RE = re.compile(r"[^\w\s]+")


def _norm_bullet_key(text: str, length: int = 60) -> str:
    """Normalize bullet text for matching: strip leading bullet glyphs, drop
    punctuation, collapse whitespace, lowercase, take first `length` chars.

    Robust against the LLM lightly rewording the echo of `text` in its JSON
    response (extra spaces, trailing punctuation, smart-quote variants)."""
    if not text:
        return ""
    cleaned = text.strip().lstrip("-•*→— ").strip()
    cleaned = _BULLET_NORM_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split()).lower()
    return cleaned[:length]


def _short_bullet_key(text: str, words: int = 5) -> str:
    """Last-resort fallback: first `words` words, normalized."""
    norm = _norm_bullet_key(text, length=200)
    return " ".join(norm.split()[:words])

_OVERALL_WEIGHTS: dict[str, float] = {
    "authenticity": 0.08,
    "realism": 0.08,
    "specificity": 0.10,
    "clarity": 0.08,
    "grammar": 0.06,
    "relevance": 0.10,
    "ats_compatibility": 0.12,
    "format_consistency": 0.06,
    "section_completeness": 0.06,
    "keyword_coverage": 0.10,
    "parseability": 0.06,
    "role_quality": 0.05,
    "bullet_quality": 0.05,
}


def _avg(scores: list[float]) -> float:
    return sum(scores) / max(len(scores), 1)


def _grade(score: float) -> str:
    if score >= 9.0:
        return "Excellent"
    if score >= 8.0:
        return "Strong"
    if score >= 7.0:
        return "Good"
    if score >= 6.0:
        return "Needs Improvement"
    return "Weak"


def _parse_llm_rubric(raw: dict | None) -> RubricScore:
    if not raw or not isinstance(raw, dict):
        return _DEFAULT_RUBRIC
    try:
        return RubricScore(
            score=float(raw.get("score", 5.0)),
            reason=str(raw.get("reason", "")),
            suggestion=str(raw.get("suggestion", "")),
        )
    except (ValueError, TypeError):
        return _DEFAULT_RUBRIC


def _bullet_id(text: str, role_id: str) -> str:
    raw = f"{role_id}|{text[:60].strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def score_resume(text: str, job_description: str = "") -> ResumeScoreResponse:
    """Parse, score (rules + LLM), and return a full ResumeScoreResponse."""

    cache_key = _score_cache_key(text, job_description)
    cached = _score_cache_get(cache_key)
    if cached is not None:
        logger.info("score_resume cache hit (key=%s)", cache_key[:12])
        return cached

    # --- 1. Parse ---
    parsed = parse_resume(text)

    # --- 2. Rule-based ATS scores ---
    parseability = score_parseability(parsed)
    section_comp = score_section_completeness(parsed)
    fmt_consistency = score_format_consistency(parsed)
    kw_coverage = score_keyword_coverage(parsed, job_description)

    ats_issues: list[str] = []
    for rubric in (parseability, section_comp, fmt_consistency, kw_coverage):
        if rubric.score < 7 and rubric.suggestion:
            ats_issues.append(rubric.suggestion)

    ats_audit = AtsAudit(
        parseability=parseability,
        section_completeness=section_comp,
        format_consistency=fmt_consistency,
        keyword_coverage=kw_coverage,
        issues=ats_issues,
    )

    # --- 3. LLM scoring ---
    llm_data = llm_score_resume(text, parsed, job_description)
    llm_resume_rubrics = llm_data.get("resume_rubrics", {})
    llm_roles = {r["id"]: r for r in llm_data.get("roles", []) if isinstance(r, dict) and "id" in r}
    llm_bullets_raw = llm_data.get("bullets", [])
    llm_bullets_by_text: dict[str, dict] = {}
    llm_bullets_by_short: dict[str, dict] = {}
    for b in llm_bullets_raw:
        if not (isinstance(b, dict) and "text" in b):
            continue
        norm = _norm_bullet_key(b["text"])
        if norm:
            llm_bullets_by_text.setdefault(norm, b)
        short = _short_bullet_key(b["text"])
        if short:
            llm_bullets_by_short.setdefault(short, b)

    # --- 4. Build resume-level rubrics (LLM semantic + rule systemic) ---
    semantic_names = ["authenticity", "realism", "specificity", "clarity", "grammar", "relevance"]
    resume_rubrics: dict[str, RubricScore] = {}
    for name in semantic_names:
        resume_rubrics[name] = _parse_llm_rubric(llm_resume_rubrics.get(name))

    ats_avg = _avg([parseability.score, section_comp.score, fmt_consistency.score, kw_coverage.score])
    resume_rubrics["ats_compatibility"] = RubricScore(
        score=round(ats_avg, 1),
        reason=f"Composite ATS score from parseability, sections, formatting, keywords.",
        suggestion="Improve ATS compatibility by addressing structural issues." if ats_avg < 7 else "",
    )
    resume_rubrics["format_consistency"] = fmt_consistency
    resume_rubrics["section_completeness"] = section_comp
    resume_rubrics["keyword_coverage"] = kw_coverage
    resume_rubrics["parseability"] = parseability

    # --- 5. Build role analyses ---
    roles: list[RoleAnalysis] = []
    for pr in parsed.roles:
        llm_role = llm_roles.get(pr.id, {})
        llm_role_rubrics = llm_role.get("rubrics", {}) if isinstance(llm_role, dict) else {}

        role_rubric_names = [
            "stack_completeness", "technical_depth", "impact_coverage",
            "ownership_profile", "role_relevance", "story_strength",
        ]
        role_rubrics: dict[str, RubricScore] = {}
        for name in role_rubric_names:
            role_rubrics[name] = _parse_llm_rubric(llm_role_rubrics.get(name))

        role_scores = [r.score for r in role_rubrics.values()]
        composite = round(_avg(role_scores), 1)

        strengths = llm_role.get("strengths", []) if isinstance(llm_role, dict) else []
        issues = llm_role.get("issues", []) if isinstance(llm_role, dict) else []

        roles.append(RoleAnalysis(
            id=pr.id,
            company=pr.company,
            title=pr.title,
            date_range=pr.date_range,
            composite_score=composite,
            rubrics=role_rubrics,
            strengths=strengths[:5],
            issues=issues[:5],
        ))

    # --- 6. Build bullet analyses ---
    bullets: list[BulletAnalysis] = []
    all_bullet_scores: list[float] = []

    for pr in parsed.roles:
        for bt in pr.bullets:
            rule_rubrics = score_bullet_heuristics(bt)

            norm_key = _norm_bullet_key(bt)
            short_key = _short_bullet_key(bt)
            llm_bullet = llm_bullets_by_text.get(norm_key) or llm_bullets_by_short.get(short_key) or {}
            match_path = "exact"
            if not llm_bullet:
                match_path = "miss"
            elif norm_key not in llm_bullets_by_text and short_key in llm_bullets_by_short:
                match_path = "short"
            if not llm_bullet and norm_key:
                # Last-ditch substring scan — pick the LLM bullet whose normalized
                # 60-char prefix is a substring of ours, or vice versa.
                for cand_key, cand in llm_bullets_by_text.items():
                    if cand_key and (cand_key in norm_key or norm_key.startswith(cand_key[:30])):
                        llm_bullet = cand
                        match_path = "substring"
                        break
            if match_path != "exact" and logger.isEnabledFor(logging.WARNING):
                logger.warning(
                    "bullet match=%s parsed=%r llm_keys_count=%d",
                    match_path,
                    bt[:60],
                    len(llm_bullets_by_text),
                )
            llm_bullet_rubrics = llm_bullet.get("rubrics", {}) if isinstance(llm_bullet, dict) else {}

            merged_rubrics: dict[str, RubricScore] = dict(rule_rubrics)
            llm_only_names = [
                "technical_specificity", "impact_strength", "scope_clarity",
                "ownership_clarity", "role_relevance", "evidence_completeness",
                "claim_defensibility",
            ]
            for name in llm_only_names:
                merged_rubrics[name] = _parse_llm_rubric(llm_bullet_rubrics.get(name))

            for name in ["concision", "information_density", "readability"]:
                llm_val = llm_bullet_rubrics.get(name)
                if llm_val and isinstance(llm_val, dict):
                    parsed_llm = _parse_llm_rubric(llm_val)
                    rule_val = rule_rubrics.get(name, _DEFAULT_RUBRIC)
                    merged_rubrics[name] = RubricScore(
                        score=round((rule_val.score + parsed_llm.score) / 2, 1),
                        reason=parsed_llm.reason or rule_val.reason,
                        suggestion=parsed_llm.suggestion or rule_val.suggestion,
                    )

            tags = compute_bullet_tags(bt, merged_rubrics)
            repair = compute_repair_readiness(merged_rubrics)

            b_scores = [r.score for r in merged_rubrics.values()]
            composite = round(_avg(b_scores), 1)
            all_bullet_scores.append(composite)

            strengths = llm_bullet.get("strengths", []) if isinstance(llm_bullet, dict) else []
            issues = llm_bullet.get("issues", []) if isinstance(llm_bullet, dict) else []
            rewrite = str(llm_bullet.get("rewrite", "")) if isinstance(llm_bullet, dict) else ""

            bullets.append(BulletAnalysis(
                id=_bullet_id(bt, pr.id),
                role_id=pr.id,
                text=bt,
                composite_score=composite,
                rubrics=merged_rubrics,
                tags=tags,
                strengths=strengths[:3],
                issues=issues[:3],
                rewrite=rewrite,
                repair_readiness=repair,
            ))

    repetition = score_repetition(parsed.all_bullets)

    # --- 7. Compute overall score ---
    role_quality = _avg([r.composite_score for r in roles]) if roles else 5.0
    bullet_quality = _avg(all_bullet_scores) if all_bullet_scores else 5.0

    score_map: dict[str, float] = {}
    for name, rubric in resume_rubrics.items():
        score_map[name] = rubric.score
    score_map["role_quality"] = role_quality
    score_map["bullet_quality"] = bullet_quality

    overall = 0.0
    total_weight = 0.0
    for name, weight in _OVERALL_WEIGHTS.items():
        if name in score_map:
            overall += score_map[name] * weight
            total_weight += weight
    if total_weight > 0:
        overall /= total_weight
    overall = round(min(10, max(0, overall)), 1)

    grade = _grade(overall)

    # --- 8. Generate summary and highlights ---
    top_strengths: list[str] = []
    top_issues: list[str] = []

    for name, rubric in sorted(resume_rubrics.items(), key=lambda x: -x[1].score):
        if rubric.score >= 7.5 and len(top_strengths) < 5:
            top_strengths.append(f"{name.replace('_', ' ').title()}: {rubric.reason}")
    for role in roles:
        for s in role.strengths[:2]:
            if len(top_strengths) < 5:
                top_strengths.append(s)

    for name, rubric in sorted(resume_rubrics.items(), key=lambda x: x[1].score):
        if rubric.score < 6.5 and len(top_issues) < 5:
            top_issues.append(f"{name.replace('_', ' ').title()}: {rubric.reason}")
    for role in roles:
        for issue in role.issues[:2]:
            if len(top_issues) < 5:
                top_issues.append(issue)

    if repetition.score < 7 and len(top_issues) < 5:
        top_issues.append(f"Bullet Repetition: {repetition.reason}")

    summary = (
        f"Overall score: {overall}/10 ({grade}). "
        f"{'Strong' if overall >= 7 else 'Moderate' if overall >= 5 else 'Weak'} resume "
        f"with {len(parsed.roles)} role(s) and {len(parsed.all_bullets)} bullet point(s)."
    )

    # --- 9. Build recommendations ---
    recommendations: list[Recommendation] = []

    if parseability.score < 7:
        recommendations.append(Recommendation(
            category="Structure",
            text="Add clear section headings to improve ATS parseability.",
            priority="high",
            expected_gain=round((7 - parseability.score) * 0.3, 2),
        ))
    if section_comp.score < 7:
        recommendations.append(Recommendation(
            category="Content",
            text=section_comp.suggestion,
            priority="high",
            expected_gain=round((7 - section_comp.score) * 0.3, 2),
        ))
    if kw_coverage.score < 7:
        recommendations.append(Recommendation(
            category="Keywords",
            text=kw_coverage.suggestion or "Add more relevant technical keywords.",
            priority="high" if job_description else "medium",
            expected_gain=round((7 - kw_coverage.score) * 0.3, 2),
        ))
    if fmt_consistency.score < 7:
        recommendations.append(Recommendation(
            category="Formatting",
            text=fmt_consistency.suggestion or "Standardize formatting across the resume.",
            priority="medium",
            expected_gain=round((7 - fmt_consistency.score) * 0.2, 2),
        ))
    if repetition.score < 7:
        recommendations.append(Recommendation(
            category="Content",
            text=repetition.suggestion or "Diversify bullet point content.",
            priority="medium",
            expected_gain=round((7 - repetition.score) * 0.2, 2),
        ))

    weak_bullets = [b for b in bullets if b.composite_score < 6]
    if weak_bullets:
        recommendations.append(Recommendation(
            category="Bullets",
            text=f"{len(weak_bullets)} bullet(s) scored below 6.0 — consider rewriting with metrics and specifics.",
            priority="high" if len(weak_bullets) > 3 else "medium",
            expected_gain=round(len(weak_bullets) * 0.15, 2),
        ))

    no_metric_bullets = [b for b in bullets if "Missing Metric" in b.tags]
    if no_metric_bullets:
        recommendations.append(Recommendation(
            category="Impact",
            text=f"{len(no_metric_bullets)} bullet(s) lack quantifiable metrics — add numbers, percentages, or outcomes.",
            priority="high",
            expected_gain=round(len(no_metric_bullets) * 0.1, 2),
        ))

    for name in ["authenticity", "realism", "specificity"]:
        rubric = resume_rubrics.get(name)
        if rubric and rubric.score < 6 and rubric.suggestion:
            recommendations.append(Recommendation(
                category="Quality",
                text=rubric.suggestion,
                priority="medium",
                expected_gain=round((6 - rubric.score) * 0.15, 2),
            ))

    recommendations.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r.priority, 1))

    # --- 10. Build response ---
    response = ResumeScoreResponse(
        overall_score=overall,
        grade=grade,
        summary=summary,
        top_strengths=top_strengths[:5],
        top_issues=top_issues[:5],
        resume_rubrics=resume_rubrics,
        roles=roles,
        bullets=bullets,
        ats_audit=ats_audit,
        recommendations=recommendations[:10],
    )
    _score_cache_put(cache_key, response)
    return response
