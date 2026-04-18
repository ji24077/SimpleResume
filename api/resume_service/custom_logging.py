"""Logging configuration (placeholder — Loguru integration, structured logs, etc.)."""

import logging


def setup_logging() -> None:
    """Configure application logging. Currently uses stdlib defaults."""
    logging.basicConfig(level=logging.INFO)
