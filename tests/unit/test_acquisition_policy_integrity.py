"""Regression gates for operation authority, observed evidence and read bounds."""

import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.application.research.contracts import RankedEvidence
from backend.application.research.reading import DeepReadingStage
from backend.infrastructure.acquisition.service import AgentReachService
from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import CandidateSource, ChannelStatus, EvidenceFragment, FetchedDocument, RetrievalRequest
from backend.services.agent_reach.native.adapters import GitHubAdapter, SearchDiscoveryAdapter, WebAdapter, YouTubeAdapter
from backend.services.agent_reach.native.operation_capabilities import RuntimeOperationCapabilities
from backend.services.agent_reach.profile import ScoutAcquisition
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.services.research.deep_reader import DeepReader
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import EvidenceItem, ResearchRequest


@pytest.mark.parametrize("channel,operation", [("rss", "read"), ("v2ex", "latest"), ("twitter", "search"), ("xiaoyuzhou", "episodes")])
def test_legacy_auth_probe_does_not_disable_public_operations(channel, operation):
    service = AgentReachService()
    service.registry.update_status(channel, ChannelStatus.AUTH_REQUIRED)
    source = service.registry.get_channel(channel)
    source.search = Mock(return_value=[EvidenceFragment(platform=channel, url="https://example.com/source", content="Observed evidence")])
    runtime = RuntimeOperationCapabilities()
    with patch("backend.infrastructure.acquisition.service.runtime_operation_capabilities", runtime):
        result = service.retrieve_many({channel: [{"query_text": "source", "operation": operation}]}, perform_reads=False)
    source.search.assert_called_once()
    assert len(result.fragments) == 1


def test_runtime_policy_still_excludes_reddit_without_approved_access(monkeypatch):
    monkeypatch.setenv("REDDIT_APPROVED_ACCESS", "false")
    service = AgentReachService()
    source = service.registry.get_channel("reddit")
    source.search = Mock()
    with patch("backend.infrastructure.acquisition.service.runtime_operation_capabilities", RuntimeOperationCapabilities()):
        result = service.retrieve_many({"reddit": ["source"]}, perform_reads=False)
    source.search.assert_not_called()
    assert result.fragments == []
    assert result.query_records[0].status == "SKIPPED"


def test_direct_channel_dispatch_cannot_bypass_policy(monkeypatch):
    monkeypatch.setenv("REDDIT_APPROVED_ACCESS", "false")
    router = NativeRouter()
    with patch.object(router.channel_dispatcher.social, "execute") as provider:
        fragments, telemetry = router.execute_channel_query("reddit", "r/investing")
    provider.assert_not_called()
    assert fragments == []
    assert telemetry["attempts"] == 0
    assert telemetry["outcome"] == "EXCLUDED"


def test_direct_read_cannot_bypass_policy(monkeypatch):
    monkeypatch.setenv("REDDIT_APPROVED_ACCESS", "false")
    router = NativeRouter()
    with patch("backend.infrastructure.acquisition.routing.router.is_safe_url", return_value=(True, "safe")), \
         patch.object(router, "_fetch_arctic_shift_post") as provider:
        result = router.execute_channel_read("https://reddit.com/r/test/comments/abc123/title")
    provider.assert_not_called()
    assert result["status"] == "failed"
    assert "POLICY_BLOCKED" in result["error"]


def test_direct_channel_dispatch_preserves_cooldown():
    router = NativeRouter()
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("github", "releases", {"outcome": "FAILED", "http_statuses": [429], "network_observed": True})
    with patch("backend.infrastructure.acquisition.routing.channel_dispatcher.runtime_operation_capabilities", runtime), \
         patch.object(router.channel_dispatcher.standard, "execute") as provider:
        _, telemetry = router.execute_channel_query("github", "owner/repo", operation="releases")
    provider.assert_not_called()
    assert telemetry["outcome"] == "DEFERRED"
    assert runtime.assess("github", "releases")["last_outcome"] == "RATE_LIMITED"


def test_empty_validated_source_plan_fails_closed():
    service = AgentReachService()
    service.source_planner.plan = Mock(return_value=SimpleNamespace(
        channels=[], actions=[], to_dict=lambda: {"actions": [], "excluded": [{"reason": "POLICY_BLOCKED"}]}
    ))
    request = RetrievalRequest(query="topic", allowed_channels=["reddit"])
    with patch("backend.infrastructure.acquisition.service.native_router.execute_retrieval_request") as execute:
        assert service.execute(request) == []
    execute.assert_not_called()
    assert request.allowed_channels == []


def test_typed_plan_preserves_operations_and_never_runs_strategy_discovery():
    router = NativeRouter()
    request = RetrievalRequest(query="repository", agent="scout", allowed_channels=["github"], metadata={"source_plan": {
        "actions": [
            {"channel": "github", "operation": "releases", "query": "owner/repo"},
            {"channel": "twitter", "operation": "search", "query": "unauthorized"},
        ]}})
    fragment = EvidenceFragment(platform="github", url="https://github.com/owner/repo/releases", content="Published release")
    with patch("backend.infrastructure.acquisition.routing.router.runtime_operation_capabilities", RuntimeOperationCapabilities()), \
         patch.object(router, "execute_channel_query", return_value=([fragment], {})) as execute, \
         patch.object(router.search_adapter, "discover_candidates") as discover:
        assert router.execute_retrieval_request(request) == [fragment]
    execute.assert_called_once()
    assert execute.call_args.kwargs["operation"] == "releases"
    assert execute.call_args.args[:2] == ("github", "owner/repo")
    discover.assert_not_called()


