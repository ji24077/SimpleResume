"""Role-separated prompts: Generator / Fixer / Densify / Checker (diagnose only)."""

from __future__ import annotations

import json
import re

from features.paths import DHURV_PREAMBLE_PATH

from .structured_resume import resume_data_json_schema_reference


def _load_preamble_hint() -> str:
    try:
        return DHURV_PREAMBLE_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


# =============================================================================
# 1) GENERATOR — first pass only (short system; policies live in user)
# =============================================================================

GENERATOR_SYSTEM = """You are a resume generation engine.

Strict rules:
- Output must be one valid JSON object only (no markdown fences).
- Keys must be exactly: latex_document, preview_sections, coaching — no other keys.
- The LaTeX preamble: copy === TEMPLATE === from the user message verbatim through the RESUME STARTS HERE line; do not change packages or macro names.
- Do not invent employers, roles, dates, metrics, technologies, or filler bullets; ground content in --- RESUME SOURCE ---. NEVER generate generic bullets like "Completed coursework in..." or "Developed strong skills..." if the source does not say that.
- Use ASCII in visible resume prose (no emoji or fancy Unicode punctuation).
- No commentary outside JSON.

You generate an ATS-friendly resume in LaTeX following the user message POLICIES and OUTPUT FORMAT.

**First pass — maximize, do not minimize (ZERO information loss):** Extract and **refine** every usable fact from --- RESUME SOURCE --- into strong bullets (verb + scope + tools + outcome). **100% fidelity:** no sourced metric, tool name, system, or scope clause may be dropped—for roles >4 months, preserve the exact bullet count from the source; for short stints (≤4 months), use 3–5 bullets. The first draft must be **rich** enough that a recruiter sees depth—not a sparse outline. The server compiles PDF and may tighten **filler** later; **you must not** pre-shrink into vague one-liners or token-length bullets to “save space.”
"""


# =============================================================================
# 2) FIXER — revision only (targeted edits; no full creative rewrite)
# =============================================================================

FIXER_SYSTEM = """You are a LaTeX revision engine.

Strict rules:
- Output must be one valid JSON object only (no markdown fences).
- Keys must be exactly: latex_document, preview_sections, coaching — same shape as the generator output.
- Apply only what the REVISION_SIGNAL block requests. Do not rewrite unrelated sections for style or “improvement.”
- Do not invent new facts (employers, dates, metrics, technologies).
- Preserve the template: preamble through RESUME STARTS HERE must stay identical to the required TEMPLATE (packages, macros, order).
- Replace latex_document with the full updated .tex; update preview_sections and coaching to match the edited content.

When REVISION_SIGNAL is **fit_one_page**: **100% denotative preservation**—after your edit, every technology name, number/metric, product/system, audience/scale phrase, and concrete noun phrase that appeared in CURRENT_LATEX must still appear somewhere (same meaning). You may delete **filler** (“successfully”, “various”, “in order to”) only—not facts. Never shorten by turning a specific bullet into a generic one.
"""

# Used only for REVISION_SIGNAL fix_compile_error (LaTeX path): minimal syntax repair, not a rewrite.
FIXER_COMPILE_ONLY_SYSTEM = """You are a LaTeX compiler repair assistant.

Your job is NOT to rewrite the resume.
Your job is NOT to improve wording.
Your job is NOT to change formatting or style for aesthetics.

Your ONLY goal: fix the LaTeX so that it compiles successfully (pdfLaTeX / latexmk).

STRICT RULES:
- Do NOT rewrite the entire document.
- Do NOT change bullet wording except the **minimum** characters required to fix a syntax error (e.g. escape a rogue `%`, fix `&` in tabular).
- Do NOT change spacing or vertical layout unless the compiler error cannot be fixed otherwise.
- Do NOT modify the preamble or package list (through RESUME STARTS HERE) except to fix a provable syntax error in that region—normally leave it untouched.
- Preserve all content and structure; minimal diff only.
- If the error is unmatched braces, fix only the mismatched braces.
- If the error is tabular alignment (`&` / `\\\\` count), fix only that row.
- If the error is a stray line-ending backslash or a broken macro name, fix only that.

**Dhruv / tabular resume macros:** ``\\resumeSubheading`` and ``\\resumeProjectHeading`` use ``tabular*``. Messages like **Extra right brace** or **alignment ... ended prematurely** usually mean an extra ``}``, a missing ``}``, or an unescaped ``%`` (comment eats the rest of the row) **inside one braced argument**. Fix **only** that argument—escape ``%`` as ``\\%``, keep ``\\&`` for ampersands—do not delete factual wording.

If the document would compile except for one minor syntax issue, fix **only** that issue and do not touch other sections.
Large-scale rewrites are forbidden.

OUTPUT: One JSON object only (no markdown fences). Required keys:
- "reason": short string—what was wrong and what you changed (one or two sentences).
- "latex_document": the **full** corrected `.tex` (entire file, same as input shape).

Optional (may be empty arrays; server may preserve UI fields if omitted):
- "preview_sections", "coaching" — only if you already have them; otherwise omit or use [].
"""


STRUCTURED_FIXER_COMPILE_ONLY_SYSTEM = """You repair structured resume_data so the server-rendered LaTeX compiles.

NOT a rewrite: change only the **minimum** plain-text edits in resume_data fields needed to fix the compile error (odd characters, unescaped content that breaks rendering, impossibly long tokens if the log implies it).
Do NOT invent employers, dates, metrics, or technologies. Do NOT add LaTeX commands inside strings.

OUTPUT: One JSON object only. Required keys:
- "reason": short explanation of the failure and your minimal fix.
- "resume_data": full corrected object (same schema as before).

Optional: "preview_sections", "coaching" (may be []—server may merge prior UI fields).
"""


FIX_COMPILE_JSON_KEYS = """
REQUIRED JSON keys:
- "reason" (string)
- "latex_document" (string — complete .tex)

Optional: "preview_sections", "coaching" (may be empty arrays).
"""


def fixer_compile_system() -> str:
    return FIXER_COMPILE_ONLY_SYSTEM.strip() + "\n"


def structured_fixer_compile_system() -> str:
    return STRUCTURED_FIXER_COMPILE_ONLY_SYSTEM.strip() + "\n"


