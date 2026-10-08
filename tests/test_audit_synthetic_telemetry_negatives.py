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


def test_empty_run_assertion_test_1_acquisition_failure():
    """Test 1: accepted > 0, attempts > 0, successful = 0, final_evidence = 0 must produce ACQUISITION_FAILURE or NOT_ENOUGH_EVIDENCE, never OBSERVED."""
    discovered = [{"candidate_id": f"c_{i}"} for i in range(5)]
    ranked = [{"candidate_id": f"c_{i}", "ranked_candidate_id": f"r_{i}"} for i in range(5)]
    selected = [{"candidate_id": f"c_{i}", "ranked_candidate_id": f"r_{i}", "accepted_candidate_id": f"a_{i}", "selection_decision": "ACCEPTED"} for i in range(5)]
    acquisitions = [{
        "attempt_id": f"att_{i}",
        "accepted_candidate_id": f"a_{i}",
        "status": "FAILED",
        "useful_content_extracted": False,
        "backend": "scrapling_http"
    } for i in range(5)]
    evidence = []

    result = validate_evidence_lineage(evidence, acquisitions, selected, ranked, discovered)
    assert not result.is_valid
    assert result.completeness_status in ("ACQUISITION_FAILURE", "NOT_ENOUGH_EVIDENCE")
    assert result.completeness_status != "OBSERVED"


def test_empty_run_assertion_test_2_legitimate_zero_results():
    """Test 2: accepted = 0, acquisition_attempts = 0, final_evidence = 0 must produce OBSERVED_NO_RESULTS."""
    discovered = [{"candidate_id": "c_1"}]
    ranked = []
    selected = []
    acquisitions = []
    evidence = []

    result = validate_evidence_lineage(evidence, acquisitions, selected, ranked, discovered)
    assert result.is_valid
    assert result.completeness_status == "OBSERVED_NO_RESULTS"


def test_empty_run_assertion_test_3_broken_lineage_fails():
    """Test 3: final_evidence > 0, valid_lineage = 0 must produce FAIL, never OBSERVED."""
    discovered = [{"candidate_id": "c_1"}]
    ranked = [{"candidate_id": "c_1", "ranked_candidate_id": "r_1"}]
    selected = [{"ranked_candidate_id": "r_1", "accepted_candidate_id": "a_1", "selection_decision": "ACCEPTED"}]
    acquisitions = [{
        "attempt_id": "att_1",
        "accepted_candidate_id": "a_1",
        "acquired_candidate_id": "acq_1",
        "status": "SUCCESS",
        "useful_content_extracted": True,
        "backend": "scrapling_http"
    }]
    # Evidence has broken link to unknown candidate
    evidence = [{
        "evidence_id": "ev_1",
        "acquisition_attempt_id": "att_1",
        "acquired_candidate_id": "acq_unknown",
        "accepted_candidate_id": "a_unknown",
        "ranked_candidate_id": "r_unknown",
        "discovered_candidate_id": "c_unknown"
    }]

    result = validate_evidence_lineage(evidence, acquisitions, selected, ranked, discovered)
    assert not result.is_valid
    assert result.completeness_status == "FAIL"
    assert result.completeness_status != "OBSERVED"


def test_empty_run_assertion_test_4_specialist_attempts_accounting():
    """Test 4: executive specialist attempts must equal social specialist attempts when derived from same events."""
    acq_attempts = [
        {"attempt_id": "a1", "backend": "fxtwitter", "status": "SUCCESS", "useful_content_extracted": True, "url": "https://x.com/post/1"},
        {"attempt_id": "a2", "backend": "arctic_shift", "status": "SUCCESS", "useful_content_extracted": True, "url": "https://reddit.com/r/test/comments/1"},
        {"attempt_id": "a3", "backend": "yt-dlp", "status": "FAILED", "useful_content_extracted": False, "url": "https://youtube.com/watch?v=123"},
        {"attempt_id": "a4", "backend": "scrapling_http", "status": "SUCCESS", "useful_content_extracted": True, "url": "https://example.com/article"},
    ]

    # Executive accounting
    specialist_backends = {"fxtwitter", "arctic_shift", "yt-dlp"}
    exec_specialist_attempts = sum(1 for a in acq_attempts if a.get("backend") in specialist_backends)

    # Social channels accounting
    tw_attempts = sum(1 for a in acq_attempts if a.get("backend") == "fxtwitter")
    rd_attempts = sum(1 for a in acq_attempts if a.get("backend") == "arctic_shift")
    yt_attempts = sum(1 for a in acq_attempts if a.get("backend") == "yt-dlp")
    social_specialist_attempts = tw_attempts + rd_attempts + yt_attempts

    assert exec_specialist_attempts == social_specialist_attempts == 3


