"""Offline generic controls for heading/CMS/title/date loss; not accuracy labels."""
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from backend.services.research.research_models import EvidenceItem
from backend.services.research.passage_extractor import has_usable_passage, passage_extractor
from backend.services.research.content_roles import paragraph_role


@pytest.mark.parametrize("domain,target,heading,body", [
    ("financial", "Cedar Instruments", "Cedar Instruments Q3 FY2026 Earnings Call, September 10",
     "Cedar Instruments announced that its board appointed Mira Chen as chief executive officer, effective December 1, 2026. The current chair will remain until the transition is completed."),
    ("brand", "Orion", "Orion Counterfeit Products And Scam Warning Reports",
     "Orion warned that sellers were advertising counterfeit chargers. The report does not establish that every seller is unauthorized."),
    ("personal", "Ada Finch", "Ada Finch Deepfake Audio And Impersonation Allegations",
     "Ada Finch denied endorsing the investment offer shown in the manipulated video. The recording has not been independently authenticated."),
    ("trending", "battery recycling", "Battery Recycling Latest Reports And Emerging Developments",
     "Battery recycling researchers reported a pilot recovery process in a laboratory. The test does not establish commercial production or measured virality."),
])
def test_substantive_paragraph_wins_over_observed_heading(domain, target, heading, body):
    text = heading + "\n\n" + body
    item = EvidenceItem(id="source", canonical_url="https://publisher.example/article", content=text,
        title="Read more", content_depth="PARTIAL_CONTENT", metadata={"page_metadata": {
            "text_blocks": [{"start": 0, "end": len(heading), "role": "HEADING"}]}})
    passage_extractor.extract_passages([item], target, domain=domain)
    assert item.relevant_excerpt == body
    assert item.content == text and text[item.excerpt_start:item.excerpt_end] == body


@pytest.mark.parametrize("text", ["CardDescription Cedar Instruments reported a profit increase of 5%.",
    "style Three up, m spacing", "CardImageAltText Photo of a company executive.", "ContentType caas:newsroom/article"])
def test_cms_labels_are_inspectable_metadata_not_propositions(text):
    assert paragraph_role(text) == "CMS_METADATA"
    assert not has_usable_passage({"content": text, "content_depth": "PARTIAL_CONTENT"})


def test_bare_earnings_heading_is_not_usable_but_financial_measurement_is():
    assert not has_usable_passage({"content": "Cedar Instruments Q3 FY2026 Earnings Call, September 10", "content_depth": "PARTIAL_CONTENT"})
    assert has_usable_passage({"content": "Cedar Instruments revenue: USD 12 million for the quarter ended June 30, 2026.", "content_depth": "PARTIAL_CONTENT"})


def test_native_body_reconciles_captured_title_without_replacing_identity():
    from backend.services.research.deep_reader import DeepReader
    from backend.services.agent_reach import agent_reach_service
    item = EvidenceItem(id="canonical", title="Read more", canonical_url="https://publisher.example/announcement",
        source_domain="publisher.example", source_quality_score=0.6, relevance_score=0.7)
    captured = "Cedar Instruments announced that its board appointed a new chief executive officer, effective December 1, 2026."
    with patch.object(agent_reach_service, "read", return_value={"status": "success", "markdown": captured,
        "page_metadata": {"title": "Cedar Instruments announces leadership transition", "published": "2026-09-03", "modified": "2026-09-04"}}):
        sources, _ = DeepReader().deep_read([item], max_reads=1, timeout_per_read=1)
    assert sources[0].title == "Cedar Instruments announces leadership transition"
    assert sources[0].metadata["discovery_title"] == "Read more"
    assert sources[0].published_at == "2026-09-03"
    assert sources[0].metadata["page_metadata"]["modified"] == "2026-09-04"
    assert sources[0].id == "canonical" and sources[0].canonical_url.endswith("/announcement")


def test_html_structure_and_visible_date_are_kept_separate_from_publication():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    soup = BeautifulSoup('<main><h1>Cedar Instruments leadership transition</h1><p>Thursday, September 3, 2026 1:05 PM</p>'
        '<p>Cedar Instruments announced a new chief executive officer, effective December 1, 2026.</p></main>', "html.parser")
    result = extract_readable_page(soup)
    headings = [row for row in result["text_blocks"] if row["role"] == "HEADING"]
    assert result["text"][headings[0]["start"]:headings[0]["end"]] == "Cedar Instruments leadership transition"
    assert result["date_observations"][0]["meaning"] == "UNSPECIFIED_DATE_LABEL"
    assert result["date_observations"][0]["text"] == "Thursday, September 3, 2026 1:05 PM"
    assert "published" not in result


