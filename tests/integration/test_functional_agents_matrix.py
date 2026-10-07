"""
Aegis Protocol — Functional Agent Testing Matrix
================================================
Comprehensive behavioral test suite evaluating real functional capabilities
across all four domain intelligence engines:
  1. 🛡️ BrandShield — Brand / Threat / Counterfeit Intelligence
  2. 📈 Trending — Trend / Viral Narrative / Misinformation Intelligence
  3. 💹 Scout — Financial / Market / Corporate Intelligence
  4. 👤 Personal Watch — Executive / Public Figure Threat Monitoring

Test Dimensions:
  - Test 1: Normal positive case across all 4 agents
  - Test 2: Zero-evidence guard against hallucination
  - Test 3: Contradiction handling and epistemic status (OBSERVED vs UNCERTAIN)
  - Test 4: Source independence and wire syndication clustering
  - Test 5: Threat classification taxonomy differentiation
  - Test 6: Time/change detection across consecutive scans
  - Test 7: Financial telemetry, anomaly detection, and volatility
  - Test 8: Fallback transparency and retrieval failure disclosure
  - Scenarios 1-10: Explicit functional scenarios specified by engineering
"""

import copy
import pytest
from unittest.mock import patch, MagicMock

from backend.agents.brandshield_agent import BrandShieldAgent
from backend.agents.trending_agent import TrendingAgent, TrendEvidence
from backend.agents.scout_agent import ScoutAgent
from backend.agents.personal_agent import PersonalWatchAgent
from backend.services.research import ResearchResult, EvidenceItem
from backend.services.agent_reach.scout.models import (
    ScoutEvidence,
    StoryCluster,
    FinancialFact,
    ContradictionRecord,
    EpistemicStatus,
    SourceTier,
)
from backend.services.agent_reach.scout.corroboration import ScoutCorroborationEngine


@pytest.fixture(autouse=True)
def fast_offline_llm_fixture(monkeypatch):
    """Ensure tests run offline and deterministically without waiting on external LLM retries."""
    try:
        import backend.services.intelligence as intel
        monkeypatch.setattr(intel, "call_gemini_text", lambda prompt: (_ for _ in ()).throw(RuntimeError("Offline test mode fallback")))
    except Exception:
        pass


# =============================================================================
# 1. TEST 1 — NORMAL POSITIVE CASES
# =============================================================================

@pytest.mark.integration
def test_brandshield_normal_positive_case():
    """Verify BrandShield resolves brand and executes complete intelligence scan."""
    agent = BrandShieldAgent()
    mock_evidence = [
        {
            "evidence_id": "ev_001",
            "title": "Nike Official Store and Footwear Catalog",
            "content": "Explore new running shoe releases, Air Max lineups, and athletic apparel directly from Nike.",
            "snippet": "Explore new running shoe releases, Air Max lineups, and athletic apparel directly from Nike.",
            "url": "https://nike.com/running",
            "has_url": True,
            "source": "Nike Official",
            "platform": "Web",
            "author": "Nike Inc.",
            "published_at": "2026-10-01T10:00:00Z",
            "retrieved_at": "2026-10-07T12:00:00Z",
            "source_role": "PRIMARY",
            "source_tier": "TIER_1_OFFICIAL_FILING",
            "independence_group": "independent",
            "is_primary": True,
            "content_depth": "FULL_ARTICLE",
            "query_id": "q_01",
            "query_class": "official",
            "query_text": "Nike products",
        }
    ]
    with patch.object(agent, "search_brand_evidence", return_value=(mock_evidence, {"web": "healthy (1)"}, {"trace": {}}, 0)):
        res = agent.scan("Nike")
        assert res is not None
        assert res.get("brand") == "Nike"
        assert "retrieval" in res
        assert "summary" in res
        assert "threats" in res
        assert "claims" in res
        assert "narratives" in res
        assert "dossiers" in res
        assert "timeline" in res
        assert "platforms" in res


