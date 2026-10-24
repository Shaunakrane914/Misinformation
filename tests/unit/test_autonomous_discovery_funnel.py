"""Offline synthetic boundary controls. These are NOT live or independent labels."""
import time
from unittest.mock import patch
import pytest
from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.search_observations import capture_search, result_fit
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError
from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.research.research_models import EvidenceItem, ResearchRequest


def html_response(body, endpoint="https://www.bing.com/search"):
    return BoundedHTTPResponse(body=body.encode(), endpoint=endpoint, status_code=200,
        content_type="text/html", headers={"Content-Type": "text/html"}, latency_ms=1, attempts=1)


@pytest.mark.parametrize("case", ["empty", "irrelevant", "mixed", "blocked"])
def test_provider_funnel_and_fallback(case):
    bad = '<li class="b_algo"><h2><a href="https://other.example/">Other company products</a></h2></li>'
    good = '<li class="b_algo"><h2><a href="https://cedar.example/earnings">Cedar Instruments quarterly results revenue</a></h2></li>'
    payload = "" if case == "empty" else bad + good if case == "mixed" else bad
    response = html_response(payload)
    with capture_search("Cedar Instruments", "financial") as observations, \
         patch("backend.infrastructure.acquisition.routing.router.fetch_public_http", return_value=response,
               side_effect=ProviderHTTPError("blocked", endpoint="https://www.bing.com", status_code=403) if case == "blocked" else None), \
         patch.object(NativeRouter, "_execute_yahoo_search", return_value=[]) as secondary:
        rows = NativeRouter()._execute_web_search("Cedar Instruments quarterly results revenue", limit=1)
    assert bool(rows) == (case == "mixed")
    if case != "mixed":
        secondary.assert_called_once()
    assert observations and observations[0]["provider"] == "bing"
    if case == "blocked":
        assert observations[0]["http_status"] == 403 and observations[0]["response_received"] is True
    elif case != "empty":
        assert observations[0]["decisions"][0]["discard_reason"] == "SUBJECT_MISMATCH"


def test_legacy_fallback_cannot_restore_rejected_headline():
    router = NativeRouter()
    fragment = EvidenceFragment(platform="web", title="Cedar products", url="https://cedar.example/")
    with capture_search("Cedar Instruments", "financial") as observations, \
         patch.object(router, "_execute_web_search", return_value=[]), \
         patch.object(router, "_fallback_web_scraper", return_value=[fragment]):
        rows = router.channel_dispatcher.standard._execute_web("Cedar Instruments customs seizure report", 3,
            "q1", "publisher_url_resolution", "", {})
    assert not rows
    assert observations[-1]["decisions"][0]["discard_reason"] == "HEADLINE_MISMATCH"


def test_navigation_hub_links_are_not_added_to_article_text():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details, extract_readable_page
    soup = BeautifulSoup('<nav><a href="/investors">Investor Relations</a></nav><main><p>Captured article content is unchanged.</p></main>', "html.parser")
    details = extract_observed_page_details(soup, "https://cedar.example/")
    assert details["discovery_links"][0]["url"] == "https://cedar.example/investors"
    assert "Investor Relations" not in extract_readable_page(soup)["text"]


def test_observed_same_publisher_article_reaches_reading_with_original_budget():
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services import agent_reach
    from backend.services.research.deep_reader import deep_reader
    hub = EvidenceItem(id="hub", canonical_url="https://cedar.example/", title="Cedar Instruments",
        source_domain="cedar.example", relevance_score=0.8, source_quality_score=0.8)
    body = "Cedar Instruments reported revenue of $12 million for the quarter ended June 30, 2026."
    called = []
    def read(url, **kwargs):
        called.append(url)
        return {"status": "success", "markdown": "Cedar Instruments investor information." if url.endswith("/") else body,
            "page_metadata": {"observed_links": [{"text": "Cedar Instruments quarterly financial results", "url": "https://cedar.example/earnings"},
                {"text": "Quarterly financial results", "url": "https://other.example/earnings"}]}}
    deep_reader._cache.clear()
    with patch.object(agent_reach.agent_reach_service, "read", side_effect=read):
        result = DeepReadingStage().run(ResearchRequest(target="Cedar Instruments", domain="financial", deep_read_budget=3),
            ResearchBudget(deep_read_budget=3), RankedEvidence([hub], [hub], {}, []), time.monotonic(), 20)
    assert len(called) <= 3 and "https://cedar.example/earnings" in called
    assert "https://other.example/earnings" not in called
    article = next(item for item in result.investigated if item.content == body)
    assert article.acquired_id and article.acquisition_attempt_id
    assert article.metadata["discovered_on_candidate_id"] == "hub"
    assert any(row["discard_reason"] == "DIFFERENT_PUBLISHER" for row in result.telemetry["publisher_link_audit"])


