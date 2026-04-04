"""Compile LaTeX to PDF: Docker + latexmk in TeX Live full only (no host TinyTeX/pdflatex)."""

import io
import logging
import os
import re
import unicodedata
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PREAMBLE_PATH = Path(__file__).resolve().parent / "dhruv_preamble.tex"
_TEX_ASSETS_DIR = Path(__file__).resolve().parent / "tex_assets"
_ASSET_SUFFIXES = frozenset(
    {".tex", ".sty", ".cls", ".bib", ".bst", ".png", ".jpg", ".jpeg", ".pdf", ".eps"}
)

_INSTALL_HINT = (
    "PDF requires Docker TeX Live (host latexmk/pdflatex/TinyTeX are disabled). "
    "From repo root: `docker compose build texlive`. In api/.env set "
    "LATEX_DOCKER_IMAGE=simpleresume-texlive:full, ensure Docker Desktop is running and "
    "`docker` is in PATH, then restart the API."
)


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _latexmk_argv(tex_basename: str) -> list[str]:
    """
    Overleaf-style multi-pass build; -no-shell-escape reduces arbitrary shell execution risk.
    %O %S are latexmk placeholders for options and the source file.
    """
    pdflatex_cmd = (
        "pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -no-shell-escape %O %S"
    )
    return [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"-pdflatex={pdflatex_cmd}",
        tex_basename,
    ]


def _docker_run_prefix() -> list[str]:
    """Extra isolation: default --network=none (override with LATEX_DOCKER_NETWORK=bridge)."""
    net = os.environ.get("LATEX_DOCKER_NETWORK", "none").strip() or "none"
    return ["docker", "run", "--rm", "--network", net]


