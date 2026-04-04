"""Resume build pipeline (machine gates + future LLM orchestration).

HTTP stays in ``api/main.py``; PDF compile lives in ``api/features/pdf_rendering/`` (import also via ``compile_pdf`` shim).
This package is additive: import it where you want explicit lint/signal checks.
"""

from .pipeline.signals import HardCheckResult, Signal, run_hard_checks

__all__ = ["HardCheckResult", "Signal", "run_hard_checks"]