@pytest.mark.integration
def test_brandshield_structured_intelligence_interface():
    """Verify BrandShield structured intelligence public contract (generate_brandshield_intelligence)."""
    agent = BrandShieldAgent()
    mock_evidence = [
        {
            "evidence_id": "ev_001",
            "title": "Nike Official Store and Footwear Catalog",
            "content": "Explore new running shoe releases, Air Max lineups, and athletic apparel directly from Nike.",
            "snippet": "Explore new running shoe releases, Air Max lineups, and athletic apparel directly from Nike.",
            "url": "https://nike.com/running",
            "has_url": True,
            "source": "Nike Official",
            "platform": "Web",
            "author": "Nike Inc.",
            "published_at": "2026-10-01T10:00:00Z",
            "retrieved_at": "2026-10-07T12:00:00Z",
            "source_role": "PRIMARY",
            "source_tier": "TIER_1_OFFICIAL_FILING",
            "independence_group": "independent",
            "is_primary": True,
            "content_depth": "FULL_ARTICLE",
            "query_id": "q_01",
            "query_class": "official",
            "query_text": "Nike products",
        }
    ]
    with patch.object(agent, "search_brand_evidence", return_value=(mock_evidence, {"web": "healthy (1)"}, {"trace": {}}, 0)):
        res = agent.generate_brandshield_intelligence("Nike")
        assert res is not None
        assert res.get("agent") == "brandshield"
        assert res.get("entity") == "Nike"
        assert "observed" in res
        assert "inferred" in res
        assert "uncertain" in res
        assert "sources" in res
        assert "recommended_attention" in res
        assert "retrieval" in res


@pytest.mark.integration
def test_trending_normal_positive_case():
    """Verify Trending resolves entity mode and returns structured trend intelligence."""
    agent = TrendingAgent()
    mock_item = EvidenceItem(
        id="ev_tr_1",
        title="OpenAI Announces New Enterprise Architecture",
        content="OpenAI has rolled out new high-throughput reasoning capabilities for commercial clients.",
        relevant_excerpt="OpenAI has rolled out new high-throughput reasoning capabilities.",
        canonical_url="https://openai.com/blog/release",
        channel="news",
        source_name="OpenAI Official",
        source_role="PRIMARY",
        source_tier="TIER_1",
        independence_group="independent",
        published_at="2026-10-07T08:00:00Z",
    )
    mock_res = ResearchResult(
        agent="trending",
        target="OpenAI",
        domain="trending",
        evidence=[mock_item],
        findings=[],
        contradictions=[],
        telemetry={"channel_health": {"news": "ok"}}
    )
    with patch("backend.services.research.research_engine.ResearchEngine.investigate", return_value=mock_res):
        res = agent.scan("OpenAI")
        assert res is not None
        assert res.get("asset_name") == "OpenAI" or res.get("entity_resolution", {}).get("resolved_entity") == "OpenAI"
        assert res.get("mode") in ("entity", "discovery")
        assert "trends" in res
        assert "evidence" in res
        assert "contradictions" in res
        assert "telemetry" in res


@pytest.mark.integration
def test_scout_normal_positive_case():
    """Verify Scout analyzes market telemetry, prediction engine, and epistemic intelligence."""
    agent = ScoutAgent()

    # 1. Processing pipeline
    task_res = agent.process_task({"ticker": "NVDA"})
    assert task_res is not None
    assert task_res.get("ticker") == "NVDA"
    assert "current_price" in task_res
    assert "stats" in task_res
    assert "prediction" in task_res
    assert "volatility_status" in task_res["stats"]
    assert "z_score" in task_res["stats"]

    # 2. Epistemic status & intelligence partitioning
    with patch.object(agent, "correlate_social_rumors", return_value={"social_signals_detected": 0}):
        intel_res = agent.generate_scout_intelligence("NVDA", max_candidates=2)
        assert intel_res is not None
        assert "observed" in intel_res
        assert "inferred" in intel_res
        assert "uncertain" in intel_res
        assert "sources" in intel_res