def extract_latex_error_line_hint(log_text: str) -> str:
    """Best-effort line pointer from pdflatex/latexmk log for the user prompt."""
    if not log_text or not log_text.strip():
        return "(Line number not found in log; use ERROR_SNIPPET and the first error message.)"
    m = re.search(r"\bl\.(\d+)\b", log_text)
    if m:
        n = m.group(1)
        return f"Engine often reports the error as **l.{n}** (approx. line {n} in the submitted `.tex`)."
    m = re.search(r"resume\.tex:(\d+):", log_text)
    if m:
        n = m.group(1)
        return f"Log references **resume.tex:{n}** (approx. line {n})."
    m = re.search(r"line (\d+)", log_text, re.IGNORECASE)
    if m:
        return f"Log mentions **line {m.group(1)}**."
    return "(Line number not detected in ERROR_SNIPPET; search for the first `!` error line.)"


def extract_engine_line_numbers_from_log(log_text: str, max_lines: int = 6) -> list[int]:
    r"""Collect `resume.tex:NN:` / `l.NN` line refs from pdflatex / latexmk logs."""
    found: set[int] = set()
    for m in re.finditer(r"\./resume\.tex:(\d+):", log_text):
        found.add(int(m.group(1)))
    for m in re.finditer(r"\bl\.(\d+)\b", log_text):
        found.add(int(m.group(1)))
    return sorted(found)[:max_lines]


def latex_source_context_numbered(latex: str, line_numbers: list[int], *, pad: int = 10) -> str:
    """Numbered excerpt around engine-reported lines (matches submitted full `.tex`)."""
    if not latex.strip():
        return "(empty LaTeX source)"
    lines = latex.splitlines()
    n = len(lines)
    if not line_numbers:
        return (
            "(No line numbers parsed from ERROR_SNIPPET; inspect CURRENT_LATEX, especially "
            "any \\resumeSubheading / \\resumeProjectHeading / \\resumeItem arguments.)"
        )
    chunks: list[str] = []
    for ln in line_numbers:
        if ln < 1:
            continue
        i = ln - 1
        lo = max(0, i - pad)
        hi = min(n, i + pad + 1)
        chunks.append(f"--- source lines {lo + 1}–{hi} (engine reported near line {ln}) ---")
        for j in range(lo, hi):
            chunks.append(f"{j + 1:5d} | {lines[j]}")
    return "\n".join(chunks)


# =============================================================================
# 3) DENSIFY — safe density pass only
# =============================================================================

DENSIFY_SYSTEM = """You are a content refinement engine for resume LaTeX.

Strict rules:
- Output must be one valid JSON object only with keys: latex_document, preview_sections, coaching only.
- Do not invent new employers, projects, roles, dates, or metrics.
- Expand only by restructuring or elaborating wording already supported by CURRENT_LATEX (and ALLOWED_FACTS if present).
- Preserve quantified metrics already in the document; do not change section order or the verbatim TEMPLATE preamble.
- Do not add new projects or experiences unless explicitly listed under ALLOWED_FACTS.

**Density goals:** Fill excessive bottom whitespace by making Experience **fuller**: target as many \\resumeItem per role as the source has (commonly 4–8). **Restore** any detail that looks over-compressed (vague verbs where specifics existed): re-expand using **only** facts already present in CURRENT_LATEX (same technologies, numbers, systems—do not drop them to “sound simple”). Turn thin one-liners into **1–2 line** bullets; split overloaded bullets only when clarity improves; do not invent new claims.
"""


# =============================================================================
# 4) CHECKER — diagnose only (optional; no rewrite)
# =============================================================================

CHECKER_SYSTEM = """You are a resume quality auditor.

Strict rules:
- Do not rewrite the resume and do not output LaTeX.
- Do not suggest stylistic rewording for its own sake.
- Diagnose structural, impact, and ATS-risk patterns only.
- Output one JSON object only (no markdown fences) with a single key: issues (array of objects).
Each issue object: type (string), location_hint (string), fix_plan (string, actionable but short).
"""


# --- User blocks (generator user: template + policies + source) ----------------

