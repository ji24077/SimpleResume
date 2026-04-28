"""
Deterministic LaTeX assembly from structured resume data (no LLM-authored TeX).

Flow: validate JSON-like dict → sanitize Unicode → escape every string field →
emit fixed macro structure (Dhruv preamble-compatible).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from compile_pdf import sanitize_unicode_for_latex
from features.paths import DHURV_PREAMBLE_PATH


class ResumeSchemaError(Exception):
    """resume_data failed Pydantic / layout validation; carries LLM-facing error lines."""

    def __init__(self, errors: list[str], model_response: dict[str, Any]) -> None:
        self.errors = errors
        self.model_response = model_response
        super().__init__(str(errors))


def format_resume_validation_errors(exc: ValidationError) -> list[str]:
    """Turn Pydantic errors into SCHEMA_ERROR lines (paths under resume_data.*)."""
    lines: list[str] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        path = "resume_data"
        for x in loc:
            if isinstance(x, int):
                path += f"[{x}]"
            else:
                path += f".{x}"
        msg = err.get("msg", "invalid")
        if isinstance(msg, str) and msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        lines.append(f"- {path}: {msg}")
    return lines


# LaTeX special characters in ordinary text (pdflatex).
_SPECIALS: tuple[tuple[str, str], ...] = (
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("^", r"\textasciicircum{}"),
    ("~", r"\textasciitilde{}"),
)


def escape_latex(text: str) -> str:
    """Escape user-controlled strings for use inside \\resumeItem / \\resumeSubheading arguments."""
    for k, v in _SPECIALS:
        text = text.replace(k, v)
    return text


def tex_plain(s: str) -> str:
    """Unicode-safe + LaTeX-escaped fragment for resume body text."""
    return escape_latex(sanitize_unicode_for_latex(s))


def _load_preamble() -> str:
    p = DHURV_PREAMBLE_PATH
    try:
        return p.read_text(encoding="utf-8").rstrip()
    except OSError:
        return ""


class HeaderLink(BaseModel):
    label: str
    url: str

    @field_validator("label", "url")
    @classmethod
    def non_none(cls, v: str) -> str:
        return v if isinstance(v, str) else ""


class ResumeHeader(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = ""
    email: str = ""
    links: list[HeaderLink] = Field(default_factory=list)

    @field_validator("name", "phone", "email")
    @classmethod
    def strip_str(cls, v: str) -> str:
        return (v or "").strip() if isinstance(v, str) else ""


class EducationEntry(BaseModel):
    school: str
    degree: str
    date: str
    location: str = ""
    bullets: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    title: str
    company: str
    date: str
    location: str = ""
    bullets: list[str] = Field(..., min_length=1)


class ProjectEntry(BaseModel):
    name: str
    date: str = ""
    tech_line: str = ""
    """Optional stack / subtitle (plain text; escaped)."""
    bullets: list[str] = Field(default_factory=list)


class PublicationEntry(BaseModel):
    title: str = Field(..., min_length=1)
    authors: list[str] = Field(default_factory=list)
    self_name: str = ""
    """Substring within ``authors`` to bold (e.g. ``"A. Anand"``); case-insensitive match."""
    venue: str = ""
    """Italic full venue name (e.g. ``"European Conference on Computer Vision"``)."""
    venue_short: str = ""
    """Bold short venue or abbreviation (e.g. ``"ECCV 2026"``); falls back to ``year`` if empty."""
    year: str = ""
    type: str = ""
    """Free text or one of journal/conference/preprint/workshop. Not enum-locked."""
    status: str = ""
    """E.g. ``"Under review at"``, ``"Accepted at"``, ``"Published in"``, ``"To appear at"``."""
    link: str = ""
    """arXiv id, DOI, or full URL (rendered as plain text — no \\href wrap)."""


class SkillsBlock(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    header: ResumeHeader
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    publications: list[PublicationEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    skills: SkillsBlock

    @staticmethod
    def _nonempty_skill_items(vals: list[str]) -> bool:
        return any(isinstance(s, str) and s.strip() for s in vals)

    @model_validator(mode="after")
    def skills_must_have_some_content(self) -> ResumeData:
        sk = self.skills
        if not (
            self._nonempty_skill_items(sk.languages)
            or self._nonempty_skill_items(sk.frameworks)
            or self._nonempty_skill_items(sk.tools)
        ):
            raise ValueError(
                "At least one of skills.languages, skills.frameworks, or skills.tools "
                "must contain a non-empty string"
            )
        return self


def resume_data_json_schema_reference(*, max_chars: int = 14_000) -> str:
    """Subset of JSON Schema (from Pydantic) for LLM self-heal prompts."""
    schema = ResumeData.model_json_schema(mode="validation")
    raw = json.dumps(schema, ensure_ascii=False, indent=2)
    if len(raw) <= max_chars:
        return raw
    half = max_chars // 2 - 80
    return (
        raw[:half]
        + "\n\n[... truncated JSON Schema ...]\n\n"
        + raw[-half:]
    )


def parse_resume_data(raw: dict[str, Any]) -> ResumeData:
    """Pydantic validation after JSON parse; raises ValidationError on bad shape."""
    return ResumeData.model_validate(raw)


def _join_skill_line(items: list[str]) -> str:
    parts = [tex_plain(x.strip()) for x in items if isinstance(x, str) and x.strip()]
    return ", ".join(parts)


def render_header(h: ResumeHeader) -> str:
    name = tex_plain(h.name)
    phone = tex_plain(h.phone) if h.phone else ""
    email_raw = (h.email or "").strip()
    pieces: list[str] = []
    if phone:
        pieces.append(phone)
    if email_raw:
        em_disp = tex_plain(email_raw)
        pieces.append(f"\\href{{mailto:{email_raw}}}{{{em_disp}}}")
    for link in h.links:
        lab = (link.label or "").strip()
        url = (link.url or "").strip()
        if not lab or not url:
            continue
        pieces.append(f"\\href{{{tex_plain(url)}}}{{{tex_plain(lab)}}}")
    contact = " $|$ ".join(pieces) if pieces else ""
    block = (
        f"\\begin{{center}}\n"
        f"\\textbf{{\\Huge {name}}} \\\\ \\vspace{{4pt}}\n"
        f"\\small {contact}\n"
        f"\\end{{center}}\n"
        f"\\vspace{{-7pt}}\n"
    )
    return block


def render_education(entries: list[EducationEntry]) -> str:
    if not entries:
        return ""
    lines = ["\\section{Education}", "\\resumeSubHeadingListStart"]
    for edu in entries:
        school = tex_plain(edu.school)
        deg = tex_plain(edu.degree)
        dt = tex_plain(edu.date)
        loc = tex_plain(edu.location) if edu.location else ""
        lines.append(
            f"\\resumeSubheading\n{{{school}}}{{{dt}}}\n{{{deg}}}{{{loc}}}\n"
        )
        bs = [b for b in edu.bullets if isinstance(b, str) and b.strip()]
        if bs:
            lines.append("\\resumeItemListStart")
            for b in bs:
                lines.append(f"\\resumeItem{{{tex_plain(b)}}}")
            lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines) + "\n"


def render_experience(entries: list[ExperienceEntry]) -> str:
    if not entries:
        return ""
    lines = ["\\section{Experience}", "\\resumeSubHeadingListStart"]
    for exp in entries:
        title = tex_plain(exp.title)
        company = tex_plain(exp.company)
        dt = tex_plain(exp.date)
        loc = tex_plain(exp.location) if exp.location else ""
        lines.append(
            f"\\resumeSubheading\n{{{company}}}{{{dt}}}\n{{{title}}}{{{loc}}}\n"
        )
        lines.append("\\resumeItemListStart")
        for bullet in exp.bullets:
            if isinstance(bullet, str) and bullet.strip():
                lines.append(f"\\resumeItem{{{tex_plain(bullet)}}}")
        lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines) + "\n"


def render_projects(entries: list[ProjectEntry]) -> str:
    if not entries:
        return ""
    lines = ["\\section{Projects}", "\\resumeSubHeadingListStart"]
    for proj in entries:
        dt = tex_plain(proj.date) if proj.date else ""
        nm = tex_plain(proj.name)
        tech = proj.tech_line.strip() if proj.tech_line else ""
        if tech:
            left_tex = f"\\textbf{{{nm}}} | {tex_plain(tech)}"
        else:
            left_tex = f"\\textbf{{{nm}}}"
        lines.append(f"\\resumeProjectHeading{{{left_tex}}}{{{dt}}}\n")
        bs = [b for b in proj.bullets if isinstance(b, str) and b.strip()]
        if bs:
            lines.append("\\resumeItemListStart")
            for b in bs:
                lines.append(f"\\resumeItem{{{tex_plain(b)}}}")
            lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines) + "\n"


def render_publications(entries: list[PublicationEntry]) -> str:
    """Render Publications section using existing macros only (no preamble change).

    Layout per entry:
        \\textbf{<title>}, <authors w/ self bolded>\\newline
        <status> \\textit{<venue> \\textbf{<short-or-year>}}. <link>.
    Empty fields collapse cleanly.
    """
    if not entries:
        return ""
    lines = ["\\section{Publications}", "\\resumeSubHeadingListStart"]
    for pub in entries:
        title_tex = tex_plain(pub.title.strip())

        author_parts: list[str] = []
        self_norm = pub.self_name.strip().lower()
        for a in pub.authors:
            if not isinstance(a, str) or not a.strip():
                continue
            a_clean = a.strip()
            a_tex = tex_plain(a_clean)
            if self_norm and a_clean.lower() == self_norm:
                author_parts.append(f"\\textbf{{{a_tex}}}")
            else:
                author_parts.append(a_tex)
        authors_line = ", ".join(author_parts)

        venue_clean = pub.venue.strip()
        venue_tex = tex_plain(venue_clean) if venue_clean else ""
        bold_inner = pub.venue_short.strip() or pub.year.strip()
        bold_tex = tex_plain(bold_inner) if bold_inner else ""
        status_clean = pub.status.strip()
        status_tex = tex_plain(status_clean) if status_clean else ""
        link_clean = pub.link.strip()
        link_tex = tex_plain(link_clean) if link_clean else ""

        if venue_tex and bold_tex:
            venue_segment = f"\\textit{{{venue_tex} \\textbf{{{bold_tex}}}}}"
        elif venue_tex:
            venue_segment = f"\\textit{{{venue_tex}}}"
        elif bold_tex:
            venue_segment = f"\\textbf{{{bold_tex}}}"
        else:
            venue_segment = ""

        if status_tex and venue_segment:
            line2 = f"{status_tex} {venue_segment}"
        elif status_tex:
            line2 = status_tex
        elif venue_segment:
            line2 = venue_segment
        else:
            line2 = ""
        if line2 and not line2.rstrip().endswith("."):
            line2 += "."
        if link_tex:
            sep = " " if line2 else ""
            line2 = f"{line2}{sep}{link_tex}."

        if authors_line:
            first_line = f"\\textbf{{{title_tex}}}, {authors_line}"
        else:
            first_line = f"\\textbf{{{title_tex}}}"

        if line2:
            body = f"{first_line}\\newline\n{line2}"
        else:
            body = first_line
        lines.append(f"\\item[]\\small{{{body}}}")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines) + "\n"


def render_skills(sk: SkillsBlock) -> str:
    lang = _join_skill_line(sk.languages)
    fw = _join_skill_line(sk.frameworks)
    tools = _join_skill_line(sk.tools)
    inner = (
        f"\\textbf{{Languages}}{{{':' + lang}}} \\\\\n"
        f"\\vspace{{3pt}}\n"
        f"\\textbf{{Frameworks}}{{{':' + fw}}} \\\\\n"
        f"\\vspace{{3pt}}\n"
        f"\\textbf{{Tools}}{{{':' + tools}}}\n"
    )
    return (
        "\\section{Technical Skills}\n"
        "\\begin{itemize}[leftmargin=0in, label={}]\n"
        "\\item[]\\small{\n"
        f"{inner}"
        "}\n"
        "\\end{itemize}\n"
    )


def resume_data_to_source_text(data: ResumeData) -> str:
    """Serialize ResumeData → plain RESUME SOURCE text the generator LLM expects.

    Round-trip-friendly: preserves every bullet, date, title, and skill so the
    downstream pipeline sees the user's edits without a JSON-aware fast path.
    """
    lines: list[str] = []

    h = data.header
    if h.name.strip():
        lines.append(f"NAME: {h.name.strip()}")
    if h.email.strip():
        lines.append(f"EMAIL: {h.email.strip()}")
    if h.phone.strip():
        lines.append(f"PHONE: {h.phone.strip()}")
    visible_links = [
        link for link in h.links if (link.label or "").strip() and (link.url or "").strip()
    ]
    if visible_links:
        lines.append("LINKS:")
        for link in visible_links:
            lines.append(f"- {link.label.strip()}: {link.url.strip()}")

    if data.education:
        lines.append("")
        lines.append("=== EDUCATION ===")
        for edu in data.education:
            if edu.school.strip():
                lines.append(f"School: {edu.school.strip()}")
            if edu.degree.strip():
                lines.append(f"Degree: {edu.degree.strip()}")
            if edu.date.strip():
                lines.append(f"Date: {edu.date.strip()}")
            if edu.location.strip():
                lines.append(f"Location: {edu.location.strip()}")
            for b in edu.bullets:
                if isinstance(b, str) and b.strip():
                    lines.append(f"- {b.strip()}")
            lines.append("")

    if data.experience:
        lines.append("=== EXPERIENCE ===")
        for exp in data.experience:
            if exp.company.strip():
                lines.append(f"Company: {exp.company.strip()}")
            if exp.title.strip():
                lines.append(f"Title: {exp.title.strip()}")
            if exp.date.strip():
                lines.append(f"Date: {exp.date.strip()}")
            if exp.location.strip():
                lines.append(f"Location: {exp.location.strip()}")
            for b in exp.bullets:
                if isinstance(b, str) and b.strip():
                    lines.append(f"- {b.strip()}")
            lines.append("")

    if data.publications:
        lines.append("=== PUBLICATIONS ===")
        for pub in data.publications:
            if pub.title.strip():
                lines.append(f"Title: {pub.title.strip()}")
            authors_clean = [a.strip() for a in pub.authors if isinstance(a, str) and a.strip()]
            if authors_clean:
                lines.append(f"Authors: {', '.join(authors_clean)}")
            if pub.self_name.strip():
                lines.append(f"Self: {pub.self_name.strip()}")
            if pub.venue.strip():
                lines.append(f"Venue: {pub.venue.strip()}")
            if pub.venue_short.strip():
                lines.append(f"VenueShort: {pub.venue_short.strip()}")
            if pub.year.strip():
                lines.append(f"Year: {pub.year.strip()}")
            if pub.type.strip():
                lines.append(f"Type: {pub.type.strip()}")
            if pub.status.strip():
                lines.append(f"Status: {pub.status.strip()}")
            if pub.link.strip():
                lines.append(f"Link: {pub.link.strip()}")
            lines.append("")

    if data.projects:
        lines.append("=== PROJECTS ===")
        for proj in data.projects:
            if proj.name.strip():
                lines.append(f"Name: {proj.name.strip()}")
            if proj.tech_line.strip():
                lines.append(f"Tech: {proj.tech_line.strip()}")
            if proj.date.strip():
                lines.append(f"Date: {proj.date.strip()}")
            for b in proj.bullets:
                if isinstance(b, str) and b.strip():
                    lines.append(f"- {b.strip()}")
            lines.append("")

    sk = data.skills
    sk_langs = [s.strip() for s in sk.languages if isinstance(s, str) and s.strip()]
    sk_fws = [s.strip() for s in sk.frameworks if isinstance(s, str) and s.strip()]
    sk_tools = [s.strip() for s in sk.tools if isinstance(s, str) and s.strip()]
    if sk_langs or sk_fws or sk_tools:
        lines.append("=== SKILLS ===")
        if sk_langs:
            lines.append(f"Languages: {', '.join(sk_langs)}")
        if sk_fws:
            lines.append(f"Frameworks: {', '.join(sk_fws)}")
        if sk_tools:
            lines.append(f"Tools: {', '.join(sk_tools)}")

    return "\n".join(lines).rstrip() + "\n"


def build_latex_document(data: ResumeData, *, preamble: str | None = None) -> str:
    """Full .tex file: fixed preamble + deterministic body."""
    pre = (preamble if preamble is not None else _load_preamble()).rstrip()
    if not pre or "\\documentclass" not in pre:
        raise ValueError("Dhruv preamble missing or invalid (dhruv_preamble.tex).")

    body_parts = [
        "\\begin{document}",
        render_header(data.header),
    ]
    edu = render_education(data.education)
    if edu:
        body_parts.append(edu)
    exp = render_experience(data.experience)
    if exp:
        body_parts.append(exp)
    pubs = render_publications(data.publications)
    if pubs:
        body_parts.append(pubs)
    proj = render_projects(data.projects)
    if proj:
        body_parts.append(proj)
    body_parts.append(render_skills(data.skills))
    body_parts.append("\\end{document}")
    body = "\n".join(body_parts)
    return f"{pre}\n\n{body}\n"
