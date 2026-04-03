"""
Generator LLM (first pass).

**Live implementation:** ``api/main.py`` ``iterate_generate_progress`` + ``api/prompts.py``
(``generator_system``, ``build_generation_user_message``).

This module is a placeholder so the package layout matches the target architecture
without duplicating OpenAI calls or altering the existing API.
"""


def generate_resume(source_text: str):  # pragma: no cover
    raise NotImplementedError(
        "Use POST /generate or iterate_generate_progress in api/main.py; "
        "wire this module when extracting the client into the pipeline."
    )
