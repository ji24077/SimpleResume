"""Pytest bootstrap: ensure ``api`` is on sys.path when running from repo root."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_API = _ROOT / "api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))
