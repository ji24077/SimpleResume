"""Resume-related Pydantic models."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from resume_service.models.coaching import CoachingSection

PagePolicy = Literal["strict_one_page", "allow_multi"]


class PreviewSection(BaseModel):
    kind: str
    title: str
    subtitle: str | None = None
    bullets: list[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    latex_document: str
    preview_sections: list[PreviewSection]
    coaching: list[CoachingSection]
    pdf_page_count: int | None = None
    one_page_enforced: bool = False
    page_policy_applied: PagePolicy = "strict_one_page"
    revision_log: list[str] = Field(default_factory=list)
    revision_log_ko: list[str] = Field(default_factory=list)
    pdf_layout_underfull: bool | None = None
    density_expand_rounds: int = 0
    ats_issue_code: str | None = None
    quality_issues: list[dict[str, Any]] | None = None


class GenerateJsonBody(BaseModel):
    text: str
    page_policy: PagePolicy = "strict_one_page"
    contact_email: str = ""
    contact_linkedin: str = ""
    contact_phone: str = ""


class ParseResponse(BaseModel):
    """Result of POST /resume/parse — verify-parse stage feeds the editable form."""

    resume_data: dict[str, Any]
    parse_warnings: list[str] = Field(default_factory=list)


class GenerateFromStructuredBody(BaseModel):
    """Body for POST /resume/generate-from-structured — user-edited structured form."""

    resume_data: dict[str, Any]
    page_policy: PagePolicy = "strict_one_page"