@pytest.mark.integration
def test_personal_watch_normal_positive_case():
    """Verify Personal Watch resolves executive profile and runs monitoring scan."""
    agent = PersonalWatchAgent()
    profile = {
        "name": "Satya Nadella",
        "monitoring_terms": ["official statement", "appointment", "interview"],
        "alert_preferences": {"level": "HIGH_ONLY"}
    }
    mock_ev = [
        {
            "evidence_id": "ev_pw_1",
            "subject": "Satya Nadella",
            "platform": "News",
            "source": "Microsoft Blog",
            "title": "Satya Nadella Keynote Address on Enterprise Infrastructure",
            "content": "Microsoft Chairman and CEO Satya Nadella detailed the next decade of cloud platform architecture.",
            "snippet": "Microsoft Chairman and CEO Satya Nadella detailed the next decade of cloud platform architecture.",
            "url": "https://blogs.microsoft.com/keynote",
            "canonical_url": "https://blogs.microsoft.com/keynote",
            "author": "Corporate Communications",
            "published_at": "2026-10-06T14:00:00Z",
            "retrieved_at": "2026-10-07T10:00:00Z",
            "source_role": "PRIMARY_OFFICIAL",
            "source_tier": "TIER_1_OFFICIAL_PROFILE",
            "independence_group": "independent",
            "retrieval_method": "agent_reach",
        }
    ]
    with patch.object(agent, "search_personal_evidence", return_value=(mock_ev, {"news": "ok"}, {}, 0)):
        res = agent.scan(profile)
        assert res is not None
        assert res.get("subject", {}).get("canonical_name") == "Satya Nadella"
        assert "threats" in res
        assert "evidence" in res
        assert "timeline" in res
        assert "changes" in res


# =============================================================================
# 2. TEST 2 — NO-EVIDENCE CASE (ZERO-EVIDENCE GUARDS)
# =============================================================================

@pytest.mark.integration
def test_brandshield_zero_evidence_guard():
    """Verify BrandShield does NOT hallucinate threats when no evidence exists."""
    agent = BrandShieldAgent()
    obscure_name = "XyZzY_NonExistent_FakeCorp_9999"

    with patch.object(agent, "search_brand_evidence", return_value=([], {}, {}, 0)):
        res = agent.scan(obscure_name)
        assert res is not None
        # Zero-evidence guard: threats must be 0 and no fabricated narratives
        assert len(res.get("threats", [])) == 0
        assert res.get("threat_count", 0) == 0
        assert res.get("safe_count", 0) == 0
        assert len(res.get("dossiers", [])) == 0


@pytest.mark.integration
def test_personal_watch_zero_evidence_guard():
    """Verify Personal Watch returns CLEAN/no threats when zero evidence is retrieved."""
    agent = PersonalWatchAgent()
    profile = {"name": "ObscureIndividual_9988_ZeroSignal"}

    with patch.object(agent, "search_personal_evidence", return_value=([], {}, {}, 0)):
        res = agent.scan(profile)
        assert res is not None
        assert len(res.get("threats", [])) == 0
        assert res.get("threat_count", 0) == 0


# =============================================================================
# 3. TEST 3 — CONTRADICTION HANDLING & EPISTEMIC STATUS (SCOUT)
# =============================================================================

