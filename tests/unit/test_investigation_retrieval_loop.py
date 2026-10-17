"""Development regressions from real empty-investigation traces, not held-out labels."""
from types import SimpleNamespace


def test_legacy_web_fallback_preserves_actual_url_and_date(monkeypatch):
    from backend.infrastructure.acquisition.routing import router as module
    scraper = SimpleNamespace(search_web=lambda *a, **k: [{
        "title": "Nike attributable report", "url": "https://example.org/report",
        "snippet": "Captured discovery text", "date": "2026-10-17",
    }])
    monkeypatch.setattr(module, "_get_legacy_scraper", lambda: scraper)
    fragments = object.__new__(module.NativeRouter)._fallback_web_scraper("Nike")
    assert fragments[0].url == "https://example.org/report"
    assert fragments[0].published == "2026-10-17"
    assert fragments[0].content_depth == "SNIPPET"


def test_empty_initial_discovery_is_not_saturation():
    from backend.services.research.evidence_saturation import EvidenceNoveltyTracker
    tracker = EvidenceNoveltyTracker()
    tracker.record_step("first", "OpenAI", "web", [], ["OpenAI"])
    assert not tracker.is_saturated


def test_entity_query_drops_parenthesized_ticker_but_preserves_factual_claim():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    planner = SourcePlanningEngine()
    plan = planner.plan("Infosys (INFY.NS)", entity="Infosys (INFY.NS)", domain="financial", use_llm=False)
    assert all("(INFY.NS)" not in action.query for action in plan.actions)
    claim = 'Infosys reported "not profitable" in Q1 2024'
    exact = planner.plan(claim, entity="Infosys", domain="financial", use_llm=False)
    assert any(claim in action.query for action in exact.actions)


def test_publisher_feeds_are_discovery_not_claim_answers():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    for target in ("OpenAI", "NVIDIA", "Apple", "Microsoft"):
        plan = SourcePlanningEngine().plan(target, entity=target, use_llm=False)
        feeds = [a for a in plan.actions if a.source_category == "publisher_announcements"]
        assert len(feeds) == 1 and feeds[0].channel == "rss" and feeds[0].operation == "read"
        assert feeds[0].expected_depth == "SYNDICATED_SUMMARY"


def test_case_normalized_entity_uses_feed_without_changing_factual_claim():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    planner = SourcePlanningEngine()
    plan = planner.plan("NVIDIA", entity="Nvidia", use_llm=False)
    assert any(a.source_category == "publisher_announcements" for a in plan.actions)
    assert not any(a.source_category == "contradiction_probe" for a in plan.actions)
    claim = "NVIDIA did not release a product in Q1 2024"
    plan = planner.plan(claim, entity="Nvidia", use_llm=False)
    assert any(claim in a.query for a in plan.actions)


def test_empty_target_does_not_block_other_queries_but_rate_limit_does():
    from backend.services.agent_reach.native.operation_capabilities import RuntimeOperationCapabilities
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("news", "search", {"outcome": "EMPTY", "http_statuses": [200], "network_observed": True})
    state = runtime.assess("news", "search")
    assert state["decision"] == "ELIGIBLE_UNVERIFIED" and state["last_outcome"] == "EMPTY"
    runtime.record_observation("news", "search", {"outcome": "FAILED", "http_statuses": [429], "network_observed": True})
    assert runtime.assess("news", "search")["decision"] == "DEFER_TEMPORARY"


def test_observed_index_links_remain_unread_leads_not_acquired_evidence():
    from backend.application.research.acquisition import _observed_issuer_documents
    from backend.services.research.research_models import EvidenceItem
    parent = EvidenceItem(id="parent", title="Issuer index", canonical_url="https://www.infosys.com/investors/reports-filings.html",
        channel="web", query_class="issuer_documents", metadata={"read_success": True, "page_metadata": {"observed_links": [
            {"url": "https://www.infosys.com/investors/results.html", "text": "Quarterly results"},
            {"url": "https://www.infosys.com.evil.invalid/results.html", "text": "Quarterly results"},
            {"url": "https://www.infosys.com/careers.html", "text": "Careers"},
        ]}})
    children = _observed_issuer_documents(parent)
    assert len(children) == 1 and children[0].content == ""
    assert not children[0].acquired_id and children[0].content_depth == "INDEX_SNIPPET"
    assert children[0].metadata["discovered_on_candidate_id"] == "parent"


def test_pipeline_timings_are_nonnegative_additive_diagnostics():
    from tests.unit.test_research_pipeline_golden import capture_scenario
    payload = capture_scenario("relevant", include_payload=True)
    timings = payload["result"]["telemetry"]["stage_timings_ms"]
    assert "Deep reading" in timings and "Query planning" in timings
    assert len(timings) == 11 and all(isinstance(v, (int, float)) and v >= 0 for v in timings.values())


def test_native_body_is_preserved_but_snippet_and_profile_are_not_upgraded(monkeypatch):
    from backend.application.research.acquisition import CandidateQualificationStage
    from backend.services.agent_reach.channels import EvidenceFragment
    from backend.services.research.research_models import ResearchRequest
    from backend.services.research.relevance_gate import relevance_gate
    monkeypatch.setattr(relevance_gate, "filter_candidates", lambda items, **kw: (items, []))
    fragments = [EvidenceFragment(platform="web", url="https://example.org/"+depth,
        content="Captured native source body.", evidence_id=depth, content_depth=depth)
        for depth in ("PARTIAL_CONTENT", "COMMENT", "VIDEO_TRANSCRIPT", "SNIPPET", "PROFILE_METADATA")]
    discovery = CandidateQualificationStage().run(ResearchRequest(target="Example"),
        SimpleNamespace(source_article=None, fragments=fragments))
    for item in discovery.accepted:
        if item.id in {"SNIPPET", "PROFILE_METADATA"}:
            assert not item.acquired_id
        else:
            assert item.acquired_id and item.metadata["acquired_during_discovery"]
            assert item.content == "Captured native source body."
