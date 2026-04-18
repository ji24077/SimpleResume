"""Resume Review response models — document-annotation-style issue data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IssueBBox(BaseModel):
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


class IssueLocation(BaseModel):
    page: int = 1
    bbox: IssueBBox | None = None
    section_id: str = ""
    bullet_id: str = ""
    line_hint: str = ""


class ReviewIssue(BaseModel):
    id: str
    title: str
    severity: str = Field(description="critical | moderate | minor")
    category: str = Field(description="ats | impact | clarity | formatting | credibility")
    description: str
    location_label: str = ""
    location: IssueLocation = Field(default_factory=IssueLocation)
    original_text: str = ""
    suggested_text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CategoryScores(BaseModel):
    ats: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    formatting: int = Field(ge=0, le=100)
    credibility: int = Field(ge=0, le=100)


class CredibilityInfo(BaseModel):
    level: str = Field(description="high | medium | low")
    signals: list[str] = Field(default_factory=list)


class ResumeBulletView(BaseModel):
    id: str
    text: str
    issue_ids: list[str] = Field(default_factory=list)


class ResumeRoleView(BaseModel):
    id: str
    company: str
    title: str
    date_range: str = ""
    bullets: list[ResumeBulletView] = Field(default_factory=list)
    issue_ids: list[str] = Field(default_factory=list)


class ResumeSectionView(BaseModel):
    id: str
    type: str = Field(description="header | summary | education | experience | skills | projects | other")
    title: str
    lines: list[str] = Field(default_factory=list)
    roles: list[ResumeRoleView] = Field(default_factory=list)
    issue_ids: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    resume_id: str
    overall_score: int = Field(ge=0, le=100)
    category_scores: CategoryScores
    credibility: CredibilityInfo
    issues: list[ReviewIssue] = Field(default_factory=list)
    sections: list[ResumeSectionView] = Field(default_factory=list)
