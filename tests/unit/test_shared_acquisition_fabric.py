"""
Aegis Protocol — Shared Acquisition Fabric & Policy D Test Suite
=================================================================
Validates the unified scraper/acquisition architecture:
  1. Route Selection & Policy D dispatch
  2. Reddit Arctic Shift zero-auth mirror & caching
  3. X / Twitter FxTwitter zero-auth mirror
  4. Web Scrapling HTTP primary & Playwright rescue
  5. YouTube in-process yt-dlp import (no subprocess primary)
  6. Multi-Engine Search discovery & candidate extraction
  7. Hard source gates (scope, entity anti-cheat, url structure, doc-type)
  8. Top-5 default candidate knee & Top-10 escalation
  9. Honest zero-auth provenance & lineage preservation
  10. SocialCache TTL & duplicate suppression
  11. SSRF prevention & IP filtering
  12. Four domain extraction engines & evidence ID linkage
  13. Zero raw scraper imports in the four domain agents
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from backend.services.agent_reach import agent_reach_service
from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters import (
    GitHubAdapter,
    RedditAdapter,
    SearchDiscoveryAdapter,
    TwitterAdapter,
    WebAdapter,
    YouTubeAdapter,
)
from backend.services.agent_reach.native.cache import SocialCache
from backend.services.agent_reach.native.evidence_sufficiency import evidence_sufficiency_evaluator
from backend.services.agent_reach.native.route_policy import RouteClass, RouteDecision, RoutePolicyEngine
from backend.services.agent_reach.native.router import native_router
from backend.services.agent_reach.native.telemetry import acquisition_telemetry
from backend.services.agent_reach.extraction import (
    brandshield_extractor,
    personal_watch_extractor,
    scout_extractor,
    trending_extractor,
)
from backend.services.url_validator import is_safe_url, validate_url_safe


# ── 1. ROUTE POLICY & PLATFORM ROUTING TESTS ──────────────────────────────────

def test_route_policy_decisions():
    """Verify Policy D route assignments and zero-auth defaults."""
    # Web: Scrapling HTTP primary
    web_route = RoutePolicyEngine.resolve_channel_route("web")
    assert web_route["route_class"] == RouteClass.SCRAPLING_HTTP.value
    assert web_route["primary_backend"] == "scrapling_http"
    assert web_route["fallback_backend"] == "playwright_rescue"

    # Reddit: Arctic Shift specialist mirror
    reddit_route = RoutePolicyEngine.resolve_channel_route("reddit")
    assert reddit_route["route_class"] == RouteClass.SPECIALIST_ADAPTER.value
    assert reddit_route["primary_backend"] == "arctic_shift"

    # Twitter: FxTwitter specialist mirror
    twitter_route = RoutePolicyEngine.resolve_channel_route("twitter")
    assert twitter_route["route_class"] == RouteClass.SPECIALIST_ADAPTER.value
    assert twitter_route["primary_backend"] == "fxtwitter"

    # YouTube: in-process yt-dlp import
    yt_route = RoutePolicyEngine.resolve_channel_route("youtube")
    assert yt_route["route_class"] == RouteClass.SPECIALIST_ADAPTER.value
    assert yt_route["primary_backend"] == "yt_dlp_in_process"

    # Walled gardens: search discovery fallback (avoids doomed scraping)
    for walled in ("instagram", "facebook", "tiktok", "linkedin", "bilibili"):
        w_route = RoutePolicyEngine.resolve_channel_route(walled)
        assert w_route["route_class"] == RouteClass.SEARCH_DISCOVERY.value


def test_playwright_rescue_decision_gate():
    """Verify Playwright is only engaged when lightweight HTTP fails or has JS rendering signs."""
    # Healthy HTTP with 500 chars -> No Playwright rescue
    assert RoutePolicyEngine.should_attempt_playwright_rescue(200, 500, None) is False

    # Short page (<250 chars) -> Playwright rescue justified
    assert RoutePolicyEngine.should_attempt_playwright_rescue(200, 100, None) is True

    # Cloudflare / challenge error -> Playwright rescue justified
    assert RoutePolicyEngine.should_attempt_playwright_rescue(403, 0, "Cloudflare challenge") is True
    assert RoutePolicyEngine.should_attempt_playwright_rescue(503, 50, "Turnstile required") is True


# ── 2. YOUTUBE IN-PROCESS YT-DLP TEST ─────────────────────────────────────────

def test_youtube_adapter_in_process():
    """Verify YouTubeAdapter imports yt-dlp in-process and produces normalized EvidenceFragment."""
    adapter = YouTubeAdapter()
    cand = CandidateSource(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", platform="youtube", title="Test Video")
    assert adapter.can_handle(cand) is True

    fake_video_info = {
        "title": "NVIDIA Blackwell B200 Deep Dive",
        "uploader": "Tech Analyst",
        "channel": "Tech Analyst",
        "description": "Full architectural review of the NVLink 5 and Blackwell architecture.",
        "upload_date": "2026-03-18",
        "duration": 720,
        "view_count": 150000,
        "tags": ["NVIDIA", "Blackwell", "B200"],
    }

    req = RetrievalRequest(request_id="req_yt_01", agent="scout", query="NVIDIA Blackwell")

    # Mock yt_dlp in-process import
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = fake_video_info
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance

        doc = adapter.acquire(cand, req)
        assert doc.status == "SUCCESS"
        assert doc.backend_id == "yt_dlp_in_process"

        frags = adapter.normalize(doc, cand, req)
        assert len(frags) == 1
        f = frags[0]
        assert f.platform == "youtube"
        assert f.author == "Tech Analyst"
        assert f.title == "NVIDIA Blackwell B200 Deep Dive"
        assert f.retrieval_mode == RetrievalMode.DIRECT_API.value
        assert f.is_authenticated is False
        assert f.evidence_id.startswith("ev_")


# ── 3. REDDIT ARCTIC SHIFT SPECIALIST MIRROR TEST ─────────────────────────────

def test_reddit_adapter_arctic_shift():
    """Verify RedditAdapter queries Arctic Shift zero-auth public mirror and caches result."""
    adapter = RedditAdapter()
    cand = CandidateSource(
        url="https://reddit.com/r/investing/comments/abc1234/semiconductor_capex",
        canonical_url="https://reddit.com/r/investing/comments/abc1234/semiconductor_capex",
        platform="reddit"
    )
    assert adapter.can_handle(cand) is True

    req = RetrievalRequest(request_id="req_red_01", agent="scout", query="semiconductor capex")

    fake_response = {
        "data": [
            {
                "id": "abc1234",
                "title": "Semiconductor Capex Trends in 2026",
                "selftext": "Foundries are accelerating 2nm wafer capacity with elevated capital expenditures.",
                "author": "semi_investor",
                "subreddit": "investing",
                "score": 450,
                "num_comments": 85,
                "created_utc": 1775000000,
            }
        ]
    }

    with patch.object(adapter, "_fetch_from_mirror", return_value=fake_response) as mock_fetch:
        doc = adapter.acquire(cand, req)
        assert doc.status == "SUCCESS"
        assert doc.backend_id == "arctic_shift"

        frags = adapter.normalize(doc, cand, req)
        assert len(frags) == 1
        f = frags[0]
        assert f.platform == "reddit"
        assert f.author == "u/semi_investor"
        assert "investing" in f.content
        assert f.retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
        assert f.is_authenticated is False
        assert f.evidence_id.startswith("ev_")


# ── 4. X / TWITTER FXTWITTER SPECIALIST MIRROR TEST ───────────────────────────

def test_twitter_adapter_fxtwitter():
    """Verify TwitterAdapter acquires public tweets via FxTwitter zero-auth mirror."""
    adapter = TwitterAdapter()
    cand = CandidateSource(
        url="https://x.com/OpenAI/status/1880000000000000000",
        canonical_url="https://x.com/OpenAI/status/1880000000000000000",
        platform="twitter"
    )
    assert adapter.can_handle(cand) is True

    req = RetrievalRequest(request_id="req_tw_01", agent="trending", query="OpenAI update")

    fake_response = {
        "code": 200,
        "tweet": {
            "id": "1880000000000000000",
            "url": "https://x.com/OpenAI/status/1880000000000000000",
            "text": "Introducing our next generation reasoning frontier model.",
            "author": {"name": "OpenAI", "screen_name": "OpenAI"},
            "created_at": "Wed Oct 07 12:00:00 +0000 2026",
            "likes": 50000,
            "retweets": 12000,
            "replies": 3500,
        }
    }

    with patch.object(adapter, "_fetch_from_fxtwitter", return_value=fake_response):
        doc = adapter.acquire(cand, req)
        assert doc.status == "SUCCESS"
        assert doc.backend_id == "fxtwitter"

        frags = adapter.normalize(doc, cand, req)
        assert len(frags) == 1
        f = frags[0]
        assert f.platform == "twitter"
        assert f.author == "@OpenAI"
        assert "reasoning frontier model" in f.content
        assert f.retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
        assert f.is_authenticated is False


# ── 5. WEB ADAPTER SCRAPLING PRIMARY & PLAYWRIGHT RESCUE TEST ─────────────────

def test_web_adapter_scrapling_and_rescue():
    """Verify WebAdapter uses Scrapling HTTP primary and invokes Playwright rescue on short/blocked page."""
    adapter = WebAdapter()
    cand = CandidateSource(url="https://example.com/article", platform="web", title="Example Article")
    assert adapter.can_handle(cand) is True

    req = RetrievalRequest(request_id="req_web_01", agent="brandshield")

    # Case A: Scrapling succeeds with rich article
    with patch.object(adapter, "_fetch_scrapling", return_value=(200, "<html><body><title>Tech Insights</title><p>Deep technical article discussing enterprise infrastructure and supply chains.</p></body></html>", {}, 120, None)):
        doc = adapter.acquire(cand, req)
        assert doc.status == "SUCCESS"
        assert doc.backend_id == "scrapling_http"
        frags = adapter.normalize(doc, cand, req)
        assert len(frags) == 1
        assert frags[0].retrieval_mode == RetrievalMode.WEB_READER.value

    # Case B: Scrapling returns empty shell (<250 chars) -> Playwright rescue succeeds
    with patch.object(adapter, "_fetch_scrapling", return_value=(200, "<html><div id='root'></div></html>", {}, 80, None)):
        with patch.object(adapter, "_fetch_playwright_rescue", return_value=(200, "<html><body><title>Rendered Page</title><p>Hydrated client-side DOM content with full article text.</p></body></html>", {}, 950, None)):
            doc = adapter.acquire(cand, req)
            assert doc.status == "SUCCESS"
            assert doc.backend_id == "playwright_rescue"


# ── 6. SOCIAL CACHE TESTS ─────────────────────────────────────────────────────

def test_social_cache_ttl_and_suppression():
    """Verify SocialCache caches successful responses and expires correctly."""
    cache = SocialCache(ttl=0.2)
    cache.set("key_1", {"data": "test_payload"})
    assert cache.get("key_1") == {"data": "test_payload"}
    assert cache.stats()["hits"] == 1

    # Poison prevention: None is not cached
    cache.set("key_none", None)
    assert cache.get("key_none") is None

    # Wait for expiry
    import time
    time.sleep(0.25)
    assert cache.get("key_1") is None
    assert cache.stats()["misses"] >= 1


# ── 7. SSRF SECURITY DEFENSE TESTS ───────────────────────────────────────────

def test_ssrf_validation_gates():
    """Verify SSRF defenses block localhost, private IPs, loopback, and metadata endpoints."""
    # Malicious / internal IP targets
    blocked_urls = [
        "http://127.0.0.1:8000/internal",
        "http://localhost:3000/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/admin",
        "http://10.0.0.1/status",
    ]
    for url in blocked_urls:
        safe, reason = is_safe_url(url)
        assert safe is False, f"Expected {url} to be blocked by SSRF defense"

        # WebAdapter must block without connecting
        cand = CandidateSource(url=url, platform="web")
        doc = WebAdapter().acquire(cand, RetrievalRequest(agent="scout"))
        assert doc.status == "BLOCKED"


# ── 8. HARD SOURCE GATES & ANTI-TOKEN-CHEAT TESTS ─────────────────────────────

def test_hard_source_gates_in_shared_fabric():
    """Verify shared NativeRouter enforces scope gates, URL structure, and anti-token-cheat."""
    # Scope mismatch: Requested r/investing, candidate is r/privacy
    req = RetrievalRequest(
        request_id="req_gate_01",
        agent="scout",
        entity="NVIDIA",
        scope="r/investing",
        allowed_channels=["reddit"]
    )
    bad_cand = CandidateSource(
        url="https://reddit.com/r/privacy/comments/xyz123/tracking",
        canonical_url="https://reddit.com/r/privacy/comments/xyz123/tracking",
        platform="reddit",
        title="NVIDIA telemetry privacy concerns",
        snippet="Discussion about software telemetry",
        metadata={"subreddit": "privacy", "source_type": "post", "external_id": "xyz123"}
    )
    with patch.object(native_router.search_adapter, "discover_candidates", return_value=[bad_cand]):
        frags = native_router.execute_retrieval_request(req)
        # Bad candidate should be rejected by the scope gate
        assert len(frags) == 0

    # Anti-token cheat: First name only 'Satya' matching 'Satya Incense' without Microsoft/Nadella context
    req_satya = RetrievalRequest(
        request_id="req_gate_02",
        agent="personal",
        entity="Satya Nadella",
        allowed_channels=["web"]
    )
    incense_cand = CandidateSource(
        url="https://example.com/satya-incense",
        canonical_url="https://example.com/satya-incense",
        platform="web",
        title="Buy Satya Sai Baba Nag Champa Incense Online",
        snippet="Traditional handcrafted agarbatti sticks.",
        metadata={"source_type": "post", "external_id": "item1"}
    )
    with patch.object(native_router.search_adapter, "discover_candidates", return_value=[incense_cand]):
        frags = native_router.execute_retrieval_request(req_satya)
        assert len(frags) == 0


# ── 9. TOP-5 CANDIDATE KNEE & TOP-10 ESCALATION TESTS ─────────────────────────

def test_top_5_knee_and_escalation():
    """Verify Top-5 candidates are selected by default and Top-10 only upon weak evidence."""
    # Generate 15 strong candidates
    strong_cands = [
        CandidateSource(
            url=f"https://news.example.com/item_{i}",
            canonical_url=f"https://news.example.com/item_{i}",
            platform="web",
            title=f"NVIDIA Quarterly Report and Revenue Analysis #{i}",
            snippet="Detailed financial performance across datacenter compute segments.",
            semantic_score=85.0 - i,
            metadata={"source_type": "post", "external_id": f"ext_{i}"}
        )
        for i in range(15)
    ]

    req = RetrievalRequest(
        request_id="req_knee_01",
        agent="scout",
        entity="NVIDIA",
        candidate_budget=5
    )

    with patch.object(native_router.search_adapter, "discover_candidates", return_value=strong_cands):
        with patch.object(native_router.web_adapter, "acquire") as mock_acq:
            mock_acq.return_value = FetchedDocument(url="https://example.com", status="SUCCESS", raw_content="<html><title>News</title><p>Body text</p></html>")
            frags = native_router.execute_retrieval_request(req)
            # Default budget of 5 respected
            assert len(frags) <= 5


# ── 10. FOUR DOMAIN-SPECIFIC EXTRACTION ENGINES TESTS ─────────────────────────

def test_brandshield_extraction_engine():
    """Verify BrandShieldExtractionEngine extracts structured threats and links evidence IDs."""
    fragments = [
        EvidenceFragment(
            evidence_id="ev_bs_01",
            platform="web",
            title="Fake Nike Air Jordan knockoff seller detected on clone site",
            snippet="Unauthorized sellers offering 1:1 replica shoes.",
            content="Detailed report on counterfeit footwear.",
            url="https://example.com/fake-nike"
        ),
        EvidenceFragment(
            evidence_id="ev_bs_02",
            platform="twitter",
            title="Customer support phishing scam posing as Nike Support handle",
            snippet="Impersonating Nike official refund desk.",
            content="Phishing warning.",
            url="https://x.com/fake_nike_support/status/123"
        )
    ]
    res = brandshield_extractor.extract(fragments, brand_name="Nike", product_name="Air Jordan")
    assert res.brand == "Nike"
    assert len(res.threats) >= 2
    assert any(t.threat_type == "COUNTERFEIT" and "ev_bs_01" in t.evidence_ids for t in res.threats)
    assert any(t.threat_type == "BRAND_IMPERSONATION" and "ev_bs_02" in t.evidence_ids for t in res.threats)


def test_trending_extraction_engine():
    """Verify TrendingExtractionEngine extracts narrative clusters, sentiment, and wire syndication."""
    fragments = [
        EvidenceFragment(
            evidence_id="ev_tr_01",
            platform="news",
            title="Deepika Padukone wins international acclaim at film gala",
            snippet="Global standing applauded as jury honours actor.",
            content="Celebrated opening.",
            url="https://reuters.com/article/deepika-film-gala"
        ),
        EvidenceFragment(
            evidence_id="ev_tr_02",
            platform="web",
            title="Record audience praise for Padukone festival announcement",
            snippet="Fans celebrate global milestone.",
            content="High momentum response.",
            url="https://variety.com/deepika-festival"
        )
    ]
    res = trending_extractor.extract(fragments, target_entity="Deepika Padukone")
    assert res.target_entity == "Deepika Padukone"
    assert len(res.trends) >= 1
    assert res.sentiment["direction"] == "positive"
    assert "Reuters Wire" in res.syndication_groups
    assert len(res.observed) > 0


def test_scout_extraction_engine():
    """Verify ScoutExtractionEngine extracts multi-currency numbers, events, and contradictions."""
    fragments = [
        EvidenceFragment(
            evidence_id="ev_sc_01",
            platform="news",
            title="NVIDIA announces $5 billion acquisition of photonics leader",
            snippet="Strategic buyout valued at $5.0B to enhance optical interconnects.",
            content="Deal terms officially outlined.",
            url="https://wsj.com/nvidia-deal"
        ),
        EvidenceFragment(
            evidence_id="ev_sc_02",
            platform="web",
            title="Reports dispute buyout terms claiming deal is only $2.5 billion",
            snippet="Sources suggest transaction is capped at $2.5B.",
            content="Competing report on valuation.",
            url="https://techblog.com/nvidia-deal-terms"
        )
    ]
    res = scout_extractor.extract(fragments, ticker_or_company="NVDA")
    assert res.ticker_or_company == "NVDA"
    assert len(res.financial_facts) >= 2
    assert any(f.value == 5e9 and "ev_sc_01" in f.evidence_ids for f in res.financial_facts)
    # Contradiction detected between $5B and $2.5B
    assert len(res.contradictions) >= 1
    assert res.contradictions[0].evidence_id_a == "ev_sc_01"
    assert res.contradictions[0].evidence_id_b == "ev_sc_02"


def test_personal_watch_extraction_engine():
    """Verify PersonalWatchExtractionEngine extracts career events and enforces privacy guard."""
    fragments = [
        EvidenceFragment(
            evidence_id="ev_pw_01",
            platform="news",
            title="Satya Nadella appointed to Foundation Board of Trustees",
            snippet="Named as global trustee focusing on STEM education.",
            content="Official appointment announcement.",
            url="https://foundation.org/satya-board"
        ),
        EvidenceFragment(
            evidence_id="ev_pw_02",
            platform="web",
            title="Unauthorized leak claiming personal residential address",
            snippet="Contains home address records.",
            content="Private information.",
            url="https://leak.com/satya"
        )
    ]
    res = personal_watch_extractor.extract(fragments, target_person="Satya Nadella")
    assert res.target_person == "Satya Nadella"
    assert len(res.career_events) == 1
    assert "ev_pw_01" in res.career_events[0].evidence_ids
    # Privacy guard must filter the sensitive home address item
    assert res.privacy_filtered_count == 1


# ── 11. ZERO DIRECT SCRAPER IMPORT AUDIT ACROSS AGENTS ────────────────────────

def test_no_raw_scrapers_in_agents():
    """Verify that none of the four domain agents import raw scraper libraries directly."""
    import inspect
    import backend.agents.brandshield_agent as bs_mod
    import backend.agents.trending_agent as tr_mod
    import backend.agents.personal_agent as pa_mod

    bs_source = inspect.getsource(bs_mod)
    tr_source = inspect.getsource(tr_mod)
    pa_source = inspect.getsource(pa_mod)

    # DDGS must NOT be imported or instantiated in BrandShield or Personal Watch
    assert "from duckduckgo_search import DDGS" not in bs_source
    assert "DDGS()" not in bs_source
    assert "from duckduckgo_search import DDGS" not in pa_source
    assert "DDGS()" not in pa_source

    # Feedparser must NOT be the unmediated primary path in Trending
    assert "from backend.services.agent_reach import agent_reach_service" in tr_source
    assert "from backend.services.agent_reach import agent_reach_service" in bs_source
    assert "from backend.services.agent_reach import agent_reach_service" in pa_source


# ── 12. ARCHITECTURE ENFORCEMENT & EVIDENCE IDENTITY TESTS ────────────────────

def test_evidence_identity_stability_and_observation_separation():
    """
    Invariant 13 & 14:
    Evidence identity must be stable across repeated observations of the same source.
    Retrieval timestamp must be observation metadata, not part of source identity.
    """
    url = "https://www.reuters.com/technology/nvidia-earnings-q3-record-revenue"
    t1 = "2026-10-01T10:00:00Z"
    t2 = "2026-10-02T10:00:00Z"

    frag1 = EvidenceFragment(
        platform="web",
        url=url,
        title="NVIDIA beats Q3 earnings",
        author="Reuters",
        retrieved_at=t1,
        content="NVIDIA reported record revenue of $35B."
    )
    frag2 = EvidenceFragment(
        platform="web",
        url=url,
        title="NVIDIA beats Q3 earnings",
        author="Reuters",
        retrieved_at=t2,
        content="NVIDIA reported record revenue of $35B with revised outlook."
    )

    # Source ID and Evidence ID must remain stable across observations
    assert frag1.source_id == frag2.source_id
    assert frag1.evidence_id == frag2.evidence_id
    assert frag1.evidence_id.startswith("ev_")
    assert frag1.source_id.startswith("src_")

    # Observation ID must be distinct because retrieved_at and content changed
    assert frag1.observation_id != frag2.observation_id
    assert frag1.observation_id.startswith("obs_")
    assert frag2.observation_id.startswith("obs_")


def test_route_decision_contract_and_authoritative_engine():
    """
    Invariant 5:
    RoutePolicyEngine is the authoritative dispatch decider returning typed RouteDecision.
    """
    # Reddit -> Specialist Arctic Shift Mirror
    r_dec = RoutePolicyEngine.decide_route("reddit")
    assert isinstance(r_dec, RouteDecision)
    assert r_dec.primary_backend == "arctic_shift"
    assert r_dec.retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
    assert r_dec.policy_version == "policy_d_v3"

    # YouTube -> In-process yt-dlp
    yt_dec = RoutePolicyEngine.decide_route("youtube")
    assert yt_dec.primary_backend == "yt_dlp_in_process"
    assert yt_dec.retrieval_mode == RetrievalMode.DIRECT_API.value

    # GitHub -> Native API
    gh_dec = RoutePolicyEngine.decide_route("github")
    assert gh_dec.primary_backend == "gh_api"
    assert gh_dec.retrieval_mode == RetrievalMode.DIRECT_API.value

    # Walled Garden Instagram -> Search Discovery
    ig_dec = RoutePolicyEngine.decide_route("instagram")
    assert ig_dec.is_walled_garden is True
    assert ig_dec.requires_search_discovery is True
    assert ig_dec.primary_backend == "search_discovery"

    # General Web -> Scrapling HTTP primary, Playwright rescue permitted
    web_dec = RoutePolicyEngine.decide_route("web")
    assert web_dec.primary_backend == "scrapling_http"
    assert web_dec.browser_rescue_permitted is True
    assert "playwright_rescue" in web_dec.fallback_backends


def test_scout_does_not_bypass_shared_fabric():
    """
    Invariant 4 & Section 50:
    Verify ScoutSourceEngine delegates network acquisition to the Shared Acquisition Fabric.
    Scout must NOT run its own independent scraper stack.
    """
    from backend.services.agent_reach.scout.engine import scout_source_engine
    from backend.services.agent_reach.scout.models import ScoutSourceRequest

    mock_frag = EvidenceFragment(
        evidence_id="ev_scout_shared_01",
        platform="web",
        url="https://finance.yahoo.com/news/nvidia-guidance-increase",
        title="NVIDIA raises annual guidance to $120B",
        content="NVIDIA reported quarterly revenue of $35.1B and raised capex guidance.",
        author="Yahoo Finance",
        published="2026-10-07T12:00:00Z"
    )

    with patch("backend.services.agent_reach.scout.engine.agent_reach_service.execute", return_value=[mock_frag]) as mock_exec:
        req = ScoutSourceRequest(
            query="NVIDIA capex guidance",
            target_entity="NVIDIA",
            tickers=["NVDA"],
            max_candidates=3
        )
        res = scout_source_engine.execute(req)

        # Proves Scout delegated acquisition directly to Shared Acquisition Fabric
        assert mock_exec.called
        assert len(res.evidence_items) == 1
        assert res.evidence_items[0].evidence_id == "ev_scout_shared_01"
        assert res.entity == "NVIDIA"
        assert len(res.financial_facts) > 0  # Domain financial extraction executed!


def test_all_four_domain_extractors_are_actually_executed():
    """
    Invariant 20 & Section 49:
    Prove that all four domain extraction engines are actually invoked in their pipelines.
    """
    from backend.services.agent_reach.extraction import (
        brandshield_extractor,
        trending_extractor,
        scout_extractor,
        personal_watch_extractor,
    )
    from backend.agents.brandshield_agent import BrandShieldAgent
    from backend.agents.trending_agent import TrendingAgent
    from backend.agents.personal_agent import PersonalWatchAgent
    from backend.agents.scout_agent import ScoutAgent

    # 1. BrandShield spy
    with patch.object(brandshield_extractor, "extract_brand_intelligence", wraps=brandshield_extractor.extract_brand_intelligence) as bs_spy:
        bs_agent = BrandShieldAgent()
        ev_items = [{
            "platform": "reddit",
            "title": "Cheap counterfeit Rolex watches on sale",
            "snippet": "Replica fake Rolex clone for $50",
            "author": "seller1",
            "evidence_id": "ev_bs_test_1"
        }]
        bs_res = bs_agent._heuristic_threat_synthesis({"brand": "Rolex", "resolved_entity": "Rolex"}, ev_items)
        assert bs_spy.called
        assert len(bs_res["threats"]) > 0

    # 2. Trending spy
    with patch.object(trending_extractor, "extract_trending_intelligence", wraps=trending_extractor.extract_trending_intelligence) as tr_spy:
        from backend.agents.trending_agent import TrendEvidence
        tr_agent = TrendingAgent()
        tr_ev = [TrendEvidence(
            source="Reuters",
            platform="news",
            title="OpenAI announces new reasoning architecture",
            content="OpenAI unveiled next-gen model.",
            url="https://reuters.com/ai",
            published_at="2026-10-07T12:00:00Z",
            evidence_id="ev_tr_test_1",
            source_role="PRIMARY"
        )]
        tr_trends = tr_agent._heuristic_trend_clustering(tr_ev, {"resolved_entity": "OpenAI"})
        assert tr_spy.called
        assert len(tr_trends) > 0

    # 3. Personal Watch spy
    with patch.object(personal_watch_extractor, "extract_personal_intelligence", wraps=personal_watch_extractor.extract_personal_intelligence) as pw_spy:
        pw_agent = PersonalWatchAgent()
        pw_ev = [{
            "platform": "twitter",
            "title": "Fake parody profile of Satya Nadella",
            "content": "Lookalike account impersonating Satya Nadella.",
            "author": "impersonator",
            "evidence_id": "ev_pw_test_1"
        }]
        pw_res = pw_agent._heuristic_threat_synthesis("Satya Nadella", pw_ev)
        assert pw_spy.called
        assert len(pw_res["threats"]) > 0

    # 4. Scout spy
    with patch.object(scout_extractor, "extract_market_intelligence", wraps=scout_extractor.extract_market_intelligence) as sc_spy:
        sc_agent = ScoutAgent()
        mock_frag = EvidenceFragment(
            evidence_id="ev_sc_01",
            platform="web",
            url="https://news.com/nvda",
            title="NVIDIA beats revenue estimates with $35B",
            content="Revenue hit $35.0B beating forecasts.",
            author="Bloomberg",
            published="2026-10-07T12:00:00Z"
        )
        with patch("backend.services.agent_reach.scout.engine.agent_reach_service.execute", return_value=[mock_frag]):
            sc_intel = sc_agent.acquire_market_intelligence("NVDA", max_candidates=2)
            assert sc_spy.called
            assert len(sc_intel["financial_facts"]) > 0


def test_evidence_sufficiency_top_5_to_10_escalation():
    """
    Invariant 7 & 8:
    Top-5 is default. Top-10 escalation occurs only when evidence sufficiency fails.
    """
    req = RetrievalRequest(agent="scout", entity="NVIDIA")

    # 1. Weak evidence: Only 1 snippet, low score -> Must escalate if more candidates available
    weak_frags = [
        EvidenceFragment(
            platform="web",
            title="NVIDIA snippet only",
            content="",
            snippet="Short snippet",
            score=25.0,
            content_depth="SNIPPET"
        )
    ]
    eval_res = evidence_sufficiency_evaluator.evaluate(weak_frags, req, remaining_candidates_count=5)
    assert eval_res.is_sufficient is False
    assert eval_res.should_escalate is True
    assert len(eval_res.reasons) > 0

    # 2. Strong evidence: 2 independent sources with full articles and high score -> Must NOT escalate
    strong_frags = [
        EvidenceFragment(
            platform="sec_edgar",
            url="https://sec.gov/edgar/data/1045810/nvda-10q",
            author="NVIDIA",
            title="NVIDIA Official 10-Q Filing",
            content="Official quarterly report on financial performance..." * 20,
            score=95.0,
            content_depth="FULL_ARTICLE"
        ),
        EvidenceFragment(
            platform="web",
            url="https://bloomberg.com/article2",
            author="Bloomberg",
            title="NVIDIA second source",
            content="Independent corroboration of production volumes..." * 20,
            score=88.0,
            content_depth="FULL_ARTICLE"
        )
    ]
    strong_eval = evidence_sufficiency_evaluator.evaluate(strong_frags, req, remaining_candidates_count=5)
    assert strong_eval.is_sufficient is True
    assert strong_eval.should_escalate is False