LATEX_BODY_SHAPE = """
CRITICAL — LaTeX body shape (after the TEMPLATE marker line):

1) Immediately after the RESUME STARTS HERE line, you MUST have exactly:
   \\begin{document}
   then \\begin{center} ... \\end{center} with:
   - \\textbf{\\Huge <Name>} \\\\ \\vspace{4pt}
   - \\small phone $|$ \\href{mailto:you@x.com}{you@x.com} $|$ \\href{https://github.com/USER}{GitHub} $|$ \\href{https://linkedin.com/in/...}{LinkedIn} $|$ \\href{https://SITE}{site}
   NEVER \\href{}{Label} (empty URL). Use a real https URL or plain text (no \\href).
   You MUST close with \\end{center} before any \\section. Then (optional) \\vspace{-7pt} after \\end{center}. Never put \\section{...} inside an unclosed \\begin{center} — pdfLaTeX breaks.

2) Then \\vspace{-7pt} (only after \\end{center}, before first \\section)

2b) Summary section (only if present in source):
   \\section{Summary}
   \\begin{itemize}[leftmargin=0in, label={}]
     \\item[]\\small{1--2 concise lines: years-of-experience + domain + 1--2 strongest differentiators. No filler.}
   \\end{itemize}
   If the source has no summary/objective/profile section, skip this block entirely.

3) Education block EXACTLY (NEVER invent bullets for education—only include \\resumeItemListStart/End if the source lists specific honors, coursework, or activities under that school; otherwise just the \\resumeSubheading with no bullets):
   \\section{Education}
   \\resumeSubHeadingListStart
     \\resumeSubheading{School}{date range}{degree line with \\textbf{field}}{}
     \\resumeItemListStart
       \\resumeItem{...}
     \\resumeItemListEnd
   \\resumeSubHeadingListEnd

4) Experience block EXACTLY:
   \\section{Experience}
   \\resumeSubHeadingListStart
   \\resumeSubheading{Company}{dates}{Role title (Lang, Tech, Tech, Tech)}{}
   Third argument: normalized job title, then **parentheses** with **3–4** languages/frameworks/tools for **that** role (comma-separated, from the source). Developer IC roles use **Software Engineer** or **Software Engineer Intern** (see POLICIES below). Second argument **dates**: real range from the source, or **empty `{}`** if the source has no dates (never invent ranges).
   \\resumeItemListStart
   \\resumeItem{...}
   ...
   \\resumeItemListEnd
   Each \\resumeItem should carry **substance**: normally **one or two full sentences** worth of prose (natural line wrap), not a 5-word fragment—unless the source truly states only one atomic fact.
   (repeat subheading + item list for each job; fourth arg of \\resumeSubheading is always {} unless a city is required.)

   **CRITICAL list nesting:** After ``\\section{Education}``, ``\\section{Experience}``, or ``\\section{Projects}`` you MUST have ``\\resumeSubHeadingListStart`` before the first ``\\resumeSubheading``, ``\\resumeProjectHeading``, or ``\\resumeItemListStart``. Never place ``\\resumeItemListStart`` directly after ``\\resumeSubHeadingListStart`` without a ``\\resumeSubheading`` or ``\\resumeProjectHeading`` line in between (pdfLaTeX often stops at ``\\resumeItemListStart`` with an interactive prompt).

4b) Publications (only if the source has a Publications / Pubs / Selected Publications section — otherwise skip this block entirely):
   Use existing macros only (no preamble change). Each publication is one ``\\item[]\\small{...}`` row inside ``\\resumeSubHeadingListStart`` … ``\\resumeSubHeadingListEnd``.
   EXACTLY:
   \\section{Publications}
   \\resumeSubHeadingListStart
     \\item[]\\small{\\textbf{Paper Title}, A1, A2, \\textbf{Self Name}, A4\\newline
     Status \\textit{Full Venue Name \\textbf{ShortVenue Year}}. arXiv:0000.00000.}
   \\resumeSubHeadingListEnd
   - Bold the candidate's own name in the author list (match by header.name or initial form).
   - Italic outer wraps the venue; the abbreviation/year is bolded inside the italic.
   - Status prefixes (``Under review at``, ``Accepted at``, ``Published in``, ``To appear at``) come from the source — never invent.
   - Link goes last (arXiv id, DOI, or URL); render plain (no \\href wrap unless the source already provided a clickable URL).
   - **Never** invent papers, venues, or authors. If unsure, omit the block entirely.

5) Projects (if any) — **CRITICAL (compile will fail if skipped):**
   \\resumeProjectHeading uses \\item[] internally, so it MUST sit inside \\resumeSubHeadingListStart … \\resumeSubHeadingListEnd
   (same outer wrapper as Education/Experience). Never put \\resumeProjectHeading directly under \\section{Projects} with no wrapper.

   EXACTLY:
   \\section{Projects}
   \\resumeSubHeadingListStart
     \\resumeProjectHeading{\\textbf{ProjectName} | Comma, Separated, Techs}{dates or {}}
     **Never** output the literal word ``stack`` as a placeholder---use **real** technologies from --- RESUME SOURCE --- (e.g. ``React, Flask, LangChain``).
     \\resumeItemListStart
       \\resumeItem{...}
     \\resumeItemListEnd
     Aim for **2–4** \\resumeItem per project when the source describes work (same substance as Experience).
     (repeat heading + item list per project)
   \\resumeSubHeadingListEnd

6) Close ALL open lists: \\resumeSubHeadingListEnd after the last experience/project block.

7) Technical Skills EXACTLY this shape (three lines with \\vspace{3pt} between).
   **Content rules for skills:** Keep as many skills from the source as possible — preserve the original breadth. But: (a) remove true duplicates and overlaps (e.g. if "Pandas" and "Python" both listed, keep both but don’t list "Python3" separately), (b) drop vague/non-technical filler ("Microsoft Office", "Communication", "Teamwork"), (c) group intuitively: Languages = programming languages, Frameworks = libraries/frameworks/platforms, Tools = infrastructure/DevOps/databases/visualization.
   **Do NOT shrink the list aggressively** — a dense skills section is good for ATS.
   \\section{Technical Skills}
   \\begin{itemize}[leftmargin=0in, label={}]
     \\item[]\\small{
       \\textbf{Languages}{: ...} \\\\
       \\vspace{3pt}
       \\textbf{Frameworks}{: ...} \\\\
       \\vspace{3pt}
       \\textbf{Tools}{: ...}
     }
   \\end{itemize}
   After each ``\\textbf{...}{: ...}`` line you MUST use **two** backslashes ``\\\\`` then newline---**not** a single ``\\`` with spaces (``\\ ``), which breaks layout.

8) End with \\end{document} only once.

9) Optional lines may be commented with % (e.g. old bullets). Every \\resumeItem must use valid LaTeX (escape $, %, &, #, ~). For a literal percent sign in text use a **single** backslash: `\\%`. Never write `\\\\%` (double backslash before %) — it forces a line break and breaks layout.

10) Ampersand in ANY argument of \\resumeSubheading, \\resumeItem, or plain text: use the LaTeX pair backslash-plus-ampersand only (one backslash before &). Example company names: Ernst backslash-ampersand Young. WRONG: two backslashes immediately before & (that is a line-break command then alignment tab — compile error in tabular).
"""

