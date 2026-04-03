#!/usr/bin/env python3
"""
Measure bottom-strip mean luminance (0-255) for Overleaf / golden "full 1 page" calibration.

Usage (from repo):
  cd api && source .venv/bin/activate
  python scripts/measure_pdf_bottom_mean.py path/to/overleaf-output.pdf

Requires: poppler ``pdftoppm`` on PATH + Pillow (pip install -r requirements.txt).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parent.parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from compile_pdf import pdf_bottom_strip_mean_luminance  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Measure PDF page-1 bottom luminance for density calibration.")
    p.add_argument("pdf", type=Path, help="Path to a 1-page (or first page used) PDF")
    p.add_argument("--bottom-frac", type=float, default=0.15, help="Bottom fraction of raster (default 0.15)")
    p.add_argument("--dpi", type=int, default=100, help="Raster DPI (default 100, match API default)")
    p.add_argument("--margin", type=float, default=12.0, help="Suggested golden_margin for .env (default 12)")
    args = p.parse_args()

    if not args.pdf.is_file():
        print(f"Not a file: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    raw = args.pdf.read_bytes()
    m = pdf_bottom_strip_mean_luminance(raw, bottom_fraction=args.bottom_frac, dpi=args.dpi)
    if m is None:
        print(
            "Could not measure (need `pdftoppm` from Poppler on PATH and Pillow installed).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"bottom_mean_luminance={m:.2f}  (bottom_frac={args.bottom_frac}, dpi={args.dpi})")
    print()
    print("# --- Calibrate API: add to api/.env ---")
    print(f"RESUME_UNDERFULL_GOLDEN_MEAN={m:.2f}")
    print(f"RESUME_UNDERFULL_GOLDEN_MARGIN={args.margin}")
    print("# Underfull when measured_mean > GOLDEN_MEAN + GOLDEN_MARGIN (whiter bottom than your golden PDF).")
    print()
    print("# Alternative (absolute, no golden): comment out GOLDEN_MEAN and use e.g.")
    print(f"# RESUME_UNDERFULL_MEAN_THRESHOLD={min(252, int(m + 8))}  # underfull if mean >= this")


if __name__ == "__main__":
    main()
