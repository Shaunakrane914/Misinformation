"""
Aegis Protocol — Negative Test Suite for Audit Synthetic Telemetry
===================================================================
Tests that validate the Machine-Checkable Audit Lineage Validator
catches synthetic, reconstructive, or fabricated telemetry patterns:
- Test A: Reconstructed ranked pool without candidate_ranked event -> FAILS
- Test B: Reconstructed accepted pool without candidate_selected event -> FAILS
- Test C: Synthetic acquisition without useful_content_extracted -> FAILS
- Test D: Broken 5-stage ID lineage link -> FAILS
- Test E: Evidence count > acquired count -> FAILS
- Test F: Inferred/synthetic status detected -> reports NOT_ENOUGH_EVIDENCE
- Test G: Unobserved channel attempt -> FAILS
- Test H: Fabricated backend/latency without network attempt -> FAILS
"""

import pytest
from backend.services.research.audit_lineage_validator import (
    TelemetryObservationStatus,
    LineageValidationResult,
    validate_candidate_lineage,
    validate_acquisition_lineage,
    validate_evidence_lineage,
    validate_no_synthetic_events,
)


def test_a_reconstructed_ranked_pool_without_discovery_event():
    """Test A: Ranked candidate referencing an unobserved/undiscovered ID must FAIL."""
    discovered = [{"candidate_id": "cand_001", "url": "https://example.com/1"}]
    ranked = [
        {"candidate_id": "cand_001", "ranked_candidate_id": "cand_rank_001"},
        {"candidate_id": "cand_999", "ranked_candidate_id": "cand_rank_999"},  # Invented candidate
    ]
    selected = [{"ranked_candidate_id": "cand_rank_001", "accepted_candidate_id": "cand_acc_001", "selection_decision": "ACCEPTED"}]

    valid, violations = validate_candidate_lineage(discovered, ranked, selected)
    assert not valid
    assert any("cand_999" in v and "never observed" in v for v in violations)


def test_b_reconstructed_accepted_pool_without_ranked_event():
    """Test B: Accepted candidate referencing an unranked ID must FAIL."""
    discovered = [{"candidate_id": "cand_001", "url": "https://example.com/1"}]
    ranked = [{"candidate_id": "cand_001", "ranked_candidate_id": "cand_rank_001"}]
    selected = [
        {"ranked_candidate_id": "cand_rank_001", "accepted_candidate_id": "cand_acc_001", "selection_decision": "ACCEPTED"},
        {"ranked_candidate_id": "cand_rank_unranked", "accepted_candidate_id": "cand_acc_fake", "selection_decision": "ACCEPTED"},
    ]

    valid, violations = validate_candidate_lineage(discovered, ranked, selected)
    assert not valid
    assert any("unranked" in v for v in violations)


def test_c_synthetic_acquisition_without_useful_content():
    """Test C: Acquisition marked SUCCESS without useful content extracted must FAIL."""
    selected = [{"accepted_candidate_id": "cand_acc_001", "selection_decision": "ACCEPTED"}]
    acquisitions = [{
        "attempt_id": "att_001",
        "accepted_candidate_id": "cand_acc_001",
        "status": "SUCCESS",
        "useful_content_extracted": False,  # Synthetic success!
        "backend": "jina_reader",
        "acquired_candidate_id": "cand_acq_001"
    }]

    valid, violations = validate_acquisition_lineage(selected, acquisitions)
    assert not valid
    assert any("useful_content_extracted is False" in v for v in violations)


def test_d_broken_five_stage_id_lineage():
    """Test D: Evidence record pointing to missing or invalid attempt_id must FAIL."""
    discovered = [{"candidate_id": "cand_001"}]
    ranked = [{"candidate_id": "cand_001", "ranked_candidate_id": "cand_rank_001"}]
    selected = [{"ranked_candidate_id": "cand_rank_001", "accepted_candidate_id": "cand_acc_001", "selection_decision": "ACCEPTED"}]
    acquisitions = [{
        "attempt_id": "att_001",
        "accepted_candidate_id": "cand_acc_001",
        "acquired_candidate_id": "cand_acq_001",
        "status": "SUCCESS",
        "useful_content_extracted": True,
        "backend": "jina_reader",
    }]
    evidence = [{
        "evidence_id": "ev_001",
        "acquisition_attempt_id": "att_nonexistent",  # Broken link
        "acquired_candidate_id": "cand_acq_001",
        "accepted_candidate_id": "cand_acc_001",
        "ranked_candidate_id": "cand_rank_001",
        "discovered_candidate_id": "cand_001"
    }]

    result = validate_evidence_lineage(evidence, acquisitions, selected, ranked, discovered)
    assert not result.is_valid
    assert result.broken_lineage_count == 1
    assert any("non-existent acquisition attempt" in v for v in result.violations)


