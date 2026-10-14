"""
Aegis Protocol — Phase 5 Domain Agent Golden Master Verification Test Suite
===========================================================================
Validates 100% deterministic pre/post-refactor output equivalence between
historical monoliths (commit 81702f0) and new modular domain packages (HEAD)
across all four domain intelligence agents:
  1. BrandShieldAgent (backend/agents/brandshield/)
  2. TrendingAgent (backend/agents/trending/)
  3. ScoutAgent (backend/agents/scout/)
  4. PersonalWatchAgent (backend/agents/personal_watch/)

Evaluates:
  - Threat taxonomy classifications & risk levels
  - Finding counts & safe item filtering
  - Epistemic statuses & contradiction detection
  - Wire syndication & story clustering
  - Agent-specific reporting fields & privacy guards
"""

from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from backend.agents.brandshield_agent import BrandShieldAgent
from backend.agents.trending_agent import TrendingAgent, TrendEvidence
from backend.agents.scout_agent import ScoutAgent
from backend.agents.personal_agent import PersonalWatchAgent
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.scout.models import ScoutSourceRequest
from backend.services.agent_reach.scout.engine import scout_source_engine

GOLDEN_MANIFEST = Path(__file__).with_name("fixtures") / "agents_phase5_golden.json"
STAMP = "2026-10-10T00:00:00Z"


