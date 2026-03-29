"""Compile LaTeX to PDF using pdflatex (or tectonic)."""

import logging
import re
import unicodedata
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PREAMBLE_PATH = Path(__file__).resolve().parent / "dhruv_preamble.tex"

_INSTALL_HINT = (
    "Install TeX packages: macOS → `brew install --cask basictex` then "
    "`sudo tlmgr install collection-latexextra` (or MacTeX). "
    "Or use `brew install tectonic` and ensure it can fetch packages."
)


def _latex_log_error_excerpt(log: str) -> str:
    """Pull the real failure from pdflatex .log (skip long package-loading spam)."""
    if not log:
        return ""
    # Last occurrence of LaTeX error / fatal markers
    for marker in (
        "! LaTeX Error:",
        "! LaTeX Error",
        "! Undefined control sequence.",
        "! I can't find file",
        "! ",
        "Fatal error",
        "Emergency stop",
    ):
        idx = log.rfind(marker)
        if idx != -1:
            start = max(0, idx - 400)
            end = min(len(log), idx + 4500)
            return log[start:end].strip()
    # No '!' found — tail only
    return log[-5000:].strip()


def _extract_resume_body(latex: str) -> str:
    """Body inside \\begin{document}...\\end{document}, or heuristic if model skipped \\begin{document}."""
    latex = latex.strip()
    doc = re.search(
        r"\\begin\{document\}(.*)\\end\{document\}",
        latex,
        re.DOTALL | re.IGNORECASE,
    )
    if doc:
        body = doc.group(1).strip()
        # Some inputs can leave a trailing "\" from regex capture.
        body = re.sub(r"\\\s*$", "", body)
        return body
    m = re.search(r"\\begin\{document\}(.*)", latex, re.DOTALL | re.IGNORECASE)
    if m:
        body = re.sub(r"\\end\{document\}.*$", "", m.group(1), flags=re.DOTALL).strip()
        body = re.sub(r"\\\s*$", "", body)
        return body

    # Many models omit \\begin{document} after the macro block and jump to \\begin{center} / \\section
    tail = latex
    if re.search(r"(?i)%%%%%%\s*RESUME\s+STARTS\s+HERE", latex):
        parts = re.split(r"(?i)%%%%%%\s*RESUME\s+STARTS\s+HERE\s*%%%%%%\s*", latex, maxsplit=1)
        if len(parts) > 1:
            tail = parts[-1].strip()
    # First real document content
    start = re.search(
        r"(\\begin\{center\}|\\section\{)",
        tail,
    )
    if start:
        tail = tail[start.start() :].strip()
    tail = re.sub(r"\\end\{document\}\s*$", "", tail, flags=re.IGNORECASE).strip()
    # Strip accidental leading \\begin{document} without matching structure
    tail = re.sub(r"^\\begin\{document\}\s*", "", tail, flags=re.IGNORECASE).strip()
    tail = re.sub(r"\\\s*$", "", tail)
    return tail


def normalize_to_dhruv_template(latex: str) -> str:
    """
    Force Dhruv preamble/macros; wrap extracted body in exactly one \\begin{document}...\\end{document}.
    """
    latex = latex.strip()
    if not latex:
        return latex
    try:
        preamble = _PREAMBLE_PATH.read_text(encoding="utf-8").rstrip()
    except OSError:
        return latex
    body = _extract_resume_body(latex)
    if not body:
        body = r"\textit{(No resume body parsed; check model output.)}"
    return f"{preamble}\n\n\\begin{{document}}\n\n{body}\n\n\\end{{document}}\n"


