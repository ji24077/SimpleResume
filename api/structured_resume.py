"""Shim: structured assembly in ``features.generation.structured_resume``."""

from features.generation.structured_resume import (
    ResumeSchemaError,
    build_latex_document,
    format_resume_validation_errors,
    parse_resume_data,
)

__all__ = [
    "ResumeSchemaError",
    "build_latex_document",
    "format_resume_validation_errors",
    "parse_resume_data",
]