def _latex_log_error_excerpt(log: str) -> str:
    """Pull the real failure from pdflatex .log (skip long package-loading spam)."""
    if not log:
        return ""
    markers = (
        "Something's wrong--perhaps a missing",
        "Lonely \\item",
        "LaTeX Error:",
        "! LaTeX Error:",
        "! LaTeX Error",
        "! Undefined control sequence.",
        "! I can't find file",
        "Runaway argument",
        "Emergency stop",
        "Fatal error",
        "! ",
    )
    best_idx = -1
    for marker in markers:
        idx = log.rfind(marker)
        if idx > best_idx:
            best_idx = idx
    if best_idx != -1:
        start = max(0, best_idx - 600)
        end = min(len(log), best_idx + 5000)
        return log[start:end].strip()
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
    Set env ``LATEX_PORTABLE_PREAMBLE=1`` to comment out ``fullpage`` / ``glyphtounicode`` in the preamble
    for a portable retry variant inside Docker (Docker full TeX usually leaves this off).
    """
    latex = latex.strip()
    if not latex:
        return latex
    try:
        preamble = _PREAMBLE_PATH.read_text(encoding="utf-8").rstrip()
    except OSError:
        return latex
    if _env_truthy("LATEX_PORTABLE_PREAMBLE"):
        preamble = _strip_fullpage_package(preamble)
        preamble = _strip_problematic_inputs(preamble)
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
    ("\u223c", r"$\sim$"),  # ∼ operator (invalid in many OT1 runs)
    ("\uff5e", " "),  # fullwidth tilde ～
    ("\u02dc", " "),  # small tilde ˜
    ("\u223f", " "),  # sine wave ∿
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
    # Tabs confuse column alignment and sometimes trigger odd breaks; use spaces in body text.
    tex = tex.replace("\t", " ")
    return tex


def _copy_optional_tex_assets(work_dir: Path) -> None:
    """Mirror Overleaf: extra .tex/.sty/.cls/images in the compile directory."""
    if not _TEX_ASSETS_DIR.is_dir():
        return
    for src in _TEX_ASSETS_DIR.iterdir():
        if not src.is_file() or src.name.startswith("."):
            continue
        if src.suffix.lower() not in _ASSET_SUFFIXES:
            continue
        try:
            shutil.copy2(src, work_dir / src.name)
        except OSError as e:
            logger.warning("Could not copy tex asset %s: %s", src.name, e)


def _unlink_resume_pdf(work_dir: Path) -> None:
    p = work_dir / "resume.pdf"
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


def _run_latexmk_docker(work_dir: Path, image: str) -> tuple[bool, dict[str, Any]]:
    """TeX Live full (or similar) in Docker — fixed environment, no host TinyTeX drift."""
    if not shutil.which("docker"):
        return False, {
            "engine": "latexmk-docker",
            "exit_code": None,
            "log_excerpt": "docker CLI not found in PATH",
        }
    host_mount = str(work_dir.resolve())
    proc = subprocess.run(
        _docker_run_prefix()
        + [
            "-v",
            f"{host_mount}:/work",
            "-w",
            "/work",
            image,
            *_latexmk_argv("resume.tex"),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    pdf = work_dir / "resume.pdf"
    if pdf.is_file() and pdf.stat().st_size > 0:
        return True, {}
    log_raw = ""
    log_path = work_dir / "resume.log"
    if log_path.is_file():
        log_raw = log_path.read_text(encoding="utf-8", errors="replace")
    excerpt = _latex_log_error_excerpt(log_raw)
    combined = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
    if not excerpt and combined:
        excerpt = combined[-8000:]
    return False, {
        "engine": "latexmk-docker",
        "exit_code": proc.returncode,
        "log_excerpt": excerpt or combined or "(no log)",
        "log_bytes": len(log_raw),
    }


def _normalize_tex_line_endings(tex: str) -> str:
    r"""CRLF / lone CR break LaTeX commands (e.g. ``\resume`` + CR + ``ProjectHeading`` → weird errors)."""
    if not tex:
        return tex
    return tex.replace("\r\n", "\n").replace("\r", "\n")


def _fix_line_start_missing_backslash_resume_project_heading(tex: str) -> str:
    r"""Model drops leading backslash: ``resumeProjectHeading{`` → ``\resumeProjectHeading{``."""
    return re.sub(r"(?m)^(\s*)resumeProjectHeading\s*\{", r"\1\\resumeProjectHeading{", tex)


def _skip_ws_tex_comments(s: str, start: int) -> int:
    """Advance index past spaces/newlines and %-to-EOL comments."""
    j = start
    n = len(s)
    while j < n:
        if s[j] in " \t\r\n\v\f":
            j += 1
            continue
        if s[j] == "%":
            while j < n and s[j] != "\n":
                j += 1
            if j < n:
                j += 1
            continue
        break
    return j


def _ensure_subheading_list_after_key_sections(tex: str) -> str:
    r"""
    Models sometimes emit ``\section{Education|Experience|Projects}`` then ``\resumeSubheading`` /
    ``\resumeProjectHeading`` / ``\resumeItemListStart`` without ``\resumeSubHeadingListStart``.
    The Dhruv macros require an outer ``itemize`` from ``\resumeSubHeadingListStart`` first.
    """
    pattern = re.compile(
        r"\\section\s*\{\s*(Education|Experience|Projects)\s*\}\s*",
        re.IGNORECASE,
    )
    out: list[str] = []
    pos = 0
    for m in pattern.finditer(tex):
        out.append(tex[pos : m.end()])
        pos = m.end()
        j = _skip_ws_tex_comments(tex, pos)
        rest = tex[j : j + 160].lstrip()
        if rest.startswith(r"\resumeSubHeadingListStart"):
            continue
        if re.match(
            r"\\resumeSubheading|\\resumeProjectHeading|\\resumeItemListStart",
            rest,
        ):
            out.append("\\resumeSubHeadingListStart\n")
    out.append(tex[pos:])
    return "".join(out)


def _fix_missing_item_before_resume_item_list(tex: str) -> str:
    r"""
    ``\resumeItemListStart`` expands to ``\begin{itemize}`` and must be nested inside a parent
    ``\item`` (normally from ``\resumeSubheading`` / ``\resumeProjectHeading``). If the model
    omits ``\resumeSubheading`` and puts ``\resumeItemListStart`` right after
    ``\resumeSubHeadingListStart``, insert ``\item[]`` (empty label item) so the inner list is legal.
    """
    pat = re.compile(
        r"(\\resumeSubHeadingListStart)((?:\s|%[^\n]*\n)*)(\\resumeItemListStart)",
    )

    def repl(mm: re.Match[str]) -> str:
        mid = mm.group(2)
        if r"\resumeSubheading" in mid or r"\resumeProjectHeading" in mid:
            return mm.group(0)
        return mm.group(1) + mid + r"\item[]" + "\n" + mm.group(3)

    prev = None
    while prev != tex:
        prev = tex
        tex = pat.sub(repl, tex)
    return tex


def _ensure_projects_subheading_list(tex: str) -> str:
    r"""
    ``\resumeProjectHeading`` expands to ``\item[]`` and must be inside ``\resumeSubHeadingListStart`` …
    ``End`` (same as Experience). Models often omit the outer list after ``\section{Project}`` /
    ``\section{Projects}``, which triggers interactive-style failures on the first project line.
    """
    pos = 0
    out: list[str] = []
    sec_re = re.compile(r"\\section\s*\{\s*Projects?\s*\}", re.IGNORECASE)
    while True:
        m = sec_re.search(tex, pos)
        if not m:
            out.append(tex[pos:])
            return "".join(out)
        out.append(tex[pos : m.start()])
        header_end = tex.find("\n", m.end())
        if header_end == -1:
            out.append(tex[m.start() :])
            return "".join(out)
        content_start = header_end + 1
        n = re.search(
            r"\\section\s*\{|\\end\s*\{\s*document\s*\}",
            tex[content_start:],
            flags=re.IGNORECASE,
        )
        block_end = content_start + (n.start() if n else len(tex) - content_start)
        block = tex[content_start:block_end]
        ph = block.find(r"\resumeProjectHeading")
        if ph != -1:
            rs = block.find(r"\resumeSubHeadingListStart")
            if rs == -1 or rs > ph:
                wrapped = (
                    "\n"
                    + r"\resumeSubHeadingListStart"
                    + "\n"
                    + block.rstrip()
                    + "\n"
                    + r"\resumeSubHeadingListEnd"
                    + "\n"
                )
                out.append(tex[m.start() : content_start] + wrapped)
                pos = block_end
                continue
        out.append(tex[m.start() : block_end])
        pos = block_end


def _fix_typo_extbf(tex: str) -> str:
    r"""Model drops backslash: ``extbf{`` → ``\textbf{`` (e.g. ``\resumeSubheading{..}{}{ extbf{Title}}{}``)."""
    tex = re.sub(r"\}\s*\{\s*extbf\s*\{", r"}{\\textbf{", tex)
    tex = re.sub(r"\{\s*extbf\s*\{", r"{\\textbf{", tex)
    tex = re.sub(r"(?<![\\a-zA-Z])extbf\s*\{", r"\\textbf{", tex)
    return tex


def _fix_line_start_missing_backslash_vspace(tex: str) -> str:
    r"""Model often emits ``vspace{4pt}`` after ``\\`` instead of ``\vspace{4pt}``."""
    return re.sub(r"(?m)^(\s*)vspace\{", r"\1\\vspace{", tex)


def _fix_lonely_resume_items_in_sublist(tex: str) -> str:
    r"""
    ``\resumeItem`` expands to ``\item`` and must sit inside ``\resumeItemListStart`` … ``End``.
    Sections like "Industry Designations" often omit the list wrapper (compile error near first ``\resumeItem``).
    """
    start_tok = r"\resumeSubHeadingListStart"
    end_tok = r"\resumeSubHeadingListEnd"
    pos = 0
    chunks: list[str] = []
    while pos < len(tex):
        i = tex.find(start_tok, pos)
        if i == -1:
            chunks.append(tex[pos:])
            break
        chunks.append(tex[pos:i])
        depth = 1
        j = i + len(start_tok)
        end_pos = -1
        while j < len(tex) and depth > 0:
            ns = tex.find(start_tok, j)
            ne = tex.find(end_tok, j)
            if ne == -1:
                chunks.append(tex[i:])
                return "".join(chunks)
            if ns != -1 and ns < ne:
                depth += 1
                j = ns + len(start_tok)
            else:
                depth -= 1
                if depth == 0:
                    end_pos = ne
                    break
                j = ne + len(end_tok)
        if end_pos == -1:
            chunks.append(tex[i:])
            break
        inner = tex[i + len(start_tok) : end_pos]
        stripped = inner.strip()
        if (
            r"\resumeItem" in inner
            and r"\resumeItemListStart" not in inner
            and r"\resumeSubheading" not in inner
            and r"\resumeProjectHeading" not in inner
        ):
            inner_new = (
                "\n"
                + r"\resumeItemListStart"
                + "\n"
                + stripped
                + "\n"
                + r"\resumeItemListEnd"
                + "\n"
            )
            chunks.append(start_tok + inner_new + end_tok)
        else:
            chunks.append(tex[i : end_pos + len(end_tok)])
        pos = end_pos + len(end_tok)
    return "".join(chunks)


def _wrap_bare_https_after_pipe(tex: str) -> str:
    """Header lines often use bare ``https://...``; ``_`` in URL breaks text mode — wrap with ``\\url``."""
    prev = None
    while prev != tex:
        prev = tex
        tex = re.sub(
            r"(\$\|\$\s*)(https?://[^\s\\}%$]+)",
            r"\1\\url{\2}",
            tex,
        )
    return tex


def _fix_technical_skills_broken_linebreaks(tex: str) -> str:
    r"""
    Models often emit ``} \ `` (single backslash + space) before the next line instead of a proper
    LaTeX line break ``\\``. Fix only inside ``\section{Technical Skills}`` … ``\end{itemize}``.
    """
    m = re.search(
        r"(\\section\s*\{\s*Technical Skills\s*\}.*?\\end\s*\{\s*itemize\s*\})",
        tex,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return tex
    block = m.group(1)
    # Wrong: `} \` or `}  \` then newline; right: `}` then `\\` then newline.
    fixed = re.sub(
        r"(\})\s*\\\s*\n(?=\s*\\vspace)",
        r"}\n\\\\\n",
        block,
    )
    fixed = re.sub(
        r"(\})\s*\\\s*\n(?=\s*\\textbf)",
        r"}\n\\\\\n",
        fixed,
    )
    return tex[: m.start()] + fixed + tex[m.end() :]


def _fix_project_heading_literal_stack_placeholder(tex: str) -> str:
    r"""Prompt example ``| stack`` is sometimes copied verbatim; strip that placeholder after ``\textbf{...}``."""
    return re.sub(
        r"(\\textbf\{[^}]+\})\s*\|\s*stack\b",
        r"\1",
        tex,
        flags=re.IGNORECASE,
    )


def _fix_unclosed_center_before_first_section(tex: str) -> str:
    """
    If ``\\begin{center}`` opens the header but ``\\end{center}`` never closes before the first
    ``\\section``, pdfLaTeX often fails or renders a broken page. Insert ``\\end{center}`` before
    the usual ``\\vspace{-7pt}`` that precedes the first section, or before ``\\section`` if absent.
    """
    sec = re.search(r"\\section\s*\{", tex)
    if not sec:
        return tex
    doc = re.search(r"\\begin\s*\{\s*document\s*\}", tex, re.IGNORECASE)
    start_body = doc.end() if doc else 0
    span = tex[start_body : sec.start()]
    if r"\begin{center}" not in span:
        return tex
    if r"\end{center}" in span:
        return tex
    bc = start_body + span.find(r"\begin{center}")
    inner = tex[bc : sec.start()]
    vmark = r"\vspace{-7pt}"
    idx = inner.rfind(vmark)
    if idx != -1:
        insert_at = bc + idx
        return tex[:insert_at] + "\\end{center}\n\n" + tex[insert_at:]
    return tex[: sec.start()] + "\\end{center}\n\n" + tex[sec.start() :]


def sanitize_latex_for_overleaf(tex: str) -> str:
    """
    Fix common model mistakes that break Overleaf / pdflatex:
    - Missing ``\\end{center}`` before first ``\\section`` (header stuck inside center)
    - ``extbf`` typo instead of ``\\textbf``
    - Line-start ``vspace{`` → ``\\vspace{`` (missing backslash after ``\\\\``)
    - ``\\resumeItem`` without surrounding ``\\resumeItemListStart`` (e.g. Industry Designations block)
    - Bare ``https://`` after ``$|$`` → ``\\url{...}`` (underscores in URL)
    - \\\\& → \\& (Misplaced alignment tab & inside \\resumeSubheading tabular)
    - \\\\% → \\% (AI often emits double backslash before % → forced line break + broken layout)
    - \\href{}{Label} → Label (empty URL breaks hyperref / looks wrong)
    - CRLF / lone ``\\r`` normalized to ``\\n`` (prevents split macro names)
    - ``\\section{Project(s)}`` then ``\\resumeProjectHeading`` without ``\\resumeSubHeadingListStart`` → wrap
    - Line-start ``resumeProjectHeading{`` → ``\\resumeProjectHeading{``
    - ``\\textbf{...} | stack`` (literal placeholder) → drop ``| stack``
    - Technical Skills: ``} \\ `` before ``\\vspace`` / ``\\textbf`` → ``} \\\\`` newline
    - ``\\section{Education|Experience|Projects}`` without ``\\resumeSubHeadingListStart`` before
      subheading / project heading / item list → insert outer list
    - ``\\resumeSubHeadingListStart`` then ``\\resumeItemListStart`` with no ``\\resumeSubheading``
      between → insert ``\\item[]``
    """
    if not tex:
        return tex
    tex = _normalize_tex_line_endings(tex)
    tex = _fix_project_heading_literal_stack_placeholder(tex)
    tex = _fix_typo_extbf(tex)
    tex = _fix_line_start_missing_backslash_vspace(tex)
    tex = _fix_line_start_missing_backslash_resume_project_heading(tex)
    tex = _ensure_projects_subheading_list(tex)
    tex = _ensure_subheading_list_after_key_sections(tex)
    tex = _fix_missing_item_before_resume_item_list(tex)
    tex = _fix_lonely_resume_items_in_sublist(tex)
    tex = _wrap_bare_https_after_pipe(tex)
    tex = _fix_unclosed_center_before_first_section(tex)
    tex = _fix_technical_skills_broken_linebreaks(tex)
    bad = "\\\\&"  # two backslashes + & (LaTeX linebreak + tab char in tabular)
    good = "\\&"
    while bad in tex:
        tex = tex.replace(bad, good)
    badp = "\\\\%"  # two backslashes + % — almost always meant to be literal \\%
    goodp = "\\%"
    while badp in tex:
        tex = tex.replace(badp, goodp)
    tex = re.sub(r"\\href\{\s*\}\{([^}]*)\}", r"\1", tex)
    return tex


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


def _strip_fullpage_package(tex: str) -> str:
    """
    TinyTeX/BasicTeX often omit fullpage.sty; Overleaf/TeX Live full have it.
    Margins in our preamble still use \\addtolength, so layout stays close without fullpage.
    """
    return re.sub(
        r"(?im)^[ \t]*\\usepackage(?:\s*\[[^]]*\])?\s*\{\s*fullpage\s*\}\s*$",
        "% fullpage package omitted (TinyTeX/BasicTeX often lack fullpage.sty); margin lines below still apply",
        tex,
    )


_FA_STUB_AFTER_DOCCLASS = """
% SR: fontawesome5 unavailable — empty placeholders (install tlmgr package or Docker TeX Live for icons)
\\providecommand{\\faLinkedin}{}
\\providecommand{\\faGithub}{}
\\providecommand{\\faEnvelope}{}
\\providecommand{\\faPhone}{}
\\providecommand{\\faGlobe}{}
\\providecommand{\\faMapMarker}{}
\\providecommand{\\faIcon}[2][]{}
"""


def _strip_fontawesome5_package(tex: str) -> str:
    """Strip fontawesome5 for a portable retry variant if the model injected it."""
    stripped = re.sub(
        r"(?im)^[ \t]*\\usepackage(?:\s*\[[^]]*\])?\s*\{\s*fontawesome5\s*\}\s*$",
        "% fontawesome5 omitted — install: tlmgr install fontawesome5, or use Docker TeX Live",
        tex,
    )
    if stripped == tex:
        return tex
    m = re.search(r"(?m)^\\documentclass[^\n]*\n", stripped)
    if m:
        return stripped[: m.end()] + _FA_STUB_AFTER_DOCCLASS + stripped[m.end() :]
    return _FA_STUB_AFTER_DOCCLASS + stripped


def _should_use_portable_variant_order() -> bool:
    """Docker TeX Live full: prefer canonical preamble first; portable strips are last-resort retries."""
    return False


def _compile_variants(tex_source: str, *, portable_first: bool) -> list[tuple[str, str]]:
    """
    Deduped retries. portable_first: TinyTeX-safe order (drop fullpage / glyph / fontawesome first).
    Otherwise: canonical first (best for Docker TeX Live full).
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def push(label: str, t: str) -> None:
        if t in seen:
            return
        seen.add(t)
        out.append((label, t))

    no_fp = _strip_fullpage_package(tex_source)
    no_glyph = _strip_problematic_inputs(tex_source)
    both = _strip_problematic_inputs(no_fp)
    no_fp_fa = _strip_fontawesome5_package(no_fp)
    fullpage_glyph_fa = _strip_problematic_inputs(no_fp_fa)

    if portable_first:
        push("fullpage_glyph_fa_skipped", fullpage_glyph_fa)
        push("fullpage_and_glyphtounicode_skipped", both)
        push("fullpage_fontawesome_skipped", no_fp_fa)
        push("fullpage_skipped", no_fp)
        push("glyphtounicode_skipped", no_glyph)
        push("canonical", tex_source)
    else:
        push("canonical", tex_source)
        push("fullpage_skipped", no_fp)
        push("glyphtounicode_skipped", no_glyph)
        push("fullpage_and_glyphtounicode_skipped", both)
        push("fullpage_fontawesome_skipped", no_fp_fa)
        push("fullpage_glyph_fa_skipped", fullpage_glyph_fa)
    return out


def _try_compile_variant(work_dir: Path, variant_label: str) -> tuple[bool, list[dict[str, Any]]]:
    """
    Docker latexmk only (TeX Live full image). Host latexmk / tectonic / pdflatex are not used.
    """
    pdf_path = work_dir / "resume.pdf"
    attempts: list[dict[str, Any]] = []

    docker_image = os.environ.get("LATEX_DOCKER_IMAGE", "").strip()
    has_docker = bool(shutil.which("docker"))

    if not docker_image:
        return False, [
            {
                "engine": "latexmk-docker",
                "exit_code": None,
                "log_excerpt": (
                    "LATEX_DOCKER_IMAGE is not set. Set it in api/.env (e.g. "
                    "simpleresume-texlive:full) and run `docker compose build texlive` from the repo root."
                ),
                "variant": variant_label,
            }
        ]

    if not has_docker:
        return False, [
            {
                "engine": "latexmk-docker",
                "exit_code": None,
                "log_excerpt": (
                    "`docker` is not in PATH. Start Docker Desktop (or install the Docker CLI). "
                    "Host TeX / TinyTeX is not used for PDF builds."
                ),
                "variant": variant_label,
            }
        ]

    _unlink_resume_pdf(work_dir)
    ok, info = _run_latexmk_docker(work_dir, docker_image)
    if info:
        attempts.append({**info, "variant": variant_label})
    if ok and pdf_path.is_file() and pdf_path.stat().st_size > 0:
        return True, attempts
    return False, attempts


def compile_latex_to_pdf(tex_source: str) -> tuple[bytes | None, dict[str, Any] | None]:
    """
    Returns (pdf_bytes, None) on success, or (None, error_detail) on failure.
    error_detail is JSON-serializable for HTTP 422 responses.

    Uses a temp project dir (Overleaf-style): optional files from api/tex_assets/ plus resume.tex.
    Docker + latexmk in TeX Live full only. Retries alternate preamble variants if the canonical build fails.
    """
    tex_source = tex_source.strip()
    tex_source = sanitize_unicode_for_latex(tex_source)
    tex_source = sanitize_latex_for_overleaf(tex_source)
    if not tex_source or "\\documentclass" not in tex_source:
        return None, {
            "code": "INVALID_TEX",
            "message": "Invalid LaTeX: missing \\documentclass",
            "attempts": [],
            "hint": _INSTALL_HINT,
        }

    variants = _compile_variants(
        tex_source, portable_first=_should_use_portable_variant_order()
    )

    with tempfile.TemporaryDirectory(prefix="sr_tex_") as tmp:
        out = Path(tmp)
        _copy_optional_tex_assets(out)
        tex_path = out / "resume.tex"
        pdf_path = out / "resume.pdf"
        attempts: list[dict[str, Any]] = []

        for variant_label, tex in variants:
            tex_path.write_text(tex, encoding="utf-8")
            ok, variant_attempts = _try_compile_variant(out, variant_label)
            attempts.extend(variant_attempts)

            if ok and pdf_path.is_file() and pdf_path.stat().st_size > 0:
                data = pdf_path.read_bytes()
                logger.info("Compiled PDF: %d bytes (%s)", len(data), variant_label)
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


def count_pdf_pages_from_bytes(pdf_bytes: bytes) -> int:
    """
    Page count after compile (for 1-page enforcement).

    Order: ``pdfinfo`` (poppler) -> ``qpdf --show-npages`` -> ``pypdf`` (always available).
    CLI tools are optional on the host running the API; Docker TeX image is unrelated here
    because counting runs on the API process after PDF bytes are returned.
    """
    if not pdf_bytes:
        raise ValueError("empty PDF bytes")

    def _write_temp_pdf() -> Path:
        fd, path_str = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        p = Path(path_str)
        p.write_bytes(pdf_bytes)
        return p

    if shutil.which("pdfinfo"):
        tmp: Path | None = None
        try:
            tmp = _write_temp_pdf()
            out = subprocess.check_output(
                ["pdfinfo", str(tmp)],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            m = re.search(r"Pages:\s+(\d+)", out, re.IGNORECASE)
            if m:
                return int(m.group(1))
        except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError, OSError):
            pass
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)

    if shutil.which("qpdf"):
        tmp = None
        try:
            tmp = _write_temp_pdf()
            out = subprocess.check_output(
                ["qpdf", "--show-npages", str(tmp)],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=30,
            ).strip()
            if out.isdigit():
                return int(out)
        except (subprocess.CalledProcessError, ValueError, TimeoutError, OSError):
            pass
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def pdf_bottom_strip_mean_luminance(
    pdf_bytes: bytes,
    *,
    bottom_fraction: float = 0.15,
    dpi: int = 100,
) -> float | None:
    """
    Rasterize PDF page 1 (``pdftoppm``) and return mean grayscale (0-255) of the bottom
    ``bottom_fraction`` of the image. Used to calibrate "full page" vs underfull:
    measure your Overleaf golden PDF once, then set env or compare with margins.

    Returns ``None`` if ``pdftoppm``/Pillow are missing or rasterize fails.
    """
    if not shutil.which("pdftoppm"):
        return None
    try:
        from PIL import Image
    except ImportError:
        return None

    if not pdf_bytes or bottom_fraction <= 0 or bottom_fraction >= 0.9:
        return None

    tmpdir = tempfile.mkdtemp(prefix="sr-pdf-lum-")
    try:
        pdf_path = Path(tmpdir) / "doc.pdf"
        pdf_path.write_bytes(pdf_bytes)
        out_base = str(Path(tmpdir) / "p")
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-singlefile",
                f"-r{dpi}",
                "-f",
                "1",
                "-l",
                "1",
                str(pdf_path),
                out_base,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        png_path = Path(tmpdir) / "p.png"
        if not png_path.is_file():
            logger.warning("pdftoppm did not produce expected PNG")
            return None
        with Image.open(png_path) as im:
            gray = im.convert("L")
            w, h = gray.size
            if h < 20:
                return None
            y0 = max(0, int(h * (1.0 - bottom_fraction)))
            region = gray.crop((0, y0, w, h))
            pixels = region.getdata()
            n = region.size[0] * region.size[1]
            if n == 0:
                return None
            total = 0
            for px in pixels:
                total += int(px)
            return total / n
    except (subprocess.CalledProcessError, OSError, TimeoutError, ValueError) as e:
        logger.warning("pdf bottom luminance raster failed: %s", e)
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def pdf_first_page_bottom_underfull(
    pdf_bytes: bytes,
    *,
    bottom_fraction: float = 0.15,
    mean_threshold: float = 233.0,
    dpi: int = 100,
) -> bool | None:
    """True if bottom strip mean luminance >= ``mean_threshold`` (too much white)."""
    mean = pdf_bottom_strip_mean_luminance(
        pdf_bytes, bottom_fraction=bottom_fraction, dpi=dpi
    )
    if mean is None:
        return None
    return mean >= mean_threshold


def compiler_available() -> dict[str, Any]:
    docker_image = os.environ.get("LATEX_DOCKER_IMAGE", "").strip()
    has_docker = bool(shutil.which("docker"))
    latexmk = bool(shutil.which("latexmk"))
    pdflatex = bool(shutil.which("pdflatex"))
    tectonic = bool(shutil.which("tectonic"))
    docker_ready = bool(docker_image and has_docker)
    docker_network = os.environ.get("LATEX_DOCKER_NETWORK", "none").strip() or "none"

    pdf_compile = docker_ready

    hint: str | None = None
    if not docker_image:
        hint = (
            "Set LATEX_DOCKER_IMAGE=simpleresume-texlive:full in api/.env, run "
            "`docker compose build texlive` from the repo root, restart the API. "
            "Host latexmk/pdflatex is not used."
        )
    elif not has_docker:
        hint = (
            "Docker CLI not in PATH — start Docker Desktop. "
            "LATEX_DOCKER_IMAGE is set but PDF builds require a working `docker` command."
        )

    pdfinfo = bool(shutil.which("pdfinfo"))
    qpdf = bool(shutil.which("qpdf"))
    pdf_page_counter = "pdfinfo" if pdfinfo else ("qpdf" if qpdf else "pypdf")
    pdftoppm = bool(shutil.which("pdftoppm"))
    try:
        import PIL  # noqa: F401

        pillow_installed = True
    except ImportError:
        pillow_installed = False
    pdf_density_check_ready = bool(pdftoppm and pillow_installed)

    return {
        "pdflatex": pdflatex,
        "tectonic": tectonic,
        "latexmk": latexmk,
        "docker": has_docker,
        "latex_docker_image": docker_image or None,
        "latex_docker_ready": docker_ready,
        "latex_docker_only": True,
        "latex_docker_allow_fallback": False,
        "latex_docker_network": docker_network,
        "pdf_compile": pdf_compile,
        "compile_hint": hint,
        "pdfinfo": pdfinfo,
        "qpdf": qpdf,
        "pdf_page_counter": pdf_page_counter,
        "pdftoppm": pdftoppm,
        "pillow": pillow_installed,
        "pdf_density_check_ready": pdf_density_check_ready,
        "latex_portable_preamble": _env_truthy("LATEX_PORTABLE_PREAMBLE"),
    }
