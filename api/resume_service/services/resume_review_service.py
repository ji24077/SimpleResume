"""Transform ResumeScoreResponse into ReviewResponse with issue-level detail."""

from __future__ import annotations

import hashlib
import logging

from resume_service.models.resume_review import (
    CategoryScores,
    CredibilityInfo,
    IssueLocation,
    ResumeBulletView,
    ResumeRoleView,
    ResumeSectionView,
    ReviewIssue,
    ReviewResponse,
)
from resume_service.models.resume_score import (
    BulletAnalysis,
    ParsedResume,
    ResumeScoreResponse,
    RoleAnalysis,
    RubricScore,
)

logger = logging.getLogger(__name__)


def _issue_id(prefix: str, text: str) -> str:
    raw = f"{prefix}|{text[:80].strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def _severity_from_score(score: float) -> str:
    if score < 4:
        return "critical"
    if score < 6:
        return "moderate"
    return "minor"


def _to_100(score_10: float) -> int:
    return max(0, min(100, round(score_10 * 10)))


def _avg(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def _rubric_val(rubrics: dict[str, RubricScore], name: str) -> float:
    r = rubrics.get(name)
    return r.score if r else 5.0


def _build_category_scores(score: ResumeScoreResponse) -> CategoryScores:
    rb = score.resume_rubrics
    return CategoryScores(
        ats=_to_100(_rubric_val(rb, "ats_compatibility")),
        impact=_to_100(_avg([
            _rubric_val(rb, "specificity"),
            _rubric_val(rb, "relevance"),
        ])),
        clarity=_to_100(_rubric_val(rb, "clarity")),
        formatting=_to_100(_rubric_val(rb, "format_consistency")),
        credibility=_to_100(_avg([
            _rubric_val(rb, "authenticity"),
            _rubric_val(rb, "realism"),
        ])),
    )


def _build_credibility(score: ResumeScoreResponse) -> CredibilityInfo:
    rb = score.resume_rubrics
    cred_score = _avg([
        _rubric_val(rb, "authenticity"),
        _rubric_val(rb, "realism"),
    ])
    if cred_score >= 8.0:
        level = "high"
    elif cred_score >= 6.0:
        level = "medium"
    else:
        level = "low"

    signals: list[str] = []
    auth = rb.get("authenticity")
    if auth and auth.score >= 8:
        signals.append("Career progression looks consistent")
    real = rb.get("realism")
    if real and real.score >= 8:
        signals.append("Achievements appear realistic")
    gram = rb.get("grammar")
    if gram and gram.score >= 8:
        signals.append("Professional writing quality")
    if score.ats_audit.parseability.score >= 8:
        signals.append("Resume structure well-formed")
    if not signals:
        signals.append("Limited verification signals available")

    return CredibilityInfo(level=level, signals=signals)


def _role_label(role: RoleAnalysis) -> str:
    parts = [role.company or "Unknown Company"]
    if role.title:
        parts.append(role.title)
    return " > ".join(parts)


def _bullet_location_label(bullet: BulletAnalysis, roles: list[RoleAnalysis]) -> str:
    role = next((r for r in roles if r.id == bullet.role_id), None)
    base = _role_label(role) if role else "Unknown Role"
    return f"Experience > {base}"


def _issues_from_bullets(
    bullets: list[BulletAnalysis],
    roles: list[RoleAnalysis],
) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for bullet in bullets:
        role = next((r for r in roles if r.id == bullet.role_id), None)
        loc_label = _bullet_location_label(bullet, roles)
        location = IssueLocation(
            section_id="experience",
            bullet_id=bullet.id,
            line_hint=bullet.text[:60],
        )

        for tag in bullet.tags:
            sev = "moderate" if bullet.composite_score >= 5 else "critical"
            cat = "impact"
            if tag in ("Missing Metric", "Missing Scope"):
                cat = "impact"
            elif tag in ("Too Short", "Too Long", "Vague"):
                cat = "clarity"

            suggestion = ""
            for name, rubric in bullet.rubrics.items():
                if rubric.suggestion:
                    suggestion = rubric.suggestion
                    break

            issues.append(ReviewIssue(
                id=_issue_id("btag", f"{bullet.id}_{tag}"),
                title=tag,
                severity=sev,
                category=cat,
                description=f"Bullet: \"{bullet.text[:80]}...\"" if len(bullet.text) > 80 else f"Bullet: \"{bullet.text}\"",
                location_label=loc_label,
                location=location,
                original_text=bullet.text,
                suggested_text=suggestion,
                confidence=round(min(1.0, max(0.0, (10 - bullet.composite_score) / 10)), 2),
            ))

        for issue_text in bullet.issues:
            issues.append(ReviewIssue(
                id=_issue_id("biss", f"{bullet.id}_{issue_text}"),
                title=issue_text[:80],
                severity=_severity_from_score(bullet.composite_score),
                category="impact",
                description=issue_text,
                location_label=loc_label,
                location=location,
                original_text=bullet.text,
                suggested_text="",
                confidence=0.7,
            ))

    return issues


def _issues_from_roles(roles: list[RoleAnalysis]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for role in roles:
        location = IssueLocation(section_id="experience", line_hint=role.company)
        for issue_text in role.issues:
            sev = _severity_from_score(role.composite_score)
            issues.append(ReviewIssue(
                id=_issue_id("role", f"{role.id}_{issue_text}"),
                title=issue_text[:80],
                severity=sev,
                category="impact",
                description=issue_text,
                location_label=_role_label(role),
                location=location,
                confidence=0.75,
            ))
    return issues


def _issues_from_ats(score: ResumeScoreResponse) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    audit = score.ats_audit
    for i, issue_text in enumerate(audit.issues):
        issues.append(ReviewIssue(
            id=_issue_id("ats", f"ats_{i}_{issue_text}"),
            title=issue_text[:80],
            severity="moderate",
            category="ats",
            description=issue_text,
            location_label="ATS Compatibility",
            location=IssueLocation(section_id="ats"),
            suggested_text="",
            confidence=0.8,
        ))

    for name, rubric in [
        ("parseability", audit.parseability),
        ("section_completeness", audit.section_completeness),
        ("format_consistency", audit.format_consistency),
        ("keyword_coverage", audit.keyword_coverage),
    ]:
        if rubric.score < 7 and rubric.suggestion:
            issues.append(ReviewIssue(
                id=_issue_id("ats_rubric", name),
                title=f"{name.replace('_', ' ').title()} needs improvement",
                severity="moderate" if rubric.score >= 5 else "critical",
                category="ats" if name != "format_consistency" else "formatting",
                description=rubric.reason,
                location_label="Resume Structure",
                location=IssueLocation(section_id=name),
                suggested_text=rubric.suggestion,
                confidence=0.85,
            ))

    return issues


def _issues_from_rubrics(score: ResumeScoreResponse) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    cat_map = {
        "authenticity": "credibility",
        "realism": "credibility",
        "specificity": "impact",
        "clarity": "clarity",
        "grammar": "clarity",
        "relevance": "impact",
    }
    for name, rubric in score.resume_rubrics.items():
        if name in cat_map and rubric.score < 7 and rubric.suggestion:
            issues.append(ReviewIssue(
                id=_issue_id("rubric", name),
                title=f"{name.replace('_', ' ').title()} could be stronger",
                severity=_severity_from_score(rubric.score),
                category=cat_map[name],
                description=rubric.reason,
                location_label="Overall Resume",
                location=IssueLocation(section_id=name),
                suggested_text=rubric.suggestion,
                confidence=0.8,
            ))
    return issues


def _build_sections(
    parsed: ParsedResume,
    score: ResumeScoreResponse,
    all_issues: list[ReviewIssue],
) -> list[ResumeSectionView]:
    """Build renderable sections from parsed resume, linking issues to bullets."""
    bullet_issue_map: dict[str, list[str]] = {}
    role_issue_map: dict[str, list[str]] = {}
    for issue in all_issues:
        loc = issue.location
        if loc.bullet_id:
            bullet_issue_map.setdefault(loc.bullet_id, []).append(issue.id)
        if loc.section_id == "experience" and loc.line_hint:
            for role in score.roles:
                if role.company and loc.line_hint.startswith(role.company[:20]):
                    role_issue_map.setdefault(role.id, []).append(issue.id)

    sections: list[ResumeSectionView] = []

    if parsed.header:
        sections.append(ResumeSectionView(
            id="header",
            type="header",
            title="Contact",
            lines=[l for l in parsed.header.split("\n") if l.strip()],
        ))

    if parsed.summary:
        sections.append(ResumeSectionView(
            id="summary",
            type="summary",
            title="Summary",
            lines=[l for l in parsed.summary.split("\n") if l.strip()],
        ))

    if parsed.education:
        sections.append(ResumeSectionView(
            id="education",
            type="education",
            title="Education",
            lines=parsed.education,
        ))

    if parsed.roles:
        role_views: list[ResumeRoleView] = []
        for pr in parsed.roles:
            bullet_views: list[ResumeBulletView] = []
            for bt in pr.bullets:
                bt_key = bt[:60].strip().lower()
                bid = hashlib.md5(f"{pr.id}|{bt_key}".encode()).hexdigest()[:8]
                bullet_views.append(ResumeBulletView(
                    id=bid,
                    text=bt,
                    issue_ids=bullet_issue_map.get(bid, []),
                ))
            role_views.append(ResumeRoleView(
                id=pr.id,
                company=pr.company,
                title=pr.title,
                date_range=pr.date_range,
                bullets=bullet_views,
                issue_ids=role_issue_map.get(pr.id, []),
            ))
        sections.append(ResumeSectionView(
            id="experience",
            type="experience",
            title="Experience",
            roles=role_views,
        ))

    if parsed.skills:
        sections.append(ResumeSectionView(
            id="skills",
            type="skills",
            title="Technical Skills",
            lines=parsed.skills,
        ))

    for key, body in parsed.sections.items():
        norm = key.upper()
        if any(x in norm for x in ("EXPERIENCE", "SKILL", "EDUCATION", "SUMMARY", "OBJECTIVE")):
            continue
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        if lines:
            sec_id = norm.lower().replace(" ", "_")
            sections.append(ResumeSectionView(
                id=sec_id,
                type="projects" if "PROJECT" in norm else "other",
                title=key.title(),
                lines=lines,
            ))

    return sections


def build_review(
    score: ResumeScoreResponse,
    parsed: ParsedResume | None = None,
    resume_id: str = "",
) -> ReviewResponse:
    """Transform a ResumeScoreResponse into a ReviewResponse."""
    if not resume_id:
        resume_id = hashlib.md5(score.summary.encode()).hexdigest()[:12]

    all_issues: list[ReviewIssue] = []
    all_issues.extend(_issues_from_rubrics(score))
    all_issues.extend(_issues_from_ats(score))
    all_issues.extend(_issues_from_roles(score.roles))
    all_issues.extend(_issues_from_bullets(score.bullets, score.roles))

    severity_order = {"critical": 0, "moderate": 1, "minor": 2}
    all_issues.sort(key=lambda i: severity_order.get(i.severity, 1))

    sections: list[ResumeSectionView] = []
    if parsed:
        sections = _build_sections(parsed, score, all_issues)

    return ReviewResponse(
        resume_id=resume_id,
        overall_score=_to_100(score.overall_score),
        category_scores=_build_category_scores(score),
        credibility=_build_credibility(score),
        issues=all_issues,
        sections=sections,
    )