RESUME_RULES = """
POLICIES — content and style

Target **one** U.S. letter page **after** the server may request mild tightening. On the **first draft**, never sacrifice facts for length.

Retain **all** information from --- RESUME SOURCE --- (every school, job, project, skill, contact line, and fact). Reformat and tighten wording only; do not invent content.

**100% source fidelity (non-negotiable):**
- **Nothing sourced may vanish:** Every metric, technology name, library/API, team/audience scale, compliance label (e.g. WCAG), audit outcome, concrete deliverable, company name, role title, date range, GPA, certification, award, and course that appears in --- RESUME SOURCE --- must still appear in the resume (you may rephrase or move it to another bullet, but **not** omit it to look “cleaner” or shorter).
- **Do NOT summarize away detail:** If the source has 8 bullet points for one role, all 8 points must appear as 8 separate items (merge only true duplicates). Never reduce a rich description into a vague one-liner.
- **Do NOT drop sections:** If the source has a Summary, Objective, Profile, About Me, Awards, Certifications, or Publications section, you MUST include it. **Skip** Personal / Interests / Hobbies sections. Rename to standard headings if needed but never silently delete the content.
- Plain, simple English is fine; **omission** of a sourced fact is not. If one page is tight, the server may adjust layout later—you must **not** pre-remove detail.

**Maximize signal (first pass — required):**
- Read the **entire** source; do not stop after a shallow skim. Turn responsibilities, project blurbs, and bullet lists into **distinct** \\resumeItem lines—one achievement or theme per item when the text supports it.
- **Refine without deleting:** Normalize phrasing and strong verbs, but **surface** implied detail the source already suggests (e.g. stack, users, scale, integration partners) using **only** grounded facts—no new employers, numbers, or tools.
- If the source lists **more** than five points for one job, **keep every fact** (metrics, tools, scope)—output one \\resumeItem per distinct point. Merge **only** true duplicates; never drop detail to hit an arbitrary count.
- **Forbidden output style:** A resume where most Experience \\resumeItem bodies read like titles or tags (under ~10–12 words) **without** the source being that thin. When the source has depth, bullets must read like **sentences**, not keywords.

**Anti–over-compression (first pass):**
- Do **not** drop whole bullets, roles, or projects because you assume one page—you are not the PDF engine.
- If the source gives **many** distinct bullets for one job, output **one \\resumeItem per achievement**. Fold **only** true duplicate or overlapping facts; **never** cap bullets at an arbitrary number—preserve the source’s bullet count for roles >4 months.
- **Experience bullets (count + fidelity):**
- **Short roles (≤4 months / internships / co-ops):** 3–5 \\resumeItem max. Condense the source into strong, high-signal bullets.
- **Longer roles (>4 months):** Preserve the EXACT number of bullets from the source. If a role has 8 bullets, output 8 \\resumeItem. If it has 6, output 6. **Never** reduce count to fit an arbitrary limit—every original point must appear as its own \\resumeItem.
- **Sub-headings within experience:** If the source organizes bullets under sub-categories (e.g. "ETL and data pipelines:", "Data Infrastructure:", "Commercial charging:"), preserve them as bold text within a \\resumeItem like: \\resumeItem{\\textbf{ETL and data pipelines:}} followed by the relevant bullets. This preserves the original structure.

**Objective (bullets):**
- Mention specific technologies where the source names them.
- Include quantified impact when the source provides numbers (do not fabricate metrics).
- **Length:** Use a **mix of 1- and 2-line** bullets. **At least half** of Experience bullets (when the source is not tiny) should be **two lines** after PDF wrap or equivalently **two clauses joined** (context + outcome) in one \\resumeItem. Avoid a wall of identical one-line fragments.
- Avoid generic filler; keep verb + action + tech + outcome.

**Projects (when present):** Aim for **2–4** \\resumeItem per project when the source describes work beyond a title—same substance rules as Experience.

**Sections required:** Education, Experience, Projects (if relevant in the source), Technical Skills (or Technical Summary if the source uses that heading). **Do NOT include a Personal / Interests / Hobbies section** even if the source has one.
**Summary / Objective / Profile:** If the source contains a summary, objective, profile, or introductory paragraph, you MUST include it as \\section{Summary} placed immediately after the header and before Education. Rewrite it to be 1--2 lines only, impactful, and scannable: lead with years of experience + domain, then 1--2 strongest differentiators (e.g. scale, systems, outcomes). Cut generic filler ("passionate", "team player", "detail-oriented"). Never silently drop an intro section. HARD LIMIT: the Summary must not exceed 2 printed lines on the PDF.

**Header links:** Never leave placeholder URLs like ``github.com/USER``, ``linkedin.com/in/...``, or ``https://SITE``---use real https URLs from the source, or omit the link and show plain text (no ``\\href`` / ``\\url`` with fake paths).

**Experience line conventions:** (1) Third argument: `Software Engineer (3–4 techs from source)` or `Software Engineer Intern (...)` for dev IC roles; parentheses hold **3–4** stack items when possible. (2) Second argument: date range from source only, or `{}` if no dates given.

LaTeX text safety (pdflatex / ASCII-first body text):
- Inside \\resumeItem, \\resumeSubheading arguments, and visible prose: ASCII punctuation only unless part of a LaTeX command.
- Do NOT use: Unicode en-dash (–), em-dash (—), smart quotes, Unicode bullet (•), ellipsis (…), fullwidth punctuation, emoji.
- Company names like "Ernst & Young" must use \\& for ampersand; never two backslashes before & in tabular arguments.

Additional rules:
0. The server compiles your LaTeX to PDF. If the PDF is 2+ pages, it may request **fit_one_page** revisions that remove **filler words and spacing only**—not technologies, metrics, or scope. If one page looks under-empty at the bottom, it may request densification to **restore** fuller phrasing from facts already in the doc.
1. **Full coverage:** Every employer, role, internship (one \\resumeSubheading each), projects if listed, Technical Skills listing **every** technology from the source (group/abbreviate; do not omit). Map odd facts to the closest section rather than dropping them.
1b. **Same company, multiple titles/dates:** If the source lists separate positions (e.g. Frontend vs Backend vs DevOps), use **separate** \\resumeSubheading blocks—do not collapse into one role unless the source literally describes a single title.
2. One clear message per bullet. Bold numbers with \\textbf{...} inside \\resumeItem. Bold ~1 niche differentiating tech per bullet when it matters; do not bold generic stack (Python, SQL, React) by default.
3. **Role line + stack (third arg of \\resumeSubheading):** Title + parentheses with **3–4** technologies from the source for that role. If only 1–2 named, use those; do not invent.
4. **Developer titles:** Primarily software IC (FE/BE/full-stack/platform/DevOps-SRE coding, data/ML engineering with code, embedded) → **Software Engineer**; internship/co-op → **Software Engineer Intern**. Non-dev-centric roles: keep faithful to the source.
5. **Dates (second arg):** From source only; if none, use `{}`. No guessing; no `N/A` or em-dash placeholders unless the user literally wrote them.

Coaching: For each preview section, explain why the block is stronger (scanability, metrics, niche bolding, credibility).
"""

OUTPUT_FORMAT = """
OUTPUT FORMAT

Return a SINGLE JSON object (no markdown fences) with keys:
- "latex_document": string — FULL .tex file: **verbatim** === TEMPLATE === from this message through the RESUME STARTS HERE line, then \\begin{document} … \\end{document} in the structural shape under POLICIES.
- "preview_sections": array of objects for UI preview only:
  - "kind": one of "education" | "experience" | "project" | "skills"
  - "title": string (school, company, or project name)
  - "subtitle": string or null (degree, role, dates summary)
  - "bullets": array of plain-text strings (no LaTeX), what the reader sees
- "coaching": array aligned with preview_sections (same order and count):
  - "section_why": string — why this block works for recruiters / what improved vs generic resume
  - "items": array of objects, same length as bullets:
    - "why_better": string — why THIS bullet is stronger (e.g. metric bold, 1–2 line depth, niche tech)

If a section has no bullets (e.g. skills line), bullets can be one string; items one entry with why_better for the whole line.
"""

JSON_KEYS_REMINDER = """
You MUST return JSON with exactly these keys and no others:
- latex_document (string)
- preview_sections (array)
- coaching (array)
"""


def generator_system() -> str:
    return GENERATOR_SYSTEM.strip() + "\n"


def fixer_system() -> str:
    return FIXER_SYSTEM.strip() + "\n"


def densify_system() -> str:
    return DENSIFY_SYSTEM.strip() + "\n"


def checker_system() -> str:
    return CHECKER_SYSTEM.strip() + "\n"


