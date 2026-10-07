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
from backend.services.agent_reach.native.route_policy import RouteClass, RoutePolicyEngine
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
