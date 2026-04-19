"""ResumeScore response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RubricScore(BaseModel):
    score: float = Field(ge=0, le=10)
    reason: str
    suggestion: str = ""


class RepairReadiness(BaseModel):
    recoverability: str = "medium"
    missing_dimensions: list[str] = Field(default_factory=list)
    ask_back_priority: str = "medium"
    revision_gain_potential: float = 0.0


class BulletAnalysis(BaseModel):
    id: str
    role_id: str
    text: str
    composite_score: float = Field(ge=0, le=10)
    rubrics: dict[str, RubricScore] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    rewrite: str = ""
    repair_readiness: RepairReadiness = Field(default_factory=RepairReadiness)


class RoleAnalysis(BaseModel):
    id: str
    company: str
    title: str
    date_range: str = ""
    composite_score: float = Field(ge=0, le=10)
    rubrics: dict[str, RubricScore] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class AtsAudit(BaseModel):
    parseability: RubricScore
    section_completeness: RubricScore
    format_consistency: RubricScore
    keyword_coverage: RubricScore
    issues: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    category: str
    text: str
    priority: str = "medium"
    expected_gain: float = 0.0


class ResumeScoreResponse(BaseModel):
    overall_score: float = Field(ge=0, le=10)
    grade: str
    summary: str
    top_strengths: list[str] = Field(default_factory=list)
    top_issues: list[str] = Field(default_factory=list)
    resume_rubrics: dict[str, RubricScore] = Field(default_factory=dict)
    roles: list[RoleAnalysis] = Field(default_factory=list)
    bullets: list[BulletAnalysis] = Field(default_factory=list)
    ats_audit: AtsAudit
    recommendations: list[Recommendation] = Field(default_factory=list)


class ResumeScoreTextBody(BaseModel):
    text: str
    job_description: str = ""


# --- Parsed resume structure (internal) ---

class ParsedBullet(BaseModel):
    text: str
    role_id: str = ""

class ParsedRole(BaseModel):
    id: str
    company: str
    title: str
    date_range: str = ""
    bullets: list[str] = Field(default_factory=list)

class ParsedResume(BaseModel):
    raw_text: str
    header: str = ""
    summary: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    roles: list[ParsedRole] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    all_bullets: list[str] = Field(default_factory=list)
