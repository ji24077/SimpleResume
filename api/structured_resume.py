"""Shim: structured assembly in ``features.generation.structured_resume``."""

from features.generation.structured_resume import (
    ResumeData,
    ResumeSchemaError,
    build_latex_document,
    format_resume_validation_errors,
    parse_resume_data,
    resume_data_to_source_text,
)

__all__ = [
    "ResumeData",
    "ResumeSchemaError",
    "build_latex_document",
    "format_resume_validation_errors",
    "parse_resume_data",
    "resume_data_to_source_text",
]