def test_expired_stage_never_follows_publisher_links():
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    with patch("backend.application.research.reading.deep_reader.deep_read") as read:
        result = DeepReadingStage().run(ResearchRequest(target="Cedar", domain="financial"), ResearchBudget(),
            RankedEvidence([], [], {}, []), 0, 1)
    read.assert_not_called()
    assert result.telemetry["attempted"] == 0


def test_query_local_observations_do_not_leak_between_scopes():
    from backend.infrastructure.acquisition.adapters.web.search_observations import begin_search
    with capture_search("first") as outer:
        begin_search("first-provider")
        with capture_search("second") as inner:
            begin_search("second-provider")
    assert [row["provider"] for row in outer] == ["first-provider"]
    assert [row["provider"] for row in inner] == ["second-provider"]


@pytest.mark.parametrize("domain,target,other", [("financial", "Canon", "Casio"), ("brand", "Puma", "Reebok"),
    ("personal", "Mary Barra", "Mary Jones"), ("trending", "solid state batteries", "solid waste recycling")])
def test_varied_subjects_do_not_qualify_first_token_results(domain, target, other):
    with capture_search(target, domain):
        assert result_fit(target + " independent reporting", other, "", "https://publisher.example/article")[1]


def test_old_uninstrumented_provider_counts_stay_unknown():
    from backend.services.research.discovery_funnel import build_discovery_funnel
    from backend.application.research.contracts import QueryPlan, ReadEvidence
    result = build_discovery_funnel(QueryPlan(None, {}, {}), [], [], [], [], ReadEvidence([], {}), [])
    assert result["provider_attempts_observed"] is None
    assert result["first_observed_empty_boundary"] == "PLANNING"


def test_genuine_saved_title_url_pairs_remain_rejected_in_normalized_replay():
    """Real saved observations, synthetic HTML envelope; not fresh discovery."""
    import json
    from html import escape
    from pathlib import Path
    saved = json.loads((Path(__file__).parent / "fixtures" / "search_drift_20261019.json").read_text(encoding="utf-8"))
    html = "".join('<li class="b_algo"><h2><a href="' + escape(row["url"], quote=True) + '">'
                   + escape(row["title"]) + '</a></h2></li>' for row in saved["records"])
    with capture_search("LEGO", "brand") as observations, \
         patch("backend.infrastructure.acquisition.routing.router.fetch_public_http", return_value=html_response(html)), \
         patch.object(NativeRouter, "_execute_yahoo_search", return_value=[]) as secondary:
        rows = NativeRouter()._execute_web_search(saved["query"], query_class="publisher_url_resolution")
    assert not rows
    secondary.assert_called_once()
    assert len(observations[0]["decisions"]) == 5
    assert all(row["discard_reason"] == "HEADLINE_MISMATCH" for row in observations[0]["decisions"])


def test_topic_search_uses_existing_conservative_topic_variants():
    with capture_search("quantum computing", "trending"):
        assert result_fit("quantum computing", "Quantum computers tested in laboratory", "",
                          "https://publisher.example/article")[1] is None
        assert result_fit("quantum computing", "Quantum storage opens office", "",
                          "https://publisher.example/article")[1] == "SUBJECT_MISMATCH"


@pytest.mark.parametrize("agent", ["scout", "trending", "brandshield", "personal_watch"])
def test_all_agents_keep_provider_failure_in_query_records(monkeypatch, agent):
    from unittest.mock import MagicMock
    from backend.infrastructure.acquisition import service as module
    from backend.infrastructure.acquisition.adapters.web.search_observations import begin_search
    from backend.services.agent_reach.channels import ChannelStatus
    service = module.AgentReachService()
    channel, registry = MagicMock(), MagicMock()
    def failed_search(*args, **kwargs):
        begin_search("bing").update(status="TRANSPORT_FAILURE", http_status=503, response_received=True)
        return []
    channel.search.side_effect = failed_search
    registry.channel_names = ["web"]
    registry.get_status.return_value = ChannelStatus.AVAILABLE
    registry.get_channel.return_value = channel
    service.registry = registry
    monkeypatch.setattr(type(module.runtime_operation_capabilities), "assess", lambda *args, **kwargs: {"decision": "ALLOW"})
    result = service.retrieve_many({"web": ["Cedar Instruments quarterly results"]}, agent_name=agent,
        target_name="Cedar Instruments", domain="financial", perform_reads=False, timeout=1.0)
    record = result.query_records[0].to_dict()
    assert record["status"] == "FAILED" and record["search_attempts"][0]["http_status"] == 503