def build_system_prompt() -> str:
    """Backward-compatible alias for the generator system prompt."""
    return generator_system()


def build_generation_user_message(raw: str) -> str:
    """Generator user: TEMPLATE + OUTPUT + OBJECTIVE/POLICIES + RESUME SOURCE."""
    template = _load_preamble_hint().strip()
    if not template:
        template = (
            "% TEMPLATE file missing on server — use letterpaper article + Dhruv resume macros "
            "from project api/features/pdf_rendering/dhruv_preamble.tex\n"
        )
    _marker = "%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%"
    objective = """
--- OBJECTIVE ---
Generate an ATS-friendly resume from --- RESUME SOURCE --- (one-page **target**; the server tightens wording if the PDF is too long).

**Maximize the first draft:** Your output should **feel full**—recruiter-grade detail from the source, not a stub. **100% of sourced facts** (numbers, tech names, systems, scope) must remain visible in the LaTeX—never sacrifice detail for a “simple” look.

**First draft:** Every role, project, skill, section, and fact line from the source should appear (rephrased), not summarized away. If the source has a Summary/Objective/Profile, include it as \\section{Summary}.
**Experience:** For roles >4 months, preserve the EXACT bullet count from the source (8 source bullets = 8 \\resumeItem). For short stints (≤4 months / internships), condense to 3–5 strong bullets. **Every** original detail must appear; merge **only** true duplicates. Each item **sentence-level**, not keyword-only.
**Projects:** **2–4** bullets when the source describes real work.

Bullets should:
- Mention specific technologies from the source.
- Include quantified impact only when the source supports it.
- **Mix 1- and 2-line** depth; prefer fuller lines over many tiny fragments; never merge **distinct** achievements into one vague line.

Sections required: Summary (if in source), Education, Experience, Projects (if relevant), Technical Skills.
Follow === POLICIES === for Dhruv-style LaTeX structure, title normalization, dates, and full coverage.
"""
    parts = [
        "=== TEMPLATE ===",
        f"Copy from the first line through the line containing exactly this marker (verbatim) at the start of latex_document:\n{_marker}",
        "",
        template,
        "",
        OUTPUT_FORMAT.strip(),
        JSON_KEYS_REMINDER.strip(),
        objective.strip(),
        "",
        "=== POLICIES ===",
        LATEX_BODY_SHAPE.strip(),
        "",
        RESUME_RULES.strip(),
        "",
        "--- RESUME SOURCE ---",
        raw.strip() if raw else "(empty)",
    ]
    return "\n".join(parts).strip() + "\n"


def revision_user_fit_one_page(*, latex: str, pages: int) -> str:
    return f"""REVISION_SIGNAL: fit_one_page

The document compiles to **{pages}** page(s); it must fit **exactly ONE** U.S. letter page.

**Hard rule — 100% factual preservation:** After editing, **every** technology name, number/metric, system/product, compliance or audit term, and concrete scope phrase that appears in CURRENT_LATEX must **still** appear (same meaning). You may rephrase for brevity but **forbidden:** dropping a specific tool/metric to replace with a generic verb; shortening a bullet so a sourced detail disappears.

Instructions (follow in order; stop when one page):
1) Optional **mild** negative \\vspace only where the template already uses \\vspace (do not break macros).
2) Remove **filler** only: empty intensifiers, redundant “that/which” clauses, “successfully/various/in order to”—**not** nouns, numbers, or tech names.
3) Tighten phrasing: same facts, fewer words **without** losing any named entity or number from step 0.
4) Only if still 2+ pages: merge two \\resumeItem lines **only** when they repeat the **same** outcome with no **exclusive** fact in either line.
5) **Last resort:** remove **one** bullet **only** if that bullet adds **no** exclusive fact vs the rest of the role (verify before deleting).

- Preserve every \\resumeSubheading (job/project); preserve bullet count unless step 5 applies.
- Do not remove entire sections. Do not invent facts. Do not change the verbatim TEMPLATE preamble.

{JSON_KEYS_REMINDER}

=== CURRENT_LATEX ===
{latex}
"""


def revision_user_fix_compile(*, latex: str, error_snippet: str) -> str:
    raw_log = error_snippet.strip() if error_snippet.strip() else ""
    line_nums = extract_engine_line_numbers_from_log(raw_log)
    source_ctx = latex_source_context_numbered(latex, line_nums)
    capped = raw_log if raw_log else "(no log detail)"
    if len(capped) > 12_000:
        capped = capped[:6000] + "\n\n[...truncated...]\n\n" + capped[-6000:]
    line_hint = extract_latex_error_line_hint(raw_log)
    return f"""REVISION_SIGNAL: fix_compile_error

The LaTeX failed to compile (pdfLaTeX / latexmk). Fix **only** syntax so it compiles.
**Preserve all resume content and wording** except the minimum edit required (e.g. escape ``%``, fix ``}}`` / ``&`` in tabular arguments).

=== ERROR_SNIPPET ===
{capped}

**Compilation error location hint:** {line_hint}

=== SOURCE_CONTEXT (numbered; same file as CURRENT_LATEX) ===
{source_ctx}

=== CURRENT_LATEX ===
{latex}

Return the **full** corrected document in JSON (see system message for keys).

{FIX_COMPILE_JSON_KEYS.strip()}
"""


def revision_user_fix_ats(*, latex: str, ats_issue: str) -> str:
    return f"""REVISION_SIGNAL: fix_ats_readability

The resume failed an ATS-style text extraction check.

=== ATS_ISSUE_CODE ===
{ats_issue}

Improve machine-readable structure without changing facts. Address the issue above (e.g. ensure standard section titles appear in reading order: Education before Experience when both exist).

Fix:
- Ensure section headings (Education, Experience, Technical Skills) remain clear in logical order.
- Avoid layout tricks that break reading order; keep the same template macros.
- Preserve content meaning; do not invent facts.

{JSON_KEYS_REMINDER}

=== CURRENT_LATEX ===
{latex}
"""