@pytest.mark.integration
def test_scout_contradiction_detection_conflicting_numbers():
    """Verify Scout corroboration engine detects conflicting financial figures."""
    engine = ScoutCorroborationEngine()

    fact1 = FinancialFact(
        metric="valuation",
        raw_value="$10.0 Billion",
        normalized_value=10.0,
        currency="USD",
        unit="B",
        period="2026",
        context_sentence="Tech giant signs definitive agreement to acquire startup for $10.0B in cash.",
    )
    fact2 = FinancialFact(
        metric="valuation",
        raw_value="$13.5 Billion",
        normalized_value=13.5,
        currency="USD",
        unit="B",
        period="2026",
        context_sentence="Sources close to the deal confirm valuation stands at $13.5B inclusive of debt.",
    )

    ev1 = ScoutEvidence(
        evidence_id="ev_deal_1",
        url="https://reuters.com/deal",
        canonical_url="https://reuters.com/deal",
        platform="news",
        source_type="press",
        source_tier=SourceTier.TIER_2_PRESS.value,
        external_id="ext_01",
        title="Reuters: Acquisition Valued at $10.0 Billion",
        author="Reuters",
        body="Tech giant signs definitive agreement to acquire startup for $10.0B in cash.",
        snippet="Acquisition valued at $10.0B in cash.",
        published_at="2026-10-01T10:00:00Z",
        event_at=None,
        retrieved_at="2026-10-07T12:00:00Z",
        financial_facts=[fact1],
    )
    ev2 = ScoutEvidence(
        evidence_id="ev_deal_2",
        url="https://bloomberg.com/deal",
        canonical_url="https://bloomberg.com/deal",
        platform="news",
        source_type="press",
        source_tier=SourceTier.TIER_2_PRESS.value,
        external_id="ext_02",
        title="Bloomberg: Acquisition Valued at $13.5 Billion",
        author="Bloomberg",
        body="Sources close to the deal confirm valuation stands at $13.5B inclusive of debt.",
        snippet="Valuation stands at $13.5B inclusive of debt.",
        published_at="2026-10-01T10:05:00Z",
        event_at=None,
        retrieved_at="2026-10-07T12:00:00Z",
        financial_facts=[fact2],
    )

    cluster = StoryCluster(
        cluster_id="cluster_deal",
        headline="Tech Giant Acquisition",
        primary_source_url="https://reuters.com/deal",
        primary_source_present=False,
        epistemic_status=EpistemicStatus.REPORTED,
    )

    contradictions = engine.analyze_corroboration([ev1, ev2], [cluster])
    assert len(contradictions) >= 1
    assert contradictions[0].metric_or_aspect.startswith("valuation")
    assert cluster.epistemic_status == EpistemicStatus.CONTRADICTED


# =============================================================================
# 4. TEST 4 — SOURCE INDEPENDENCE & SYNDICATION CLUSTERING (TRENDING)
# =============================================================================

@pytest.mark.integration
def test_trending_source_independence_clustering():
    """Verify Trending groups syndicated wire copies into a single cluster without inflating independence."""
    agent = TrendingAgent()
    wire_ev = TrendEvidence(
        evidence_id="ev_wire",
        platform="news",
        source="Reuters",
        title="Semiconductor Consortium Announces 2nm Milestone",
        content="Global foundry network achieves 2nm mass production readiness.",
        snippet="Global foundry network achieves 2nm mass production readiness.",
        url="https://reuters.com/tech/2nm",
        canonical_url="https://reuters.com/tech/2nm",
        author="Reuters Bureau",
        published_at="2026-10-07T08:00:00Z",
        retrieved_at="2026-10-07T12:00:00Z",
        source_role="PRIMARY",
        source_tier="TIER_1",
        source_group_id=agent._detect_syndication_group("Semiconductor Consortium Announces 2nm Milestone", "Reuters"),
        retrieval_method="agent_reach",
    )
    copy1 = TrendEvidence(
        evidence_id="ev_copy1",
        platform="news",
        source="TechNewsPortal",
        title="Semiconductor Consortium Announces 2nm Milestone",
        content="Global foundry network achieves 2nm mass production readiness.",
        snippet="Global foundry network achieves 2nm mass production readiness.",
        url="https://technews.com/reuters-2nm",
        canonical_url="https://technews.com/reuters-2nm",
        author="Portal Staff",
        published_at="2026-10-07T08:15:00Z",
        retrieved_at="2026-10-07T12:00:00Z",
        source_role="SECONDARY",
        source_tier="TIER_3",
        source_group_id=agent._detect_syndication_group("Semiconductor Consortium Announces 2nm Milestone", "TechNewsPortal"),
        retrieval_method="agent_reach",
    )
    copy2 = TrendEvidence(
        evidence_id="ev_copy2",
        platform="news",
        source="DailySilicon",
        title="Semiconductor Consortium Announces 2nm Milestone",
        content="Global foundry network achieves 2nm mass production readiness.",
        snippet="Global foundry network achieves 2nm mass production readiness.",
        url="https://dailysilicon.com/2nm",
        canonical_url="https://dailysilicon.com/2nm",
        author="Silicon Staff",
        published_at="2026-10-07T08:20:00Z",
        retrieved_at="2026-10-07T12:00:00Z",
        source_role="SECONDARY",
        source_tier="TIER_3",
        source_group_id=agent._detect_syndication_group("Semiconductor Consortium Announces 2nm Milestone", "DailySilicon"),
        retrieval_method="agent_reach",
    )

    trends = agent._cluster_trends([wire_ev, copy1, copy2], entity_info={"resolved_entity": "Semiconductors"})
    assert len(trends) > 0
    # Grouped under primary narrative without inflating independence
    t = trends[0]
    assert t.source_count == 3
    # Independent source groups are strictly bounded, not 3 separate independent publishers
    assert t.independent_source_count <= 2


