"""Compile LaTeX to PDF using pdflatex (or tectonic)."""

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_PREAMBLE_PATH = Path(__file__).resolve().parent / "dhruv_preamble.tex"


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


def _run_pdflatex(tex_file: Path, out_dir: Path) -> tuple[bool, str]:
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        return False, "pdflatex not found"
    log_parts: list[str] = []
    for _ in range(2):
        proc = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={out_dir}",
                tex_file.name,
            ],
            cwd=str(out_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        log_parts.append(proc.stdout or "")
        log_parts.append(proc.stderr or "")
    pdf = out_dir / "resume.pdf"
    if pdf.is_file() and pdf.stat().st_size > 0:
        return True, ""
    log_path = out_dir / "resume.log"
    tail = ""
    if log_path.is_file():
        raw = log_path.read_text(encoding="utf-8", errors="replace")
        tail = raw[-6000:] if len(raw) > 6000 else raw
    return False, "\n".join(log_parts)[-4000:] + "\n--- log tail ---\n" + tail


def _run_tectonic(tex_file: Path, out_dir: Path) -> tuple[bool, str]:
    tectonic = shutil.which("tectonic")
    if not tectonic:
        return False, "tectonic not found"
    proc = subprocess.run(
        [tectonic, "--outdir", str(out_dir), str(tex_file)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    pdf = out_dir / "resume.pdf"
    if pdf.is_file():
        return True, ""
    return False, (proc.stderr or proc.stdout or "tectonic failed")[-5000:]


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


def compile_latex_to_pdf(tex_source: str) -> tuple[bytes | None, str]:
    """
    Returns (pdf_bytes, error_message). error_message empty on success.
    """
    tex_source = _strip_problematic_inputs(tex_source.strip())
    if not tex_source or "\\documentclass" not in tex_source:
        return None, "Invalid LaTeX: missing documentclass"

    with tempfile.TemporaryDirectory(prefix="sr_tex_") as tmp:
        out = Path(tmp)
        tex_path = out / "resume.tex"
        tex_path.write_text(tex_source, encoding="utf-8")

        ok, err = _run_pdflatex(tex_path, out)
        if not ok:
            ok, err = _run_tectonic(tex_path, out)

        pdf_path = out / "resume.pdf"
        if ok and pdf_path.is_file():
            data = pdf_path.read_bytes()
            logger.info("Compiled PDF: %d bytes", len(data))
            return data, ""

        hint = (
            err
            + "\n\nInstall: macOS → MacTeX or `brew install --cask basictex` then `tlmgr install collection-latexextra` "
            "or use `brew install tectonic`."
        )
        # Debug aid: show whether the generated tex actually contains \\begin{document}.
        contains_begin_doc = "\\begin{document}" in tex_source
        first_lines = "\n".join(tex_source.splitlines()[:35])
        debug = (
            f"\n\n--- debug: contains \\begin{{document}}={contains_begin_doc} ---\n"
            + first_lines
            + "\n--- end debug ---"
        )
        return None, (hint + debug)[:8000]


def compiler_available() -> dict[str, bool]:
    return {
        "pdflatex": bool(shutil.which("pdflatex")),
        "tectonic": bool(shutil.which("tectonic")),
    }
