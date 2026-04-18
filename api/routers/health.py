"""Backward-compatible shim — real router lives in resume_service.routers.health."""

from resume_service.routers.health import router  # noqa: F401