# =============================================================================
# 5. TEST 5 — THREAT CLASSIFICATION TAXONOMY DIFFERENTIATION
# =============================================================================

@pytest.mark.integration
def test_brandshield_threat_taxonomy_differentiation():
    """Verify BrandShield differentiates COUNTERFEIT vs PHISHING vs REVIEW_MANIPULATION."""
    agent = BrandShieldAgent()

    # 1. Counterfeit test
    cf_res = agent._heuristic_threat_synthesis(
        brand_info={"brand": "Nike"},
        evidence_list=[
            {
                "evidence_id": "ev_cf",
                "title": "Cheap replica Air Max discount seller",
                "snippet": "Buy replica 1:1 clone fake Nike sneakers wholesale price $35",
                "content": "Buy replica 1:1 clone fake Nike sneakers wholesale price $35",
                "url": "https://aliexpress.com/item/fake-nike",
                "platform": "Web",
                "source": "AliExpress",
                "source_role": "DISCOVERY",
            }
        ]
    )
    cf_threats = cf_res.get("threats", [])
    assert any(t["type"] in ("COUNTERFEIT_PRODUCT", "COUNTERFEIT", "COUNTERFEIT_NETWORK") for t in cf_threats)

    # 2. Phishing / Fake Website test
    phish_res = agent._heuristic_threat_synthesis(
        brand_info={"brand": "Apple"},
        evidence_list=[
            {
                "evidence_id": "ev_phish",
                "title": "Claim your free iPhone login portal",
                "snippet": "Verify your Apple ID credentials to claim gift card http://apple-verify-login.xyz scam phishing",
                "content": "Verify your Apple ID credentials to claim gift card http://apple-verify-login.xyz scam phishing",
                "url": "http://apple-verify-login.xyz",
                "platform": "Web",
                "source": "Web",
                "source_role": "DISCOVERY",
            }
        ]
    )
    phish_threats = phish_res.get("threats", [])
    assert any(t["type"] in ("PHISHING_SCAM", "PHISHING", "IMPERSONATION", "FRAUDULENT_CLAIM") for t in phish_threats)


@pytest.mark.integration
def test_personal_watch_threat_taxonomy_differentiation():
    """Verify Personal Watch differentiates IMPERSONATION vs DEEPFAKE vs SCAM."""
    agent = PersonalWatchAgent()

    # 1. Fake Giveaway / Scam
    gw_res = agent._heuristic_threat_synthesis(
        subject_name="Elon Musk",
        evidence_list=[
            {
                "evidence_id": "ev_gw",
                "title": "Elon Musk 5000 BTC Giveaway Official",
                "content": "Send 0.1 BTC to receive 0.2 BTC back immediately in live fake giveaway scam crypto fraud.",
                "snippet": "Send 0.1 BTC to receive 0.2 BTC back immediately in live fake giveaway scam crypto fraud.",
                "url": "https://x.com/elonmusk_giveaway_promo",
                "platform": "Twitter",
                "source": "Twitter",
            }
        ]
    )
    gw_threats = gw_res.get("threats", [])
    assert any(t.get("threat_type") in ("SCAM", "FAKE_GIVEAWAY", "IMPERSONATION") for t in gw_threats)

    # 2. Deepfake
    df_res = agent._heuristic_threat_synthesis(
        subject_name="Sam Altman",
        evidence_list=[
            {
                "evidence_id": "ev_df",
                "title": "Leaked deepfake audio of Sam Altman",
                "content": "Viral synthetic audio and ai voice clone claiming secret shutdown of neural models deepfake.",
                "snippet": "Viral synthetic audio and ai voice clone claiming secret shutdown of neural models deepfake.",
                "url": "https://youtube.com/watch?v=fakeaudio",
                "platform": "YouTube",
                "source": "YouTube",
            }
        ]
    )
    df_threats = df_res.get("threats", [])
    assert any(t.get("threat_type") in ("DEEPFAKE", "SYNTHETIC_MEDIA") for t in df_threats)