def revision_user_densify(*, latex: str, allowed_facts: str | None = None) -> str:
    """Safe mode by default; optional ALLOWED_FACTS block for controlled additions."""
    allowed_block = ""
    if allowed_facts and allowed_facts.strip():
        allowed_block = f"""
ALLOWED_FACTS (you may incorporate **only** these additional factual claims, nowhere else):
{allowed_facts.strip()}
"""
    return f"""REVISION_SIGNAL: densify

The bottom whitespace is excessive on an otherwise one-page PDF. Increase density without new employers or projects unless listed in ALLOWED_FACTS.

Increase density by:
- **Per role:** Preserve existing bullet count; expand thin bullets to fill the page. **Do not** shorten or remove bullets on this pass—**lengthen** thin lines so the page fills, using only facts already in CURRENT_LATEX.
- **Restore** specifics that were over-compressed (bring back tech names, subsystems, methods) if they still appear elsewhere in the document or can be split out from a dense line without inventing.
- Expanding technical detail (method, scope, stack) using wording already implied.
- Clarifying impact; slightly elaborating metrics **already present** (no new numbers).
- Prefer **mix of 1- and 2-line** bullets over many identical one-line fragments.

Do not add new projects or experiences.{allowed_block}

{JSON_KEYS_REMINDER}

=== CURRENT_LATEX ===
{latex}
"""


def build_checker_user(*, latex: str) -> str:
    return f"""Analyze this resume LaTeX for:

- Missing quantified impact (where the text could reasonably support a metric but has none)
- Bullets that lack technologies where the role implies stack
- Inconsistent tense
- Weak verbs
- ATS risk patterns (unclear headings, suspicious structure)

Return JSON with key "issues" only — array of objects with type, location_hint, fix_plan.

=== RESUME_LATEX ===
{latex}
"""


# Backward-compatible names used by main.py
def revision_user_one_page(*, latex: str, pages: int) -> str:
    return revision_user_fit_one_page(latex=latex, pages=pages)


# =============================================================================
# Structured pipeline — LLM outputs resume_data only; server renders LaTeX
# =============================================================================

JSON_KEYS_REMINDER_STRUCTURED = """
You MUST return JSON with exactly these keys and no others:
- resume_data (object — schema in user message)
- preview_sections (array)
- coaching (array)
"""

JSON_KEYS_REMINDER_STRUCTURED_COMPILE_FIX = """
You MUST return JSON with exactly these keys and no others:
- "reason" (string) — one or two sentences: what failed and the minimal fix
- "resume_data" (object) — full corrected resume_data (same schema as before)
- "preview_sections" (array) — use [] if you did not rebuild preview data
- "coaching" (array) — use [] if you did not rebuild coaching
"""

STRUCTURED_GENERATOR_SYSTEM = """You are a resume data extraction and structuring engine.

Strict rules:
- Output must be one valid JSON object only (no markdown fences).
- Keys must be exactly: resume_data, preview_sections, coaching — no other keys.
- Do NOT output LaTeX, macros, backslash commands, or a latex_document field.
- Ground every fact in --- RESUME SOURCE ---; do not invent employers, roles, dates, metrics, or technologies.
- Use ASCII in visible resume prose (no emoji or fancy Unicode punctuation).
- No commentary outside JSON.

You produce structured resume data; the server deterministically renders PDF-ready LaTeX.

**First pass — maximize:** Pull **all** usable detail from the source into experience/project bullet **strings**—full sentences where possible. For longer roles (>4 months): preserve the EXACT bullet count from the source (8 source bullets = 8 strings). For short stints (≤4 months / internships): 3–5 strings. **100% fidelity:** every sourced metric, technology, system, and scope clause must appear across those strings (rephrase OK; omission not OK). Do **not** return token-short strings when the source is rich.
"""

STRUCTURED_FIXER_SYSTEM = """You are a resume data revision engine.

Strict rules:
- Output must be one valid JSON object only (no markdown fences).
- Keys must be exactly: resume_data, preview_sections, coaching — same shape as the generator output.
- Do NOT output LaTeX or latex_document.
- Apply only what the REVISION_SIGNAL block requests. Do not rewrite unrelated sections.
- Do not invent new facts (employers, dates, metrics, technologies).
- If REVISION_SIGNAL is fix_schema: fix resume_data so it passes validation; keep preview_sections/coaching consistent.
- If REVISION_SIGNAL is fix_ats_structured: improve ATS readability via resume_data only (section coverage, keywords, bullet length).
- If REVISION_SIGNAL is **fit_one_page**: **100% denotative preservation**—every tech name, metric, system, and concrete phrase in CURRENT_RESUME_DATA must remain (rephrase OK; omission forbidden except as explicitly allowed in the signal).
"""

STRUCTURED_DENSIFY_SYSTEM = """You are a content refinement engine for structured resume data.

Strict rules:
- Output JSON with keys: resume_data, preview_sections, coaching only.
- Do NOT output LaTeX or latex_document.
- Do not invent new employers, projects, roles, dates, or metrics.
- Expand density by elaborating wording already supported by CURRENT_RESUME_DATA (and ALLOWED_FACTS if present).
- Preserve quantified metrics already implied; do not add new numbers.
- Preserve existing bullet count per experience entry; do not cap when expanding.

**Density goals:** Preserve existing bullet count per experience entry; expand thin strings. **Never** shorten on this pass—expand thin strings so the page fills; **preserve and restore** every tech name, metric, and scope already in CURRENT_RESUME_DATA. Use **1–2 sentence** strings with full context. Split one overloaded bullet into two only if both stay truthful.
"""


STRUCTURED_RESUME_SCHEMA = """
resume_data MUST match this shape (all string fields plain text; no LaTeX):

{
  "header": {
    "name": "Full Name",
    "phone": "+1 ...",
    "email": "you@example.com",
    "links": [{"label": "GitHub", "url": "https://github.com/USER"}, ...]
  },
  "education": [
    {"school": "...", "degree": "...", "date": "2020--2024", "location": "", "bullets": ["optional honor lines"]}
  ],
  "experience": [
    {
      "title": "Software Engineer Intern",
      "company": "Company",
      "date": "Summer 2025",
      "location": "",
      "bullets": ["At least one bullet per entry."]
    }
  ],
  "publications": [
    {
      "title": "Paper title (no trailing comma in the field itself).",
      "authors": ["X. Shan", "H. Shen", "A. Anand", "Z. Tu"],
      "self_name": "A. Anand",
      "venue": "European Conference on Computer Vision",
      "venue_short": "ECCV 2026",
      "year": "2026",
      "type": "conference",
      "status": "Under review at",
      "link": "arXiv:2603.14957"
    }
  ],
  "projects": [
    {"name": "Project", "date": "", "tech_line": "Python, FastAPI", "bullets": ["..."]}
  ],
  "skills": {
    "languages": ["Python", "C++"],
    "frameworks": ["FastAPI", "CUDA"],
    "tools": ["Git", "Docker"]
  }
}

Rules:
- Include header.name; use links for GitHub/LinkedIn/website (https URLs) plus email for mailto.
- education / experience / projects may be empty arrays only if the source truly has none (usually at least one of education or experience exists).
- Every experience entry MUST have a non-empty bullets array. For longer roles (>4 months): preserve the EXACT bullet count from the source (if a role has 8 bullets, output 8 strings). For short stints (≤4 months / internships): 3–5 strings. **100%** of sourced facts (metrics, technologies, systems, scope) must appear across those strings (merge **only** true duplicate facts); fewer strings only if the source is genuinely thin. Each string should be **one or two sentences** of plain text (substantive), not a 3–5 word tag—unless the source is genuinely one fact.
- Project bullets: **2–4** strings when the source describes work (same substance rule).
- skills must be present; at least one of languages, frameworks, or tools must list a non-empty string.
- publications: only populate if the source has a Publications / Pubs / Selected Publications section. Copy each entry verbatim—do NOT invent papers, venues, authors, or years. Set ``self_name`` to whichever author string in ``authors`` matches the candidate (i.e. matches ``header.name`` or its initial form like ``A. Anand``); leave empty if not detectable. Use ``venue_short`` for abbreviations or year tags (e.g. ``"ECCV 2026"``); ``venue`` for the full name. ``status`` carries leading phrases like ``"Under review at"``, ``"Accepted at"``, ``"Published in"``, ``"To appear at"``. ``link`` carries the arXiv id, DOI, or URL exactly as written in the source. If the source has no publications section, return ``[]``.
"""