def test_completed_irrelevant_search_is_not_called_a_transport_failure():
    from backend.infrastructure.acquisition.adapters.web.search_observations import empty_search_failure
    assert empty_search_failure([{"status": "IRRELEVANT_RESULTS"}, {"status": "TRANSPORT_FAILURE"}]) is None
    assert empty_search_failure([{"status": "TIMEOUT"}])[0] == "TIMEOUT"
    assert empty_search_failure([{"status": "UNINSTRUMENTED_TRANSPORT"}]) is None


def test_irrelevant_feed_activates_existing_fallback_without_restoring_bad_hits():
    router = NativeRouter()
    bad = {"title": "Unrelated retail store", "link": "https://other.example/shop", "summary": "Other products"}
    good = EvidenceFragment(platform="news", title="Cedar Instruments revenue reported",
        url="https://publisher.example/cedar-results")
    with capture_search("Cedar Instruments", "financial") as observations, \
         patch.object(router.executor, "execute_rss_read", return_value={"items": [bad], "transport": {"http_status": 200}}), \
         patch.object(router, "_fallback_news_scraper", return_value=[good]) as fallback:
        rows = router.channel_dispatcher.standard._execute_feed("news", "Cedar Instruments revenue", 2, "q", "financial", "", {})
    fallback.assert_called_once()
    assert rows == [good]
    assert observations[0]["status"] == "IRRELEVANT_RESULTS"
    assert observations[0]["decisions"][0]["discard_reason"] == "SUBJECT_MISMATCH"


def test_news_collection_is_discovery_not_an_article_even_inside_article_tag():
    from backend.services.research.content_roles import document_role
    from backend.services.research.passage_extractor import passage_extractor
    links = [{"url": f"https://publisher.example/story-{i}", "text": "Cedar Instruments earnings reported"} for i in range(6)]
    item = EvidenceItem(id="index", canonical_url="https://publisher.example/stocks/CEDAR/news/",
        title="Cedar Instruments news", content="Cedar Instruments reported earnings. " * 20,
        content_depth="PARTIAL_CONTENT", metadata={"page_metadata": {"observed_links": links, "content_scope": "article"}})
    assert document_role(item) == "NEWS_INDEX"
    passage_extractor.extract_passages([item], "Cedar Instruments", domain="financial")
    assert item.extraction_status == "NO_RELEVANT_PASSAGE" and not item.relevant_excerpt
    item.canonical_url = "https://publisher.example/news/cedar-quarterly-results"
    assert document_role(item) == "SUBSTANTIVE_CANDIDATE"


def test_observed_icon_is_rejected_but_actual_corporate_news_link_survives():
    from backend.services.research.publisher_links import observed_publisher_articles
    from backend.services.research.content_roles import document_role
    assert document_role({"url": "https://publisher.example/assets/investor.svg", "content": "Investor Relations icon"}) == "ASSET_METADATA"
    parent = EvidenceItem(id="hub", canonical_url="https://publisher.example/news/", title="Cedar Instruments news",
        metadata={"read_success": True, "page_metadata": {"observed_links": [
            {"text": "Investor Relations icon", "url": "https://publisher.example/assets/investor.svg"},
            {"text": "Cedar Instruments appoints new CEO", "url": "https://publisher.example/news/cedar-appoints-ceo"}]}})
    audit = []
    children = observed_publisher_articles(parent, "financial", audit)
    assert len(children) == 1 and children[0].canonical_url.endswith("cedar-appoints-ceo")
    assert audit[0]["discard_reason"] == "NON_DOCUMENT_ASSET"


def test_resolver_reserves_body_time_without_extending_parent_deadline():
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from backend.services.research.deep_reader import DeepReader
    from backend.infrastructure.acquisition.network.budget import acquisition_deadline
    item = EvidenceItem(id="wrapper", canonical_url="https://news.google.com/rss/articles/opaque",
        title="Cedar Instruments reports quarterly results - Publisher")
    service = MagicMock()
    service.retrieve_many.return_value = SimpleNamespace(query_records=[], fragments=[])
    with acquisition_deadline(time.monotonic() + 0.9):
        DeepReader()._resolve_wrapper(item, service)
    observed = service.retrieve_many.call_args.kwargs
    assert 0 < observed["timeout"] <= 0.6
    assert observed["budget"]["channel_timeout"] == observed["timeout"]


