# Archived frontend modules

These files were the previous SimpleResume frontend before the **Dusk Roast redesign** (PR `feature/dusk-roast-redesign`). They are **kept for revival**, not deleted, because each will be repurposed in a future plan.

The `_archive/` prefix opts the directory out of Next.js routing (App Router only mounts `app/...`, not `_archive/app/...`). Imports from outside `_archive/` are forbidden — these files must not affect the production bundle.

## Archived routes (`web/src/_archive/app/`)

| Path | Previous URL | Future plan |
|------|--------------|-------------|
| `resume-score/` | `/resume-score` | Standalone score page comes back behind `/score` once auth/dashboard ships, OR stays merged into `/review` permanently. Components feed the rubric drawer. |
| `resume-review/` | `/resume-review` | Replaced by the new `/review` route. Keep until the new flow has parity (PDF text-layer matching, issue panel UX). |
| `result/` | `/result/[id]` | Stub for future per-resume persistence (depends on auth + storage). |

## Archived components (`web/src/_archive/components/`)

| Module | Used by | Notes |
|--------|---------|-------|
| `resume-score/*` | old `/resume-score` page | Tabbed score breakdown — overview, rubric grid, role/bullet analysis, ATS audit, recommendations. Reuse pieces inside `RubricDrawer` if score gets its own tab again. |
| `resume-review/*` (minus `PdfAnnotationViewer.tsx`) | old `/resume-review` page | Annotated workspace, issue panel, fix drawer, score header, credibility badge. Replaced by new `components/review/*`. |
| `CoachingPanel.tsx` | old `/` post-generate `coaching` tab | Coaching markdown view — fold into Review later if we expose section-level coaching. |
| `LatexViewer.tsx` | old `/` post-generate `latex` tab | LaTeX read-only viewer — wire up to a "View source" affordance on Review later. |
| `PdfPreview.tsx` | old `/` post-generate `preview` tab | Live PDF preview with text-only fallback — replaced by `components/review/PdfPanel.tsx`. |

## Promoted (not archived)
- `resume-review/PdfAnnotationViewer.tsx` → `components/review/PdfAnnotationViewer.tsx`. Severity colors retargeted to design tokens (`var(--error)` / `var(--warn)` / `var(--success)`).

## When to revive
- **Auth lands** → revive `result/` and reintroduce a Dashboard route consuming the saved-resume list.
- **JD-tuning lands** → reuse `resume-score/ResumeScoreUpload.tsx` JD textarea wiring on the Landing drop zone.
- **Standalone score requested** → revive `resume-score/` route and link it from nav.

## Removing for real
Delete this directory only after a feature plan has fully replaced its content. Don't half-delete.
