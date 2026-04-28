"""Single-bullet refine chat: take user push-back + history, return new bullet.

Anti-drift guardrails (v1.1):
1. Freeze baseline — only original_text and baseline_suggestion are trusted as
   ground truth. The mutating current_suggestion (UI-side) is NOT sent as fact.
2. ALLOWED_FACTS whitelist — extract numeric tokens, percentages, dollar amounts,
   ALL-CAPS acronyms, and capitalized tool tokens from baseline + user messages.
   Inject as a hard whitelist in the prompt.
3. Two-mode response — LLM may return mode="rewrite" or mode="clarify". Clarify
   asks the user for a missing fact instead of inventing one.
4. Server audit + retry — if the LLM still produces a token outside the allowed
   set, retry once with the offending token flagged. If retry also violates,
   fall back to a hard-coded clarify response. Fabrications never reach the UI.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterator

from openai import OpenAI

from features.generation.prompts import (
    bullet_refine_system,
    build_bullet_refine_user_message,
)
from resume_service.config import settings
from resume_service.models.bullet_chat import BulletChatMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------

# Hard-coded English ALL-CAPS words to ignore. The whitelist is permissive by
# design — false positives in the allow list are fine; false negatives are the
# audit's job.
_ENGLISH_CAPS_STOPWORDS = {
    "A", "I", "AS", "AT", "BY", "IN", "IS", "IT", "OF", "ON", "OR", "TO", "UP",
    "AND", "ANY", "ARE", "FOR", "NOT", "THE", "WAS", "WITH", "FROM",
}

_NUMERIC_RE = re.compile(
    r"""
    \$\s*\d[\d.,]*\s*[KMB]?      # money: $2.4M, $ 2.4 M, $1,200
    | \d+(?:\.\d+)?\s*%          # percentages: 40%, 70 %, 12.5%
    | \d+(?:\.\d+)?\s*[xX]\b     # multipliers: 10x, 10 x
    | \d+\s*\+                   # plus quantities: 200+, 200 +
    | \b\d{2,}(?:[.,]\d+)?\b     # bare numbers ≥ 2 digits
    """,
    re.VERBOSE,
)


def _canonicalize_numeric(token: str) -> str:
    """Strip internal whitespace from numeric tokens so '70 %' == '70%'."""
    return re.sub(r"\s+", "", token)

_ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")

# Capitalized non-acronym tokens (likely tool/product names: "Kafka",
# "Iceberg", "Airflow"). We accept these as facts so the LLM can use them.
_CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b")


_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*\b")


def _is_mixed_case_acronym(token: str) -> bool:
    """Capture acronym-like tokens with multiple capitals: YoY, MoM, PnL, KPIs."""
    if not token.isalpha():
        return False
    if len(token) > 6:
        return False
    cap_count = sum(1 for c in token if c.isupper())
    return cap_count >= 2


def extract_facts(text: str) -> set[str]:
    """Pull facts out of a piece of text. Permissive — better to over-allow."""
    if not text:
        return set()
    facts: set[str] = set()
    for m in _NUMERIC_RE.finditer(text):
        facts.add(_canonicalize_numeric(m.group(0)))
    for m in _ACRONYM_RE.finditer(text):
        token = m.group(0)
        if token not in _ENGLISH_CAPS_STOPWORDS:
            facts.add(token)
    for m in _CAPITALIZED_RE.finditer(text):
        facts.add(m.group(0))
    # Mixed-case acronyms (YoY, MoM, PnL) — not caught by either regex above.
    for m in _WORD_RE.finditer(text):
        token = m.group(0)
        if _is_mixed_case_acronym(token) and token not in _ENGLISH_CAPS_STOPWORDS:
            facts.add(token)
    return facts


def _build_allowed_facts(
    *,
    original_text: str,
    baseline_suggestion: str,
    history: list[BulletChatMessage],
    user_message: str,
) -> set[str]:
    allowed = set()
    allowed |= extract_facts(original_text)
    allowed |= extract_facts(baseline_suggestion)
    for turn in history:
        if turn.role == "user":
            allowed |= extract_facts(turn.content)
    allowed |= extract_facts(user_message)
    return allowed


def _format_allowed_facts(facts: set[str]) -> str:
    if not facts:
        return ""
    return ", ".join(sorted(facts, key=lambda x: (x.lower(), x)))


def _is_numeric_match(token: str, allowed: set[str]) -> bool:
    """Check if a numeric token is allowed, with bare-number wildcard logic.

    A bare number in `allowed` (e.g. "70") matches the same number with any
    unit suffix in `token` (e.g. "70%", "70x", "$70", "70+"). This handles
    the common case where the user types "70" and the LLM normalizes to
    "70%" in the rewrite — they unambiguously mean the same fact.
    """
    if token in allowed:
        return True
    digits = re.match(r"\$?\s*(\d+(?:\.\d+)?)", token)
    if not digits:
        return False
    bare = digits.group(1)
    return bare in allowed


def find_audit_violations(proposed_text: str, allowed: set[str]) -> list[str]:
    """Return tokens in proposed_text that are NOT in allowed_facts.

    Only audits the *strict* categories (numbers/money/percentages/acronyms +
    mixed-case acronyms). We don't audit Capitalized tool names because the
    LLM rephrasing may legitimately preserve a tool name from baseline that
    our extractor missed — over-rejecting on tool names causes false retries.
    """
    if not proposed_text:
        return []
    numeric_tokens: set[str] = set()
    other_tokens: set[str] = set()
    for m in _NUMERIC_RE.finditer(proposed_text):
        numeric_tokens.add(_canonicalize_numeric(m.group(0)))
    for m in _ACRONYM_RE.finditer(proposed_text):
        token = m.group(0)
        if token not in _ENGLISH_CAPS_STOPWORDS:
            other_tokens.add(token)
    for m in _WORD_RE.finditer(proposed_text):
        token = m.group(0)
        if _is_mixed_case_acronym(token) and token not in _ENGLISH_CAPS_STOPWORDS:
            other_tokens.add(token)
    violations = []
    for t in numeric_tokens:
        if not _is_numeric_match(t, allowed):
            violations.append(t)
    for t in other_tokens:
        if t not in allowed:
            violations.append(t)
    return sorted(violations)


# ---------------------------------------------------------------------------
# LLM call + parsing
# ---------------------------------------------------------------------------


def _coerce_result(raw: dict[str, Any]) -> tuple[str, str, str]:
    """Return (mode, proposed_text, assistant_message)."""
    mode = raw.get("mode") or "rewrite"
    if not isinstance(mode, str):
        mode = "rewrite"
    mode = mode.strip().lower()
    if mode not in ("rewrite", "clarify"):
        mode = "rewrite"

    proposed = raw.get("proposed_text") or ""
    if not isinstance(proposed, str):
        proposed = str(proposed or "")
    proposed = proposed.strip().strip('"').strip("'")
    if proposed.startswith(("- ", "* ", "• ")):
        proposed = proposed[2:].strip()

    msg = raw.get("assistant_message") or raw.get("message") or ""
    if not isinstance(msg, str):
        msg = str(msg or "")
    msg = msg.strip()

    if mode == "clarify":
        proposed = ""
    return mode, proposed, msg


def _call_llm(
    client: OpenAI,
    messages: list[dict[str, str]],
) -> tuple[str | None, str | None]:
    """Returns (content, error_detail). At most one of them is non-None."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"},
            max_tokens=600,
        )
    except Exception as exc:
        logger.exception("bullet_chat OpenAI call failed")
        return None, f"LLM call failed: {exc}"

    content = (response.choices[0].message.content or "").strip()
    if not content:
        return None, "LLM returned empty content."
    return content, None


