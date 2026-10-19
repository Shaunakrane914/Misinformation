"""Long research opportunities, bounded calls; no live providers or AI."""
from unittest.mock import Mock, patch
import time

import pytest

from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import ResearchRequest, EvidenceItem


@pytest.mark.parametrize("server", [False, True])
def test_patient_defaults_apply_on_desktop_and_server(monkeypatch, server):
    for name in ("RENDER", "PORT", "SERVER_MODE", "SERVER_RESEARCH_TIMEOUT", "LOCAL_RESEARCH_TIMEOUT",
                 "RESEARCH_MAX_TOTAL_LATENCY_SECONDS", "SERVER_RESEARCH_CHANNEL_TIMEOUT",
                 "LOCAL_RESEARCH_CHANNEL_TIMEOUT", "RESEARCH_CHANNEL_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    if server:
        monkeypatch.setenv("SERVER_MODE", "1")
    budget = ResearchBudget.from_env()
    assert budget.timeout_seconds == 120
    assert budget.channel_timeout_seconds == 15
    assert budget.discovery_timeout_seconds == 54
    assert budget.deep_read_timeout_seconds == 48


def test_explicit_short_budget_is_still_respected(monkeypatch):
    monkeypatch.setenv("SERVER_MODE", "1")
    monkeypatch.setenv("SERVER_RESEARCH_TIMEOUT", "7")
    monkeypatch.setenv("SERVER_RESEARCH_CHANNEL_TIMEOUT", "2")
    budget = ResearchBudget.from_env()
    assert budget.timeout_seconds == 7
    assert budget.channel_timeout_seconds == 2


def test_broad_discovery_no_hidden_two_call_cutoff(monkeypatch):
    from backend.application.research.acquisition import BroadDiscoveryStage
    from backend.services import agent_reach
    from types import SimpleNamespace
    service = agent_reach.agent_reach_service
    retrieve = Mock(return_value=SimpleNamespace())
    # Patch the class to avoid creating a lasting instance-bound override.
    monkeypatch.setattr(type(service), "retrieve_many", retrieve)
    BroadDiscoveryStage().run(ResearchRequest("Public Company"), ResearchBudget(), 120,
                             SimpleNamespace(channel_queries={"web": ["Public Company report"]}))
    assert retrieve.call_args.kwargs["timeout"] == 54
    assert retrieve.call_args.kwargs["budget"]["channel_timeout"] == 15


def test_reading_can_still_start_after_forty_seconds(monkeypatch):
    from backend.application.research import reading
    from backend.application.research.contracts import RankedEvidence
    item = EvidenceItem(id="source", title="Public Company earnings report",
                        canonical_url="https://publisher.example/report")
    read = Mock(return_value=([], {"attempted": 1, "successful": 0}))
    now = time.monotonic()
    with patch.object(reading.deep_reader, "deep_read", read):
        reading.DeepReadingStage().run(ResearchRequest("Public Company"), ResearchBudget(),
                                      RankedEvidence([item], [item], {}, []), now - 40, 120)
    assert read.call_args.kwargs["timeout_per_read"] == 15


def test_frontend_wait_exceeds_research_window():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[2] / "frontend" / "agent-research-client.js").read_text(encoding="utf-8")
    assert "const ANALYSIS_MS = 300000" in source
    assert ResearchBudget().timeout_seconds * 1000 < 300000
