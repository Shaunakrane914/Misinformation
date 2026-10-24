"""Offline financial-context regressions; fixture excerpts are genuine, not new research."""
import copy
import json
from pathlib import Path

import pytest

from backend.agents.scout.assessment import financial_source_observation, synthesize_financial_intelligence
from backend.application.research.synthesis import synthesize_grounded_findings
from backend.services.research.financial_context import financial_passage_context
from backend.services.research.research_models import EvidenceItem


@pytest.fixture
def genuine_records():
    path = Path(__file__).parents[1] / "fixtures" / "scout_financial_context_2026-10-21.json"
    fixture = json.loads(path.read_text(encoding="utf-8"))
    assert fixture["origin"] == "GENUINE_SAVED_API_EXCERPTS_NOT_FRESH_ACQUISITION_OR_COMPLETE_ARTICLES"
    records = fixture["records"]
    for record in records:
        record["relevant_excerpt"] = record["content"]
    return records


def typed(record):
    return EvidenceItem(id=record["evidence_id"], canonical_url=record["url"], title=record["title"],
        content=record["content"], relevant_excerpt=record["content"], content_depth=record["content_depth"],
        published_at=record.get("published_at", ""), discovered_at=record.get("retrieved_at", ""))


def test_genuine_sources_remain_separate_by_publication_period_and_forecast(genuine_records):
    before = copy.deepcopy(genuine_records)
    observations = [financial_source_observation(record, "Infosys") for record in genuine_records]
    assert [row["publication_scope"] for row in observations] == ["RECENT_REPORTING_CONTEXT", "HISTORICAL_BACKGROUND", "HISTORICAL_BACKGROUND"]
    assert observations[0]["observed_period_labels"] == ["Q3FY26"]
    assert observations[0]["title_period_labels"] == ["Q4FY26", "FY27"]
    assert observations[1]["observed_period_labels"] == ["2010/11"]
    assert observations[1]["result_scope"] == observations[2]["result_scope"] == "FORECAST_OR_MIXED_REPORTED_CONTEXT"
    assert observations[0]["observed_currencies"] == ["RUPEE_LABEL_UNSPECIFIED"]
    assert all(row["period_alignment"] == "NOT_RECONCILED" for row in observations)
    assert genuine_records == before  # No raw text, timestamp, citation or ID mutation.


def test_genuine_old_guidance_and_buyback_never_become_current_catalysts_or_findings(genuine_records):
    result = synthesize_financial_intelligence("Infosys", "", {}, genuine_records)
    current_id = genuine_records[0]["evidence_id"]
    catalyst_ids = {ident for group in result["catalysts"].values() for row in group for ident in row["evidence_ids"]}
    assert catalyst_ids == {current_id}
    assert len(result["financial_observations"]) == 3
    assert result["financial_context_summary"]["historical_background_count"] == 2
    assert result["filing_comparison"]["status"] == "NOT_PERFORMED"
    findings = synthesize_grounded_findings("Infosys", "financial", [typed(record) for record in genuine_records], [])
    assert [row.supporting_evidence_ids for row in findings] == [[current_id]]
    assert findings[0].metadata["financial_context"]["source_claim_status"] == "UNVERIFIED"


@pytest.mark.parametrize("published,observed,status", [
    ("2024-01-15", "2026-04-01", "HISTORICAL_BACKGROUND"),
    ("2026-03-15Z", "2026-04-01", "RECENT_REPORTING_CONTEXT"),
    ("bad-date", "2026-04-01", "UNKNOWN_PUBLICATION_OR_CAPTURE_TIME"),
    ("2026-03-15", "", "UNKNOWN_PUBLICATION_OR_CAPTURE_TIME"),
    ("2027-03-15", "2026-04-01", "FUTURE_PUBLICATION"),
])
def test_time_scope_uses_only_recorded_capture_clock(published, observed, status):
    result = financial_passage_context("Aster reported Q2 FY2026 revenue of USD 12 million.", published_at=published, observed_at=observed)
    assert result["publication_scope"] == status
    assert result["current_assessment_eligible"] is (status == "RECENT_REPORTING_CONTEXT")


def test_period_currency_actual_and_forecast_context_are_not_reconciled():
    text = "Aster reported Q2 FY2026 revenue of USD 12 million; analysts expect Q3FY26 revenue to reach EUR 14 million."
    result = financial_passage_context(text, issuer="Aster", title="Aster Components guidance FY27")
    assert result["observed_currencies"] == ["USD", "EUR"]
    assert result["observed_period_labels"] == ["Q2 FY2026", "Q3FY26"]
    assert result["title_period_labels"] == ["FY27"]
    assert [row["scope"] for row in result["statement_scopes"]] == ["REPORTED_SOURCE_ASSERTION", "FORECAST_OR_CONDITIONAL"]
    for span in result["statement_scopes"]:
        assert text[span["start"]:span["end"]] == span["text"]
    assert result["issuer_alignment"] == "MENTION_ONLY_NOT_AUTHENTICATED"
    assert not result["currency_conversion_performed"]


