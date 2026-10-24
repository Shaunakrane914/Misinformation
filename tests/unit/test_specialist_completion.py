"""Offline controls for observed full-agent projection defects, not live recall."""
import copy

import pytest

from backend.agents.personal_watch.assessment import synthesize_personal_threats, verify_identity_match
from backend.agents.personal_watch.dossier import compute_change_detection
from backend.agents.personal_watch.monitoring import normalize_item
from backend.agents.scout.assessment import _financial_direction, financial_source_observation, synthesize_financial_intelligence
from backend.services.research.passage_records import public_statement_attribution


def quote_record():
    # Fictional prose control, deliberately not a saved real-source article.
    text = 'Aria Vale said "People should verify sources and preserve the surrounding context before sharing a claim."'
    return {"evidence_id": "native_article", "url": "https://publisher.test/article/statement",
        "title": "Aria Vale interview", "content": text, "content_depth": "PARTIAL_CONTENT",
        "metadata": {"read_success": True, "layer2_eligible": True,
            "acquisition_objective": "IDENTITY_THREAT", "page_metadata": {"body_kind": "ARTICLE_BODY"},
            "authorization": "must-not-survive"}}


def test_full_normalization_retains_article_quote_attribution_without_identity_proof():
    original = quote_record()
    record = normalize_item(original, "Web", "SECONDARY", "Aria Vale")
    assert "authorization" not in record["metadata"]
    assert record["metadata"]["page_metadata"]["body_kind"] == "ARTICLE_BODY"
    result = synthesize_personal_threats({"canonical_name": "Aria Vale"}, [record])
    statement = result["public_statements"][0]
    assert statement["evidence_id"] == original["evidence_id"]
    assert record["content"][statement["start"]:statement["end"]] == statement["text"]
    assert statement["claim_status"] == "UNVERIFIED"
    assert statement["identity_authenticated"] is False
    assert result["identity_risk"] == result["impersonation_status"] == "UNASSESSED"
    assert not result["threats"]


@pytest.mark.parametrize("scope", ["IDENTITY_THREAT", "PUBLIC_STATEMENT"])
def test_other_speaker_not_attributed_to_named_subject_in_any_query_scope(scope):
    item = quote_record()
    item["metadata"]["acquisition_objective"] = scope
    item["content"] = 'Aria Vale listened while Marco Bell said "This statement belongs to a different speaker, not the investigated person."'
    assert public_statement_attribution(item, item["content"], "Aria Vale") is None


def test_contextual_identity_description_never_says_confirmed():
    result = verify_identity_match({"name": "Aria Vale", "affiliations": ["Cedar Labs"]},
        {"content": "Aria Vale leads research at Cedar Labs."})
    assert result["identity_authenticated"] is False
    assert "confirmed" not in result["rationale"].lower()


def test_initial_change_is_readable_and_disappearing_allegation_is_not_resolved():
    history = {}
    threat = {"threat_type": "IMPERSONATION", "title": "Unverified account report"}
    changes, _ = compute_change_detection("Aria Vale", [threat], [], history)
    assert "No prior window" in changes[0]["description"]
    changes, _ = compute_change_detection("Aria Vale", [], [], history)
    assert changes[0]["change_type"] == "NOT_REOBSERVED"
    assert "resolution unverified" in changes[0]["description"]


@pytest.mark.parametrize("text,expected", [("Quarterly revenues rose", "positive"),
    ("Margins fell", "negative"), ("A profitable plan was announced", "unresolved"),
    ("Share prices fell but revenue rose", "unresolved")])
def test_financial_direction_respects_metric_word_and_end_boundaries(text, expected):
    assert _financial_direction(text)[0] == expected


def test_financial_source_context_never_reconciles_unknown_period_currency_or_affiliate():
    body = "Cedar Components reported Q2 revenue of KRW 3.46 trillion; analysts expect next-quarter operating profit to rise."
    source = {"evidence_id": "cedar_component", "url": "https://publisher.test/article/cedar",
        "title": "Cedar Components earnings outlook", "content": body, "relevant_excerpt": body,
        "content_depth": "PARTIAL_CONTENT"}
    observed = financial_source_observation(source, "Cedar")
    assert observed["observed_entity_names"] == ["Cedar Components"]
    assert observed["entity_alignment"] == "EXTENDED_ENTITY_REQUIRES_REVIEW"
    assert observed["observed_currencies"] == ["KRW"]
    assert observed["period_alignment"] == "NOT_RECONCILED"
    assert observed["result_scope"] == "FORECAST_OR_MIXED_REPORTED_CONTEXT"
    assert observed["passage"]["exact_capture_span"]
    result = synthesize_financial_intelligence("Cedar", "", {}, [source])
    assert result["filing_comparison"]["status"] == "NOT_PERFORMED"
    assert result["contradictions"] == {"for": [], "against": [], "unresolved": []}
    assert not result["misinformation"]["primary_corroboration"]


def test_bullish_headline_cannot_override_forecast_passage():
    source = quote_record()
    source.update(title="Cedar profit rose sharply", relevant_excerpt="Cedar expects operating profit to rise next quarter; this is a forecast, not actual results.")
    source["content"] = source["relevant_excerpt"]
    result = synthesize_financial_intelligence("Cedar", "", {}, [source])
    assert not result["catalysts"]["positive"]
    assert result["catalysts"]["unresolved"]


def test_analyst_future_forecast_and_hyphenated_name_never_imply_actual_growth_or_currency():
    text = '"Cedar will enter profit growth in 2027," said Kim Dong-won.'
    assert _financial_direction(text)[0] == "unresolved"
    source = {"evidence_id": "forecast", "content": text, "relevant_excerpt": text}
    assert not financial_source_observation(source, "Cedar")["observed_currencies"]


def test_related_quote_tail_does_not_become_investigated_speakers_words():
    from backend.services.research.passage_records import captured_passages
    record = quote_record()
    original = record["content"]
    record["content"] += ' (Also read: Marco Bell says "This unrelated quote belongs to a different speaker.")'
    result = captured_passages(record, "personal", "Aria Vale")
    statement = result[0]
    assert statement["text"] == original
    quoted = statement["quotation"]
    assert record["content"][quoted["start"]:quoted["end"]] == quoted["text"]
    assert "Marco Bell" not in quoted["text"]
    assert "Also read" in record["content"]


def test_financial_selection_prefers_target_results_to_other_company_comparison():
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.passage_extractor import passage_extractor
    target = "Cedar reported quarterly revenue of USD 10 billion and operating profit of USD 3 billion for the June quarter."
    comparison = "Beside Cedar, another company posted large profit. Oilco reported USD 86.5 billion in operating profit in 2022."
    item = EvidenceItem(id="control", canonical_url="https://publisher.test/article/cedar", title="Cedar earnings",
        content=target + "\n\n" + comparison, content_depth="PARTIAL_CONTENT")
    original = copy.deepcopy(item.content)
    passage_extractor.extract_passages([item], "Cedar", domain="financial")
    assert item.relevant_excerpt == target
    assert item.content == original