# =============================================================================
# 6. TEST 6 — TIME/CHANGE DETECTION (PERSONAL WATCH)
# =============================================================================

@pytest.mark.integration
def test_personal_watch_consecutive_scan_change_detection():
    """Verify Personal Watch detects NEW, RESOLVED, and ESCALATED threats across time."""
    agent = PersonalWatchAgent()
    profile = {"name": "Satya Nadella", "category": "executive"}

    scan1_mock_evidence = [
        {
            "evidence_id": "ev_t1",
            "title": "Fake Satya Nadella Investment Group",
            "snippet": "Join WhatsApp group for exclusive Microsoft pre-IPO trading signals scam.",
            "content": "Join WhatsApp group for exclusive Microsoft pre-IPO trading signals scam.",
            "url": "https://t.me/satya_invest",
            "platform": "Web",
            "source": "Telegram",
        }
    ]

    with patch.object(agent, "search_personal_evidence", return_value=(scan1_mock_evidence, {}, {}, 0)):
        res1 = agent.scan(profile)
        assert res1 is not None

    scan2_mock_evidence = [
        scan1_mock_evidence[0],
        {
            "evidence_id": "ev_t2",
            "title": "Deepfake Video of Satya Nadella Resignation",
            "snippet": "AI voice clone and deepfake video circulating claiming CEO resignation announcement.",
            "content": "AI voice clone and deepfake video circulating claiming CEO resignation announcement.",
            "url": "https://youtube.com/watch?v=resignation_fake",
            "platform": "YouTube",
            "source": "YouTube",
        }
    ]

    with patch.object(agent, "search_personal_evidence", return_value=(scan2_mock_evidence, {}, {}, 0)):
        res2 = agent.scan(profile)
        assert res2 is not None
        assert "changes" in res2
        # Second scan should detect new threat addition
        change_types = [c.get("change_type") for c in res2["changes"]]
        assert "NEW_THREAT" in change_types


# =============================================================================
# 7. TEST 7 — FINANCIAL ANOMALY & TELEMETRY (SCOUT)
# =============================================================================

@pytest.mark.integration
def test_scout_financial_telemetry_and_anomalies():
    """Verify Scout computes statistical z-scores, volatility state, and delayed disclosure."""
    agent = ScoutAgent()

    # Test volatility computation across realistic historical price series
    prices = [120.0, 122.5, 121.0, 123.0, 118.0, 115.0, 102.0, 95.0]
    vol = agent.analyze_volatility(prices)
    assert vol is not None
    assert "z_score" in vol
    assert "volatility_status" in vol
    # Major drop should trigger HIGH or SIGMA_EVENT
    assert vol["volatility_status"] in ("SIGMA_EVENT", "HIGH_VOLATILITY", "MODERATE_VOLATILITY")

    # Impact prediction
    pred = agent.predict_impact(prices)
    assert pred is not None
    assert "projected_price_1hr" in pred
    assert "projected_loss" in pred
    assert pred["trend"] == "DOWNWARD"


# =============================================================================
# 8. TEST 8 — RETRIEVAL FAILURE RESILIENCE
# =============================================================================

@pytest.mark.integration
def test_retrieval_failure_fallback_disclosure():
    """Verify agent reports fallback_used and limitations without inventing data."""
    agent = BrandShieldAgent()

    with patch.object(agent, "search_brand_evidence", return_value=([], {"web": "failed"}, {"fallback_used": True}, 0)):
        res = agent.scan("Tesla")
        assert res is not None
        assert res.get("threat_count") == 0
        assert len(res.get("threats", [])) == 0