def test_bare_dollar_and_rupee_labels_are_not_silently_converted():
    result = financial_passage_context("Aster reported $12 million and Rs 50 crore in different entities.")
    assert set(result["observed_currencies"]) == {"DOLLAR_SYMBOL_UNSPECIFIED", "RUPEE_LABEL_UNSPECIFIED"}
    assert set(result["observed_currency_labels"]) == {"$", "Rs"}


def test_explicit_historical_query_keeps_old_assertion_labelled_not_current(genuine_records):
    old = genuine_records[1]
    result = synthesize_grounded_findings("Infosys", "financial", [typed(old)], [], intent="Historical guidance for 2010")
    assert len(result) == 1
    assert result[0].temporal_status == "HISTORICAL_CONTEXT"
    assert not result[0].metadata["financial_context"]["current_assessment_eligible"]
    assert result[0].importance == "LOW"
    assert result[0].title.startswith("Historical Financial Context")


def test_unknown_date_is_not_a_current_performance_claim():
    record = {"evidence_id": "aster", "title": "Aster revenues rose", "url": "https://publisher.example/aster",
        "content": "Aster reported that revenues rose by 12 percent in its quarterly results.", "content_depth": "PARTIAL_CONTENT"}
    result = synthesize_financial_intelligence("Aster", "", {}, [record])
    assert not result["catalysts"]["positive"] and not result["catalysts"]["negative"]
    assert result["catalysts"]["unresolved"][0]["current_financial_conclusion"] is False
    findings = synthesize_grounded_findings("Aster", "financial", [typed(record)], [])
    assert findings[0].title.startswith("Undated Financial Observation")
    assert findings[0].metadata["financial_context"]["current_assessment_eligible"] is False


def test_competitive_context_is_propagated_without_promoting_to_direct_topic():
    item = EvidenceItem(id="context", canonical_url="https://publisher.example/competitor",
        title="Aster competition", content="Aster announced a processor intended to compete with Beryl in the cloud market.",
        relevant_excerpt="Aster announced a processor intended to compete with Beryl in the cloud market.", content_depth="PARTIAL_CONTENT",
        metadata={"trend_source_context": {"classification": "COMPETITIVE_CONTEXT", "reason": "SOURCE_REPORTS_COMPETITIVE_IMPACT_NOT_TARGET_ANNOUNCEMENT", "is_heuristic": True}})
    result = synthesize_grounded_findings("Beryl", "trending", [item], [])
    assert result[0].importance == "LOW"
    assert result[0].metadata["source_context"]["classification"] == "COMPETITIVE_CONTEXT"


def test_brand_strategy_remains_context_not_financial_verification_or_catalyst():
    text = "Aster announced a new customer-facing brand identity as part of its brand strategy. The new proposition reflects the heritage and aspirations of its customers."
    record = {"evidence_id": "brand-context", "title": "Aster launches new brand identity",
        "url": "https://publisher.example/aster-brand", "content": text, "relevant_excerpt": text,
        "content_depth": "PARTIAL_CONTENT", "published_at": "2026-08-01", "retrieved_at": "2026-10-21"}
    result = synthesize_financial_intelligence("Aster", "", {}, [record])
    assert not any(result["catalysts"].values())
    assert result["financial_context_summary"]["corporate_strategy_context_count"] == 1
    context = result["financial_observations"][0]
    assert context["content_kind"] == "CORPORATE_STRATEGY_CONTEXT"
    assert context["financial_verification_status"] == "NOT_PERFORMED"
    assert not context["financial_assessment_eligible"]


def test_direct_trending_sources_precede_context_before_six_finding_cap():
    context = [EvidenceItem(id=f"context-{i}", canonical_url=f"https://publisher.example/competitor/{i}",
        title=f"Aster competitor announcement {i}", content=f"Aster announced processor number {i} intended to compete with Beryl in the cloud market.",
        relevant_excerpt=f"Aster announced processor number {i} intended to compete with Beryl in the cloud market.", content_depth="PARTIAL_CONTENT",
        metadata={"trend_source_context": {"classification": "COMPETITIVE_CONTEXT", "reason": "SOURCE_REPORTS_COMPETITIVE_IMPACT_NOT_TARGET_ANNOUNCEMENT", "is_heuristic": True}}) for i in range(6)]
    direct = EvidenceItem(id="direct", canonical_url="https://publisher.example/direct", title="Beryl new processor",
        content="Beryl announced a new processor with additional testing results in the current release.",
        relevant_excerpt="Beryl announced a new processor with additional testing results in the current release.",
        content_depth="PARTIAL_CONTENT", metadata={"trend_source_context": {"classification": "PRIMARY_TOPIC", "reason": "TARGET_REPORTING_CONTEXT", "is_heuristic": True}})
    result = synthesize_grounded_findings("Beryl", "trending", context + [direct], [])
    assert result[0].supporting_evidence_ids == ["direct"]
    assert len(result) == 6


