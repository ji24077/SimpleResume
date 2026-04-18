"""Path constants and timeouts (placeholder for future use)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = Path(__file__).resolve().parent.parent

LLM_TIMEOUT_SECONDS = 120
MAX_UPLOAD_SIZE_BYTES = 12 * 1024 * 1024
