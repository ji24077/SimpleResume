"""Backward-compatible shim — real code lives in resume_service.config."""

from resume_service.config import *  # noqa: F401,F403
from resume_service.config import (  # noqa: F401 — explicit re-exports for type checkers
    API_DIR,
    Settings,
    logger,
    settings,
)