STRUCTURED_OUTPUT_FORMAT = """
OUTPUT FORMAT

Return a SINGLE JSON object (no markdown fences):
- "resume_data": object — exactly the schema under STRUCTURED_RESUME_SCHEMA in this message.
- "preview_sections": same meaning as the LaTeX pipeline (UI preview).
- "coaching": same meaning as the LaTeX pipeline (aligned with preview_sections).
"""


def structured_generator_system() -> str:
    return STRUCTURED_GENERATOR_SYSTEM.strip() + "\n"


def structured_fixer_system() -> str:
    return STRUCTURED_FIXER_SYSTEM.strip() + "\n"


def structured_densify_system() -> str:
    return STRUCTURED_DENSIFY_SYSTEM.strip() + "\n"


def build_structured_generation_user_message(raw: str) -> str:
    objective = """
--- OBJECTIVE ---
From --- RESUME SOURCE ---, produce structured resume_data for a U.S. ATS-friendly resume (one-page target after server-side passes).

**Maximize:** The rendered resume must **read dense** when the source is dense—extract and refine **every** distinct win. **100% fidelity:** no sourced metric, tool, or scope may be omitted. Do not output sparse JSON to “save tokens.”

**First pass:** Every role, project, and skill from the source—no pre-trim.
**Experience:** For longer roles (>4 months): preserve the EXACT bullet count from the source (8 source bullets = 8 strings)—**all** source detail retained; **one string per distinct achievement** when listed separately (combine only true duplicates, never drop metrics/tools). For short stints (≤4 months / internships): 3–5 strings.
**Projects:** **2–4** bullet strings when work is described.
Bullet strings: **sentence-level** prose; **mix** shorter and longer lines; forbid a pattern where most bullets are single short clauses when the source has more to say.
"""
    parts = [
        STRUCTURED_OUTPUT_FORMAT.strip(),
        JSON_KEYS_REMINDER_STRUCTURED.strip(),
        STRUCTURED_RESUME_SCHEMA.strip(),
        objective.strip(),
        "=== CONTENT POLICIES ===",
        RESUME_RULES.strip(),
        "",
        "--- RESUME SOURCE ---",
        raw.strip() if raw else "(empty)",
    ]
    return "\n".join(parts).strip() + "\n"


def revision_user_fit_one_page_structured(*, resume_data: dict, pages: int) -> str:
    payload = json.dumps(resume_data, ensure_ascii=False, indent=2)
    if len(payload) > 100_000:
        payload = payload[:50_000] + "\n\n[...truncated...]\n\n" + payload[-50_000:]
    return f"""REVISION_SIGNAL: fit_one_page

The PDF renders to **{pages}** page(s); content must fit **exactly ONE** U.S. letter page.

**Hard rule — 100% factual preservation:** After editing, **every** technology name, number/metric, system/product, and concrete scope phrase that appears anywhere in CURRENT_RESUME_DATA must **still** appear (same meaning). Forbidden: dropping specifics to sound shorter.

Edit resume_data only, in order:
1) Remove **filler** words only (not nouns, numbers, or tech names).
2) Tighten wording: same facts, fewer characters **without** losing any named entity or number.
3) If still too long: merge two bullets **only** if they repeat the same fact with no exclusive detail in either.
4) **Last resort:** delete **one** bullet per role **only** if it adds no exclusive fact vs the rest.

Preserve every job/school/project entry. Do not remove entire jobs or schools.

{JSON_KEYS_REMINDER_STRUCTURED}

=== CURRENT_RESUME_DATA ===
{payload}
"""


def revision_user_fix_compile_structured(
    *,
    resume_data: dict,
    error_snippet: str,
    rendered_latex: str | None = None,
) -> str:
    raw_log = error_snippet.strip() if error_snippet.strip() else ""
    capped = raw_log if raw_log else "(no log detail)"
    if len(capped) > 12_000:
        capped = capped[:6000] + "\n\n[...truncated...]\n\n" + capped[-6000:]
    payload = json.dumps(resume_data, ensure_ascii=False, indent=2)
    if len(payload) > 80_000:
        payload = payload[:40_000] + "\n\n[...truncated...]\n\n" + payload[-40_000:]
    line_hint = extract_latex_error_line_hint(raw_log)
    ctx_block = ""
    if rendered_latex and rendered_latex.strip():
        nums = extract_engine_line_numbers_from_log(raw_log)
        ctx_block = (
            "\n=== RENDERED_LATEX_CONTEXT (numbered; server output before compile) ===\n"
            + latex_source_context_numbered(rendered_latex, nums)
            + "\n"
        )
    return f"""REVISION_SIGNAL: fix_compile_error

Server-rendered LaTeX failed to compile. Apply the **smallest** edits to **resume_data** plain-text fields so the next render compiles.
**Preserve all factual content**—only fix characters that break LaTeX (e.g. raw `%` in bullets, stray braces). Do **not** rewrite the whole resume_data tree. Do NOT add LaTeX commands inside strings. Do not invent facts.

**Compile log hint:** {line_hint}
{ctx_block}
=== ERROR_SNIPPET ===
{capped}

{JSON_KEYS_REMINDER_STRUCTURED_COMPILE_FIX.strip()}

=== CURRENT_RESUME_DATA ===
{payload}
"""