# AI 출력에 흔한 유니코드 → tectonic/pdflatex "Text line contains an invalid character"
_UNICODE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("\u2014", "---"),  # em dash —
    ("\u2013", "--"),  # en dash –
    ("\u2012", "-"),  # figure dash
    ("\u2010", "-"),  # hyphen
    ("\u2011", "-"),  # non-breaking hyphen ‑ (often triggers invalid char)
    ("\u2212", "-"),  # minus sign − (not ASCII hyphen)
    ("\u2015", "-"),  # horizontal bar ―
    ("\u2028", " "),  # LINE SEPARATOR — common paste/AI culprit for "invalid character"
    ("\u2029", " "),  # PARAGRAPH SEPARATOR
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201b", "'"),  # single high-reversed
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u201e", '"'),  # double low-9
    ("\u2032", "'"),  # prime
    ("\u2033", '"'),
    ("\u2022", "-"),  # bullet •
    ("\u2023", "-"),
    ("\u2043", "-"),
    ("\u25cf", "-"),  # black circle
    ("\u25cb", "-"),  # white circle
    ("\u2026", "..."),  # …
    ("\u00a0", " "),  # NBSP
    ("\u2009", " "),  # thin space
    ("\u2002", " "),
    ("\u2003", " "),
    ("\u2004", " "),
    ("\u2005", " "),
    ("\u2006", " "),
    ("\u2007", " "),
    ("\u2008", " "),
    ("\u202f", " "),  # narrow NBSP
    ("\u200b", ""),  # ZWSP
    ("\u200c", ""),
    ("\u200d", ""),
    ("\u2060", ""),
    ("\ufeff", ""),  # BOM
    ("\uff5c", "|"),  # fullwidth vertical line ｜
    ("\uff1a", ":"),  # fullwidth colon ：
    ("\uff0c", ","),  # fullwidth comma ，
    ("\uff0e", "."),  # fullwidth period ．
    ("\u3001", ","),  # ideographic comma 、
    ("\u3002", "."),  # ideographic full stop 。
    ("\u3000", " "),  # ideographic space
)


def _drop_unicode_format_chars(tex: str) -> str:
    """Remove category Cf (format) chars — invisible but can trigger invalid char in TeX."""
    return "".join(ch for ch in tex if unicodedata.category(ch) != "Cf")


def _strip_control_chars_except_newline_tab(tex: str) -> str:
    """Remove Unicode Cc (control) except \\n, \\r, \\t — TeX often rejects other Cc as invalid."""
    out: list[str] = []
    for ch in tex:
        if unicodedata.category(ch) == "Cc" and ch not in "\n\r\t":
            continue
        out.append(ch)
    return "".join(out)


def sanitize_unicode_for_latex(tex: str) -> str:
    """
    Replace smart punctuation / invisible Unicode with ASCII-safe text so pdflatex
    does not die with 'Invalid character' on typical AI-generated resume lines.
    Standard library only; does not interpret LaTeX commands.
    """
    if not tex:
        return tex
    tex = tex.replace("\x00", "")
    for old, new in _UNICODE_REPLACEMENTS:
        tex = tex.replace(old, new)
    # Fullwidth alnum/punct → ASCII where NFKC maps them
    tex = unicodedata.normalize("NFKC", tex)
    # Re-apply dash fixes in case NFKC introduced variants
    for old, new in _UNICODE_REPLACEMENTS:
        tex = tex.replace(old, new)
    tex = _drop_unicode_format_chars(tex)
    tex = _strip_control_chars_except_newline_tab(tex)
    return tex


def sanitize_latex_for_overleaf(tex: str) -> str:
    """
    Fix common model mistakes that break Overleaf / pdflatex:
    - \\\\& → \\& (Misplaced alignment tab & inside \\resumeSubheading tabular)
    - \\href{}{Label} → Label (empty URL breaks hyperref / looks wrong)
    """
    if not tex:
        return tex
    bad = "\\\\&"  # two backslashes + & (LaTeX linebreak + tab char in tabular)
    good = "\\&"
    while bad in tex:
        tex = tex.replace(bad, good)
    tex = re.sub(r"\\href\{\s*\}\{([^}]*)\}", r"\1", tex)
    return tex


