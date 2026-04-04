"""
High-level orchestration sketch.

The live FastAPI flow remains in ``api/main.py`` (generate + revision + PDF).
Use ``run_machine_gate`` from scripts or future wiring without changing HTTP behavior.
"""

from __future__ import annotations

from .pipeline.signals import HardCheckResult, Signal, run_hard_checks

def run_machine_gate(
    latex: str,
    *,
    allow_multi_page: bool = False,
    skip_ats: bool = False,
) -> HardCheckResult:
    """
    Single deterministic pass: lint → compile → pages → ATS.

    Returns ``HardCheckResult`` with ``ok=True`` when all gates pass.
    """
    return run_hard_checks(
        latex,
        allow_multi_page=allow_multi_page,
        skip_ats=skip_ats,
    )


def next_action(signal: Signal | None) -> str:
    """Human/debug label for a signal (for logging or future fixer routing)."""
    if signal is None:
        return "done"
    return signal.kind