def test_genuine_tata_branding_lead_does_not_become_corporate_event_from_ceo_attribution():
    # Exact first paragraph from the Oct21 native Business Standard capture,
    # ev_hv_0ae539934fa897babde0; excerpt replay, not new acquisition.
    passage = "Tata Motors Passenger Vehicles (TMPV) on Thursday unveiled Tata.cars as its new customer-facing identity, giving its passenger vehicle business a distinct brand expression as the company enters what Managing Director and Chief Executive Officer Shailesh Chandra described as its \u201cnext chapter\u201d. The new identity will progressively be visible across dealerships and showrooms, digital touchpoints, after-sales and service, and marketing communications. The company\u2019s legal and registered name will, however, continue to be Tata Motors Passenger Vehicles Limited, and will be used for statutory filings, manufacturing plants and official contracts. The move comes after the demerger of the erstwhile Tata Motors into independently run passenger vehicle and commercial vehicle businesses, and gives the passenger vehicle company a sharper consumer-facing identity of its own. The demerger became effective on October 1, 2025. The commercial vehicle undertaking was transferred to the erstwhile TML Commercial Vehicles Ltd, which subsequently became Tata Motors Ltd, while the passenger vehicle business remained with the company now named Tata Motors Passenger Vehicles Ltd. The commercial vehicle business already operates with a distinct identity and the brand promise \u201cBetter Always\u201d, which Tata Motors describes as guiding its standalone CV business following the demerger. For the passenger vehicle business, \u201cNothing\u2019s too far\u201d will form the central brand promise underpinning Tata.cars."
    source = {"evidence_id": "ev_hv_0ae539934fa897babde0",
        "title": "Tata Motors PV unveils Tata.cars as new customer-facing brand identity",
        "url": "https://www.business-standard.com/companies/news/tata-motors-pv-unveils-tata-cars-as-new-customer-facing-brand-identity-126082701429_1.html",
        "content": passage, "relevant_excerpt": passage, "content_depth": "PARTIAL_CONTENT",
        "published_at": "2026-08-27T20:50:44+05:30", "retrieved_at": "2026-10-21T04:48:16.902442"}
    report = synthesize_financial_intelligence("Tata Motors", "", {}, [source])
    assert report["financial_observations"][0]["content_kind"] == "CORPORATE_STRATEGY_CONTEXT"
    assert report["financial_context_summary"]["corporate_strategy_context_count"] == 1
    assert not any(report["catalysts"].values())
    assert report["financial_observations"][0]["passage"]["text"] == passage


def test_recent_nonfinancial_company_context_does_not_create_unresolved_catalyst():
    passage = "Aster's chief executive is speaking to students about the company's early history and its community volunteers."
    source = {"evidence_id": "aster-background", "title": "Aster chief executive interview",
        "url": "https://publisher.example/aster-interview", "content": passage,
        "relevant_excerpt": passage, "content_depth": "PARTIAL_CONTENT",
        "published_at": "2026-10-20", "retrieved_at": "2026-10-21"}
    report = synthesize_financial_intelligence("Aster", "", {}, [source])
    assert report["financial_observations"][0]["content_kind"] == "FINANCIAL_CONTEXT_INCOMPLETE"
    assert not any(report["catalysts"].values())
    assert report["financial_context_summary"]["incomplete_financial_context_count"] == 1


def test_explicit_usd_does_not_assign_another_bare_dollar_amount_to_us_currency():
    context = financial_passage_context("Aster reported USD 12 million at one subsidiary and $3 million at another.")
    assert set(context["observed_currencies"]) == {"USD", "DOLLAR_SYMBOL_UNSPECIFIED"}
    explicit = financial_passage_context("Aster reported US$12 million.")
    assert explicit["observed_currencies"] == ["USD"]


@pytest.mark.parametrize("typed_source", [True, False])
def test_scout_normalization_preserves_recorded_acquisition_clock(monkeypatch, typed_source):
    from types import SimpleNamespace
    from backend.agents.scout.agent import ScoutAgent
    from backend.services.research import research_engine

    captured_at = "2026-10-21T04:49:34.506884"
    text = "Aster reported Q3 FY2026 revenues of USD 12 million, an increase of 8 percent in its quarterly results."
    if typed_source:
        source = EvidenceItem(id="captured-clock", canonical_url="https://publisher.example/results",
            title="Aster quarterly results", content=text, relevant_excerpt=text,
            content_depth="PARTIAL_CONTENT", published_at="2026-04-23", discovered_at="2026-10-22T08:00:00Z",
            metadata={"acquired_at": captured_at})
    else:
        source = {"evidence_id": "captured-clock", "url": "https://publisher.example/results",
            "title": "Aster quarterly results", "content": text, "relevant_excerpt": text,
            "content_depth": "PARTIAL_CONTENT", "published_at": "2026-04-23", "retrieved_at": "2026-10-22T08:00:00Z",
            "metadata": {"acquired_at": captured_at}}
    response = SimpleNamespace(evidence=[source], findings=[], telemetry={})
    monkeypatch.setattr(research_engine, "investigate", lambda _request: response)
    monkeypatch.setattr(ScoutAgent, "check_stock_impact", lambda _self, _symbol: {})
    result = ScoutAgent().analyze_stock("Aster")
    assert result["sources"][0]["retrieved_at"] == captured_at
    assert result["financial_observations"][0]["observed_at"] == captured_at
