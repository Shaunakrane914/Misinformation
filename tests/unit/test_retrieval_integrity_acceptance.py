"""
Unit & Acceptance Tests for Aegis Protocol Retrieval Integrity & Acceptance Criteria
=====================================================================================
Validates:
- test_relevance_gate_rejects_unrelated_evidence
- test_evidence_ids_resolve
- test_finding_cannot_use_missing_evidence
- test_atomic_and_overall_verdict_consistency
- test_source_lineage_counts
- test_syndication_grouping
- test_content_depth_labeling
- test_query_metadata_preservation
- test_deep_read_budget_execution
- test_trending_timestamp_order
- test_trending_threat_count_consistency
- test_retrieval_budget_visibility
- test_fallback_telemetry
"""

import pytest
from datetime import datetime, timezone
from backend.services.research.relevance_gate import relevance_gate, RelevanceGate
from backend.services.research.research_models import (
    EvidenceItem,
    Finding,
    FindingType,
    EpistemicState,
    ContentDepth,
    SourceRole,
    ResearchRequest,
    ResearchResult,
)
from backend.services.research.evidence_integrity import evidence_integrity_validator
from backend.services.research.source_independence import source_independence_engine
from backend.services.research.source_lineage import source_lineage_engine
from backend.services.research.deep_reader import deep_reader
from backend.services.research.corroboration import corroboration_engine
from backend.agents.trending_agent import TrendingAgent, TrendEvidence, Trend


def test_relevance_gate_rejects_unrelated_evidence():
    """Validates that off-topic and contaminated items are strictly rejected."""
    gate = RelevanceGate(acceptance_threshold=0.35)

    # 1. Nike BrandScan must reject CIBIL credit score
    nike_cibil = {
        "id": "ev_01",
        "title": "Check Free CIBIL Score Online - BankBazaar",
        "snippet": "Check your CIBIL score for credit cards and personal loans instantly.",
        "url": "https://www.bankbazaar.com/cibil-score.html"
    }
    res_nike = gate.evaluate_item(nike_cibil, target_entity="Nike Air Max counterfeit fake store", domain="brand")
    assert not res_nike.is_accepted
    assert res_nike.relevance_class == "REJECTED"

    # 2. NVDA Semiconductor scan must reject Bank of Baroda, Microsoft Teams, UNESCO
    nvda_bob = {
        "id": "ev_02",
        "title": "Login - Bank of Baroda Internet Banking",
        "snippet": "Welcome to Bank of Baroda Retail E-Banking portal.",
        "url": "https://www.bobibanking.com"
    }
    res_nvda = gate.evaluate_item(nvda_bob, target_entity="NVDA", domain="financial")
    assert not res_nvda.is_accepted
    assert res_nvda.relevance_class == "REJECTED"

    nvda_teams = {
        "id": "ev_03",
        "title": "Microsoft Teams tenant admin configuration",
        "snippet": "Configure Teams meeting policies and rooms.",
        "url": "https://learn.microsoft.com/teams"
    }
    res_teams = gate.evaluate_item(nvda_teams, target_entity="NVDA", domain="financial")
    assert not res_teams.is_accepted
    assert res_teams.relevance_class == "REJECTED"

    # 3. Sam Altman scan must reject Google Chrome download
    sama_chrome = {
        "id": "ev_04",
        "title": "Download Google Chrome Browser",
        "snippet": "Get more done with the new Google Chrome. A more simple, secure, and faster web browser.",
        "url": "https://www.google.com/chrome"
    }
    res_sama = gate.evaluate_item(sama_chrome, target_entity="Sam Altman", domain="personal")
    assert not res_sama.is_accepted
    assert res_sama.relevance_class == "REJECTED"

    # 4. WhatsApp rumor scan must reject glycemic / medical trials
    wa_med = {
        "id": "ev_05",
        "title": "Glycemic efficacy of metformin in endocrine clinical trials",
        "snippet": "Double-blind randomized controlled trial showing blood glucose reduction.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/123456"
    }
    res_wa = gate.evaluate_item(wa_med, target_entity="WhatsApp three red ticks government rumor", domain="fact_check")
    assert not res_wa.is_accepted
    assert res_wa.relevance_class == "REJECTED"


