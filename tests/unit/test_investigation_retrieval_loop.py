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


def test_issuer_alias_does_not_become_extra_entity_name_tokens():
    from backend.services.research.entity_resolver import entity_resolver
    for target, name in [("Infosys (INFY.NS)", "Infosys"), ("Acme Analytics (ACME.L)", "Acme Analytics")]:
        profile = entity_resolver.parse_request(target, domain="financial").target_entity
        assert profile.canonical_name.casefold() == name.casefold()
        score, _, reason = entity_resolver.evaluate_entity_match(name + " quarterly results", profile)
        assert score >= 0.75 and reason is None


def test_document_links_and_text_share_semantic_root():
    from bs4 import BeautifulSoup
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details, extract_readable_page
    soup = BeautifulSoup('<body><article>Unrelated navigation card</article><main><h1>Issuer results</h1>'
        '<nav><a href="/menu">Menu</a></nav><a href="/investors/q2">Quarterly results</a></main></body>', 'html.parser')
    details = extract_observed_page_details(soup, "https://issuer.example/investors")
    readable = extract_readable_page(soup)
    assert details["content_scope"] == readable["content_scope"] == "main"
    assert details["observed_links"] == [{"url": "https://issuer.example/investors/q2", "text": "Quarterly results",
                                           "external_domain": False, "verification": "UNVERIFIED_PAGE_LINK"}]


def test_trending_native_and_shared_inspection_keep_late_context(monkeypatch):
    from datetime import datetime, timezone
    from backend.agents.trending import agent as module
    from backend.services.research.research_models import EvidenceItem
    from backend.services.report_builder import ReportBuilder
    # This is a preservation fixture, not a moving-window freshness test.
    # Keep its fixed publication inside the real temporal gate on every run.
    monkeypatch.setattr(module.relevance_gate, "reference_time",
                        datetime(2026, 10, 18, 12, tzinfo=timezone.utc))
    body = "Acme announcement context. " * 80 + "Correction: Acme did not approve the proposal in Q2 2024."
    item = EvidenceItem(id="ev_canonical", canonical_url="https://example.org/acme-announcement",
        title="Acme announcement", channel="web", content=body, content_depth="PARTIAL_CONTENT",
        published_at="2026-10-17T00:00:00Z", metadata={"raw_capture": {"text": "Raw menu " + body},
        "page_metadata": {"potential_corrections": ["Correction: Acme did not approve the proposal in Q2 2024."]}})
    monkeypatch.setattr(module.research_engine, "investigate", lambda req: SimpleNamespace(
        evidence=[item], telemetry={}, findings=[], contradictions=[], research_corpus={}))
    agent = module.TrendingAgent.__new__(module.TrendingAgent)
    monkeypatch.setattr(agent, "_cluster_trends", lambda *a: [])
    data = agent.scan("Acme", category="technology", mode="entity")
    record = data["evidence"][0]
    assert record["metadata"]["temporal_eligible"] is True
    assert record["evidence_id"] == "ev_canonical" and record["content"] == body
    assert record["metadata"]["raw_capture"]["text"] == "Raw menu " + body
    report = ReportBuilder.from_trending_result(query="Acme", trend_data=data).to_dict()
    cards = [e for values in report["evidence"].values() for e in values]
    extraction = cards[0]["extraction"]
    assert extraction["captured_chars"] == len(body)
    assert "did not approve" in " ".join(p["text"] for p in extraction["passages"])


def test_publisher_announcements_do_not_share_citations_for_different_propositions():
    from backend.application.research.synthesis import synthesize_grounded_findings
    from backend.services.research.research_models import EvidenceItem
    items = [EvidenceItem(id=code, channel="rss", canonical_url="https://example.org/"+code,
        content=text, relevant_excerpt=text, content_depth="PARTIAL_CONTENT", query_class="publisher_announcements")
        for code, text in [("release_a", "Acme announced a new laptop with 64 GB of memory."),
                           ("release_b", "Acme reported a separate automobile partnership, not a laptop launch.")]]
    findings = synthesize_grounded_findings("Acme", "trending", items, [])
    assert len(findings) == 2
    assert [f.supporting_evidence_ids for f in findings] == [["release_a"], ["release_b"]]
    assert all(f.epistemic_state == "UNVERIFIED" for f in findings)


def test_passage_prefers_release_over_disclaimer_without_deleting_qualifiers():
    from backend.services.research.passage_extractor import passage_extractor
    from backend.services.research.research_models import EvidenceItem
    announcement = "Acme announced a computer with 64 GB of memory, but it will not be available until Q2 2027."
    disclaimer = "Certain statements in this press release including Acme revenue, profit, loss, earnings and reported growth are forward-looking statements."
    item = EvidenceItem(id="source", channel="web", content=announcement+"\n\n"+disclaimer, content_depth="PARTIAL_CONTENT")
    passage_extractor.extract_passages([item], "Acme")
    assert item.relevant_excerpt == announcement
    assert item.content.endswith(disclaimer)
    assert item.content[item.excerpt_start:item.excerpt_end] == item.relevant_excerpt


