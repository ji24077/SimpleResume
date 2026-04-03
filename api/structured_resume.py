"""
Deterministic LaTeX assembly from structured resume data (no LLM-authored TeX).

Flow: validate JSON-like dict → sanitize Unicode → escape every string field →
emit fixed macro structure (Dhruv preamble-compatible).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from compile_pdf import sanitize_unicode_for_latex


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
    p = Path(__file__).resolve().parent / "dhruv_preamble.tex"
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


class SkillsBlock(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    header: ResumeHeader
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
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
    proj = render_projects(data.projects)
    if proj:
        body_parts.append(proj)
    body_parts.append(render_skills(data.skills))
    body_parts.append("\\end{document}")
    body = "\n".join(body_parts)
    return f"{pre}\n\n{body}\n"
