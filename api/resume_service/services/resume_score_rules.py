"""Rule-based scoring engine for resume analysis."""

import difflib
import re

from resume_service.models.resume_score import RepairReadiness, RubricScore

_TECH_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "react", "angular", "vue", "node", "express", "django", "flask", "fastapi",
    "spring", "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "git", "ci/cd", "jenkins", "github actions", "linux", "bash",
    "machine learning", "deep learning", "tensorflow", "pytorch", "numpy",
    "pandas", "scikit-learn", "hadoop", "spark", "kafka", "rabbitmq",
    "rest", "graphql", "grpc", "microservices", "agile", "scrum",
    "html", "css", "sass", "tailwind", "webpack", "vite",
    "swift", "kotlin", "flutter", "react native",
}

_METRIC_PATTERN = re.compile(
    r"\d+\s*%"
    r"|\$\s*\d+"
    r"|\d+[kKmMbB]\+?"
    r"|\d+x\b"
    r"|\d+\s*(?:users?|customers?|clients?|requests?|transactions?)"
    r"|\d+\s*(?:hours?|days?|weeks?|months?|minutes?|seconds?)",
    re.IGNORECASE,
)


def detect_metric_presence(text: str) -> bool:
    return bool(_METRIC_PATTERN.search(text))


def score_parseability(parsed) -> RubricScore:
    score = 10.0
    reasons: list[str] = []

    if not parsed.raw_text.strip():
        return RubricScore(score=0, reason="No text extracted from resume.", suggestion="Ensure the file is readable.")

    if not parsed.sections:
        score -= 4
        reasons.append("No section headings detected")
    if not parsed.roles:
        score -= 3
        reasons.append("No work roles detected")
    if len(parsed.raw_text) < 100:
        score -= 2
        reasons.append("Very short text")

    score = max(0, score)
    reason = "; ".join(reasons) if reasons else "Resume parsed successfully with clear structure."
    suggestion = "Add clear section headings (EXPERIENCE, EDUCATION, SKILLS)." if score < 7 else ""
    return RubricScore(score=round(score, 1), reason=reason, suggestion=suggestion)


def score_section_completeness(parsed) -> RubricScore:
    score = 10.0
    missing: list[str] = []

    has_experience = any("EXPERIENCE" in k for k in parsed.sections)
    has_education = any("EDUCATION" in k for k in parsed.sections)
    has_skills = any("SKILL" in k for k in parsed.sections)

    if not has_experience:
        score -= 4
        missing.append("Experience")
    if not has_education:
        score -= 3
        missing.append("Education")
    if not has_skills:
        score -= 3
        missing.append("Skills")

    score = max(0, score)
    if missing:
        reason = f"Missing sections: {', '.join(missing)}."
        suggestion = f"Add {', '.join(missing)} section(s) to your resume."
    else:
        reason = "All core sections present."
        suggestion = ""
    return RubricScore(score=round(score, 1), reason=reason, suggestion=suggestion)


def score_format_consistency(parsed) -> RubricScore:
    score = 10.0
    issues: list[str] = []

    date_formats_found: set[str] = set()
    for role in parsed.roles:
        dr = role.date_range
        if not dr:
            continue
        if re.search(r"\d{1,2}/\d{4}", dr):
            date_formats_found.add("MM/YYYY")
        if re.search(r"[A-Z][a-z]+\.?\s+\d{4}", dr):
            date_formats_found.add("Month YYYY")
        if re.search(r"^\d{4}", dr):
            date_formats_found.add("YYYY")

    if len(date_formats_found) > 1:
        score -= 3
        issues.append(f"Mixed date formats: {', '.join(date_formats_found)}")

    bullet_styles: set[str] = set()
    for b in parsed.all_bullets:
        if b and b[0] in "•●◦▪▸":
            bullet_styles.add("symbol")
        elif b and b[0] == "-":
            bullet_styles.add("dash")
        else:
            bullet_styles.add("other")

    if len(bullet_styles) > 1:
        score -= 2
        issues.append("Inconsistent bullet point styles")

    roles_without_dates = sum(1 for r in parsed.roles if not r.date_range)
    if parsed.roles and roles_without_dates > 0:
        penalty = min(3, roles_without_dates * 1.5)
        score -= penalty
        issues.append(f"{roles_without_dates} role(s) missing date ranges")

    score = max(0, score)
    reason = "; ".join(issues) if issues else "Formatting is consistent across the resume."
    suggestion = "Standardize date formats and bullet styles." if issues else ""
    return RubricScore(score=round(score, 1), reason=reason, suggestion=suggestion)


def score_keyword_coverage(parsed, job_description: str = "") -> RubricScore:
    text_lower = parsed.raw_text.lower()
    found = {kw for kw in _TECH_KEYWORDS if kw in text_lower}
    count = len(found)

    if job_description:
        jd_lower = job_description.lower()
        jd_words = set(re.findall(r"[a-z][a-z+#/.]+", jd_lower))
        resume_words = set(re.findall(r"[a-z][a-z+#/.]+", text_lower))
        overlap = jd_words & resume_words
        jd_ratio = len(overlap) / max(len(jd_words), 1)
        score = min(10, jd_ratio * 12 + count * 0.3)
        reason = f"Matched {len(overlap)}/{len(jd_words)} JD keywords; {count} tech terms found."
        suggestion = "Tailor resume keywords to match the job description." if score < 7 else ""
    else:
        score = min(10, count * 0.8)
        reason = f"Found {count} recognized technical keywords."
        suggestion = "Add more specific technical keywords." if score < 7 else ""

    return RubricScore(score=round(max(0, score), 1), reason=reason, suggestion=suggestion)


