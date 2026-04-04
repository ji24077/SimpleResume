"""Shared filesystem paths for ``features`` packages."""

from pathlib import Path

_FEATURES_ROOT = Path(__file__).resolve().parent

# Preamble ships with the PDF stack; prompts/structured assembly read the same file.
DHURV_PREAMBLE_PATH = _FEATURES_ROOT / "pdf_rendering" / "dhruv_preamble.tex"