def refine_bullet(
    *,
    client: OpenAI,
    original_text: str,
    baseline_suggestion: str,
    user_message: str,
    history: list[BulletChatMessage],
    issue_title: str | None = None,
    issue_description: str | None = None,
    severity: str | None = None,
    category: str | None = None,
) -> Iterator[dict]:
    """Yield NDJSON-shaped events: one or more progress, then one result.

    Always emits a `result` event. On hard failure modes we emit a clarify
    fallback rather than an error so the UI keeps working.
    """
    yield {"type": "progress", "message": "Refining bullet…"}

    allowed = _build_allowed_facts(
        original_text=original_text,
        baseline_suggestion=baseline_suggestion,
        history=history,
        user_message=user_message,
    )
    allowed_facts_str = _format_allowed_facts(allowed)

    system = bullet_refine_system()
    primer_user = build_bullet_refine_user_message(
        original_text=original_text,
        baseline_suggestion=baseline_suggestion,
        allowed_facts=allowed_facts_str,
        issue_title=issue_title,
        issue_description=issue_description,
        severity=severity,
        category=category,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": primer_user},
    ]
    for turn in history:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_message})

    # ---- First attempt ----
    content, err = _call_llm(client, messages)
    if err is not None:
        yield {"type": "error", "detail": err, "status_code": 502}
        return
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("bullet_chat LLM returned non-JSON: %r", (content or "")[:200])
        yield {"type": "error", "detail": "LLM response was not valid JSON.", "status_code": 502}
        return

    mode, proposed, assistant_message = _coerce_result(data)
    violations = find_audit_violations(proposed, allowed) if mode == "rewrite" else []

    if not violations:
        # Clean response — return as-is. Empty rewrite text in rewrite mode
        # is treated as a clarify so we don't push empty bullets into the UI.
        if mode == "rewrite" and not proposed:
            yield {
                "type": "result",
                "data": {
                    "mode": "clarify",
                    "proposed_text": "",
                    "assistant_message": (
                        assistant_message
                        or "Could you give me a bit more detail to refine this?"
                    ),
                },
            }
            return
        yield {
            "type": "result",
            "data": {
                "mode": mode,
                "proposed_text": proposed,
                "assistant_message": assistant_message
                or ("Updated." if mode == "rewrite" else "Need a bit more info."),
            },
        }
        return

    # ---- Audit failed: retry once, force clarify on the offending token ----
    yield {"type": "progress", "message": "Refining bullet… (rechecking facts)"}
    violation_str = ", ".join(f'"{v}"' for v in violations)
    audit_user = build_bullet_refine_user_message(
        original_text=original_text,
        baseline_suggestion=baseline_suggestion,
        allowed_facts=allowed_facts_str,
        issue_title=issue_title,
        issue_description=issue_description,
        severity=severity,
        category=category,
        audit_violation=(
            f"Your previous response introduced {violation_str} which is NOT in "
            "ALLOWED_FACTS and was NOT provided by the user. Set mode=\"clarify\" "
            "and ask the user for the specific value(s) you need (e.g. "
            "\"How much did X improve by?\")."
        ),
    )
    retry_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": audit_user},
    ]
    for turn in history:
        retry_messages.append({"role": turn.role, "content": turn.content})
    retry_messages.append({"role": "user", "content": user_message})

    content2, err2 = _call_llm(client, retry_messages)
    if err2 is None and content2:
        try:
            data2 = json.loads(content2)
            mode2, proposed2, msg2 = _coerce_result(data2)
            violations2 = (
                find_audit_violations(proposed2, allowed) if mode2 == "rewrite" else []
            )
            if not violations2:
                yield {
                    "type": "result",
                    "data": {
                        "mode": mode2,
                        "proposed_text": proposed2,
                        "assistant_message": msg2
                        or (
                            "Updated."
                            if mode2 == "rewrite"
                            else "Could you give me a specific value for that?"
                        ),
                    },
                }
                return
        except json.JSONDecodeError:
            pass  # fall through to hard fallback

    # ---- Both attempts failed audit. Hard clarify fallback. ----
    logger.info(
        "bullet_chat audit failed twice; emitting clarify fallback. violations=%s",
        violations,
    )
    yield {
        "type": "result",
        "data": {
            "mode": "clarify",
            "proposed_text": "",
            "assistant_message": (
                "I'd need a specific number or detail to refine that — "
                "what value would you like to add?"
            ),
        },
    }