def test_public_date_observations_and_metadata_are_bounded_and_exact():
    from backend.services.research.body_context import reconcile_captured_context
    from backend.schemas.evidence_inspection import public_capture_metadata, inspect_evidence
    text = "Thursday, September 3, 2026 1:05 PM\n\nCedar Instruments appointed a chief executive officer, effective December 1, 2026."
    item = EvidenceItem(id="captured", content=text, content_depth="PARTIAL_CONTENT", metadata={
        "read_success": True, "page_metadata": {"title": "Cedar Instruments announcement"}})
    reconcile_captured_context(item)
    public = public_capture_metadata(item)
    assert public["page_metadata"]["date_observations"][0]["meaning"] == "UNSPECIFIED_DATE_LABEL"
    assert item.published_at in {None, ""}
    item.metadata["page_metadata"]["date_observations"].append({"start": 0, "end": 4, "text": "FAKE", "meaning": "VERIFIED"})
    assert len(inspect_evidence(item)["page_observations"]["date_observations"]) == 1


def test_feed_publisher_scope_survives_native_normalization_and_one_resolver_query():
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from backend.services.agent_reach.native.executor import NativeExecutor
    from backend.services.agent_reach.native.normalizer import NativeNormalizer
    from backend.services.research.deep_reader import DeepReader
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    from backend.infrastructure.acquisition.adapters.web.search_matching import headline_overlap
    xml = b'''<rss version="2.0"><channel><title>News</title><item><title>Cedar Instruments quarterly results announced</title>
        <link>https://news.google.com/rss/articles/opaque</link><source url="https://publisher.example">Publisher</source></item></channel></rss>'''
    response = BoundedHTTPResponse(body=xml, endpoint="https://news.google.com/rss/search", status_code=200,
        content_type="application/rss+xml", headers={}, latency_ms=1, attempts=1)
    with patch("backend.services.agent_reach.native.executor.is_safe_url", return_value=(True, "test")), \
         patch("backend.services.agent_reach.native.executor.fetch_public_http", return_value=response):
        result = NativeExecutor().execute_rss_read(response.endpoint)
    fragment = NativeNormalizer.normalize_rss_entries(result["items"])[0]
    item = EvidenceItem.from_evidence_fragment(fragment, "feed-item", "Cedar Instruments")
    assert item.metadata["publisher_source_url"] == "https://publisher.example"
    service = MagicMock()
    service.retrieve_many.return_value = SimpleNamespace(query_records=[], fragments=[])
    _, trace = DeepReader()._resolve_wrapper(item, service)
    service.retrieve_many.assert_called_once()
    query = service.retrieve_many.call_args.args[0]["web"][0]["query_text"]
    assert query.startswith("site:publisher.example ")
    assert trace["query_basis"] == "FEED_DECLARED_PUBLISHER_UNVERIFIED"
    assert headline_overlap(query, item.title) == 1.0


def test_failed_objective_read_releases_deferred_alternative_without_unblocking_catalog():
    import time
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.research_models import ResearchRequest
    from backend.services.research.deep_reader import deep_reader
    items = [EvidenceItem(id=str(i), canonical_url=f"https://publisher{i}.example/report", title=title,
        source_domain=f"publisher{i}.example", source_quality_score=0.7, relevance_score=0.8)
        for i, title in enumerate(["Ada Finch scam allegation", "Ada Finch interview on electric cars"])]
    called = []
    def read(url, **kwargs):
        called.append(url)
        return {"status": "failed"} if url == items[0].canonical_url else {
            "status": "success", "markdown": "Ada Finch said the pilot is not yet commercial and requires additional tests."}
    deep_reader._cache.clear()
    with patch("backend.services.agent_reach.agent_reach_service.read", side_effect=read):
        result = DeepReadingStage().run(ResearchRequest(target="Ada Finch", domain="personal", deep_read_budget=3),
            ResearchBudget(deep_read_budget=3), RankedEvidence(items, items, {}, []), time.monotonic(), 20)
    assert len(called) == 2 and result.investigated[0].id == "1"
    assert result.telemetry["attempted"] <= 3


def test_observed_feed_hub_can_reach_article_within_original_attempt_cap():
    import time
    from types import SimpleNamespace
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.research_models import ResearchRequest
    from backend.services.research.deep_reader import deep_reader
    item = EvidenceItem(id="opaque", title="Orion counterfeit seizure report", channel="news",
        canonical_url="https://news.google.com/rss/articles/opaque", source_quality_score=0.7,
        relevance_score=0.8, metadata={"publisher_source_url": "https://publisher.example/"})
    body = "Police reported that counterfeit Orion chargers were seized. The report does not establish that other sellers are unauthorized."
    called = []
    def read(url, **kwargs):
        called.append(url)
        return {"status": "success", "markdown": body if url.endswith("/seizure") else "Publisher news and reporting from multiple local communities.",
            "page_metadata": {"observed_links": [{"url": "https://publisher.example/seizure", "text": "Orion counterfeit seizure report"}]}}
    deep_reader._cache.clear()
    with patch("backend.services.agent_reach.agent_reach_service.retrieve_many", return_value=SimpleNamespace(query_records=[], fragments=[])), \
         patch("backend.services.agent_reach.agent_reach_service.read", side_effect=read):
        result = DeepReadingStage().run(ResearchRequest(target="Orion", domain="brand", deep_read_budget=3),
            ResearchBudget(deep_read_budget=3), RankedEvidence([item], [item], {}, []), time.monotonic(), 20)
    assert called == ["https://publisher.example/", "https://publisher.example/seizure"]
    assert result.telemetry["attempted"] == 3
    assert any(source.content == body and source.acquired_id for source in result.investigated)
    assert not any(source.primary_source for source in result.investigated)