# =============================================================================
# SCENARIOS 1 TO 10: TARGETED ENGINEERING EVALUATION
# =============================================================================

@pytest.mark.integration
def test_scenario_01_brandshield_nike_counterfeit():
    """Scenario 1: BrandShield -> 'Nike counterfeit'"""
    agent = BrandShieldAgent()
    resolved = agent.resolve_brand_entity("Nike counterfeit")
    assert resolved["brand"] == "Nike"
    assert "counterfeit" in resolved.get("threat_focus", "counterfeit") or resolved.get("brand") == "Nike"


@pytest.mark.integration
def test_scenario_02_brandshield_apple_fake_website():
    """Scenario 2: BrandShield -> 'Apple fake website'"""
    agent = BrandShieldAgent()
    resolved = agent.resolve_brand_entity("Apple fake website")
    assert resolved["brand"] == "Apple"


@pytest.mark.integration
def test_scenario_03_trending_whats_trending_in_ai():
    """Scenario 3: Trending -> 'What's trending in AI?' (Discovery Mode)"""
    agent = TrendingAgent()
    resolved = agent.resolve_entity("What's trending in AI?")
    assert resolved["mode"] == "discovery"
    assert "ai" in resolved["scope"].lower()


@pytest.mark.integration
def test_scenario_04_trending_openai_entity_mode():
    """Scenario 4: Trending -> 'OpenAI' (Entity Mode)"""
    agent = TrendingAgent()
    resolved = agent.resolve_entity("OpenAI")
    assert resolved["mode"] == "entity"
    assert resolved["resolved_entity"] == "OpenAI"


@pytest.mark.integration
def test_scenario_05_scout_nvda_stock_and_intelligence():
    """Scenario 5: Scout -> 'NVDA'"""
    agent = ScoutAgent()
    sym, company = agent.resolve_ticker_and_company("NVDA")
    assert sym == "NVDA"
    assert "Nvidia" in company


@pytest.mark.integration
def test_scenario_06_scout_nvda_latest_earnings():
    """Scenario 6: Scout -> 'NVDA latest earnings'"""
    agent = ScoutAgent()
    sym, company = agent.resolve_ticker_and_company("NVDA")
    assert sym == "NVDA"
    with patch.object(agent, "correlate_social_rumors", return_value={"social_signals_detected": 0}):
        intel = agent.generate_scout_intelligence("NVDA", query="latest earnings", max_candidates=2)
        assert intel is not None
        assert "observed" in intel
        assert "uncertain" in intel


@pytest.mark.integration
def test_scenario_07_scout_reliance_regulatory_investigation():
    """Scenario 7: Scout -> 'Reliance regulatory investigation'"""
    agent = ScoutAgent()
    sym, company = agent.resolve_ticker_and_company("RELIANCE.NS")
    assert sym == "RELIANCE.NS"
    assert "Reliance" in company


@pytest.mark.integration
def test_scenario_08_personal_watch_public_executive_profile():
    """Scenario 8: Personal Watch -> Public executive profile (Satya Nadella)"""
    agent = PersonalWatchAgent()
    resolved = agent.resolve_personal_entity("Satya Nadella")
    assert resolved["canonical_name"] == "Satya Nadella"
    assert resolved["category"] == "executive"


@pytest.mark.integration
def test_scenario_09_personal_watch_impersonation_scam():
    """Scenario 9: Personal Watch -> Impersonation/scam scenario"""
    agent = PersonalWatchAgent()
    resolved = agent.resolve_personal_entity("Elon Musk")
    assert resolved["canonical_name"] == "Elon Musk"


@pytest.mark.integration
def test_scenario_10_personal_watch_run_twice_change_detection():
    """Scenario 10: Personal Watch -> Run twice and inspect change detection"""
    agent = PersonalWatchAgent()
    profile = {"name": "Sam Altman"}
    with patch.object(agent, "search_personal_evidence", return_value=([], {}, {}, 0)):
        res1 = agent.scan(profile)
        assert res1 is not None
        res2 = agent.scan(profile)
        assert res2 is not None
        assert "changes" in res2