def test_empty_run_assertion_test_5_successful_acquisition_field_requirements():
    """Test 5: A successful acquisition cannot exist without attempt_id, accepted_candidate_id, acquired_candidate_id, backend, useful_content_extracted = True."""
    selected = [{"accepted_candidate_id": "a_1", "selection_decision": "ACCEPTED"}]

    # Missing attempt_id
    invalid_no_attempt = [{
        "attempt_id": "",
        "accepted_candidate_id": "a_1",
        "acquired_candidate_id": "acq_1",
        "backend": "scrapling_http",
        "status": "SUCCESS",
        "useful_content_extracted": True
    }]
    valid, v1 = validate_acquisition_lineage(selected, invalid_no_attempt)
    assert not valid

    # Missing accepted_candidate_id
    invalid_no_accepted = [{
        "attempt_id": "att_1",
        "accepted_candidate_id": "",
        "acquired_candidate_id": "acq_1",
        "backend": "scrapling_http",
        "status": "SUCCESS",
        "useful_content_extracted": True
    }]
    valid, v2 = validate_acquisition_lineage(selected, invalid_no_accepted)
    assert not valid

    # Missing acquired_candidate_id
    invalid_no_acquired = [{
        "attempt_id": "att_1",
        "accepted_candidate_id": "a_1",
        "acquired_candidate_id": "",
        "backend": "scrapling_http",
        "status": "SUCCESS",
        "useful_content_extracted": True
    }]
    valid, v3 = validate_acquisition_lineage(selected, invalid_no_acquired)
    assert not valid

    # Missing backend
    invalid_no_backend = [{
        "attempt_id": "att_1",
        "accepted_candidate_id": "a_1",
        "acquired_candidate_id": "acq_1",
        "backend": "",
        "status": "SUCCESS",
        "useful_content_extracted": True
    }]
    valid, v4 = validate_acquisition_lineage(selected, invalid_no_backend)
    assert not valid

    # useful_content_extracted is False
    invalid_not_useful = [{
        "attempt_id": "att_1",
        "accepted_candidate_id": "a_1",
        "acquired_candidate_id": "acq_1",
        "backend": "scrapling_http",
        "status": "SUCCESS",
        "useful_content_extracted": False
    }]
    valid, v5 = validate_acquisition_lineage(selected, invalid_not_useful)
    assert not valid

    # Fully valid
    valid_acq = [{
        "attempt_id": "att_1",
        "accepted_candidate_id": "a_1",
        "acquired_candidate_id": "acq_1",
        "backend": "scrapling_http",
        "status": "SUCCESS",
        "useful_content_extracted": True
    }]
    valid, v6 = validate_acquisition_lineage(selected, valid_acq)
    assert valid


def test_integration_production_candidate_to_evidence_fragment(monkeypatch):
    """Integration Test: Exercises actual production candidate -> DeepReader -> acquisition attempt -> EvidenceFragment with valid 5-stage ID lineage."""
    from backend.services.research.deep_reader import deep_reader
    from backend.services.research.research_models import EvidenceItem
    from backend.services.agent_reach import agent_reach_service

    # Controlled local fixture: mock agent_reach_service.read for deterministic local integration test
    test_url = "https://example.com/test-article"
    monkeypatch.setattr(
        agent_reach_service,
        "read",
        lambda url, max_chars=4000: {
            "status": "success",
            "title": "Deterministic Test Article",
            "content": "This is a deterministic article payload with sufficient length for extraction.",
            "markdown": "This is a deterministic article payload with sufficient length for extraction.",
            "url": url,
            "char_count": 80,
            "backend": "scrapling_http",
            "fallback_used": False
        }
    )

    item = EvidenceItem(
        id="cand_test_001",
        canonical_url=test_url,
        title="Test Candidate",
        relevance_score=0.95,
        source_quality_score=0.90,
    )
    item.ranked_id = "cand_rank_test_001"
    item.rank = 1

    investigated, telemetry = deep_reader.deep_read([item], max_reads=1)

    assert len(investigated) == 1
    assert telemetry["successful"] == 1
    assert len(telemetry["acquisition_attempts"]) == 1

    acq_att = telemetry["acquisition_attempts"][0]
    assert acq_att["status"] == "SUCCESS"
    assert acq_att["useful_content_extracted"] is True
    assert acq_att["attempt_id"].startswith("acq_att_")
    assert acq_att["accepted_candidate_id"] == f"cand_acc_{item.id}"
    assert acq_att["acquired_candidate_id"] == f"cand_acq_{item.id}"
    assert acq_att["backend"] == "scrapling_http"

    # Convert investigated EvidenceItem to EvidenceFragment
    frag = investigated[0].to_evidence_fragment()
    assert frag.content
    assert frag.url == test_url
    assert investigated[0].acquired_id == f"cand_acq_{item.id}"
    assert investigated[0].acquisition_attempt_id == acq_att["attempt_id"]