def _build_brand_fixtures():
    nike_primary = {
        "evidence_id": "ev_bs_01",
        "title": "Nike Official Store and Footwear Catalog",
        "content": "Explore new running shoe releases, Air Max lineups, and athletic apparel directly from Nike.",
        "snippet": "Explore new running shoe releases, Air Max lineups, and athletic apparel directly from Nike.",
        "url": "https://nike.com/running",
        "has_url": True,
        "source": "Nike Official",
        "platform": "Web",
        "author": "Nike Inc.",
        "published_at": "2026-10-01T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "PRIMARY",
        "source_tier": "TIER_1_OFFICIAL_FILING",
        "independence_group": "grp_nike_official",
        "is_primary": True,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_01",
        "query_class": "official",
        "query_text": "Nike products",
    }
    nike_partner = {
        "evidence_id": "ev_bs_02",
        "title": "Dick's Sporting Goods Nike Collection",
        "content": "Authorized retailer offering genuine Nike Pegasus and Invincible shoes with verified warranties.",
        "snippet": "Authorized retailer offering genuine Nike Pegasus and Invincible shoes with verified warranties.",
        "url": "https://dickssportinggoods.com/nike",
        "has_url": True,
        "source": "Dicks Sporting Goods",
        "platform": "Web",
        "author": "Retail Staff",
        "published_at": "2026-10-02T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "INDEPENDENT_CONFIRMATION",
        "source_tier": "TIER_2_RETAIL_PARTNER",
        "independence_group": "grp_dicks",
        "is_primary": False,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_02",
        "query_class": "retail",
        "query_text": "Nike authorized sellers",
    }
    apple_counterfeit = {
        "evidence_id": "ev_bs_03",
        "title": "Cheap Apple Store — 90% Off iPhones and AirPods",
        "content": "Buy fake iPhones and unauthorized replica Apple hardware with cryptocurrency or wire transfer.",
        "snippet": "Buy fake iPhones and unauthorized replica Apple hardware with cryptocurrency or wire transfer.",
        "url": "https://apple-discount-counterfeits.xyz/shop",
        "has_url": True,
        "source": "Unknown Scam Vendor",
        "platform": "Web",
        "author": "Fraud Ring",
        "published_at": "2026-10-03T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "SUSPICIOUS",
        "source_tier": "TIER_4_UNVERIFIED",
        "independence_group": "grp_scam_01",
        "is_primary": False,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_03",
        "query_class": "threat_counterfeit",
        "query_text": "Apple counterfeit shop",
    }
    apple_phishing = {
        "evidence_id": "ev_bs_04",
        "title": "Apple ID Security Alert — Login to verify iCloud account",
        "content": "Urgent Apple ID verification required. Enter your Apple password and SSN immediately to avoid lockout.",
        "snippet": "Urgent Apple ID verification required. Enter your Apple password and SSN immediately to avoid lockout.",
        "url": "https://appleid-security-verification.com/login",
        "has_url": True,
        "source": "Phishing Gate",
        "platform": "Web",
        "author": "Phishing Actor",
        "published_at": "2026-10-04T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "ADVERSARIAL",
        "source_tier": "TIER_4_UNVERIFIED",
        "independence_group": "grp_phish_01",
        "is_primary": False,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_04",
        "query_class": "threat_phishing",
        "query_text": "Apple phishing login",
    }
    sony_wire1 = {
        "evidence_id": "ev_bs_05",
        "title": "Sony Reports Q3 PlayStation Console Shipments",
        "content": "(Reuters) Sony Group reported 65 million PS5 units sold worldwide according to Tokyo filings.",
        "snippet": "(Reuters) Sony Group reported 65 million PS5 units sold worldwide according to Tokyo filings.",
        "url": "https://reuters.com/sony-earnings-ps5",
        "has_url": True,
        "source": "Reuters",
        "platform": "News",
        "author": "Reuters Tech",
        "published_at": "2026-10-05T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "PRIMARY",
        "source_tier": "TIER_1_OFFICIAL_FILING",
        "independence_group": "grp_sony_wire",
        "is_primary": True,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_05",
        "query_class": "official",
        "query_text": "Sony PS5 shipments",
    }
    sony_wire2 = {
        "evidence_id": "ev_bs_06",
        "title": "Sony Reports Q3 PlayStation Console Shipments",
        "content": "Reporting by Reuters: Sony Group reported 65 million PS5 units sold worldwide according to Tokyo filings.",
        "snippet": "Reporting by Reuters: Sony Group reported 65 million PS5 units sold worldwide according to Tokyo filings.",
        "url": "https://finance.yahoo.com/sony-earnings-ps5",
        "has_url": True,
        "source": "Yahoo Finance",
        "platform": "News",
        "author": "Reuters / Yahoo",
        "published_at": "2026-10-05T10:05:00Z",
        "retrieved_at": STAMP,
        "source_role": "INDEPENDENT_CONFIRMATION",
        "source_tier": "TIER_1_OFFICIAL_FILING",
        "independence_group": "grp_sony_wire",
        "is_primary": False,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_06",
        "query_class": "official",
        "query_text": "Sony PS5 shipments",
    }
    tesla_exec_scam = {
        "evidence_id": "ev_bs_07",
        "title": "Elon Musk Crypto Giveaway Official 5000 BTC Promo",
        "content": "Send 1 ETH to Tesla official promotion wallet and receive 2 ETH back immediately.",
        "snippet": "Send 1 ETH to Tesla official promotion wallet and receive 2 ETH back immediately.",
        "url": "https://twitter.com/elon_tesla_giveaway/status/12345",
        "has_url": True,
        "source": "Twitter/X Impersonator",
        "platform": "Twitter",
        "author": "@elon_tesla_giveaway",
        "published_at": "2026-10-06T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "ADVERSARIAL",
        "source_tier": "TIER_4_COMMUNITY",
        "independence_group": "grp_crypto_scam",
        "is_primary": False,
        "content_depth": "FULL_ARTICLE",
        "query_id": "q_07",
        "query_class": "threat_executive_scam",
        "query_text": "Tesla crypto scam",
    }
    return {
        "nike_normal": [nike_primary, nike_partner],
        "apple_threats": [apple_counterfeit, apple_phishing],
        "brand_empty": [],
        "sony_syndicated": [sony_wire1, sony_wire2],
        "tesla_scam": [tesla_exec_scam],
    }


