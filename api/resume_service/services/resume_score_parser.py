"""Resume text parser — splits raw text into structured sections, roles, and bullets."""

import hashlib
import re

from resume_service.models.resume_score import ParsedResume, ParsedRole

_SECTION_HEADINGS = re.compile(
    r"^(?:EDUCATION|EXPERIENCE|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE"
    r"|TECHNICAL\s+SKILLS|SKILLS|SUMMARY|OBJECTIVE|PROJECTS"
    r"|CERTIFICATIONS|AWARDS|PUBLICATIONS|VOLUNTEER|LEADERSHIP"
    r"|ACTIVITIES|INTERESTS|ADDITIONAL|LANGUAGES|RESEARCH)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_DATE_PATTERNS = re.compile(
    r"(?:"
    r"\d{1,2}/\d{4}"                       # MM/YYYY
    r"|\d{4}\s*[-–—]\s*(?:\d{4}|[Pp]resent)"  # YYYY -- YYYY or YYYY - Present
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}"
    r"|(?:Spring|Summer|Fall|Winter)\s+\d{4}"
    r"|Present|Current"
    r")",
    re.IGNORECASE,
)

_BULLET_CHARS = re.compile(r"^[\s]*[•●◦▪▸\-–—\*\u2022\u2023\u25E6]\s+")
_INDENTED_LINE = re.compile(r"^[ \t]{2,}\S")


def _role_id(company: str, title: str) -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def _extract_date_range(line: str) -> str:
    dates = _DATE_PATTERNS.findall(line)
    if len(dates) >= 2:
        return f"{dates[0]} – {dates[-1]}"
    if dates:
        return dates[0]
    return ""


def _is_section_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(_SECTION_HEADINGS.match(stripped))


def _split_sections(text: str) -> tuple[str, dict[str, str]]:
    """Return (header_text, {section_name: section_body})."""
    lines = text.split("\n")
    header_lines: list[str] = []
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if _is_section_heading(line):
            if current_section is not None:
                sections[current_section] = "\n".join(current_lines).strip()
            elif current_lines:
                header_lines = list(current_lines)
            current_section = line.strip().upper()
            current_lines = []
        else:
            if current_section is None:
                header_lines.append(line)
            else:
                current_lines.append(line)

    if current_section is not None:
        sections[current_section] = "\n".join(current_lines).strip()
    elif not header_lines:
        header_lines = lines[:5]

    return "\n".join(header_lines).strip(), sections


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _BULLET_CHARS.match(line) or _INDENTED_LINE.match(line):
            cleaned = _BULLET_CHARS.sub("", stripped).strip()
            if cleaned:
                bullets.append(cleaned)
    return bullets


def _extract_roles(experience_text: str) -> list[ParsedRole]:
    """Heuristic extraction of roles from experience text."""
    lines = experience_text.split("\n")
    roles: list[ParsedRole] = []
    current_company = ""
    current_title = ""
    current_date = ""
    current_bullets: list[str] = []

    def _flush():
        if current_company or current_title:
            roles.append(ParsedRole(
                id=_role_id(current_company, current_title),
                company=current_company,
                title=current_title,
                date_range=current_date,
                bullets=list(current_bullets),
            ))

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        is_bullet = bool(_BULLET_CHARS.match(lines[i])) or bool(_INDENTED_LINE.match(lines[i]))
        has_date = bool(_DATE_PATTERNS.search(line))

        if is_bullet:
            cleaned = _BULLET_CHARS.sub("", line).strip()
            if cleaned:
                current_bullets.append(cleaned)
            i += 1
            continue

        if has_date and not is_bullet:
            date_range = _extract_date_range(line)
            text_part = _DATE_PATTERNS.sub("", line).strip().strip("–—-|,. ")

            if current_company and not current_title:
                current_title = text_part if text_part else current_company
                current_date = date_range
            elif current_company and current_title and not current_bullets:
                current_title = text_part if text_part else current_title
                current_date = date_range
            else:
                _flush()
                current_bullets = []
                if i > 0 and not has_date:
                    current_company = text_part
                    current_title = ""
                else:
                    current_company = text_part
                    current_title = ""
                current_date = date_range
            i += 1
            continue

        _flush()
        current_bullets = []
        current_company = line
        current_title = ""
        current_date = ""

        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and not _BULLET_CHARS.match(lines[i + 1]):
                next_date = _extract_date_range(next_line)
                if next_date:
                    title_part = _DATE_PATTERNS.sub("", next_line).strip().strip("–—-|,. ")
                    current_title = title_part
                    current_date = next_date
                    i += 2
                    continue
                elif not _is_section_heading(next_line):
                    current_title = next_line
                    i += 2
                    continue

        i += 1

    _flush()
    return roles


def _extract_skills(skills_text: str) -> list[str]:
    skills: list[str] = []
    for line in skills_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        cleaned = _BULLET_CHARS.sub("", stripped).strip()
        parts = re.split(r"[,;|]", cleaned)
        for p in parts:
            s = p.strip().strip("•●◦▪▸-–—* ")
            if s and len(s) < 80:
                skills.append(s)
    return skills


def parse_resume(text: str) -> ParsedResume:
    """Parse raw resume text into a structured ParsedResume."""
    if not text or not text.strip():
        return ParsedResume(raw_text=text or "")

    header, sections = _split_sections(text)

    exp_keys = [k for k in sections if "EXPERIENCE" in k or k == "WORK EXPERIENCE"]
    experience_text = "\n\n".join(sections[k] for k in exp_keys)
    roles = _extract_roles(experience_text) if experience_text else []

    skill_keys = [k for k in sections if "SKILL" in k]
    skills_text = "\n\n".join(sections[k] for k in skill_keys)
    skills = _extract_skills(skills_text) if skills_text else []

    edu_keys = [k for k in sections if "EDUCATION" in k]
    education = []
    for k in edu_keys:
        for line in sections[k].split("\n"):
            stripped = line.strip()
            if stripped:
                education.append(stripped)

    summary_keys = [k for k in sections if k in ("SUMMARY", "OBJECTIVE")]
    summary = "\n".join(sections[k] for k in summary_keys).strip()

    all_bullets: list[str] = []
    for role in roles:
        all_bullets.extend(role.bullets)
    for key, body in sections.items():
        if key not in exp_keys:
            all_bullets.extend(_extract_bullets(body))

    return ParsedResume(
        raw_text=text,
        header=header,
        summary=summary,
        sections=sections,
        roles=roles,
        education=education,
        skills=skills,
        all_bullets=all_bullets,
    )
