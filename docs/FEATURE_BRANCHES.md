# Per-feature `feature/*` branch guide

This doc does not change any behavior — it just documents **which branch to use for which kind of work**.
The local branches below already exist in the repo and all currently point at the same `main` commit. When you start work, check out the right branch and commit there.

```bash
git fetch origin main
git checkout feature/<name>
# Or, off the latest main: git checkout -b feature/<name> origin/main
```

When pushing to remote:

```bash
git push -u origin feature/<name>
```

---

## Branch list (responsibilities)

| Branch | Area (one line) | Example work |
|--------|-----------------|--------------|
| `feature/pdf-rendering` | **Burning to PDF** — Docker / latexmk, the produced PDF, anything close to the 1-page measurement | Mostly `api/features/pdf_rendering/` |
| `feature/resume-generation` | **First pass** — the LLM flow that produces the resume body / structure | Mostly `api/features/generation/prompts.py`, `structured_resume.py` |
| `feature/resume-generation-editorial` | **Editorial / supplementary output** — coaching, preview sections, tone / feedback | `coaching`, `preview_sections`, user-facing copy |
| `feature/generation-revision-second-pass` | **Second-pass / retries / compaction** — fitting to one page, density expansion: the **server-side loops that re-call the model** | `resume_one_page_max_revisions`, density expand, server-side “please rewrite” re-prompts |
| `feature/error-recovery-compile` | **Recovery (compile errors)** — recovery when LaTeX fails | Compile-error parsing, fixer / heal, the `rendered_latex`-based fix loop |
| `feature/error-recovery-json-schema` | **Recovery (JSON / schema)** — fixing broken `resume_data` shape | SCHEMA_ERROR, `resume_schema_heal_max`, structured-mode schema heal |
| `feature/error-recovery-ats-quality` | **Errors / quality (ATS / checker)** — auto-fix and diagnostics after the text-extraction smoke test | `api/features/resume_pipeline/` plus the ATS / checker loops in `main.py` |
| `feature/api-extensions-flags` | **API / flags / extensions only** — adding fields or flags while preserving the contract | `FEATURE_*`, `extensions/`, response gets only optional fields added |

---

## Folder structure (`api/features/`)

The implementation is split into **feature folders** to mirror the git branch names. (The `compile_pdf.py` / `prompts.py` / `structured_resume.py` files at the `api/` root are **thin shims that preserve the existing import paths**.)

| Directory | Contents |
|-----------|----------|
| `api/features/pdf_rendering/` | `compile_pdf.py`, `dhruv_preamble.tex`, `tex_assets/` |
| `api/features/generation/` | `prompts.py`, `structured_resume.py` |
| `api/features/resume_pipeline/` | lint → compile → pages → ATS, etc. (gates) |
| `api/features/paths.py` | shared paths (preamble, etc.) |

**`extensions/`** is for **opt-in extensions** that, per governance, “core does not import”; **`features/`** is where the product’s core pipeline code lives.

---

## Rules when scope overlaps

1. **One PR = one branch = one topic** is the ideal.
2. If the **PDF pipe** and the **prompts / generation** must change together, do it in **one branch**, but in the PR description **separate** the “PDF-side change / generation-side change” into distinct paragraphs. (Same as the governance doc.)
3. Touching **protected core files** (`/.github/core-protected-paths.txt`) is blocked by CI. If you need that change, take the `allow-core-change` label or a separate approval path.
4. When in doubt, pick by **what the user sees**. (E.g. “logic that fixes compile errors when they happen” → `feature/error-recovery-compile`.)

---

## Check the local branches

```bash
git branch --list 'feature/*'
```

---

For deeper governance see [`AI_GOVERNANCE.md`](./AI_GOVERNANCE.md).