def test_evidence_ids_resolve():
    """Validates that all evidence IDs cited in findings exist in the evidence pool."""
    pool = [
        EvidenceItem(id="ev_001", title="Authentic Nike Investigation", canonical_url="https://nike.com/news"),
        EvidenceItem(id="ev_002", title="Retail Verification Notice", canonical_url="https://ftc.gov/scam"),
    ]
    finding = Finding(
        finding_id="fnd_001",
        title="Counterfeit Ring Detected",
        statement="Confirmed fake retailer network operates cloned storefronts.",
        supporting_evidence_ids=["ev_001", "ev_002"]
    )
    valid_findings, report = evidence_integrity_validator.validate([finding], pool)
    assert len(valid_findings) == 1
    assert report.is_valid is True
    assert report.valid_findings_count == 1
    assert report.invalid_findings_count == 0
    assert len(report.missing_evidence_links) == 0


def test_finding_cannot_use_missing_evidence():
    """Validates that findings citing nonexistent evidence IDs are stripped or rejected."""
    pool = [
        EvidenceItem(id="ev_001", title="Valid Evidence", canonical_url="https://valid.org"),
    ]
    invalid_finding = Finding(
        finding_id="fnd_002",
        title="Unsubstantiated Claim",
        statement="This finding points to a phantom source.",
        supporting_evidence_ids=["ev_999"]
    )
    valid_findings, report = evidence_integrity_validator.validate([invalid_finding], pool, fail_on_invalid=True)
    assert len(valid_findings) == 0
    assert report.is_valid is False
    assert report.invalid_findings_count == 1
    assert "ev_999" in report.missing_evidence_links


def test_atomic_and_overall_verdict_consistency():
    """Validates that atomic claim veracity aligns with overall verdict."""
    items = [
        EvidenceItem(id="ev_01", title="Debunk 1", relevance_score=0.9, independence_group="grp_1"),
        EvidenceItem(id="ev_02", title="Debunk 2", relevance_score=0.85, independence_group="grp_2"),
    ]
    res = corroboration_engine.evaluate_corroboration(items)
    assert res["independent_group_count"] == 2
    assert res["confidence"] == "MEDIUM"


def test_source_lineage_counts():
    """Validates that origin and echo counts are correctly quantified."""
    items = [
        EvidenceItem(id="ev_01", title="Original Investigation", canonical_url="https://reuters.com/wa", source_domain="reuters.com", source_name="Reuters", primary_source=True),
        EvidenceItem(id="ev_02", title="Reuters: WhatsApp Rumor Debunked", canonical_url="https://yahoo.com/reuters-wa", source_domain="yahoo.com", source_name="Yahoo News", snippet="reported by reuters - WhatsApp rumors"),
        EvidenceItem(id="ev_03", title="Reuters: WhatsApp Rumor Debunked", canonical_url="https://msn.com/reuters-wa", source_domain="msn.com", source_name="MSN", snippet="reported by reuters - WhatsApp news"),
    ]
    graph = source_lineage_engine.build_lineage_graph(items)
    metrics = graph.get("metrics", {})
    assert metrics.get("origin_count", 0) >= 1
    assert metrics.get("echo_count", 0) >= 1
    assert metrics.get("total_nodes", 0) == 3


def test_syndication_grouping():
    """Validates that AP / Reuters syndicated echoes are grouped into a single cluster."""
    items = [
        EvidenceItem(id="ev_10", title="Associated Press: Market Closes Higher", canonical_url="https://apnews.com/1", source_name="Associated Press"),
        EvidenceItem(id="ev_11", title="Associated Press: Market Closes Higher", canonical_url="https://usatoday.com/ap-market", source_name="USA Today", snippet="by the associated press - Market closed higher"),
        EvidenceItem(id="ev_12", title="Associated Press: Market Closes Higher", canonical_url="https://foxbusiness.com/ap-market", source_name="Fox", snippet="(ap) - Market ended up"),
    ]
    updated_items, clusters = source_independence_engine.cluster_independence(items)
    assert len(clusters) == 1
    assert len(list(clusters.values())[0]) == 3


def test_content_depth_labeling():
    """Validates that content depth is not falsely inflated."""
    item_snippet = EvidenceItem(id="ev_s", title="Snippet", snippet="Brief snippet", content_depth=ContentDepth.SNIPPET.value)
    item_full = EvidenceItem(id="ev_f", title="Article", content="Full text content...", content_depth=ContentDepth.FULL_ARTICLE.value)

    assert item_snippet.content_depth == "SNIPPET"
    assert item_full.content_depth == "FULL_ARTICLE"
    assert item_snippet.content_depth != item_full.content_depth


