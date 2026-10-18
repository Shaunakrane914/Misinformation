import hashlib
import pytest
from scripts.evaluation.evaluate_research_quality import score


def inputs():
    text = "Captured source statement."
    rows = [{"case_id": "one", "verdict": "SUPPORTED", "sources": [{
        "evidence_id": "original", "url": "https://example.org/original", "content": text,
        "content_sha256": hashlib.sha256(text.encode()).hexdigest()}],
        "citations": [{"evidence_id": "original", "start": 0, "end": len(text), "text": text}]}]
    labels = {"label_origin": "AGENT_CALIBRATION", "cases": [{"case_id": "one",
              "verdict": "SUPPORTED", "relevant_urls": ["https://example.org/original"]}]}
    return rows, labels


def test_exact_spans_do_not_claim_entailment_or_independence():
    rows, labels = inputs()
    result = score(rows, labels)
    assert result["status"] == "CALIBRATION_ONLY_NOT_ACCEPTANCE"
    assert result["citation_span_validity"] == result["relevant_source_recall"] == 1
    assert result["citation_entailment"] == "NOT_VERIFIED_BY_SPAN_MATCH"


def test_incorrect_decisions_abstention_and_broken_citation_are_separate():
    rows, labels = inputs()
    rows[0]["verdict"] = "INSUFFICIENT_EVIDENCE"
    rows[0]["citations"][0]["evidence_id"] = "missing"
    result = score(rows, labels)
    assert result["correct_verdict_rate"] == result["abstention_precision"] == 0
    assert result["counts"]["incorrect_decisive_verdicts"] == 0
    assert result["citation_span_validity"] == 0
    rows[0]["verdict"] = "REFUTED"
    assert score(rows, labels)["counts"]["incorrect_decisive_verdicts"] == 1


def test_incomplete_cases_or_changed_source_bytes_are_rejected():
    rows, labels = inputs()
    with pytest.raises(ValueError):
        score([], labels)
    rows[0]["sources"][0]["content"] += "Changed."
    with pytest.raises(ValueError):
        score(rows, labels)


def test_unfilled_reviewer_packet_cannot_establish_acceptance():
    with pytest.raises(ValueError, match="No reviewed cases"):
        score([], {"label_origin": "INDEPENDENT_HUMAN_REVIEW", "reviewer": "reviewer", "frozen_at": "2026-10-18", "cases": []})


def test_terminal_capture_ignores_grouped_native_evidence_metadata():
    from scripts.audits.run_terminal_agent_quality import native_source_records
    assert native_source_records({"evidence": {"primary": []}, "sources": []}) == []
    assert native_source_records({"sources": [{"evidence_id": "canonical"}]}) == [{"evidence_id": "canonical"}]