def revision_user_densify_structured(*, resume_data: dict, allowed_facts: str | None = None) -> str:
    allowed_block = ""
    if allowed_facts and allowed_facts.strip():
        allowed_block = f"""
ALLOWED_FACTS (you may incorporate **only** these additional factual claims, nowhere else):
{allowed_facts.strip()}
"""
    payload = json.dumps(resume_data, ensure_ascii=False, indent=2)
    if len(payload) > 100_000:
        payload = payload[:50_000] + "\n\n[...truncated...]\n\n" + payload[-50_000:]
    return f"""REVISION_SIGNAL: densify

The one-page PDF has too much bottom whitespace. Increase density via resume_data only: expand bullets using
wording already supported by CURRENT_RESUME_DATA. No new employers or projects unless in ALLOWED_FACTS.
Preserve existing bullet count per experience entry. **Expand** thin strings; **restore** any specificity that was lost to prior compression—every tech/metric in CURRENT_RESUME_DATA must stay visible. Use **longer 1–2 line** bullet strings.{allowed_block}

{JSON_KEYS_REMINDER_STRUCTURED}

=== CURRENT_RESUME_DATA ===
{payload}
"""


def revision_user_fix_schema(
    *,
    model_response: dict,
    schema_errors: list[str],
) -> str:
    err_block = "\n".join(schema_errors) if schema_errors else "(no details)"
    payload = json.dumps(model_response, ensure_ascii=False, indent=2)
    if len(payload) > 90_000:
        payload = payload[:45_000] + "\n\n[...truncated...]\n\n" + payload[-45_000:]
    schema_ref = resume_data_json_schema_reference()
    return f"""REVISION_SIGNAL: fix_schema

The last JSON response failed server-side resume_data validation. Fix resume_data so every rule below is satisfied.
Update preview_sections and coaching to stay aligned with the corrected resume_data.

=== SCHEMA_ERROR ===
{err_block}

=== JSON_SCHEMA_REFERENCE (Pydantic-generated; follow field types and required shapes) ===
{schema_ref}

{JSON_KEYS_REMINDER_STRUCTURED}

=== LAST_MODEL_JSON (full object you returned; edit and return corrected version) ===
{payload}
"""


# =============================================================================
# 5) PARSER — extract structured resume_data from raw text (verify-parse stage)
# =============================================================================

PARSER_SYSTEM = """You are a resume **extraction** engine. You do not write, rewrite, summarize, or improve resumes — you only read raw text and emit structured JSON.

Strict rules:
- Output must be one valid JSON object only (no markdown fences).
- The object must have exactly one top-level key: resume_data — matching the schema in the user message.
- Do NOT output LaTeX, markdown, commentary, preview_sections, coaching, or any other key.
- **Copy fields verbatim** from the source text. Preserve the user's wording, casing, punctuation, ordering, and bullet count.
- **Do NOT invent** employers, dates, metrics, technologies, schools, projects, locations, links, or bullets.
- **Do NOT rewrite** bullets to be punchier, shorter, or more "ATS-friendly" — that is a downstream stage.
- Empty string ("") for missing scalar fields. Empty array ([]) for missing list fields.
- Bullets are plain strings — strip leading bullet glyphs (•, -, *, →) and surrounding whitespace, but keep the sentence intact.
- Group skills by the source's own categories where possible (Languages / Frameworks / Tools); if the source uses other categories, place items in the closest bucket and do not drop any.
- **Publications:** if the source has a Publications / Pubs / Selected Publications section, populate ``publications`` (see schema). For each entry: copy the title verbatim into ``title``; split the author byline on commas into ``authors`` (preserve order); set ``self_name`` to whichever author matches ``header.name`` (or its initial form like ``A. Anand``) — leave empty if not detectable. Italic full venue name → ``venue``; bold abbreviation/year (e.g. ``ECCV 2026``) → ``venue_short``. Leading phrases like ``"Under review at"``, ``"Accepted at"``, ``"Published in"``, ``"To appear at"`` → ``status``. arXiv id, DOI, or URL → ``link``. **Do not invent** any field. If the source has no publications, return ``[]``.
- If the source has a USER-SUPPLIED CONTACT block, those values override anything else for header.email / header.phone / header.links.
- Do NOT split one source bullet into multiple bullets, and do NOT merge two source bullets into one.
- ASCII output preferred for visible prose; preserve Unicode only if it is clearly meaningful (e.g., a name with accents).
"""


def parser_system() -> str:
    return PARSER_SYSTEM.strip() + "\n"


def build_parse_user_message(raw: str) -> str:
    """Parser user message: schema reference + raw resume text. No policies, no LaTeX shape."""
    schema_ref = resume_data_json_schema_reference()
    parts = [
        "TASK: Extract structured resume data from --- RESUME SOURCE --- below.",
        "Return ONE JSON object with exactly one key: resume_data.",
        "",
        "Verbatim copy. No rewriting. No invention. Empty strings / arrays for missing fields.",
        "",
        "=== resume_data SCHEMA (Pydantic-generated; obey field names, types, and required keys) ===",
        schema_ref,
        "",
        "=== TARGET SHAPE (concrete example for orientation only — do not copy values) ===",
        STRUCTURED_RESUME_SCHEMA.strip(),
        "",
        "OUTPUT FORMAT:",
        '{ "resume_data": { ... } }',
        "",
        "--- RESUME SOURCE ---",
        raw.strip() if raw else "(empty)",
    ]
    return "\n".join(parts).strip() + "\n"


def revision_user_fix_ats_structured(*, resume_data: dict, ats_issue: str) -> str:
    payload = json.dumps(resume_data, ensure_ascii=False, indent=2)
    if len(payload) > 100_000:
        payload = payload[:50_000] + "\n\n[...truncated...]\n\n" + payload[-50_000:]
    return f"""REVISION_SIGNAL: fix_ats_structured

The resume PDF failed an ATS-style text extraction check. Adjust **resume_data only** (plain text fields).
Do NOT output LaTeX.

Goals (pick what applies to the issue code):
- Ensure content clearly supports standard section semantics when extracted as plain text (Education, Experience, Technical Skills).
- Add or clarify technology terms in bullets or skills if the issue implies missing stack visibility.
- Trim unusually long bullets if extraction order/readability may suffer.
- Reorder or merge bullets **within** the same job only if it improves reading order; do not invent new employers or dates.

=== ATS_ISSUE_CODE ===
{ats_issue}

{JSON_KEYS_REMINDER_STRUCTURED}

=== CURRENT_RESUME_DATA ===
{payload}
"""
