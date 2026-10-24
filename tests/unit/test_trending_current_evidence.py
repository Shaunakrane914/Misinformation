"""Offline date/discovery/reporting controls. No fresh-network proof is claimed."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from backend.agents.trending.agent import TrendingAgent
from backend.agents.trending.clustering import cluster_trends, detect_syndication_group
from backend.agents.trending.extraction import TrendingExtractionEngine
from backend.agents.trending.models import TrendEvidence
from backend.infrastructure.acquisition.adapters.web.search_observations import capture_search
from backend.infrastructure.acquisition.adapters.web.search_observations import result_fit
from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget
from backend.infrastructure.acquisition.routing.standard_handlers import StandardChannelHandlers
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.native.normalizer import NativeNormalizer
from backend.services.research.body_context import reconcile_captured_context
from backend.services.research.harvesting import diversified_queries
from backend.services.research.research_models import EvidenceItem
from backend.services.research.temporal_guard import temporal_guard


def fragment(title, url, date):
    return EvidenceFragment(platform="news", title=title, url=url, published=date)


def feed_handler(bing, google):
    calls = []

    def fetch(url, limit):
        calls.append(url)
        return {"items": bing if "bing.com" in url else google, "transport": {"http_status": 200}}

    router = SimpleNamespace(executor=SimpleNamespace(execute_rss_read=fetch),
        normalizer=SimpleNamespace(normalize_rss_entries=lambda items, **kwargs: items),
        _tag_fragments=Mock(), _fallback_news_scraper=Mock(return_value=[]))
    handler = StandardChannelHandlers(router)
    handler._record_transport = Mock()
    handler._attach_transport = Mock()
    return handler, calls


def test_current_queries_are_concise_and_dated_without_date_invention():
    rows = diversified_queries("ocean carbon removal", "trending",
        "discover emerging viral trends, public narratives, and cross-channel discourse for ocean carbon removal",
        reference_time=datetime(2026, 10, 20, 12, tzinfo=timezone.utc))
    assert len(rows) == 18
    assert all("after:2026-10-18 before:2026-10-21" in row["query_text"] for row in rows)
    assert all("when:2d" in row["query_text"] for row in rows)
    assert "viral trends" not in rows[0]["query_text"]
    assert len({row["query_text"] for row in rows}) == 6


def test_saved_old_bing_response_does_not_suppress_current_fallback():
    # Genuine title/date/URL observations from the 20 Oct saved grid-scale case;
    # Google positive control is explicitly synthetic, not fresh acquisition.
    old = fragment("IIT Roorkee releases comprehensive study on ‘Advanced Grid-Scale Energy Storage’ solutions",
        "https://www.hindustantimes.com/education/news/iit-roorkee-ministry-of-new-and-renewable-energy-join-forces-to-transform-india-s-renewable-energy-landscape-101701331379201.html",
        "2023-11-30T15:20:10+05:30")
    fresh = fragment("Grid-scale energy storage project deployment", "https://publisher.test/new-grid-storage",
                     (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    handler, calls = feed_handler([old], [fresh])
    telemetry = {}
    with public_request_budget(PublicRequestBudget()), capture_search("grid-scale energy storage", "trending") as trace:
        output = handler._execute_feed("news", "grid-scale energy storage recent developments when:2d",
            8, "q1", "harvest_recent", "grid-scale energy storage", telemetry)
    assert len(calls) == 2 and "google.com" in calls[1]
    assert output == [fresh, old]
    assert trace[0]["status"] == "STALE_RESULTS"
    assert old.raw_metadata["discovery_temporal_status"] == "STALE"
    assert telemetry["freshness_fallback_used"] is True


def test_undated_bing_lead_remains_provisional_without_extra_provider_call():
    undated = fragment("Ocean carbon removal research update", "https://publisher.test/carbon-removal", "")
    handler, calls = feed_handler([undated], [])
    with public_request_budget(PublicRequestBudget()), capture_search("ocean carbon removal", "trending"):
        output = handler._execute_feed("rss", "ocean carbon removal research update when:2d", 8,
            "q1", "harvest_research", "ocean carbon removal", {})
    assert output == [undated] and len(calls) == 1
    assert undated.raw_metadata["discovery_temporal_status"] == "MISSING_TIMESTAMP"
    assert not temporal_guard.evaluate(undated).is_eligible


def captured(page, published="2026-10-20T10:00:00Z", temporal=True):
    return EvidenceItem(id="native-id", canonical_url="https://publisher.test/ocean-carbon-removal",
        title="Ocean carbon removal research", content="Ocean carbon removal research published an observed analysis.",
        published_at=published, metadata={"read_success": True, "temporal_required": temporal, "page_metadata": page})


def test_feed_fetch_and_lastmod_dates_cannot_make_an_undated_body_fresh():
    item = captured({"lastmod": "2026-10-20", "updated": "2026-10-20", "body_kind": "ARTICLE_BODY"})
    reconcile_captured_context(item)
    assert item.published_at == ""
    assert item.metadata["discovery_published_at"] == "2026-10-20T10:00:00Z"
    assert temporal_guard.evaluate(item).status == "MISSING_TIMESTAMP"


def test_actual_body_publication_overrides_feed_and_stale_original_stays_stale():
    item = captured({"published": "2023-11-30T15:20:10+05:30", "updated": "2026-10-20T10:00:00Z"})
    reconcile_captured_context(item)
    assert item.published_at.startswith("2023")
    assert not temporal_guard.evaluate(item, reference_time=datetime(2026, 10, 20, 12, tzinfo=timezone.utc)).is_eligible
    ordinary = captured({}, temporal=False)
    reconcile_captured_context(ordinary)
    assert ordinary.published_at == "2026-10-20T10:00:00Z"  # other specialist semantics unchanged


def ev(title, publisher="publisher.test", content="Captured source text", identifier="one"):
    return TrendEvidence(evidence_id=identifier, platform="news", source=publisher, title=title,
        url="https://" + publisher + "/article/" + identifier, content=content,
        source_role="SECONDARY", source_group_id="observed-" + identifier,
        published_at="2026-10-20T10:00:00Z")


def test_same_broad_topic_does_not_merge_unrelated_developments_or_claim_virality():
    records = [ev("Ocean carbon removal vessel launches coastal trial", identifier="trial"),
               ev("Ocean carbon removal tax legislation introduced in senate", identifier="tax")]
    clusters = cluster_trends(records, {"resolved_entity": "Ocean carbon removal"})
    assert len(clusters) == 2
    assert all(cluster.independent_source_count is None for cluster in clusters)
    assert all(cluster.trend_nature == "NEWLY_OBSERVED" for cluster in clusters)
    assert all(cluster.velocity["popularity_growth_measured"] is False for cluster in clusters)
    assert all(cluster.debunk_status == "UNASSESSED" for cluster in clusters)


def test_copies_and_wire_labels_are_observed_groups_not_independence_proof():
    text = "Exactly the same acquired reporting reproduced by two publishers."
    records = [ev("Ocean carbon removal coastal trial announced", "one.test", text, "a"),
               ev("Ocean carbon removal coastal trial announced", "two.test", text, "b")]
    result = cluster_trends(records, {"resolved_entity": "Ocean carbon removal"})
    assert len(result) == 1 and result[0].signal_count == 2
    assert result[0].independent_source_count is None
    assert result[0].source_group_count == 2
    assert "independence are unassessed" in result[0].why_trending
    assert detect_syndication_group(records[0].title, "one.test") == detect_syndication_group(records[1].title, "two.test")


def test_extractor_never_converts_one_batch_into_high_momentum_or_verified_coverage():
    records = [fragment("Ocean carbon removal deployment announcement", f"https://p{i}.test/article", "") for i in range(5)]
    result = TrendingExtractionEngine().extract(records, target_entity="Ocean carbon removal")
    assert result.trends[0].velocity["label"] == "UNASSESSED"
    assert result.trends[0].misinformation_risk == "UNASSESSED"


def test_completed_empty_research_does_not_start_unbudgeted_headline_fallback(monkeypatch):
    agent = TrendingAgent()
    fetch = Mock(side_effect=AssertionError("completed harvesting must not repeat acquisition"))
    monkeypatch.setattr(agent, "fetch_news", fetch)
    monkeypatch.setattr("backend.agents.trending.agent.research_engine.investigate", lambda request:
        SimpleNamespace(telemetry={"harvesting": {"captures": 2}}, findings=[], contradictions=[], research_corpus={}, evidence=[]))
    result = agent.scan("ocean carbon removal")
    assert result["evidence"] == [] and result["recent_developments"] == []
    assert result["telemetry"]["popularity_growth_measured"] is False
    fetch.assert_not_called()


def test_pipeline_error_preserves_failure_without_unbudgeted_source_retry(monkeypatch):
    agent = TrendingAgent()
    fetch = Mock(side_effect=AssertionError("failed shared research must not repeat acquisition"))
    monkeypatch.setattr(agent, "fetch_news", fetch)
    monkeypatch.setattr("backend.agents.trending.agent.research_engine.investigate", Mock(side_effect=TimeoutError("offline fixture")))
    result = agent.scan("ocean carbon removal")
    assert result["evidence"] == []
    assert result["retrieval_trace"]["acquisition"]["status"] == "ACQUISITION_FAILED"
    assert result["retrieval_trace"]["acquisition"]["error_type"] == "TimeoutError"
    fetch.assert_not_called()


def test_saved_partial_topic_headline_is_a_read_lead_not_qualified_evidence():
    # Genuine rejected title from the final 20 Oct response. No body/publication
    # date was acquired for this lead; neither is manufactured in this replay.
    title = "SINEXCEL Completes PCS Shipment for 100MW/400MWh Energy Storage Project in Chile - pv magazine Global"
    url = "https://news.google.com/rss/articles/observed-fixture-wrapper"
    with capture_search("grid-scale energy storage", "trending"):
        score, reason = result_fit("grid-scale energy storage project deployment when:2d", title, "", url, "harvest_project")
    assert reason is None and score > 0
    from backend.services.research.entity_resolver import EntityResolver
    target = EntityResolver.resolve_entity("grid-scale energy storage", domain="trending")
    assert EntityResolver.evaluate_entity_match(title, target)[2] is not None
    assert temporal_guard.evaluate({"title": title}).status == "MISSING_TIMESTAMP"


def test_partial_topic_recall_cannot_admit_single_common_word_or_named_entity():
    with capture_search("ocean carbon removal", "trending"):
        assert result_fit("ocean carbon removal research", "Ocean holiday prices reduced", "",
            "https://publisher.test/ocean", "harvest_research")[1] == "SUBJECT_MISMATCH"
    with capture_search("Satya Nadella", "trending"):
        assert result_fit("Satya Nadella interview", "Satya new movie announcement", "",
            "https://publisher.test/satya", "harvest_interview")[1] == "SUBJECT_MISMATCH"
    with capture_search("grid-scale energy storage", "trending"):
        assert result_fit("exact headline", "Energy storage project", "",
            "https://publisher.test/report", "publisher_url_resolution")[1] == "HEADLINE_MISMATCH"


def test_legacy_observed_url_key_survives_rss_normalization_without_body_upgrade():
    source = {"title": "Observed project announcement", "url": "https://publisher.test/project",
              "published": "2026-10-20", "snippet": "Observed search headline"}
    native = NativeNormalizer.normalize_rss_entries([source])[0]
    assert native.url == source["url"]
    assert native.published == source["published"]
    assert native.content_depth == "METADATA"
    assert native.raw_metadata["linked_article_retrieved"] is False
    assert not NativeNormalizer.normalize_rss_entries([{"title": "No locator"}])[0].url
