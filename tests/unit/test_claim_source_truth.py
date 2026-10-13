"""Claim API must not promote unsupported synthesis into sourced evidence."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app


def _verify_with(research_result, investigator_result):
    ingestion = MagicMock()
    ingestion.ingest.return_value = {"claim_id": "claim-source-truth", "normalized_text": "A test claim about company revenue"}
    ingestion.decompose_claim.return_value = []
    research = MagicMock()
    if isinstance(research_result, Exception):
        research.gather_evidence_structured.side_effect = research_result
        research.gather_evidence.side_effect = research_result
    else:
        research.gather_evidence_structured.return_value = research_result
    investigator = MagicMock()
    investigator.process.return_value = investigator_result

    with patch("backend.api.claims.get_claim_ingestion_agent", return_value=ingestion), \
         patch("backend.api.claims.get_research_agent", return_value=research), \
         patch("backend.api.claims.get_investigator_agent", return_value=investigator), \
         patch("backend.api.claims.db.get_claim_by_hash", return_value={"id": "existing"}), \
         patch("backend.api.claims.db.get_claim_research_funnel", return_value=None), \
         patch("backend.api.claims.replay_ledger.record_investigation", return_value="R-test") as record:
        response = TestClient(app).post("/api/claims/verify", json={"claim_text": "A test claim about company revenue"})
    assert response.status_code == 200, response.text
    return response.json(), record.call_args.kwargs


def test_research_failure_cannot_become_decisive_or_fake_search_telemetry():
    data, replay = _verify_with(
        RuntimeError("research unavailable"),
        {"verdict": "False", "confidence": 0.99, "reasoning": "Invented denial", "severity": "High"},
    )
    assert data["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert data["confidence"] is None
    assert data["supporting_evidence"] == data["refuting_evidence"] == []
    assert data["debunk_statement"] is None
    assert data["action_package"] is None
    assert data["source_lineage"]["metrics"]["true_independent_count"] == 0
    assert data["funnel"]["queries_planned"] == data["funnel"]["queries_executed"] == 0
    assert data["funnel"]["independent_groups_count"] is None
    assert replay["queries"] == []
    assert data["unified_report"]["summary"].startswith("Claim is **INSUFFICIENT_EVIDENCE**")


def test_model_only_sentences_and_unsafe_links_are_not_source_evidence():
    data, _ = _verify_with(
        {
            "supporting_evidence": [
                "A test claim about company revenue is unlinked model output",
                {"source": "Reuters", "text": "A test claim about company revenue is unlinked"},
                {"source": "Example", "text": "A test claim about company revenue with unsafe link", "url": "javascript:alert(1)"},
                {"source": "Example", "text": "A test claim about company revenue has this filing excerpt", "url": "https://example.org/filing"},
            ],
            "refuting_evidence": [],
        },
        {"verdict": "True", "confidence": 0.8, "reasoning": "There is one source", "severity": "Low"},
    )
    assert data["verdict"] == "TRUE"
    assert len(data["supporting_evidence"]) == 1
    assert data["supporting_evidence"][0]["url"] == "https://example.org/filing"
    assert data["source_lineage"]["nodes"][0]["role"] == "DISCOVERY"
    assert data["source_lineage"]["nodes"][0]["tier"] == "TIER_3_AGGREGATE"
    assert data["funnel"]["primary_sources_count"] == 0
    assert len(data["rejected_evidence"]) >= 3


def test_untrue_is_not_mapped_to_true():
    data, _ = _verify_with(
        {"supporting_evidence": [{"text": "A test claim about company revenue is described here", "url": "https://example.org/article"}]},
        {"verdict": "Untrue", "confidence": 0.9, "reasoning": "Unknown taxonomy", "severity": "Low"},
    )
    assert data["verdict"] == "UNVERIFIED"
