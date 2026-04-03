"""
Fixer / revision LLM.

**Live implementation:** ``api/main.py`` (revision loop) + ``api/prompts.py``
(``revision_user_one_page``, ``revision_user_densify``).

Placeholder only — does not call OpenAI, so behavior of /generate is unchanged.
"""


def apply_revision(signal, current_latex: str):  # pragma: no cover
    raise NotImplementedError(
        "Revision LLM calls live in api/main.py; import prompts.revision_user_* there."
    )