def test_typed_plan_keeps_personal_watch_redaction_without_depth_upgrade():
    router = NativeRouter()
    request = RetrievalRequest(query="John Doe statement", agent="personal", allowed_channels=["web"],
                               metadata={"source_plan": {"actions": [{"channel": "web", "operation": "search", "query": "John Doe"}]}})
    fragment = EvidenceFragment(platform="web", url="https://example.com/statement", content="John Doe phone 555-123-4567",
                                snippet="John Doe phone 555-123-4567", content_depth="SNIPPET")
    with patch("backend.infrastructure.acquisition.routing.router.runtime_operation_capabilities", RuntimeOperationCapabilities()), \
         patch.object(router, "execute_channel_query", return_value=([fragment], {})):
        result = router.execute_retrieval_request(request)
    assert result[0].content_depth == "SNIPPET"
    assert "555-123-4567" not in result[0].content
    assert result[0].metadata["pii_filtered"] is True


def test_strategy_cannot_discover_outside_explicit_channel_boundary():
    router = NativeRouter()
    request = RetrievalRequest(entity="NVIDIA", agent="scout", allowed_channels=["web"])
    candidate = CandidateSource(url="https://github.com/nvidia/test", platform="github", title="NVIDIA repository")
    with patch.object(router.search_adapter, "discover_candidates", return_value=[candidate]), \
         patch("backend.services.agent_reach.profile.get_agent_acquisition_strategy") as strategy, \
         patch.object(router.github_adapter, "acquire") as acquire:
        assert router.execute_retrieval_request(request) == []
    assert not strategy.return_value.discover.called
    acquire.assert_not_called()


def test_empty_platform_optout_stays_empty():
    service = AgentReachService()
    with patch.object(service, "retrieve_many") as retrieve:
        result = service.unified_scan("topic", platforms=[])
    retrieve.assert_not_called()
    assert result["total_signals"] == 0


@pytest.mark.parametrize("adapter,payload", [
    (WebAdapter(), "<p>Observed article body</p>"),
    (SearchDiscoveryAdapter(), json.dumps({"title": "Source", "snippet": "Index only"})),
    (YouTubeAdapter(), json.dumps({"title": "Video", "description": "Description " * 80})),
    (GitHubAdapter(), json.dumps({"full_name": "owner/repo", "description": "Description"})),
])
def test_missing_publication_date_remains_unknown(adapter, payload):
    candidate = CandidateSource(url="https://example.com/source", platform=adapter.platform)
    fragment = adapter.normalize(FetchedDocument(url=candidate.url, raw_content=payload), candidate, RetrievalRequest())[0]
    assert fragment.published == ""
    if adapter.platform in {"github", "youtube"}:
        assert fragment.content_depth in {"VIDEO_METADATA", "STRUCTURED_METADATA"}


def test_github_adapter_preserves_git_suffix_and_uses_bounded_transport():
    candidate = CandidateSource(url="https://github.com/owner/legit.git", platform="github")
    response = BoundedHTTPResponse(body=b'{"full_name":"owner/legit"}', endpoint="https://api.github.com/repos/owner/legit",
                                   status_code=200, content_type="application/json", headers={}, latency_ms=3, attempts=1)
    with patch("backend.services.agent_reach.native.adapters.github.validate_url_safe", return_value=(True, "")), \
         patch("backend.services.agent_reach.native.adapters.github.fetch_public_http", return_value=response) as fetch:
        document = GitHubAdapter().acquire(candidate, RetrievalRequest())
    assert document.status == "SUCCESS"
    assert fetch.call_args.args[0] == "https://api.github.com/repos/owner/legit"
    assert fetch.call_args.kwargs["timeout"] == 5.0
    assert fetch.call_args.kwargs["max_bytes"] == 1_000_000


def test_github_adapter_rejects_hostname_spoof_without_fetch():
    candidate = CandidateSource(url="https://github.com.attacker.example/owner/repo", platform="github")
    with patch("backend.services.agent_reach.native.adapters.github.validate_url_safe", return_value=(True, "")), \
         patch("backend.services.agent_reach.native.adapters.github.fetch_public_http") as fetch:
        document = GitHubAdapter().acquire(candidate, RetrievalRequest())
    assert document.status == "BLOCKED"
    fetch.assert_not_called()


def test_scout_never_promotes_snippets_or_attacker_domain_to_primary():
    candidate = CandidateSource(url="https://sec.gov.attacker.example/report", platform="web")
    fragment = ScoutAcquisition().normalize(FetchedDocument(url=candidate.url, raw_content="Short index snippet"), candidate, RetrievalRequest())[0]
    assert fragment.content_depth == "SNIPPET"
    assert fragment.metadata["is_primary_source"] is False


