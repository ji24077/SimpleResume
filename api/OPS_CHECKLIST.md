# Ops checklist (one-page density / underfull)

**Just walk through these in order.**

1. **Poppler** — is `pdftoppm` on the server's PATH?
   - macOS: `brew install poppler`
   - Check: `which pdftoppm`

2. **Pillow** — is it installed in the API venv?
   - `cd api && uv sync --dev` (already includes `Pillow`)

3. **`GET /health`** — is `compiler.pdf_density_check_ready` **`true`**?
   - If `false`, density measurement and underfull decisions don’t run.

4. **`RESUME_DENSITY_EXPAND_MAX`** — is it **`1` or higher**? (default `2`)
   - If `0`, the “fill the page” auto-densify loop itself is off.

5. **Source text** — does it actually have **real** extra bullets / metrics / projects to add?
   - If not, the result **may be short or leave bottom whitespace** (we never invent achievements).
   - When that happens, an explanatory note may also be appended to `revision_log`.

## Golden PDF baseline (optional)

Pin the numbers using an Overleaf “fully-packed one-page” PDF:

```bash
cd api && uv run python scripts/measure_pdf_bottom_mean.py /path/to/golden.pdf
```

Put the printed `RESUME_UNDERFULL_GOLDEN_MEAN` (etc.) into `api/.env`.