def test_e_evidence_count_exceeds_acquired_count():
    """Test E: More evidence records than successful acquisitions must FAIL."""
    discovered = [{"candidate_id": f"c_{i}"} for i in range(3)]
    ranked = [{"candidate_id": f"c_{i}", "ranked_candidate_id": f"r_{i}"} for i in range(3)]
    selected = [{"ranked_candidate_id": f"r_{i}", "accepted_candidate_id": f"a_{i}", "selection_decision": "ACCEPTED"} for i in range(3)]
    # Only 1 acquisition succeeded
    acquisitions = [{
        "attempt_id": "att_0",
        "accepted_candidate_id": "a_0",
        "acquired_candidate_id": "acq_0",
        "status": "SUCCESS",
        "useful_content_extracted": True,
        "backend": "jina_reader",
    }]
    # But 2 evidence items returned
    evidence = [
        {"evidence_id": "ev_0", "acquisition_attempt_id": "att_0", "acquired_candidate_id": "acq_0", "accepted_candidate_id": "a_0", "ranked_candidate_id": "r_0", "discovered_candidate_id": "c_0"},
        {"evidence_id": "ev_1", "acquisition_attempt_id": None, "acquired_candidate_id": "acq_1"},
    ]

    result = validate_evidence_lineage(evidence, acquisitions, selected, ranked, discovered)
    assert not result.is_valid
    assert result.unobserved_acquisitions_count >= 1


def test_f_inferred_status_detected_reports_not_enough_evidence():
    """Test F: When unobserved or synthetic events exist, completeness_status must be NOT_ENOUGH_EVIDENCE."""
    discovered = [{"candidate_id": "c_1"}]
    ranked = [{"candidate_id": "c_1", "ranked_candidate_id": "r_1"}]
    selected = [{"ranked_candidate_id": "r_1", "accepted_candidate_id": "a_1", "selection_decision": "ACCEPTED"}]
    acquisitions = []  # No acquisitions observed!
    evidence = [{"evidence_id": "ev_1", "acquisition_attempt_id": None}]

    result = validate_evidence_lineage(evidence, acquisitions, selected, ranked, discovered)
    assert not result.is_valid
    assert result.completeness_status == "NOT_ENOUGH_EVIDENCE"


def test_g_unobserved_channel_attempt():
    """Test G: Query attempt disguised as candidate read without url must FAIL."""
    selected = [{"accepted_candidate_id": "a_1", "selection_decision": "ACCEPTED"}]
    acquisitions = [{
        "attempt_id": "att_query",
        "accepted_candidate_id": "a_1",
        "query_text": "Microsoft security",  # Query disguised as read!
        "url": "",
        "status": "SUCCESS",
        "useful_content_extracted": True,
        "backend": "bing",
        "acquired_candidate_id": "acq_1"
    }]

    valid, violations = validate_acquisition_lineage(selected, acquisitions)
    assert not valid
    assert any("looks like a discovery query" in v for v in violations)


def test_h_fabricated_backend_without_attribution():
    """Test H: Acquisition marked SUCCESS without real backend attribution must FAIL."""
    evidence = [{"evidence_id": "ev_1", "acquisition_attempt_id": "att_1"}]
    acquisitions = [{
        "attempt_id": "att_1",
        "status": "SUCCESS",
        "useful_content_extracted": True,
        "backend": "",  # Missing backend attribution!
    }]

    valid, violations = validate_no_synthetic_events("BrandShield", evidence, acquisitions)
    assert not valid
    assert any("lacks real backend attribution" in v for v in violations)
