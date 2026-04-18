"""Middleware registry (placeholder — Sentry, request logging, etc.)."""

from fastapi import FastAPI


def register_middleware(app: FastAPI) -> None:
    """Call from app factory to attach middleware. Currently a no-op placeholder."""
    pass