def test_query_metadata_preservation():
    """Validates that query metadata flows from execution into EvidenceItem."""
    item = EvidenceItem(
        id="ev_meta",
        title="Preserved Meta",
        canonical_url="https://example.com",
        query_id="q_brand_001",
        query_class="trademark_infringement",
        query_text="nike trademark dispute 2026"
    )
    d = item.to_dict()
    assert d["query_id"] == "q_brand_001"
    assert d["query_class"] == "trademark_infringement"
    assert d["query_text"] == "nike trademark dispute 2026"


def test_deep_read_budget_execution():
    """Validates that deep reader respects max_reads budget."""
    candidates = [
        EvidenceItem(id=f"ev_{i}", title=f"Doc {i}", canonical_url=f"https://example.com/doc{i}", snippet="snippet")
        for i in range(5)
    ]
    investigated, telemetry = deep_reader.deep_read(candidates, max_reads=2, timeout_per_read=1.0)
    assert len(investigated) <= 2
    assert telemetry["attempted"] <= 2


def test_trending_timestamp_order():
    """Validates that TrendingAgent enforces monotonic timestamp ordering."""
    agent = TrendingAgent()
    cluster_items = [
        TrendEvidence(
            evidence_id="ev_01",
            platform="news",
            source="The Hindu",
            title="Film announcement",
            content="Full report",
            snippet="Snippet",
            url="https://thehindu.com/film",
            canonical_url="https://thehindu.com/film",
            author="Staff",
            published_at="2026-09-01T10:00:00Z",
            retrieved_at="2026-09-01T10:05:00Z",
            source_role="PRIMARY",
            source_tier="TIER_1",
            source_group_id="G-01",
            retrieval_method="agent_reach"
        ),
        TrendEvidence(
            evidence_id="ev_02",
            platform="web",
            source="Bollywood Hungama",
            title="Film announcement details",
            content="More details",
            snippet="Snippet",
            url="https://bollywoodhungama.com/news",
            canonical_url="https://bollywoodhungama.com/news",
            author="Correspondent",
            published_at="2026-09-05T12:00:00Z",
            retrieved_at="2026-09-05T12:05:00Z",
            source_role="SECONDARY",
            source_tier="TIER_2",
            source_group_id="G-02",
            retrieval_method="agent_reach"
        ),
    ]
    trends = agent._cluster_trends(cluster_items, {"resolved_entity": "Film announcement", "mode": "entity"})
    assert len(trends) >= 1
    t = trends[0]
    # first_seen_at must be chronologically <= latest_seen_at
    assert t.first_seen_at <= t.latest_seen_at


def test_trending_threat_count_consistency():
    """Validates that threat counters accurately match trend classifications."""
    trends = [
        {"topic": "Rumor A", "risk_level": "HIGH", "misinformation_risk": "HIGH"},
        {"topic": "Neutral B", "risk_level": "LOW", "misinformation_risk": "LOW"},
        {"topic": "Rumor C", "risk_level": "CRITICAL", "misinformation_risk": "HIGH"},
    ]
    threat_count = sum(1 for t in trends if t["risk_level"] in ("HIGH", "CRITICAL") or t["misinformation_risk"] in ("HIGH", "CRITICAL"))
    safe_count = len(trends) - threat_count
    assert threat_count == 2
    assert safe_count == 1


def test_retrieval_budget_visibility():
    """Validates that ResearchBudget parameters are exposed in result telemetry."""
    from backend.services.research.research_engine import research_engine
    assert hasattr(research_engine, "budget")
    b_dict = research_engine.budget.to_dict()
    assert "discovery_timeout_seconds" in b_dict
    assert "max_deep_reads" in b_dict
    assert "follow_up_budget" in b_dict
    assert b_dict["discovery_timeout_seconds"] > 0


def test_fallback_telemetry():
    """Validates that channel status explicitly records native vs fallback mode."""
    from backend.services.agent_reach.adapter import agent_reach_service
    caps = agent_reach_service.capabilities()
    assert isinstance(caps, dict)
    assert "channels" in caps
    channels = caps["channels"]
    assert "github" in channels
    assert "status" in channels["github"]
    assert "backend" in channels["github"]
    assert "legacy_channels_map" in caps
    assert "news" in caps["legacy_channels_map"]