def _build_trending_fixtures():
    op1 = {
        "id": "tr_01",
        "url": "https://openai.com/index/gpt-5-preview",
        "title": "OpenAI announces GPT-5 Developer Preview and reasoning benchmarks",
        "content": "OpenAI published benchmarks for GPT-5 showing major reasoning accuracy improvements.",
        "platform": "web",
        "source": "OpenAI",
        "published_at": "2026-10-07T12:00:00Z",
        "source_role": "PRIMARY_SOURCE",
        "is_syndicated": False,
    }
    op2 = {
        "id": "tr_02",
        "url": "https://techcrunch.com/openai-gpt-5-launch",
        "title": "TechCrunch reviews OpenAI GPT-5 Developer Preview",
        "content": "OpenAI has officially unveiled the developer preview of GPT-5 with multimodal capability.",
        "platform": "news",
        "source": "TechCrunch",
        "published_at": "2026-10-07T13:00:00Z",
        "source_role": "CORROBORATING_REPORT",
        "is_syndicated": False,
    }
    d1 = {
        "id": "tr_03",
        "url": "https://wired.com/ai-power-datacenters",
        "title": "AI Datacenters demand unprecedented nuclear energy capacity",
        "content": "Big tech firms sign long-term nuclear power contracts to fuel expanding AI computing clusters.",
        "platform": "news",
        "source": "Wired",
        "published_at": "2026-10-08T10:00:00Z",
        "source_role": "PRIMARY_SOURCE",
        "is_syndicated": False,
    }
    d2 = {
        "id": "tr_04",
        "url": "https://nature.com/quantum-compute-milestone",
        "title": "Physicists achieve fault-tolerant logical qubit error suppression",
        "content": "Researchers at major labs demonstrate quantum error correction thresholds exceeded.",
        "platform": "web",
        "source": "Nature",
        "published_at": "2026-10-08T11:00:00Z",
        "source_role": "PRIMARY_SOURCE",
        "is_syndicated": False,
    }
    s1 = {
        "id": "tr_05",
        "url": "https://reuters.com/spacex-starship-flight",
        "title": "SpaceX launches Starship orbital test flight successfully",
        "content": "SpaceX conducted its latest Starship test flight from Starbase Texas with full stage recovery.",
        "platform": "news",
        "source": "Reuters",
        "published_at": "2026-10-09T08:00:00Z",
        "source_role": "PRIMARY_SOURCE",
        "is_syndicated": False,
    }
    s2 = {
        "id": "tr_06",
        "url": "https://apnews.com/spacex-starship-flight",
        "title": "SpaceX launches Starship orbital test flight successfully",
        "content": "SpaceX conducted its latest Starship test flight from Starbase Texas with full stage recovery.",
        "platform": "news",
        "source": "Associated Press",
        "published_at": "2026-10-09T08:02:00Z",
        "source_role": "CORROBORATING_REPORT",
        "is_syndicated": True,
    }
    c1 = {
        "id": "tr_07",
        "url": "https://rottentomatoes.com/avatar3-review",
        "title": "Avatar 3 early reviews call runtime bloated and dialogue weak",
        "content": "Critics expressed disappointment with the screenplay of Avatar 3 despite stunning ocean visuals.",
        "platform": "web",
        "source": "Rotten Tomatoes",
        "published_at": "2026-10-09T14:00:00Z",
        "source_role": "OPINION",
        "is_syndicated": False,
    }
    return {
        "openai_entity": [op1, op2],
        "discovery_mode": [d1, d2],
        "empty": [],
        "spacex_syndicated": [s1, s2],
        "avatar_criticism": [c1],
    }