def _run_pdflatex(tex_file: Path, out_dir: Path) -> tuple[bool, dict[str, Any]]:
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        return False, {
            "engine": "pdflatex",
            "exit_code": None,
            "log_excerpt": "pdflatex not found in PATH",
        }
    last_code: int | None = None
    for _ in range(2):
        proc = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-output-directory={out_dir}",
                tex_file.name,
            ],
            cwd=str(out_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        last_code = proc.returncode
    pdf = out_dir / "resume.pdf"
    if pdf.is_file() and pdf.stat().st_size > 0:
        return True, {}
    log_path = out_dir / "resume.log"
    log_raw = ""
    if log_path.is_file():
        log_raw = log_path.read_text(encoding="utf-8", errors="replace")
    excerpt = _latex_log_error_excerpt(log_raw)
    if not excerpt and log_raw:
        excerpt = log_raw[-4000:]
    return False, {
        "engine": "pdflatex",
        "exit_code": last_code,
        "log_excerpt": excerpt,
        "log_bytes": len(log_raw),
    }


def _run_tectonic(tex_file: Path, out_dir: Path) -> tuple[bool, dict[str, Any]]:
    tectonic = shutil.which("tectonic")
    if not tectonic:
        return False, {"engine": "tectonic", "exit_code": None, "log_excerpt": "tectonic not found in PATH"}
    proc = subprocess.run(
        [tectonic, "--outdir", str(out_dir), str(tex_file)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    pdf = out_dir / "resume.pdf"
    if pdf.is_file() and pdf.stat().st_size > 0:
        return True, {}
    combined = (proc.stderr or "") + "\n" + (proc.stdout or "")
    excerpt = combined.strip()
    if len(excerpt) > 6000:
        excerpt = excerpt[-6000:]
    return False, {
        "engine": "tectonic",
        "exit_code": proc.returncode,
        "log_excerpt": excerpt,
    }


def _strip_problematic_inputs(tex: str) -> str:
    """BasicTeX often fails on glyphtounicode.tex (undefined control sequence)."""
    # Replace the *whole line* so we never leave trailing un-commented text
    # after the \input{glyphtounicode} token (this can happen when the input
    # is inside a comment).
    return re.sub(
        r"(?im)^[ \t]*%?[ \t]*\\input\s*\{\s*glyphtounicode\s*\}[^\n]*$",
        "% glyphtounicode skipped for portable compile",
        tex,
    )


def compile_latex_to_pdf(tex_source: str) -> tuple[bytes | None, dict[str, Any] | None]:
    """
    Returns (pdf_bytes, None) on success, or (None, error_detail) on failure.
    error_detail is JSON-serializable for HTTP 422 responses.
    """
    tex_source = _strip_problematic_inputs(tex_source.strip())
    tex_source = sanitize_unicode_for_latex(tex_source)
    tex_source = sanitize_latex_for_overleaf(tex_source)
    if not tex_source or "\\documentclass" not in tex_source:
        return None, {
            "code": "INVALID_TEX",
            "message": "Invalid LaTeX: missing \\documentclass",
            "attempts": [],
            "hint": _INSTALL_HINT,
        }

    with tempfile.TemporaryDirectory(prefix="sr_tex_") as tmp:
        out = Path(tmp)
        tex_path = out / "resume.tex"
        tex_path.write_text(tex_source, encoding="utf-8")

        attempts: list[dict[str, Any]] = []
        # tectonic first: better Unicode + package fetch; pdflatex fallback
        ok, info = _run_tectonic(tex_path, out)
        if not ok and info:
            attempts.append(info)
        if not ok:
            ok2, info2 = _run_pdflatex(tex_path, out)
            if not ok2 and info2:
                attempts.append(info2)
            ok = ok2

        pdf_path = out / "resume.pdf"
        if ok and pdf_path.is_file():
            data = pdf_path.read_bytes()
            logger.info("Compiled PDF: %d bytes", len(data))
            return data, None

        parts: list[str] = []
        for a in attempts:
            eng = a.get("engine", "?")
            ec = a.get("exit_code")
            ex = (a.get("log_excerpt") or "").strip()
            if ex:
                parts.append(f"[{eng}] exit={ec}\n{ex}")
            else:
                parts.append(f"[{eng}] exit={ec} (no excerpt)")

        message = "\n\n---\n\n".join(parts) if parts else "Compile failed with no log excerpt."
        detail: dict[str, Any] = {
            "code": "COMPILE_FAILED",
            "message": message[:12000],
            "attempts": attempts,
            "hint": _INSTALL_HINT,
            "debug": {
                "contains_begin_document": "\\begin{document}" in tex_source,
                "tex_preview_head": "\n".join(tex_source.splitlines()[:40]),
            },
        }
        logger.warning("LaTeX compile failed: %s", message[:500])
        return None, detail


def compiler_available() -> dict[str, bool]:
    return {
        "pdflatex": bool(shutil.which("pdflatex")),
        "tectonic": bool(shutil.which("tectonic")),
    }