@pytest.mark.parametrize("blocked", [False, True])
def test_query_discovery_to_native_html_capture_and_qualified_passage(blocked):
    """Synthetic HTTP bytes, real parsing/gates/native reader/passage extraction.

    No caller-supplied source URL enters research: the article is observed in
    the search response. This proves integration, NOT live provider ranking.
    """
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence, QueryPlan
    from backend.services.research.relevance_gate import relevance_gate
    from backend.services.research.source_quality import source_quality_engine
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.passage_extractor import passage_extractor
    from backend.services.research.discovery_funnel import build_discovery_funnel
    from backend.services.agent_reach.channels import QueryExecutionRecord
    from backend.services.research.deep_reader import deep_reader
    title = "Cedar Instruments quarterly revenue results"
    search = html_response('<li class="b_algo"><h2><a href="https://publisher.example/cedar-results">'
        + title + '</a></h2><div class="b_caption"><p>Cedar Instruments reported quarterly revenue.</p></div></li>')
    article_text = "Cedar Instruments reported revenue of $12 million for the quarter ended June 30, 2026. The company reported operating income of $2 million, compared with $1 million a year earlier. These figures refer to the reported quarter, not the full year."
    article = html_response('<html><head><title>' + title + '</title></head><body><nav>Shop all Contact us Privacy policy</nav>'
        '<article><h1>' + title + '</h1><p>' + article_text + '</p></article></body></html>',
        endpoint="https://publisher.example/cedar-results")
    with capture_search("Cedar Instruments", "financial") as observations, \
         patch("backend.infrastructure.acquisition.routing.router.fetch_public_http", return_value=search):
        fragments = NativeRouter()._execute_web_search(title, limit=2)
    candidates = [EvidenceItem.from_evidence_fragment(fragment, "candidate_" + str(i), "Cedar Instruments")
                  for i, fragment in enumerate(fragments)]
    for item in candidates:
        source_quality_engine.classify_and_score(item, target_name="Cedar Instruments")
    accepted, rejected = relevance_gate.filter_candidates(candidates, target_entity="Cedar Instruments", domain="financial")
    assert len(accepted) == 1
    deep_reader._cache.clear()
    # Isolated test DNS verdict; real production SSRF checks are not altered.
    with patch("backend.infrastructure.acquisition.adapters.web.jina.is_safe_url", return_value=(True, "test public host")), \
         patch("backend.infrastructure.acquisition.routing.router.is_safe_url", return_value=(True, "test public host")), \
         patch("backend.services.agent_reach.native.executor.is_safe_url", return_value=(True, "test public host")), \
         patch("backend.services.agent_reach.native.executor.fetch_public_http", return_value=article,
               side_effect=ProviderHTTPError("blocked", endpoint=article.endpoint, status_code=403) if blocked else None):
        read = DeepReadingStage().run(ResearchRequest(target="Cedar Instruments", domain="financial", deep_read_budget=2),
            ResearchBudget(deep_read_budget=2), RankedEvidence(accepted, accepted, {}, rejected), time.monotonic(), 20)
    passage_extractor.extract_passages(read.investigated, target_name="Cedar Instruments", domain="financial")
    records = [QueryExecutionRecord(query_id="query", channel="web", query_text=title, query_class="financial",
        phase="initial", status="SUCCESS", search_attempts=observations)]
    funnel = build_discovery_funnel(QueryPlan(None, {"web": [{"query_text": title}]}, {}), records,
        candidates, accepted, rejected, read, [])
    assert funnel["selected_acquisition_attempts"] == 1
    assert funnel["qualified_evidence"] == (0 if blocked else 1)
    if blocked:
        assert funnel["first_observed_empty_boundary"] == "READING"
        assert read.telemetry["acquisition_attempts"][0]["http_status"] == 403, read.telemetry
    else:
        captured = read.investigated[0]
        assert article_text in captured.content and "Shop all" not in captured.content
        assert captured.relevant_excerpt in captured.content
        assert captured.metadata["raw_capture"]["source_text_sha256"]
        assert captured.acquired_id and captured.acquisition_attempt_id