def _build_scout_fixtures():
    sec_frag = EvidenceFragment(
        evidence_id="ev_sc_01",
        platform="web",
        url="https://sec.gov/edgar/nvda/10q",
        title="NVIDIA Corp 10-Q Quarterly Filing",
        content="NVIDIA reported quarterly revenue of $35.1B, up 94% year-over-year, and raised annual capex guidance to $120B.",
        snippet="Quarterly revenue of $35.1B and raised capex guidance.",
        author="U.S. SEC",
        published="2026-10-07T10:00:00Z",
        retrieved_at=STAMP,
    )
    press_frag = EvidenceFragment(
        evidence_id="ev_sc_02",
        platform="news",
        url="https://reuters.com/nvidia-earnings-guidance",
        title="NVIDIA projects annual capex expansion to $120B",
        content="Reuters: NVIDIA executives guided annual capital expenditures to $120B amid datacenter demand.",
        snippet="NVIDIA executives guided capex to $120B.",
        author="Reuters",
        published="2026-10-07T11:00:00Z",
        retrieved_at=STAMP,
    )
    deal_2b_frag = EvidenceFragment(
        evidence_id="ev_sc_03",
        platform="news",
        url="https://bloomberg.com/tech-merger-deal-2b",
        title="Acme Tech signs acquisition agreement valued at $2.0B",
        content="Acme Tech announced a definitive merger agreement valued at $2.0B in all-cash consideration.",
        snippet="Acme Tech merger valued at $2.0B.",
        author="Bloomberg",
        published="2026-10-08T12:00:00Z",
        retrieved_at=STAMP,
    )
    deal_3b_frag = EvidenceFragment(
        evidence_id="ev_sc_04",
        platform="news",
        url="https://wsj.com/tech-merger-deal-3b",
        title="Competing regulatory disclosure cites Acme Tech deal at $3.5B",
        content="Contradicting initial reports, regulatory filings list the total Acme Tech transaction value at $3.5B including debt.",
        snippet="Regulatory filings cite transaction value at $3.5B.",
        author="Wall Street Journal",
        published="2026-10-08T13:00:00Z",
        retrieved_at=STAMP,
    )
    rumor_frag = EvidenceFragment(
        evidence_id="ev_sc_05",
        platform="reddit",
        url="https://reddit.com/r/investing/comments/abc123/reliance_reg_rumor",
        title="Unconfirmed rumor: Regulatory inquiry into Reliance retail expansion",
        content="Rumors circulating on forums claim antitrust regulators are looking into Reliance Retail pricing.",
        snippet="Unconfirmed rumors on retail pricing probe.",
        author="reddit_user",
        published="2026-10-09T09:00:00Z",
        retrieved_at=STAMP,
    )
    official_bse_frag = EvidenceFragment(
        evidence_id="ev_sc_06",
        platform="web",
        url="https://bseindia.com/corporates/reliance-disclosure",
        title="Reliance Industries BSE Clarification on Media Speculation",
        content="Reliance clarifies that no regulatory notices have been received and operations comply with all laws.",
        snippet="Official clarification denying regulatory notice.",
        author="BSE India",
        published="2026-10-09T10:00:00Z",
        retrieved_at=STAMP,
    )
    return {
        "nvda_normal": [sec_frag, press_frag],
        "contradictory_deals": [deal_2b_frag, deal_3b_frag],
        "empty": [],
        "syndicated_earnings": [sec_frag, press_frag],
        "rumor_vs_official": [rumor_frag, official_bse_frag],
    }


