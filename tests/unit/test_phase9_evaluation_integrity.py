"""Evaluation semantics, not population accuracy or externally verified labels."""
from types import SimpleNamespace

from scripts.evaluation.run_phase9_benchmark import compute_metrics, evaluate_benchmark_case
from backend.services.research.research_models import AtomicClaim, EvidenceItem


def test_abstention_on_true_claim_counts_as_false_negative_not_correct_abstention():
    def abstain(claim, evidence):
        claim.verdict = "UNVERIFIED"
        return claim
    engine = SimpleNamespace(evaluate_claim=abstain)
    quality = SimpleNamespace(classify_and_score=lambda *args: None)
    case = {"id": "synthetic", "entity": "Example", "claim": "Example released a widget.",
            "truth_label": "TRUE", "expected_verdicts": ["SUPPORTED", "UNVERIFIED"],
            "reference": {"primary_url": "https://example.org/record", "passage": "Example released a widget.",
                          "source_tier": "TIER_1_OFFICIAL_FILING", "source_role": "PRIMARY"}}
    result = evaluate_benchmark_case(case, engine, quality, AtomicClaim, EvidenceItem)
    assert result["false_negative"] and result["incorrect_abstention"]
    assert not result["correct_abstention"]
    assert result["permitted_abstention"]
    assert result["source_retrieved_during_evaluation"] is False
    metrics = compute_metrics([result])
    assert metrics["precision_support"] is None
    assert metrics["recall_support"] == 0
    assert metrics["entailment_accuracy"] is None


def test_nonempty_but_fabricated_citation_is_not_valid_and_reference_tier_not_injected():
    def evaluate(claim, evidence):
        assert evidence[0].source_tier != "ORACLE_ONLY"
        claim.evidence_citations = [{"evidence_id": "invented", "canonical_url": "https://example.org/record",
                                    "relevant_excerpt": "invented passage", "relation": "SUPPORT"}]
        return claim
    case = {"id": "synthetic", "claim": "Example released a widget.", "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"], "reference": {"primary_url": "https://example.org/record",
            "passage": "Example released a widget.", "source_tier": "ORACLE_ONLY"}}
    result = evaluate_benchmark_case(case, SimpleNamespace(evaluate_claim=evaluate),
                                    SimpleNamespace(classify_and_score=lambda *args: None), AtomicClaim, EvidenceItem)
    assert not result["citation_valid"]