def score_bullet_heuristics(bullet_text: str) -> dict[str, RubricScore]:
    rubrics: dict[str, RubricScore] = {}

    # Concision
    length = len(bullet_text)
    if length <= 120:
        concision = 9.0
        concision_reason = "Good length."
    elif length <= 200:
        concision = 7.0
        concision_reason = "Acceptable but could be tighter."
    else:
        concision = max(3.0, 7.0 - (length - 200) / 50)
        concision_reason = f"Too long ({length} chars)."
    rubrics["concision"] = RubricScore(
        score=round(concision, 1),
        reason=concision_reason,
        suggestion="Shorten to under 120 characters." if concision < 7 else "",
    )

    # Information density
    text_lower = bullet_text.lower()
    tech_count = sum(1 for kw in _TECH_KEYWORDS if kw in text_lower)
    has_metric = detect_metric_presence(bullet_text)
    density = min(10, 4 + tech_count * 1.5 + (2 if has_metric else 0))
    rubrics["information_density"] = RubricScore(
        score=round(density, 1),
        reason=f"{tech_count} tech terms, {'has' if has_metric else 'no'} metrics.",
        suggestion="Add specific technologies or quantifiable results." if density < 7 else "",
    )

    # Metric presence
    metric_score = 9.0 if has_metric else 3.0
    rubrics["metric_presence"] = RubricScore(
        score=metric_score,
        reason="Contains quantifiable metric." if has_metric else "No metrics found.",
        suggestion="" if has_metric else "Add measurable outcomes (%, $, counts).",
    )

    # Readability
    words = bullet_text.split()
    word_count = len(words)
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
    if word_count <= 25 and avg_word_len < 8:
        readability = 9.0
        read_reason = "Clear and readable."
    elif word_count <= 40:
        readability = 7.0
        read_reason = "Slightly long but readable."
    else:
        readability = max(3.0, 7.0 - (word_count - 40) / 10)
        read_reason = f"Too wordy ({word_count} words)."
    rubrics["readability"] = RubricScore(
        score=round(readability, 1),
        reason=read_reason,
        suggestion="Break into shorter, more direct statements." if readability < 7 else "",
    )

    return rubrics


def score_repetition(bullets: list[str]) -> RubricScore:
    if len(bullets) < 2:
        return RubricScore(score=10.0, reason="Not enough bullets to assess repetition.", suggestion="")

    max_similarity = 0.0
    for i in range(len(bullets)):
        for j in range(i + 1, len(bullets)):
            ratio = difflib.SequenceMatcher(None, bullets[i].lower(), bullets[j].lower()).ratio()
            max_similarity = max(max_similarity, ratio)

    if max_similarity > 0.8:
        score = 3.0
        reason = f"High repetition detected (similarity {max_similarity:.0%})."
        suggestion = "Rewrite similar bullets to highlight different accomplishments."
    elif max_similarity > 0.6:
        score = 6.0
        reason = f"Moderate similarity between bullets ({max_similarity:.0%})."
        suggestion = "Differentiate bullet points more clearly."
    else:
        score = 9.0
        reason = "Good variety across bullet points."
        suggestion = ""

    return RubricScore(score=round(score, 1), reason=reason, suggestion=suggestion)


def compute_bullet_tags(bullet_text: str, rubrics: dict[str, RubricScore]) -> list[str]:
    tags: list[str] = []
    concision = rubrics.get("concision")
    if concision and concision.score < 6:
        tags.append("Too Long")

    metric = rubrics.get("metric_presence")
    if metric and metric.score < 5:
        tags.append("Missing Metric")

    density = rubrics.get("information_density")
    if density and density.score < 5:
        tags.append("Generic Tech")

    readability = rubrics.get("readability")
    if readability and readability.score < 5:
        tags.append("Low Impact")

    scope_words = {"team", "led", "managed", "owned", "drove", "spearheaded", "coordinated"}
    if not any(w in bullet_text.lower() for w in scope_words):
        tags.append("Missing Scope")

    all_scores = [r.score for r in rubrics.values()]
    avg = sum(all_scores) / max(len(all_scores), 1)
    if avg >= 8:
        tags.append("Strong Bullet")
    elif avg < 5:
        if any(r.score >= 4 for r in rubrics.values()):
            tags.append("Recoverable")

    return tags


def compute_repair_readiness(rubrics: dict[str, RubricScore]) -> RepairReadiness:
    missing: list[str] = []

    metric = rubrics.get("metric_presence")
    if metric and metric.score < 5:
        missing.append("missing_metric")

    density = rubrics.get("information_density")
    if density and density.score < 5:
        missing.append("low_specificity")

    concision = rubrics.get("concision")
    if concision and concision.score < 5:
        missing.append("verbose")

    readability = rubrics.get("readability")
    if readability and readability.score < 5:
        missing.append("poor_readability")

    all_scores = [r.score for r in rubrics.values()]
    avg = sum(all_scores) / max(len(all_scores), 1)

    if avg >= 7:
        recoverability = "low"
        priority = "low"
    elif avg >= 5:
        recoverability = "medium"
        priority = "medium"
    else:
        recoverability = "high"
        priority = "high"

    gain = max(0, (8 - avg) * 1.2)
    return RepairReadiness(
        recoverability=recoverability,
        missing_dimensions=missing,
        ask_back_priority=priority,
        revision_gain_potential=round(gain, 2),
    )
