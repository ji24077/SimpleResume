"""Resume build pipeline (machine gates + future LLM orchestration).

HTTP and PDF rendering stay in ``api/main.py`` and ``api/compile_pdf.py``.
This package is additive: import it where you want explicit lint/signal checks.
"""

from .pipeline.signals import HardCheckResult, Signal, run_hard_checks

__all__ = ["HardCheckResult", "Signal", "run_hard_checks"]
