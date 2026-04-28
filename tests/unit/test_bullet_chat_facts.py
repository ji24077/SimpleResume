"""Unit tests for bullet_chat_service fact extraction + audit."""

from __future__ import annotations

from resume_service.services.bullet_chat_service import (
    extract_facts,
    find_audit_violations,
)


def test_extract_facts_pulls_money_percent_acronym() -> None:
    text = "Drove $2.4M annual revenue (+40% YoY) using SLA monitoring on Kafka"
    facts = extract_facts(text)
    assert "$2.4M" in facts
    assert "40%" in facts
    assert "YoY" in facts
    assert "SLA" in facts
    assert "Kafka" in facts


def test_extract_facts_skips_english_caps_stopwords() -> None:
    text = "AND THE WAS used IT AS hub"
    facts = extract_facts(text)
    # All stopwords filtered. Empty.
    assert facts == set()


def test_extract_facts_handles_plus_quantities_and_multipliers() -> None:
    text = "Processed 200+ rows daily, reducing latency by 10x"
    facts = extract_facts(text)
    assert "200+" in facts
    assert "10x" in facts


def test_extract_facts_empty() -> None:
    assert extract_facts("") == set()
    assert extract_facts(None) == set()  # type: ignore[arg-type]


def test_find_audit_violations_empty_when_proposed_uses_only_allowed() -> None:
    allowed = {"40%", "$2.4M", "SLA", "Kafka"}
    proposed = "Drove $2.4M revenue (+40% MoM) on Kafka with SLA monitoring"
    # Note: MoM is not in allowed, so it WILL be a violation. That's correct —
    # the audit is strict on numbers/acronyms. The whitelist's job is to be
    # extended via baseline + user messages. Verify that lever:
    violations = find_audit_violations(proposed, allowed)
    assert violations == ["MoM"]
    # Add MoM via "user provides it" path:
    allowed2 = allowed | {"MoM"}
    assert find_audit_violations(proposed, allowed2) == []


def test_find_audit_violations_catches_invented_percentage() -> None:
    allowed = {"40%", "SLA"}
    proposed = "Improved response time by 20% via SLA tuning"
    # 20% is invented; SLA is allowed; 40% never appears so doesn't matter.
    assert find_audit_violations(proposed, allowed) == ["20%"]


def test_find_audit_violations_does_not_audit_capitalized_tools() -> None:
    """Capitalized non-acronym tokens (Kafka, Iceberg) are not audited — too
    many false positives if extractor missed them in baseline."""
    allowed = {"40%"}
    proposed = "Migrated to Iceberg, achieving 40% query speedup"
    # Iceberg not in allowed but it's a Capitalized token, not an acronym. OK.
    assert find_audit_violations(proposed, allowed) == []


def test_extract_facts_canonicalizes_internal_whitespace() -> None:
    """User types '70 %' or '$ 2.4 M' — extractor strips inner whitespace."""
    facts = extract_facts("research finding by 70 % from $ 2.4 M revenue, 10 x faster, 200 +")
    assert "70%" in facts
    assert "$2.4M" in facts
    assert "10x" in facts
    assert "200+" in facts


def test_audit_bare_number_acts_as_wildcard_for_units() -> None:
    """User said '70' or 'yes it was 70' — LLM emits '70%'. Should pass."""
    allowed = {"70"}
    assert find_audit_violations("Improved by 70%", allowed) == []
    assert find_audit_violations("Reduced cost by $70", allowed) == []
    assert find_audit_violations("Achieved 70x throughput", allowed) == []
    # But a different number is still flagged.
    assert find_audit_violations("Improved by 80%", allowed) == ["80%"]


def test_audit_canonicalizes_proposed_too() -> None:
    """LLM occasionally emits '70 %' (with space) — should match allowed '70%'."""
    allowed = {"70%"}
    assert find_audit_violations("up 70 %", allowed) == []


def test_find_audit_violations_multiple_in_sorted_order() -> None:
    allowed: set[str] = set()
    proposed = "Boosted by 50% over $1M with SQS and ETL"
    violations = find_audit_violations(proposed, allowed)
    assert violations == sorted(violations)
    assert "50%" in violations
    assert "$1M" in violations
    assert "SQS" in violations
    assert "ETL" in violations
