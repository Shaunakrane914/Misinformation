"""
Shared pytest fixtures for the Aegis Protocol unit test suite.
"""

import hashlib
import socket
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def expanded_adapter_fixture_environment(request, monkeypatch):
    """Positive adapter fixtures have explicit synthetic DNS/config, not live access.

    Scope is limited to the original positive fixture modules. Security tests
    outside this list retain missing-config/blocked defaults.
    """
    if request.path.name not in {
        "test_wikipedia_adapter.py", "test_sec_filings_full_adapter.py", "test_sec_edgar_adapter.py",
        "test_arxiv_adapter.py", "test_substack_adapter.py", "test_yahoo_finance_adapter.py",
        "test_consumer_review_adapter.py", "test_reddit_deep_adapter.py", "test_wikidata_exec_adapter.py",
        "test_factcheck_adapter.py", "test_expanded_social_adapters.py", "test_news_wires_adapter.py",
    }:
        return
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    monkeypatch.setenv("REDDIT_APPROVED_ACCESS", "true")
    monkeypatch.setenv("SEC_USER_AGENT", "OfflineFixture test@example.invalid")
    monkeypatch.setenv("GOOGLE_FACTCHECK_API_KEY", "offline-fixture-not-a-key")
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.research.replay_ledger import ReplayLedger


# ── App client ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def api_client():
    """FastAPI TestClient shared across the session."""
    return TestClient(app)


# ── ReplayLedger ─────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_ledger(tmp_path):
    """A ReplayLedger backed by a temp directory — no disk side-effects."""
    return ReplayLedger(storage_dir=str(tmp_path))


# ── Quality tensor ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_quality_tensor():
    """A realistic quality tensor from a genuine research corpus."""
    return {
        "source_credibility": 0.91,
        "factual_consistency": 0.87,
        "recency_decay": 0.94,
        "corroboration_depth": 0.82,
        "cross_platform_diversity": 0.68,
        "primary_source_proximity": 0.89,
        "composite_quality": 0.85,
    }


# ── Dossier ───────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_dossier():
    """Minimal but structurally complete research dossier for replay tests."""
    content = "Original article body content used in investigation."
    cand_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return {
        "session_id": "R-2026-UNIT01",
        "target": "Sample claim for unit testing",
        "domain": "fact_check",
        "created_at": "2026-10-02T10:00:00Z",
        "latency_ms": 800,
        "summary": "No definitive corroboration found.",
        "queries_executed": [
            {"channel": "news", "query_text": "sample claim unit test"}
        ],
        "candidate_hashes": {"ev_unit_001": cand_hash},
        "source_lineage": {
            "nodes": [{"id": "ev_unit_001", "url": "https://example.com/unit-test"}],
            "metrics": {"echo_count": 0},
        },
        "findings_provenance": [
            {
                "finding_id": "FND-01",
                "title": "Sample finding",
                "epistemic_state": "CONTESTED",
                "quality_tensor": None,
                "supporting_evidence_ids": ["ev_unit_001"],
                "contradicting_evidence_ids": [],
                "primary_sources": [],
            }
        ],
        "decision_log": [
            {
                "stage": "QueryPlanning",
                "decision_type": "QUERY_GENERATION",
                "rationale": "Generated 1 query for domain 'fact_check'.",
            }
        ],
        "saturation_summary": {},
        "capability_graph": [],
        "status": "COMPLETED",
    }


# ── Agent mocks ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_research_no_corpus():
    """ResearchAgent mock that returns no genuine corpus or quality tensor."""
    m = MagicMock()
    m.gather_evidence_structured.return_value = {
        "research_corpus": None,
        "quality_tensor": None,
        "evidence_chain": [],
        "research_trace": {},
        "contradictions": [],
    }
    return m


@pytest.fixture
def mock_investigator_false():
    """InvestigatorAgent mock returning a FALSE verdict."""
    m = MagicMock()
    m.process.return_value = {
        "verdict": "False",
        "confidence": 0.88,
        "reasoning": "No substantiation found in verified registries.",
        "severity": "High",
    }
    return m
