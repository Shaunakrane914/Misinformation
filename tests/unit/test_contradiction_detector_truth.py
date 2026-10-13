"""Negative cases for the lexical contradiction candidate detector."""

from backend.services.research.contradiction_detector import ContradictionDetector
from backend.services.research.research_models import EvidenceItem


def test_denial_without_opposing_report_does_not_flag_itself():
    denial = EvidenceItem(
        id="denial",
        title="Tata Motors denies battery startup acquisition talks",
        snippet="The company rejects reports about battery startup talks.",
    )

    assert ContradictionDetector().detect_contradictions([denial], "Tata Motors") == []
    assert denial.contradiction_flag is False


def test_shared_company_and_generic_news_words_are_not_a_claim_match():
    launch = EvidenceItem(
        id="launch",
        title="Tata Motors announces electric sedan deliveries",
        snippet="A company report says the new sedan will ship in June.",
    )
    denial = EvidenceItem(
        id="denial",
        title="Tata Motors denies battery startup acquisition rumor",
        snippet="A company report says the battery startup acquisition rumor is false.",
    )

    assert ContradictionDetector().detect_contradictions([launch, denial], "Tata Motors") == []
    assert launch.contradiction_flag is False
    assert denial.contradiction_flag is False


def test_clarification_or_misinformation_word_alone_is_not_denial():
    first = EvidenceItem(
        id="first",
        title="Company publishes clarification about platform misinformation policy",
    )
    second = EvidenceItem(
        id="second",
        title="Company expands platform misinformation policy",
    )

    assert ContradictionDetector().detect_contradictions([first, second], "Company") == []
    assert first.contradiction_flag is False
    assert second.contradiction_flag is False


def test_multiple_attributions_can_coexist_without_an_explicit_disagreement():
    first = EvidenceItem(
        id="first",
        title="Shares rose due to strong earnings",
        source_domain="example.com",
    )
    second = EvidenceItem(
        id="second",
        title="Shares rose driven by stronger demand",
        source_domain="other.example",
    )

    assert ContradictionDetector().detect_contradictions([first, second], "Shares") == []


def test_repeated_invocation_clears_stale_candidate_flags():
    affirmative = EvidenceItem(
        id="affirmative", title="Tata Motors in battery startup acquisition talks"
    )
    denial = EvidenceItem(
        id="denial", title="Tata Motors denies battery startup acquisition talks"
    )
    detector = ContradictionDetector()

    assert len(detector.detect_contradictions([affirmative, denial], "Tata Motors")) == 1
    assert affirmative.contradiction_flag is True
    assert denial.contradiction_flag is True
    assert detector.detect_contradictions([denial], "Tata Motors") == []
    assert denial.contradiction_flag is False
