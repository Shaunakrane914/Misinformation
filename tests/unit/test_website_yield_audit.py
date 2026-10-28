"""Metric instrumentation must observe, never change transport/admission rules."""
from unittest.mock import patch
import pytest
from scripts.audits.website_yield_observer import WebsiteYieldObserver, public_locator
from backend.infrastructure.acquisition.network import budget, http


def test_observer_preserves_admissions_and_response():
    response = http.BoundedHTTPResponse(b"body", "https://example.org/a", 200, "text/html", {}, 1, 1)

    def fetch(url, **kwargs):
        assert kwargs == {"max_attempts": 1, "max_bytes": 100}
        budget.reserve_public_request(url)
        return response

    counter = budget.PublicRequestBudget(total=1)
    with patch.object(http, "_fetch_public_http", fetch):
        with budget.public_request_budget(counter), WebsiteYieldObserver() as observation:
            assert http._fetch_public_http("https://example.org/a", max_attempts=1, max_bytes=100) is response
            with pytest.raises(TimeoutError):
                http._fetch_public_http("https://example.org/b", max_attempts=1, max_bytes=100)
    ledger = observation.export()
    assert ledger["native_http_admissions"] == counter.snapshot()["native_http_admissions"] == 1
    assert ledger["admission_rejections"] == 1
    assert [r["outcome"] for r in ledger["http_operations"]] == ["RECEIVED", "FAILED"]
    assert ledger["admissions"][0]["http_operation_id"] == ledger["http_operations"][0]["operation_id"]


def test_observer_rethrows_denial_without_retry():
    error = http.ProviderHTTPError("denied", endpoint="https://example.org/a", status_code=403)
    with patch.object(http, "_fetch_public_http", side_effect=error) as fetch:
        with WebsiteYieldObserver() as observation:
            with pytest.raises(http.ProviderHTTPError) as caught:
                http._fetch_public_http("https://example.org/a")
    assert caught.value is error and fetch.call_count == 1
    assert observation.export()["http_operations"][0]["http_status"] == 403


def test_locators_redact_credentials_without_losing_article_path():
    locator = public_locator("https://user:password@example.org/story?q=topic&api_key=secret#body")
    assert "user" not in locator and "password" not in locator and "secret" not in locator
    assert locator.startswith("https://example.org/story?q=topic&api_key=")


def test_duplicate_captured_body_does_not_abort_pipeline():
    from copy import deepcopy
    from tests.unit.test_two_layer_pipeline import capture
    from backend.services.research.harvesting import HarvestResult
    from backend.services.research.research_models import ResearchRequest
    from backend.services.research.research_budget import ResearchBudget
    from backend.application.research.harvest_pipeline import run_harvest_pipeline
    first = capture()
    duplicate = deepcopy(first)
    duplicate.id, duplicate.canonical_url = "duplicate-capture", "https://other.example/earnings"
    result = HarvestResult(candidates=[first, duplicate], captures=[duplicate, first], metrics={},
                           read_telemetry={"attempted": 2, "successful": 2, "acquisition_attempts": [],
                                           "total_chars_read": len(first.content) * 2})
    with patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=result), \
            patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        output = run_harvest_pipeline(ResearchRequest(target="Cedar Instruments", domain="financial"),
                                     ResearchBudget(timeout_seconds=30), "STANDARD")
    sources = output.research_corpus["raw_acquisition_pool"]["sources"]
    assert sum(s["qualification_status"] == "QUALIFIED" for s in sources) == 1
    assert next(s for s in sources if s["source_id"] == duplicate.id)["qualification_status"] == "DUPLICATE"


@pytest.mark.parametrize("instruction", [
    "Research Aster Devices quarterly revenue. Compare actual results with forecasts.",
    "Find attributable public statements by Elena Rivera. Preserve original context.",
    "Investigate reported impersonation involving Elena Rivera. Distinguish allegations from incidents.",
])
def test_research_instructions_are_not_atomic_assertions(instruction):
    from backend.services.research.claim_intelligence import claim_intelligence_engine
    assert claim_intelligence_engine.decompose_claims(instruction) == []


@pytest.mark.parametrize("assertion", [
    "Aster Devices reported quarterly revenue of USD 14 million.",
    "Research shows battery recycling improved material recovery by 15%.",
    'Elena Rivera said "Preserve the records" during her speech.',
])
def test_declarative_and_attributed_assertions_remain_testable(assertion):
    from backend.services.research.claim_intelligence import claim_intelligence_engine
    assert claim_intelligence_engine.decompose_claims(assertion)


@pytest.mark.parametrize("prompt,hours", [
    ("Find developments from the last seven days", 168),
    ("reporting over the past 3 days", 72), ("last 48 hours", 48),
    ("recent information", 48), ("last 90 days", 48),
    ("last 2 days or last 7 days", 48),
])
def test_explicit_window_is_bounded_and_unambiguous(prompt, hours):
    from backend.services.research.temporal_guard import requested_trending_window
    assert requested_trending_window(prompt) == hours