@pytest.mark.parametrize("request_budget,start_ts", [(0, None), (5, 0)])
def test_deep_reading_skips_zero_budget_or_expired_deadline(request_budget, start_ts):
    request = ResearchRequest(target="Topic", deep_read_budget=request_budget)
    ranked = RankedEvidence(accepted=[], ranked=[EvidenceItem(id="e1")], rejected=[], clusters={})
    with patch("backend.application.research.reading.deep_reader.deep_read") as read:
        result = DeepReadingStage().run(request, ResearchBudget(deep_read_budget=10), ranked,
                                       start_ts=time.monotonic() if start_ts is None else start_ts, effective_timeout=1)
    read.assert_not_called()
    assert result.telemetry["attempted"] == 0


def test_deep_reading_caps_request_budget_and_remaining_timeout():
    request = ResearchRequest(target="Topic", deep_read_budget=20)
    ranked = RankedEvidence(accepted=[], ranked=[EvidenceItem(id="e1")], rejected=[], clusters={})
    with patch("backend.application.research.reading.deep_reader.deep_read", return_value=([], {})) as read:
        DeepReadingStage().run(request, ResearchBudget(deep_read_budget=2), ranked, start_ts=time.monotonic(), effective_timeout=0.2)
    assert read.call_args.kwargs["max_reads"] == 2
    assert 0 < read.call_args.kwargs["timeout_per_read"] <= 0.2


def test_deep_reader_returns_at_deadline_without_executor_shutdown_wait():
    release = threading.Event()
    entered = threading.Event()
    item = EvidenceItem(id="e1", canonical_url="https://example.com/report", source_domain="example.com", source_quality_score=0.8, relevance_score=0.8)

    def slow_read(*args, **kwargs):
        entered.set()
        release.wait(2)
        return {"status": "success", "markdown": "Observed content " * 50}

    try:
        with patch("backend.services.agent_reach.agent_reach_service.read", side_effect=slow_read):
            started = time.perf_counter()
            investigated, telemetry = DeepReader().deep_read([item], max_reads=1, timeout_per_read=0.05)
            elapsed = time.perf_counter() - started
        assert entered.is_set()
        assert elapsed < 0.3
        assert investigated == []
        assert telemetry["failed"] == 1
        assert item.read_status == "TIMEOUT"
    finally:
        release.set()


def test_retrieve_many_returns_at_deadline_without_two_second_grace():
    service = AgentReachService()
    release = threading.Event()

    def slow_query(*args, **kwargs):
        release.wait(2)
        return []

    service.registry.get_channel("news").search = slow_query
    try:
        with patch("backend.infrastructure.acquisition.service.runtime_operation_capabilities", RuntimeOperationCapabilities()):
            started = time.perf_counter()
            result = service.retrieve_many({"news": ["topic"]}, timeout=0.05, perform_reads=False)
        assert time.perf_counter() - started < 0.3
        assert result.fragments == []
        assert result.query_records[0].status == "TIMEOUT"
    finally:
        release.set()


def test_source_read_consumes_same_deadline_and_does_not_launch_late_search():
    service = AgentReachService()
    release = threading.Event()
    search = Mock()
    service.registry.get_channel("news").search = search

    def slow_read(*args, **kwargs):
        release.wait(2)
        return {"status": "success", "markdown": "late content"}

    try:
        with patch.object(service, "read", side_effect=slow_read), \
             patch("backend.infrastructure.acquisition.service.runtime_operation_capabilities", RuntimeOperationCapabilities()):
            started = time.perf_counter()
            result = service.retrieve_many({"news": ["topic"]}, source_url="https://example.com/report", timeout=0.05)
        assert time.perf_counter() - started < 0.3
        search.assert_not_called()
        assert result.source_article["status"] == "failed"
    finally:
        release.set()


def test_registry_discovery_deadline_is_bounded_and_reports_unknown():
    registry = CapabilityRegistry()
    release = threading.Event()
    channel = Mock()
    channel.name = "slow"

    def slow_check():
        release.wait(2)
        return ChannelStatus.AVAILABLE

    channel.health_check = slow_check
    registry.register(channel)
    try:
        started = time.perf_counter()
        result = registry.discover(timeout=0.05)
        assert time.perf_counter() - started < 0.3
        assert result == {"slow": "UNKNOWN"}
        assert registry.get_status("slow") == ChannelStatus.UNKNOWN
    finally:
        release.set()


def test_generic_discovery_uses_real_search_fragments():
    fragment = EvidenceFragment(platform="web", title="Official announcement", snippet="Observed search summary", url="https://example.com/announcement")
    with patch("backend.services.agent_reach.native.router.native_router._execute_web_search", return_value=[fragment]) as search:
        candidates = SearchDiscoveryAdapter().discover_candidates("official announcement", platform="web")
    search.assert_called_once()
    assert len(candidates) == 1
    assert candidates[0].url == fragment.url
    assert candidates[0].snippet == fragment.snippet
