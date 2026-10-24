"""Offline boundary regressions; synthetic controls are not live accuracy proof."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest

from backend.services.research.research_models import EvidenceItem, ResearchRequest


@pytest.mark.parametrize("query", ["Unilever", "Scarlett Johansson", "Pichai", "Review Acme", "Open", "Teslaine"])
def test_sector_routing_requires_whole_terms(query):
    from backend.infrastructure.acquisition.resolution.social_resolver import EntitySubredditResolver
    sector, _ = EntitySubredditResolver().resolve(query)
    assert sector == "global_equities"


@pytest.mark.parametrize("query,sector", [("EV battery deployments", "automotive_ev"), ("AI chip foundry", "semiconductor_hardware"), ("Tesla", "automotive_ev")])
def test_explicit_sector_terms_still_work(query, sector):
    from backend.infrastructure.acquisition.resolution.social_resolver import EntitySubredditResolver
    assert EntitySubredditResolver().resolve(query)[0] == sector


def test_url_identity_preserves_distinct_paths_queries_and_ports():
    from backend.services.research.source_identity import source_url_key
    assert source_url_key("https://EXAMPLE.com:443#top") == source_url_key("https://example.com/")
    assert source_url_key("https://example.com/a") != source_url_key("https://example.com/a/")
    assert source_url_key("https://example.com/?v=1") != source_url_key("https://example.com/?v=2")
    assert source_url_key("https://example.com:8443/") != source_url_key("https://example.com/")


def test_duplicate_body_retains_original_id_and_audited_alias():
    from backend.services.research.source_identity import unique_captures
    body = "Cedar Instruments reported revenue of USD 14 million. This number has not been independently audited."
    a = EvidenceItem(id="a", canonical_url="https://a.example/article", content=body * 2)
    b = EvidenceItem(id="b", canonical_url="https://b.example/article", content=body * 2)
    audit = []
    assert unique_captures([a, b], audit) == [a]
    assert b.content == body * 2 and b.metadata["duplicate_of"] == "a"
    assert audit[0]["reason"] == "IDENTICAL_CAPTURE"


def test_real_wikipedia_failure_shape_is_background_not_financial_finding():
    # Genuine normalized source/text excerpt from the saved Unilever failure;
    # only role regression, not a new source request or independent truth label.
    from backend.services.research.passage_extractor import passage_extractor, has_usable_passage
    source = EvidenceItem(id="encyclopedia", canonical_url="https://en.wikipedia.org/wiki/Unilever",
        content="In 1978, National Starch was acquired for $487 million, marking the largest ever foreign-acquisition of a US company at that point.",
        content_depth="PARTIAL_CONTENT")
    passage_extractor.extract_passages([source], "Unilever", domain="financial")
    assert source.extraction_status == "NO_RELEVANT_PASSAGE" and not has_usable_passage(source)


@pytest.mark.parametrize("published,eligible", [(None, False), ("2000-01-01", False), ("2099-01-01", False), ("NOW", True)])
def test_undated_lead_can_be_read_but_only_fresh_body_can_yield_findings(published, eligible):
    from backend.services.research.relevance_gate import relevance_gate
    from backend.application.research.synthesis import PassageAnalysisStage
    from backend.application.research.contracts import ReadEvidence, RankedEvidence
    source = EvidenceItem(id="lead", title="Ceramic battery recycling pilot", canonical_url="https://publisher.example/article",
        snippet="Ceramic battery recycling researchers reported a pilot recovery process.", content_depth="INDEX_SNIPPET")
    assert not relevance_gate.evaluate_item(source, "ceramic battery recycling", domain="trending").is_accepted
    assert relevance_gate.evaluate_item(source, "ceramic battery recycling", domain="trending", provisional_read=True).is_accepted
    source.content = "Ceramic battery recycling researchers reported a pilot recovery process. The test does not establish commercial production."
    source.content_depth = "PARTIAL_CONTENT"
    source.metadata["read_success"] = True
    if published:
        source.metadata["page_metadata"] = {"published": datetime.now(timezone.utc).isoformat() if published == "NOW" else published}
    PassageAnalysisStage().run(ResearchRequest(target="ceramic battery recycling", domain="trending"),
        RankedEvidence([source], [source], {}, []), ReadEvidence([source], {}))
    assert source.metadata["temporal_eligible"] is eligible
    assert (source.extraction_status == "SUCCESS") is eligible


def test_observed_feed_links_are_not_article_bodies_and_lastmod_is_not_publication():
    from backend.infrastructure.acquisition.adapters.web.discovery_document import discovery_document
    feed = discovery_document('<rss><channel><item><title>Cedar earnings</title><link>https://publisher.example/results</link><pubDate>2026-10-20</pubDate></item></channel></rss>', "https://publisher.example/feed")
    assert feed["content_scope"] == "FEED_INDEX" and feed["observed_links"][0]["published"] == "2026-10-20"
    sitemap = discovery_document('<urlset><url><loc>https://publisher.example/results</loc><lastmod>2026-10-20</lastmod></url></urlset>', "https://publisher.example/sitemap.xml")
    assert sitemap["observed_links"][0]["published"] == ""
    assert discovery_document('<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><rss/>', "https://example.com") is None


def test_feed_declaration_preserved_without_injecting_it_into_body():
    from bs4 import BeautifulSoup
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details
    soup = BeautifulSoup('<link rel="alternate" type="application/rss+xml" href="/feed"><main>Publisher reporting</main>', "html.parser")
    result = extract_observed_page_details(soup, "https://publisher.example/")
    assert result["discovery_links"][0]["url"] == "https://publisher.example/feed"


def test_only_observed_same_publisher_get_search_form_can_be_followed():
    from bs4 import BeautifulSoup
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details
    from backend.services.research.publisher_links import observed_publisher_articles
    soup = BeautifulSoup('<main>Public news</main><form method="post" action="/private"><input name="q"></form>'
        '<form action="https://other.example/search"><input name="q"></form><form action="/search"><input type="search" name="q"></form>', "html.parser")
    page = extract_observed_page_details(soup, "https://publisher.example/")
    assert page["search_forms"] == [{"action": "https://publisher.example/search", "parameter": "q", "basis": "OBSERVED_PUBLIC_GET_FORM"}]
    parent = EvidenceItem(id="hub", canonical_url="https://publisher.example/", metadata={"read_success": True, "page_metadata": page})
    lead = observed_publisher_articles(parent, "brand", [], "Orion scam")[0]
    assert lead.canonical_url == "https://publisher.example/search?q=Orion+scam"
    assert not lead.content and lead.metadata["discovery_kind"] == "FEED_INDEX"


def test_gemini_advice_remains_disabled_without_explicit_scope(monkeypatch):
    from backend.services.research.search_advice import expand_with_advice
    monkeypatch.setenv("AEGIS_SEARCH_ADVISOR_ENABLED", "true")
    with patch("backend.services.agent_reach.source_planner.source_planning_engine._get_llm_suggestions") as generation:
        result, trace = expand_with_advice(ResearchRequest(target="Cedar", domain="financial"), [], None, 3)
    generation.assert_not_called()
    assert result is None and trace["status"] == "UNAVAILABLE"


def test_wrapper_hub_feed_article_chain_respects_four_existing_attempts():
    import time
    from types import SimpleNamespace
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.deep_reader import deep_reader
    source = EvidenceItem(id="opaque", title="Orion counterfeit chargers seized", canonical_url="https://news.google.com/rss/articles/opaque",
        source_quality_score=0.6, relevance_score=0.8, metadata={"publisher_source_url": "https://publisher.example/"})
    body = "Police reported that counterfeit Orion chargers were seized. The report does not identify every seller as unauthorized."
    calls = []
    def read(url, **_):
        calls.append(url)
        if url.endswith("/feed"):
            return {"status": "success", "markdown": "Observed feed entry: Orion counterfeit chargers seized.",
                "page_metadata": {"content_scope": "FEED_INDEX", "observed_links": [{"url": "https://publisher.example/report", "text": "Orion counterfeit chargers seized"}]}}
        if url.endswith("/report"):
            return {"status": "success", "markdown": body}
        return {"status": "success", "markdown": "Publisher public reporting and news updates.", "page_metadata": {
            "discovery_links": [{"url": "https://publisher.example/feed", "text": "Observed publisher feed", "kind": "FEED_INDEX"}]}}
    deep_reader._cache.clear()
    with patch("backend.services.agent_reach.agent_reach_service.retrieve_many", return_value=SimpleNamespace(query_records=[], fragments=[])), \
         patch("backend.services.agent_reach.agent_reach_service.read", side_effect=read):
        result = DeepReadingStage().run(ResearchRequest(target="Orion", domain="brand", deep_read_budget=4),
            ResearchBudget(deep_read_budget=4), RankedEvidence([source], [source], {}, []), time.monotonic(), 30)
    assert calls == ["https://publisher.example/", "https://publisher.example/feed", "https://publisher.example/report"]
    assert result.telemetry["attempted"] == 4 and result.investigated[-1].content == body


def test_financial_reads_prioritize_actual_event_titles_over_product_landings():
    import time
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    items = [EvidenceItem(id=str(i), canonical_url=f"https://publisher.example/{i}", title=title)
        for i, title in enumerate(["Cedar tablets shop online", "Cedar announces quarterly revenue results"])]
    seen = []
    def read(rows, **kwargs):
        seen.append([item.id for item in rows])
        return [], {"attempted": 0, "failed": 0, "acquisition_attempts": []}
    with patch("backend.application.research.reading.deep_reader.deep_read", side_effect=read):
        DeepReadingStage().run(ResearchRequest(target="Cedar", domain="financial"), ResearchBudget(),
            RankedEvidence(items, items, {}, []), time.monotonic(), 30)
    assert seen[0][0] == "1"


def test_ai_audit_separates_investigations_without_resetting_batch(tmp_path):
    from backend.infrastructure.llm.advisory_policy import advisory_run, investigation_scope, record_observation, observations, MODEL
    with advisory_run(verified_models=(MODEL,), database=tmp_path / "budget.sqlite"):
        with investigation_scope("first"):
            record_observation({"status": "GENERATED"})
        with investigation_scope("second"):
            assert observations(current_only=True) == []
            record_observation({"status": "TIMEOUT"})
            assert len(observations(current_only=True)) == 1
            assert len(observations()) == 2


def test_native_rss_read_uses_fetched_xml_without_second_fetch():
    from backend.services.agent_reach.native.executor import NativeExecutor
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    response = BoundedHTTPResponse(body=b'<rss><channel><item><title>Cedar quarterly results</title><link>https://publisher.example/results</link></item></channel></rss>',
        endpoint="https://publisher.example/feed", status_code=200, content_type="application/rss+xml", headers={}, latency_ms=1, attempts=1)
    with patch("backend.services.agent_reach.native.executor.is_safe_url", return_value=(True, "test")), \
         patch("backend.services.agent_reach.native.executor.fetch_public_http", return_value=response) as fetch:
        result = NativeExecutor().execute_web_read(response.endpoint)
    fetch.assert_called_once()
    assert result["page_metadata"]["content_scope"] == "FEED_INDEX"
    assert result["page_metadata"]["observed_links"][0]["url"].endswith("/results")


def test_blocked_first_publisher_does_not_consume_second_publishers_article_slot():
    import time
    from types import SimpleNamespace
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.deep_reader import deep_reader
    items = [EvidenceItem(id=str(i), title="Orion counterfeit chargers seized", canonical_url=f"https://news.google.com/rss/articles/{i}",
        source_quality_score=0.6, relevance_score=0.8, metadata={"publisher_source_url": url})
        for i, url in enumerate(["https://blocked.example/", "https://publisher.example/"])]
    body = "Police reported that counterfeit Orion chargers were seized. The report does not identify every seller as unauthorized."
    calls = []
    def read(url, **_):
        calls.append(url)
        if "blocked.example" in url:
            return {"status": "failed", "status_code": 403}
        if url.endswith("/feed"):
            return {"status": "success", "markdown": "Observed feed entry: Orion counterfeit chargers seized.",
                "page_metadata": {"content_scope": "FEED_INDEX", "observed_links": [{"url": "https://publisher.example/report", "text": "Orion counterfeit chargers seized"}]}}
        if url.endswith("/report"):
            return {"status": "success", "markdown": body}
        return {"status": "success", "markdown": "Publisher public reporting and news updates.", "page_metadata": {
            "discovery_links": [{"url": "https://publisher.example/feed", "text": "Observed publisher feed", "kind": "FEED_INDEX"}]}}
    deep_reader._cache.clear()
    with patch("backend.services.agent_reach.agent_reach_service.retrieve_many", return_value=SimpleNamespace(query_records=[], fragments=[])), \
         patch("backend.services.agent_reach.agent_reach_service.read", side_effect=read):
        result = DeepReadingStage().run(ResearchRequest(target="Orion", domain="brand", deep_read_budget=6),
            ResearchBudget(deep_read_budget=6), RankedEvidence(items, items, {}, []), time.monotonic(), 30)
    assert "https://publisher.example/report" in calls
    assert result.telemetry["attempted"] == 6
    assert any(source.content == body for source in result.investigated)
