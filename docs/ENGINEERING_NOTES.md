# Engineering notes · edge cases · what not to touch

This doc collects the **behavior we have shipped so far** and the **fragile assumptions** in one place.
Legacy rule: `.cursor/rules/do-not-touch-pdf-and-env.mdc` — the prohibition on arbitrarily editing the PDF pipeline and `.env` still stands.

---

## 1. Generation flow

| Item | Location | Summary |
|------|----------|---------|
| Synchronous generation | `POST /generate`, `/generate-json` | form / JSON → `_run_generate` |
| Streaming generation | `POST /generate-stream`, `/generate-json-stream` | NDJSON: `progress` → `result` / `error` |
| Web proxy | `web/src/app/api/generate-stream/route.ts` | multipart → backend `generate-stream`, JSON → `generate-json-stream` |
| UI | `web/src/app/page.tsx` | paste / file, `page_policy`, stream parsing, contact fields |

**Edge cases**

- If the stream is cut, it can end without a `result` event → the client must check for `type === "result"`.
- If `OPENAI_API_KEY` is missing, the API returns a JSON error before the stream even starts (same behavior as the non-streaming path).

---

## 2. Page policy (`strict_one_page` vs `allow_multi`)

| Policy | Behavior |
|--------|----------|
| `strict_one_page` | Compile → page-count loop → if 2+ pages, ask for a “mild trim” (instructed to preserve all source facts and history). |
| `allow_multi` | Skip the 1-page enforcement loop, compile once and attach `pdf_page_count`. |

**Edge cases**

- If `RESUME_ONE_PAGE_MAX_REVISIONS=0`, the page loop is disabled even in strict mode.
- If the model ignores the instruction we may still end up with 2 pages or with information dropped → the only mitigations are the prompt itself and `max_revisions`.

---

## 3. “Full-page” density (underfull)

| Item | Location |
|------|----------|
| Bottom-strip luminance measurement | `compile_pdf.pdf_bottom_strip_mean_luminance` (`pdftoppm` + Pillow) |
| Underfull decision | `main.py` — golden: `mean > GOLDEN_MEAN + MARGIN`; absolute: `mean >= THRESHOLD` |
| Densify LLM call | `features.generation.prompts.revision_user_densify` (importable through the `prompts` shim) |
| Ops check | `api/OPS_CHECKLIST.md`, `/health` → `pdf_density_check_ready` |

**Edge cases**

- Without `pdftoppm` / Pillow, measurement returns `None` → the underfull loop just passes through with no decision.
- If the source is short, finishing short is normal → an explanatory note is appended to `revision_log` (`_append_one_page_done_notes`).
- If both a golden and an absolute threshold are set, **golden wins** (in code, when `golden_mean is not None` the absolute threshold is ignored).

---

## 4. LaTeX cleanup · compile stability (`api/features/pdf_rendering/compile_pdf.py`)

The following run **immediately before compile / preview** (`sanitize_latex_for_overleaf`, `sanitize_unicode_for_latex`, `normalize_to_dhruv_template`).

| Fix | Reason |
|-----|--------|
| `\\%` → `\%` | Double-backslash plus `%` becomes a newline + comment, breaking layout. |
| `\\&` → `\&` | Stray `&` corruption inside `tabular`. |
| Remove empty `\href{}{}` | hyperref errors. |
| `extbf{` → `\textbf{` | Missing-backslash typo. |
| Unclosed `\begin{center}` before first `\section` | Auto-insert `\end{center}` (prevents broken Dhruv header). |
| Unicode substitution + tabs → spaces | pdflatex “invalid character”. |
| `LATEX_PORTABLE_PREAMBLE=1` | Preamble variant for Docker compile retries (drops `fullpage` / `glyphtounicode`). |
| CRLF / lone `\r` → `\n` | Prevents macro names from being split (e.g. `\resume` + CR + `ProjectHeading`). |
| `\section{Project(s)}` + `\resumeProjectHeading` outside a list | If the model omits `\resumeSubHeadingListStart`, `_ensure_projects_subheading_list` wraps it. |
| Line beginning with `resumeProjectHeading{` | When the leading `\` is missing, `_fix_line_start_missing_backslash_resume_project_heading` repairs it. |

### Projects / `\resumeProjectHeading` (must always hold)

- The Dhruv macro `\resumeProjectHeading` contains an internal `\item[]`, so it **must** live **only inside** `\resumeSubHeadingListStart` … `\resumeSubHeadingListEnd`.
- Putting just `\resumeProjectHeading{...}{...}` immediately after `\section{Projects}` can cause pdflatex to drop into an interactive prompt (`Try typing <return>`) and die → this is **pinned in the prompt’s `LATEX_BODY_SHAPE`**, and the server wraps it again in `sanitize_latex_for_overleaf` as a safety net.
- When introducing new templates / macros, also enforce the rule **“any custom block that uses `\item` requires an outer list macro.”**

**Things not to touch (caution)**

- `normalize_to_dhruv_template` / `api/features/pdf_rendering/dhruv_preamble.tex` — the template / macros and the user-message `=== TEMPLATE ===` (same content) are **one matched set**. Changing only one side desynchronizes it from model output.
- The **variant order** inside `compile_latex_to_pdf` (`portable_first`) — the retry order for Docker vs. host TeX failures.

---

## 5. Contact info (email / LinkedIn)

| Item | Behavior |
|------|----------|
| Web | When pasting only: if the source has no email / `linkedin.com` pattern, **the contact fields are required**. |
| File upload | The client does not text-scan the file → the same form fields are available as optional input. |
| API | `_append_contact_hints` adds a `USER-SUPPLIED CONTACT` block to the user message. |

**Edge cases**

- If the email is in some non-standard form, the heuristic may miss it → the user can type it directly into the field.

---

## 6. PDF page count

Order: `pdfinfo` → `qpdf` → `pypdf`.
`/health` exposes `pdf_page_counter`, `pdfinfo`, `qpdf`.

---

## 7. Types · response fields (`GenerateResponse`)

Keep aligned with the frontend `web/src/lib/types.ts`:

- `page_policy_applied`, `revision_log`, `revision_log_ko`
- `pdf_layout_underfull`, `density_expand_rounds`

---

## 8. Quick file index

```
api/main.py          — routes, iterate_generate_progress, contact hints, settings sync
api/features/generation/prompts.py — prompts (the root `api/prompts.py` is a shim)
api/features/pdf_rendering/compile_pdf.py — compile, sanitize, measurement, portable preamble (the root `api/compile_pdf.py` is a shim)
api/features/generation/structured_resume.py — structured → LaTeX (the root `api/structured_resume.py` is a shim)
api/features/resume_pipeline/ — lint / compile / pages / ATS gates
api/OPS_CHECKLIST.md — ops checklist
api/scripts/measure_pdf_bottom_mean.py — golden PDF luminance measurement
web/src/app/page.tsx
web/src/app/api/generate-stream/route.ts
```

---

## 9. Recommended regression checks (when changing things)

1. `GET /health` — `pdf_compile`, `pdf_density_check_ready`, `latex_portable_preamble`
2. Generate from pasted text → check the streaming `progress` messages
3. `strict 1p` → over-2-page case shows the trim log
4. Compile-pdf still succeeds on a `.tex` that has `\begin{center}` without `\end{center}`
5. `npm run build` (web), and a smoke test after starting the API with `uvicorn`

Read this doc **once before adding a feature or refactoring**, and when you discover a new edge case, add a **short bullet** to the same file.