def test_requested_week_keeps_actual_publication_gate():
    from datetime import datetime, timedelta, timezone
    from tests.unit.test_two_layer_pipeline import capture, harvest
    from backend.services.research.research_models import ResearchRequest
    from backend.services.research.research_budget import ResearchBudget
    from backend.application.research.harvest_pipeline import run_harvest_pipeline
    item = capture("battery recycling")
    item.content = ("Battery recycling researchers reported a new recovery technology at the pilot plant. "
                    "The recycling facility recovered lithium and nickel from used batteries, while its next manufacturing expansion remains a forecast.")
    item.published_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    item.metadata["page_metadata"]["published"] = item.published_at
    with patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=harvest(item)), \
            patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        result = run_harvest_pipeline(ResearchRequest(target="battery recycling", domain="trending",
                    extra_params={"trending_window_hours": 168}), ResearchBudget(timeout_seconds=30), "STANDARD")
    assert result.telemetry["trending_window_hours"] == 168
    assert result.telemetry["acquisition_metrics"]["qualified_source_count"] == 1
    from backend.services.research.temporal_guard import temporal_guard
    assert temporal_guard.evaluate(item, window_hours=48).status == "STALE"
    assert temporal_guard.evaluate(item, window_hours=168).is_eligible
    item.published_at = ""
    item.metadata["page_metadata"].pop("published")
    assert not temporal_guard.evaluate(item, window_hours=168).is_eligible


def test_ledger_never_counts_snippets_and_validates_unique_spans():
    from scripts.audits.website_word_yield import measure_case, sha
    body = "First observed paragraph describes a real reported event with context."
    source = {"source_id": "article", "source_type": "ARTICLE_BODY", "readable_text": body,
              "raw_content_hash": sha(body), "canonical_url": "https://publisher.example/article",
              "qualification_status": "QUALIFIED"}
    snippet = {"source_id": "lead", "source_type": "DISCOVERY_LEAD", "readable_text": body,
               "raw_content_hash": sha(body), "canonical_url": "https://search.example/"}
    paragraph = {"evidence_id": "article", "text": body, "start": 0, "end": len(body), "captured_text_sha256": sha(body)}
    native = {"research_corpus": {"raw_acquisition_pool": {"sources": [source, snippet]}},
              "unified_report": {"evidence_workbench": {"passages": [paragraph, paragraph]}}}
    rows, result = measure_case(native, prompt_id="S1", agent="scout")
    assert result["article_bodies"] == 1
    assert result["published_unique_evidence_words"] == len(body.split())
    assert rows[1]["raw_article_words"] == 0
    paragraph["end"] -= 1
    assert measure_case(native, prompt_id="S1", agent="scout")[1]["invalid_citations"] == 2


def test_fashion_recollection_is_not_product_recall():
    from backend.services.research.content_roles import matches_objective
    assert not matches_objective("Aster Footwear presented a sporty design recalling its earlier shoe model.", "brand")
    assert matches_objective("Aster Footwear recalled the defective shoes after injuries were reported.", "brand")
    assert matches_objective("Aster Footwear is recalling 2,000 products because of a safety hazard.", "brand")


def test_hypothetical_plural_scams_is_context_not_identity_allegation():
    from backend.services.research.passage_records import classify_passage
    assert classify_passage('Rivera said, "We cannot promise zero scams or zero misuse of technology in the future."', domain="personal") == "SOURCE_REPORTED_CONTEXT"
    assert classify_passage("Scammers impersonating Rivera stole victims' passwords in a phishing scam.", domain="personal") == "UNVERIFIED_ALLEGATION"


def test_plural_misattributed_statements_do_not_request_ordinary_interviews():
    from backend.services.research.specialist_planning import _explicit_tasks
    tasks = _explicit_tasks("Investigate impersonation or misattributed statements involving Elena Rivera.", "Elena Rivera", True)
    assert "FALSE_QUOTE" in tasks and "PUBLIC_STATEMENT" not in tasks


def test_cross_case_aggregate_deduplicates_and_separates_background():
    from scripts.audits.website_word_yield import cross_case_unique
    passage = {"valid_body_hash_and_offsets": True, "text_sha256": "same-text", "body_sha256": "same-body",
               "body_word_start": 0, "body_word_end": 10, "publication_scope": "CURRENT_OR_TASK_EVIDENCE"}
    row = {"bodies_acquired": 1, "body_sha256": "same-body", "raw_article_words": 50,
           "passage_offset_validity": [passage]}
    background = {**row, "passage_offset_validity": [{**passage, "publication_scope": "OLDER_BACKGROUND"}]}
    result = cross_case_unique([row, row, background])
    assert result["known_unique_raw_article_words"] == 50
    assert result["known_unique_published_passage_words"] == 10
    assert result["known_unique_historical_passage_words"] == 10
    assert result["known_unique_evidence_and_background_words"] == 10


def test_observer_keeps_partial_pool_after_pipeline_exception():
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.research_engine import ResearchEngine
    error = ValueError("synthetic pipeline failure")
    with patch.object(ResearchEngine, "investigate", side_effect=error):
        with WebsiteYieldObserver() as observation:
            RawAcquisitionPool("audit-partial-control")
            with pytest.raises(ValueError):
                ResearchEngine().investigate(None)
    assert len(observation.captured_pools()) == 1
    assert observation.export()["pipeline_errors"][0]["error_type"] == "ValueError"
