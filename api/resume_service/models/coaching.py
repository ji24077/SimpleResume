"""Coaching-related Pydantic models."""

from pydantic import BaseModel


class CoachingItem(BaseModel):
    why_better: str


class CoachingSection(BaseModel):
    section_why: str
    items: list[CoachingItem]