def _build_personal_fixtures():
    satya_li = {
        "evidence_id": "ev_pa_01",
        "title": "Satya Nadella on AI infrastructure and cloud growth",
        "content": "Satya Nadella shared thoughts on Azure AI scaling and responsible deployment principles.",
        "snippet": "Satya Nadella on Azure AI scaling.",
        "url": "https://linkedin.com/in/satyanadella/posts/123",
        "platform": "LinkedIn",
        "source": "LinkedIn Official",
        "author": "Satya Nadella",
        "published_at": "2026-10-05T10:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "PRIMARY",
        "source_tier": "TIER_1_OFFICIAL",
        "is_primary": True,
    }
    satya_news = {
        "evidence_id": "ev_pa_02",
        "title": "Microsoft CEO Satya Nadella delivers keynote at Ignite",
        "content": "Satya Nadella opened Microsoft Ignite highlighting enterprise Copilot adoption.",
        "snippet": "Satya Nadella delivers keynote.",
        "url": "https://news.microsoft.com/ignite-keynote-nadella",
        "platform": "News",
        "source": "Microsoft News",
        "author": "Microsoft Press",
        "published_at": "2026-10-05T11:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "INDEPENDENT_CONFIRMATION",
        "source_tier": "TIER_1_OFFICIAL",
        "is_primary": False,
    }
    jensen_impersonation = {
        "evidence_id": "ev_pa_03",
        "title": "Jensen Huang AI Giveaway — Free RTX 5090 and Sol tokens",
        "content": "Impersonating NVIDIA CEO Jensen Huang asking users to connect crypto wallets.",
        "snippet": "Fake account impersonating Jensen Huang.",
        "url": "https://x.com/jensen_nvidia_real_ceo/status/9876",
        "platform": "Twitter",
        "source": "Twitter/X Impersonator",
        "author": "@jensen_nvidia_real_ceo",
        "published_at": "2026-10-06T12:00:00Z",
        "retrieved_at": STAMP,
        "source_role": "ADVERSARIAL",
        "source_tier": "TIER_4_COMMUNITY",
        "is_primary": False,
    }
    return {
        "satya_normal": [satya_li, satya_news],
        "jensen_impersonation": [jensen_impersonation],
        "empty": [],
        "delta_scan_1": [satya_li],
        "delta_scan_2": [satya_li, jensen_impersonation],
    }