def test_unknown_source_dates_are_not_fabricated_as_recent():
    from backend.services.agent_reach.native.normalizer import NativeNormalizer, _clean_html_text
    normalizer = NativeNormalizer()
    for fragment in normalizer.normalize_bilibili_videos([{"title": "Video", "bvid": "BVexample"}]) + normalizer.normalize_linkedin_jobs([{"title": "Job"}]):
        assert fragment.published == ""
    assert _clean_html_text("Alpha&nbsp;&amp; beta") == "Alpha & beta"


def test_topic_passage_uses_verified_alias_without_accepting_unrelated_billing():
    from backend.services.research.passage_extractor import passage_extractor
    from backend.services.research.research_models import EvidenceItem
    item = EvidenceItem(id="ev", channel="web", content="EVs are gaining market share, but buyers reported delayed deliveries in 2026.", content_depth="PARTIAL_CONTENT")
    unrelated = EvidenceItem(id="billing", channel="web", content="Electricity bills are payable through your utility account online.", content_depth="PARTIAL_CONTENT")
    passage_extractor.extract_passages([item, unrelated], "electric vehicles")
    assert "but buyers" in item.relevant_excerpt
    assert unrelated.relevant_excerpt == ""


def test_issuer_follow_up_spends_one_remaining_read_slot_and_keeps_link_lineage(monkeypatch):
    import time
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_models import EvidenceItem, ResearchRequest
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.deep_reader import deep_reader
    root = EvidenceItem(id="root", canonical_url="https://www.infosys.com/investors/reports-filings.html", channel="web",
        query_class="issuer_documents", acquired_id="acq_root", acquisition_attempt_id="attempt_root",
        metadata={"acquired_during_discovery": True})
    quarter = EvidenceItem(id="q1", canonical_url="https://www.infosys.com/investors/quarter.html", channel="web",
        query_class="observed_issuer_document", independence_group="publisher_infosys.com", metadata={"document_hop": 1})
    calls = []
    def read(items, max_reads, timeout_per_read):
        calls.append(max_reads)
        for item in items[:max_reads]:
            item.acquired_id="acq_"+item.id
            item.metadata.update(read_success=True, page_metadata={"observed_links": [
                {"url": "https://www.infosys.com/investors/quarter/results.html", "text": "Financial results"}]})
        return items[:max_reads], {"attempted": min(len(items), max_reads), "successful": min(len(items), max_reads)}
    monkeypatch.setattr(deep_reader, "deep_read", read)
    ranked = RankedEvidence([root, quarter], [root, quarter], {}, [])
    result = DeepReadingStage().run(ResearchRequest(target="Infosys", domain="financial", deep_read_budget=2),
        ResearchBudget(deep_read_budget=2), ranked, time.time(), 15)
    assert calls == [1, 1] and result.telemetry["attempted"] == 2
    child = result.linked_candidates[0]
    assert child.metadata["document_hop"] == 2
    assert child.metadata["discovered_on_candidate_id"] == "q1"
    assert child in ranked.ranked and child in result.investigated
    assert child.independence_group == quarter.independence_group


def test_request_does_not_silently_override_configured_research_budget():
    from backend.services.research.research_models import ResearchRequest
    assert ResearchRequest(target="Unseen issuer").timeout_seconds is None
    assert ResearchRequest(target="Unseen issuer", timeout_seconds=0).timeout_seconds == 0


def test_adaptive_search_cannot_consume_the_reserved_read_slice():
    import concurrent.futures
    import threading
    from backend.application.research.adaptive import _bounded_channel_search
    import pytest
    release = threading.Event()
    service = SimpleNamespace(search_channel=lambda *a, **kw: release.wait(1))
    try:
        with pytest.raises(concurrent.futures.TimeoutError):
            _bounded_channel_search(service, "web", "Unseen issuer", 0.01)
    finally:
        release.set()


def test_second_hop_can_select_html_after_bounded_unread_pdf_links():
    from backend.application.research.acquisition import _observed_issuer_documents
    from backend.services.research.research_models import EvidenceItem
    links = [{"url": f"https://www.infosys.com/quarter/results-{i}.pdf", "text": "Quarterly results"} for i in range(5)]
    links.append({"url": "https://www.infosys.com/quarter/results.html", "text": "Quarterly results"})
    item = EvidenceItem(id="index", channel="web", canonical_url="https://www.infosys.com/quarter.html",
        query_class="observed_issuer_document", metadata={"read_success": True, "document_hop": 1,
                                                         "page_metadata": {"observed_links": links}})
    children = _observed_issuer_documents(item, html_only=True)
    assert len(children) == 1 and children[0].canonical_url.endswith("results.html")
    assert len(item.metadata["page_metadata"]["observed_links"]) == 6


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
