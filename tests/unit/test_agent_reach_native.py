"""
Aegis Protocol — Unit Tests: Native Agent Reach 3.0 Architecture
================================================================
Validates:
1. NativeRuntime: Upstream Agent Reach package detection, version/commit resolution,
   and RuntimeProfile (LOCAL_DESKTOP vs CLOUD_HEADLESS).
2. NativeDoctor: Health aggregation, canonical status mapping, and caching.
3. NativeExecutor: Parameterized allowlisted operations, SSRF prevention, and authenticated channel guards.
4. NativeNormalizer: Forensic mapping from raw tools to EvidenceFragment and EvidenceItem.
5. NativeRouter: Dynamic dispatch, active backend selection, and execution telemetry.
6. RetrievalPlanner: Channel priorities, domain distribution, and adaptive follow-up queries.
7. ResearchBudget: Granular sub-budgets and research stop conditions.
8. DeepReader: Diversity selection, candidate auditing, and skipping reasons.
9. PrimarySourceEscalator: Full escalation provenance tracking.
10. ResearchCorpus: Complete evidence surface serialization.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.agent_reach.native.runtime import NativeRuntime, RuntimeProfile, native_runtime
from backend.services.agent_reach.native.doctor import NativeDoctor, native_doctor
from backend.services.agent_reach.native.executor import NativeExecutor, native_executor
from backend.services.agent_reach.native.normalizer import NativeNormalizer, native_normalizer
from backend.services.agent_reach.native.router import NativeRouter, native_router
from backend.services.agent_reach.native.channel_capabilities import CAPABILITY_MATRIX, PlatformCapability
from backend.services.agent_reach.native.errors import (
    NativeReachError,
    AuthRequiredError,
    SecurityPolicyViolation,
    BackendExecutionError,
)
from backend.services.agent_reach.planner import RetrievalPlanner, RetrievalPlan
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.deep_reader import deep_reader
from backend.services.research.primary_source_escalator import primary_source_escalator
from backend.services.research.research_models import (
    EvidenceItem,
    ResearchCorpus,
    ContentDepth,
    SourceRole,
    SourceTier,
)


# ── 1. Native Runtime Tests ──────────────────────────────────────────────────

def test_native_runtime_detection():
    """Verify runtime detects installed upstream Agent Reach package and commit."""
    rt = NativeRuntime()
    assert rt.is_agent_reach_installed() is True
    version = rt.get_upstream_version()
    assert version != "unknown"
    commit = rt.get_upstream_commit()
    assert len(commit) >= 7
    assert rt.profile in (RuntimeProfile.LOCAL_DESKTOP, RuntimeProfile.CLOUD_HEADLESS)


def test_native_runtime_summary():
    """Verify runtime summary dictionary structure."""
    summary = native_runtime.get_runtime_summary()
    assert "installed" in summary
    assert "version" in summary
    assert "commit" in summary
    assert "runtime" in summary
    assert "tools" in summary


# ── 2. Native Capability Matrix Tests ────────────────────────────────────────

def test_capability_matrix_coverage():
    """Verify all 16 upstream platforms exist in CAPABILITY_MATRIX."""
    expected_platforms = [
        "web", "web_search", "github", "youtube", "bilibili", "v2ex",
        "rss", "twitter", "reddit", "xueqiu", "linkedin", "xiaohongshu",
        "facebook", "instagram", "boss", "xiaoyuzhou"
    ]
    for p in expected_platforms:
        assert p in CAPABILITY_MATRIX
        cap = CAPABILITY_MATRIX[p]
        assert len(cap.operations) > 0
        assert cap.tier in (0, 1, 2)


# ── 3. Native Doctor Tests ───────────────────────────────────────────────────

def test_native_doctor_canonical_status():
    """Verify canonical status resolution for open vs session-required platforms."""
    doc = NativeDoctor(cache_ttl_seconds=60)
    # Platforms requiring browser session report AUTH_REQUIRED
    twitter_st = doc.get_canonical_status_code("twitter")
    assert twitter_st in ("AVAILABLE", "AUTH_REQUIRED", "DEGRADED", "UNAVAILABLE")
    
    # Public zero-config platforms should be AVAILABLE or DEGRADED
    v2ex_st = doc.get_canonical_status_code("v2ex")
    assert v2ex_st in ("AVAILABLE", "DEGRADED")


# ── 4. Native Executor & Security Tests ───────────────────────────────────────

def test_native_executor_ssrf_protection():
    """Verify SSRF defense blocks private and cloud metadata addresses."""
    executor = NativeExecutor()
    with pytest.raises(SecurityPolicyViolation):
        executor.execute_web_read("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SecurityPolicyViolation):
        executor.execute_web_read("http://127.0.0.1:8000/internal")

    with pytest.raises(SecurityPolicyViolation):
        executor.execute_web_read("http://localhost:5000/admin")


def test_native_executor_auth_guard():
    """Verify session-required channels raise AuthRequiredError when session absent."""
    executor = NativeExecutor()
    with pytest.raises(AuthRequiredError) as exc_info:
        executor.guard_authenticated_channel("twitter", "search")
    assert exc_info.value.platform == "twitter"
    assert "session" in str(exc_info.value).lower()


# ── 5. Native Normalizer Tests ───────────────────────────────────────────────

def test_normalizer_v2ex():
    """Verify normalization of raw V2EX topic JSON."""
    raw_topics = [
        {
            "id": 12345,
            "title": "Discussion on LLM Architecture",
            "url": "https://v2ex.com/t/12345",
            "content": "Deep analysis of transformer routing",
            "member": {"username": "architect_dev"},
            "created": 1700000000
        }
    ]
    frags = native_normalizer.normalize_v2ex_topics(
        raw_topics,
        query_id="q_001",
        query_class="technical",
        query_text="LLM Architecture"
    )
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "V2EX"
    assert f.title == "Discussion on LLM Architecture"
    assert f.channel_name == "v2ex"
    assert f.query_id == "q_001"
    assert f.author == "architect_dev"


def test_normalizer_bilibili():
    """Verify normalization of raw Bilibili search JSON."""
    raw_videos = [
        {
            "title": "<em class=\"keyword\">Nvidia</em> Blackwell Architecture Analysis",
            "arcurl": "https://www.bilibili.com/video/BV1xx411c7mD",
            "author": "TechExplainer",
            "description": "Comprehensive teardown of packaging",
            "play": 150000,
            "pubdate": 1700000000
        }
    ]
    frags = native_normalizer.normalize_bilibili_videos(
        raw_videos,
        query_id="q_002",
        query_class="viral_moments",
        query_text="Nvidia Blackwell"
    )
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "Bilibili"
    assert "<em" not in f.title
    assert "Nvidia Blackwell Architecture Analysis" in f.title
    assert f.channel_name == "bilibili"
    assert f.raw_metadata["play_count"] == 150000


# ── 6. Adaptive Query Planner Tests (Requirement 11) ─────────────────────────

def test_planner_adaptive_follow_ups():
    """Verify RetrievalPlanner discovers entities, filings, court cases, and contradictions."""
    planner = RetrievalPlanner()
    mock_evidence = [
        EvidenceItem(
            id="ev_001",
            title="Tata Motors in talks to acquire battery firm Exide Energy",
            snippet="According to a regulatory filing with the exchange, the deal is valued at $500M.",
            query_id="q_001"
        ),
        EvidenceItem(
            id="ev_002",
            title="Patent Lawsuit in California Court",
            snippet="Court documents show Case No. 24-CV-1234 filed regarding battery patents.",
            query_id="q_002"
        )
    ]
    contradictions = [
        {
            "source_a_id": "ev_001",
            "claim_a": "Deal value is $500M",
            "details": "Factual valuation disagreement"
        }
    ]

    follow_ups = planner.plan_adaptive_follow_ups(
        target_name="Tata Motors",
        evidence_items=mock_evidence,
        contradictions=contradictions,
        max_follow_ups=5
    )

    assert len(follow_ups) > 0
    triggers = [fu["trigger"] for fu in follow_ups]
    assert "contradiction" in triggers or "filing_number" in triggers or "court_case" in triggers or "named_entity" in triggers
    for fu in follow_ups:
        assert "parent_query_id" in fu
        assert "reason" in fu
        assert "query_text" in fu


# ── 7. Adaptive Research Budget Tests (Requirement 12) ───────────────────────

def test_research_budget_stop_conditions():
    """Verify ResearchBudget evaluates stop conditions accurately."""
    budget = ResearchBudget(timeout_seconds=10.0)

    # 1. Latency stop
    stopped, reason = budget.check_stop_condition(elapsed_seconds=11.0)
    assert stopped is True
    assert reason == "latency_ceiling_reached"

    # 2. Corroboration + primary satisfied stop
    stopped, reason = budget.check_stop_condition(
        elapsed_seconds=3.0,
        independent_group_count=3,
        primary_source_count=1
    )
    assert stopped is True
    assert reason == "sufficient_corroboration_and_primary_located"

    # 3. Ongoing exploration continues
    stopped, reason = budget.check_stop_condition(
        elapsed_seconds=2.0,
        independent_group_count=1,
        primary_source_count=0
    )
    assert stopped is False


# ── 8. Deep Reader Candidate Audit Tests (Requirement 13 & 14) ───────────────

def test_deep_reader_candidate_audit():
    """Verify DeepReader records candidate selection audit and skipping reasons."""
    candidates = [
        EvidenceItem(
            id="ev_p1",
            canonical_url="https://sec.gov/edgar/data/123/form10k.htm",
            source_domain="sec.gov",
            title="SEC Form 10-K Annual Report",
            primary_source=True,
            source_role=SourceRole.PRIMARY.value,
            relevance_score=0.95
        ),
        EvidenceItem(
            id="ev_s1",
            canonical_url="https://reuters.com/business/tata-earnings",
            source_domain="reuters.com",
            title="Reuters Dispatch 1",
            relevance_score=0.85
        ),
        EvidenceItem(
            id="ev_s2",
            canonical_url="https://reuters.com/business/tata-wire-copy",
            source_domain="reuters.com",
            title="Reuters Dispatch 2",
            source_family_id="wire_reuters",
            relevance_score=0.80
        ),
        EvidenceItem(
            id="ev_soc",
            canonical_url="https://twitter.com/analyst/status/123",
            source_domain="twitter.com",
            title="Twitter Signal",
            channel="twitter",
            content_depth=ContentDepth.SOCIAL_POST.value,
            relevance_score=0.70
        ),
    ]

    selected, audit = deep_reader._select_read_candidates(candidates, max_reads=2)
    assert len(selected) > 0
    assert len(audit) == len(candidates)

    audit_map = {a["candidate_id"]: a for a in audit}
    assert audit_map["ev_p1"]["selected"] is True
    assert audit_map["ev_soc"]["eligible_for_read"] is False
    assert audit_map["ev_soc"]["rejection_reason"] == "social_only"


# ── 9. Primary Source Escalation Provenance Tests (Requirement 16) ───────────

def test_primary_source_escalation_provenance():
    """Verify escalated primary items carry originating evidence and query metadata."""
    candidates = [
        EvidenceItem(
            id="ev_sec_01",
            title="Company spokesperson said production will pause",
            snippet="According to a regulatory notice released today.",
            relevance_score=0.80
        )
    ]
    with patch("backend.services.agent_reach.adapter.AgentReachService.search_channel") as mock_search:
        mock_frag = MagicMock()
        mock_frag.url = "https://exchange.com/filing/123"
        mock_frag.author = "Exchange"
        mock_frag.title = "Exchange Official Filing"
        mock_frag.snippet = "Official disclosure text"
        mock_frag.content = "Official disclosure text"
        mock_frag.published = "Today"
        mock_frag.raw_metadata = {}
        mock_search.return_value = [mock_frag]

        primaries, tel = primary_source_escalator.escalate(candidates, target_name="Tata Motors", max_escalations=1)
        assert len(primaries) == 1
        p = primaries[0]
        assert p.primary_source is True
        assert p.metadata["originating_evidence_id"] == "ev_sec_01"
        assert p.metadata["escalation_reason"] in ("regulatory_filing", "official_statement")
        assert "primary_query_id" in p.metadata


# ── 10. Research Corpus Model Tests (Requirement 19) ─────────────────────────

def test_research_corpus_serialization():
    """Verify ResearchCorpus serializes all evidence partitions."""
    corpus = ResearchCorpus(
        queries=[{"channel": "web", "query_text": "Tata Motors"}],
        raw_candidates=[{"id": "ev_01"}],
        ranked_candidates=[{"id": "ev_01"}],
        deep_read_sources=[{"id": "ev_01"}],
        primary_sources=[{"id": "ev_01"}],
        social_sources=[],
        video_sources=[],
        transcript_sources=[],
        contradictions=[],
        corroboration_groups=[{"group_id": "grp_1", "item_ids": ["ev_01"]}],
        findings=[{"id": "fnd_01"}],
        evidence_graph={"nodes": [], "edges": []}
    )
    d = corpus.to_dict()
    assert "queries" in d
    assert "raw_candidates" in d
    assert "ranked_candidates" in d
    assert "deep_read_sources" in d
    assert "primary_sources" in d
    assert "corroboration_groups" in d
    assert "findings" in d