@pytest.fixture(scope="module")
def golden_data():
    with open(GOLDEN_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("scenario_name", [
    "nike_normal", "apple_threats", "brand_empty", "sony_syndicated", "tesla_scam"
])
def test_brandshield_golden_master_parity(scenario_name, golden_data):
    agent = BrandShieldAgent()
    scenarios = _build_brand_fixtures()
    evidence = scenarios[scenario_name]
    expected = golden_data["brandshield"][scenario_name]

    with patch.object(
        agent,
        "search_brand_evidence",
        return_value=(evidence, {"web": "healthy (1)"}, {"trace": {"query_count": len(evidence)}}, 0)
    ):
        target = "Nike" if "nike" in scenario_name else ("Apple" if "apple" in scenario_name else ("Tesla" if "tesla" in scenario_name else "Sony"))
        res = agent.scan(target)

        actual = {
            "brand": res.get("brand"),
            "total_findings": res.get("total_findings"),
            "threat_count": res.get("threat_count"),
            "safe_count": res.get("safe_count"),
            "threat_types": [t.get("threat_type") for t in res.get("threats", [])],
            "threat_severities": [t.get("severity") for t in res.get("threats", [])],
            "claims_count": len(res.get("claims", [])),
            "narratives_count": len(res.get("narratives", [])),
            "dossiers_count": len(res.get("dossiers", [])),
            "counterfeits_count": len(res.get("counterfeits", [])),
            "impersonations_count": len(res.get("impersonations", [])),
            "has_limitations": bool(res.get("limitations")),
        }
        assert actual == expected


@pytest.mark.parametrize("scenario_name", [
    "openai_entity", "discovery_mode", "empty", "spacex_syndicated", "avatar_criticism"
])
def test_trending_golden_master_parity(scenario_name, golden_data):
    agent = TrendingAgent()
    scenarios = _build_trending_fixtures()
    items = scenarios[scenario_name]
    expected = golden_data["trending"][scenario_name]

    evidence_objs = [
        TrendEvidence(
            evidence_id=f"EV-TR-{idx+1:03d}",
            platform=it["platform"],
            source=it["source"],
            title=it["title"],
            content=it["content"],
            snippet=it["content"][:200],
            url=it["url"],
            canonical_url=it["url"],
            author=it["source"],
            published_at=it["published_at"],
            retrieved_at="2026-10-10T00:00:00Z",
            source_role=it["source_role"],
            source_tier="TIER_1" if it["source_role"] == "PRIMARY_SOURCE" else "TIER_2",
            source_group_id="G-WIRE" if it.get("is_syndicated") else f"G-{idx}",
            retrieval_method="agent_reach",
        )
        for idx, it in enumerate(items)
    ]

    trends = agent._cluster_trends(evidence_objs, {"resolved_entity": "TrendTarget", "category": "general"})
    actual = {
        "trends_count": len(trends),
        "topics": [t.topic for t in trends],
        "sentiments": [t.sentiment for t in trends],
        "misinfo_risks": [t.misinformation_risk for t in trends],
        "debunk_statuses": [t.debunk_status for t in trends],
        "signal_counts": [t.signal_count for t in trends],
        "evidence_counts": [len(t.evidence_ids) for t in trends],
    }
    assert actual == expected


@pytest.mark.parametrize("scenario_name", [
    "nvda_normal", "contradictory_deals", "empty", "syndicated_earnings", "rumor_vs_official"
])
def test_scout_golden_master_parity(scenario_name, golden_data):
    scenarios = _build_scout_fixtures()
    frags = scenarios[scenario_name]
    expected = golden_data["scout"][scenario_name]

    with patch("backend.services.agent_reach.scout.engine.agent_reach_service.execute", return_value=frags):
        req = ScoutSourceRequest(
            query="NVDA intelligence" if "nvda" in scenario_name else "Market query",
            target_entity="NVIDIA" if "nvda" in scenario_name else "Acme",
            tickers=["NVDA"] if "nvda" in scenario_name else ["ACME"],
            max_candidates=5
        )
        res = scout_source_engine.execute(req)
        actual = {
            "entity": res.entity,
            "evidence_count": len(res.evidence_items),
            "financial_facts_count": len(res.financial_facts),
            "fact_values": [f.raw_value for f in res.financial_facts],
            "fact_metrics": [f.metric for f in res.financial_facts],
            "contradictions_count": len(res.contradictions),
            "has_contradictions": len(res.contradictions) > 0,
            "epistemic_status": res.epistemic_status.value if hasattr(res.epistemic_status, "value") else str(res.epistemic_status),
            "story_clusters_count": len(res.clusters),
            "cluster_epistemic_statuses": [c.epistemic_status.value if hasattr(c.epistemic_status, "value") else str(c.epistemic_status) for c in res.clusters],
        }
        assert actual == expected


@pytest.mark.parametrize("scenario_name", [
    "satya_normal", "jensen_impersonation", "empty", "delta_scan_1", "delta_scan_2"
])
def test_personal_watch_golden_master_parity(scenario_name, golden_data):
    agent = PersonalWatchAgent()
    scenarios = _build_personal_fixtures()
    items = scenarios[scenario_name]
    expected = golden_data["personal_watch"][scenario_name]

    with patch.object(
        agent,
        "search_personal_evidence",
        return_value=(items, {"web": "healthy"}, {"trace": {}}, 0)
    ):
        target = "Satya Nadella" if "satya" in scenario_name else ("Jensen Huang" if "jensen" in scenario_name else "Target VIP")
        res = agent.scan(target)

        actual = {
            "vip_name": res.get("vip_name") or res.get("subject"),
            "total_mentions": res.get("total_mentions"),
            "threats_count": len(res.get("threats", [])),
            "high_risk_count": res.get("high_risk_count"),
            "medium_risk_count": res.get("medium_risk_count"),
            "low_risk_count": res.get("low_risk_count"),
            "threat_types": [t.get("threat_type") for t in res.get("threats", [])],
            "alerts_sent": res.get("alerts_sent"),
            "has_privacy_guard": "privacy_guard" in res or "disclaimer" in res or "limitations" in res,
        }
        assert actual == expected
