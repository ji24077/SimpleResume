"""
Golden regression: structured resume_data → deterministic LaTeX body hash.

If this fails after an intentional template/body change, update
``expected/structured_minimal_document_body.sha256`` in the same PR and document why.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from features.generation.structured_resume import build_latex_document, parse_resume_data

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_EXPECTED = Path(__file__).resolve().parent / "expected"


def _document_body(tex: str) -> str:
    mark = "\\begin{document}"
    i = tex.find(mark)
    assert i != -1, "full LaTeX must contain \\begin{document}"
    return tex[i:]


def test_golden_minimal_resume_body_hash_unchanged() -> None:
    raw = json.loads((_FIXTURES / "minimal_resume_data.json").read_text(encoding="utf-8"))
    data = parse_resume_data(raw)
    tex = build_latex_document(data)
    body = _document_body(tex)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    expected = (_EXPECTED / "structured_minimal_document_body.sha256").read_text(encoding="utf-8").strip()
    assert digest == expected, (
        "Golden body hash drift. If preamble/body rendering changed intentionally, "
        f"update expected file. got={digest} expected={expected}"
    )