@pytest.mark.parametrize("url", ["https://user:password@publisher.example/", "javascript:alert(1)",
    "https://publisher.example/?token=secret", "https://publisher.example/invented-slug"])
def test_feed_hub_rejects_non_hubs_credentials_and_query_tokens(url):
    from backend.services.research.publisher_links import failed_feed_publisher_hubs
    item = EvidenceItem(id="source", metadata={"publisher_source_url": url})
    assert not failed_feed_publisher_hubs([item], [{"candidate_id": "source", "failure_kind": "PUBLISHER_UNRESOLVED"}], set())


def test_trending_news_plans_request_fresh_results_without_changing_eligibility():
    from backend.application.research.acquisition import QueryPlanningStage
    from backend.services.research.research_models import ResearchRequest
    from backend.infrastructure.acquisition.adapters.web.search_observations import result_fit, capture_search
    plan = QueryPlanningStage().run(ResearchRequest(target="ceramic battery recycling", domain="trending", agent_name="trending"))
    assert plan.channel_queries.get("news")
    assert all("when:2d" in q["query_text"] for q in plan.channel_queries["news"])
    with capture_search("ceramic battery recycling", "trending"):
        assert result_fit("ceramic battery recycling when:2d", "Ceramic battery recycling pilot", "", "https://publisher.example/article")[1] is None


def test_brief_requires_complete_captured_paragraph_and_preserves_negation():
    from backend.services.report_builder import _captured_observation_brief
    text = "Cedar Instruments announced a new pilot, but it is not commercially available."
    detail = {"statement": text, "supporting_evidence_ids": ["canonical"], "metadata": {"observation_only": True}}
    source = {"id": "canonical", "canonical_url": "https://publisher.example/article", "content": text,
              "content_depth": "PARTIAL_CONTENT"}
    assert text in _captured_observation_brief({"sources": [source]}, [detail])
    assert "not independently verified" in _captured_observation_brief({"sources": [source]}, [detail])
    assert not _captured_observation_brief({"sources": [source]}, [{**detail, "statement": text.split(", but")[0]}])
    assert not _captured_observation_brief({"sources": [source]}, [{**detail, "supporting_evidence_ids": ["missing"]}])


def test_trending_empty_report_explains_actual_temporal_rejections():
    from backend.services.report_builder import ReportBuilder
    data = {"retrieval_trace": {"acquisition": {"status": "INSUFFICIENT_EVIDENCE"},
        "discovery_funnel": {"qualification_rejections": [{"rejection_stage": "TEMPORAL_GATE_ERROR"}],
                             "successful_body_captures": 0}}}
    report = ReportBuilder.from_trending_result(trend_data=data, query="ceramic battery recycling")
    assert "TEMPORAL_GATE_ERROR: 1" in report.summary
    assert "48-hour" in report.summary and report.investigation_status == "INSUFFICIENT_EVIDENCE"


def test_background_hub_does_not_complete_research_or_hide_resolution_failure():
    from backend.services.report_builder import ReportBuilder
    from backend.services.research.discovery_funnel import build_discovery_funnel
    from backend.application.research.contracts import QueryPlan, ReadEvidence
    hub = EvidenceItem(id="hub", canonical_url="https://publisher.example/", content="Publisher news and updates.",
        content_depth="PARTIAL_CONTENT", metadata={"read_success": True})
    attempts = [{"status": "FAILED", "failure_kind": "PUBLISHER_UNRESOLVED"}]
    funnel = build_discovery_funnel(QueryPlan(None, {}, {}), [{"status": "SUCCESS"}], [hub], [hub], [],
        ReadEvidence([hub], {"acquisition_attempts": attempts, "attempted": 2}), [])
    assert funnel["first_observed_empty_boundary"] == "PUBLISHER_RESOLUTION"
    data = {"retrieval_trace": {"acquisition": {"status": "COMPLETED", "acquired_sources": 1}, "discovery_funnel": funnel}}
    report = ReportBuilder.from_trending_result(trend_data=data, query="ceramic batteries")
    assert report.investigation_status == "INSUFFICIENT_EVIDENCE"
    assert report.processing_notes["acquisition"]["status"] == "COMPLETED"
