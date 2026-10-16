"""
Aegis Protocol — Phase 9 Misinformation Benchmark Evaluation Runner
===================================================================
Evaluates claim understanding, evidence reasoning, and verdict accuracy
across the Phase 9 reference benchmark splits:
- dev_set.json (development / diagnostics)
- regression_set.json (regression prevention)
- held_out_set.json (independent held-out evaluation)

Computes:
- Verdict accuracy (exact match against expected verdicts)
- Truth resolution rate (correct SUPPORTED for TRUE, REFUTED for FALSE)
- Abstention metrics (correct vs incorrect abstentions)
- False positive rate (SUPPORTED on FALSE/INSUFFICIENT claims)
- False negative rate (REFUTED on TRUE/INSUFFICIENT claims)
- Entailment and contradiction identification accuracy
- Execution latency per case
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


def load_benchmark_split(benchmark_dir: Path, split_name: str) -> List[Dict[str, Any]]:
    """Load benchmark cases from specified split or combine all splits."""
    if split_name == "all":
        cases = []
        for s in ["dev", "regression", "held_out"]:
            f = benchmark_dir / f"{s}_set.json"
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8"))
                cases.extend(data.get("cases", data) if isinstance(data, dict) else data)
        return cases
    
    target_file = benchmark_dir / f"{split_name}_set.json"
    if not target_file.exists():
        raise FileNotFoundError(f"Benchmark split file not found: {target_file}")
    data = json.loads(target_file.read_text(encoding="utf-8"))
    return data.get("cases", data) if isinstance(data, dict) else data


def evaluate_benchmark_case(
    case: Dict[str, Any],
    claim_intel_engine: Any,
    source_quality_engine: Any,
    AtomicClaim: Any,
    EvidenceItem: Any,
) -> Dict[str, Any]:
    """Evaluates a single benchmark case against its adjudicated reference evidence."""
    t0 = time.perf_counter()
    ref = case["reference"]
    
    # Construct EvidenceItem with provided reference context
    evidence = EvidenceItem(
        id=f"ev_{case['id']}",
        title=ref.get("claim_context", case["claim"]),
        content=ref.get("passage", ""),
        canonical_url=ref.get("primary_url", "https://example.org/source"),
        content_depth="DIRECT_CONTENT" if ref.get("passage") else "DIRECT_METADATA",
        source_name=ref.get("claim_context", "Primary Reference"),
        primary_source=ref.get("source_role") in {"PRIMARY", "REGULATORY_FILING", "OFFICIAL_COMMUNICATION", "RESEARCH_REGISTRY"},
    )
    
    # Classify source quality
    source_quality_engine.classify_and_score(evidence, case.get("entity", ""))
    
    # Override tier/role if explicitly specified in benchmark ground truth
    if ref.get("source_tier"):
        evidence.source_tier = ref["source_tier"]
    if ref.get("source_role"):
        evidence.source_role = ref["source_role"]
    
    # Evaluate claim
    claim = AtomicClaim(
        claim_id=case["id"],
        entity=case.get("entity", ""),
        claim_text=case["claim"],
        claim_type=case.get("category", "ASSERTION"),
    )
    
    evaluated_claim = claim_intel_engine.evaluate_claim(claim, [evidence])
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    
    actual_verdict = evaluated_claim.verdict
    expected_verdicts = case["expected_verdicts"]
    truth_label = case["truth_label"]
    
    # Correctness metrics
    is_acceptable = actual_verdict in expected_verdicts
    
    is_truth_resolved = False
    if truth_label.startswith("TRUE") and actual_verdict == "SUPPORTED":
        is_truth_resolved = True
    elif truth_label.startswith("FALSE") and actual_verdict == "REFUTED":
        is_truth_resolved = True
    elif truth_label in {"PARTIALLY_TRUE", "MIXED"} and actual_verdict in {"MIXED", "PARTIAL"}:
        is_truth_resolved = True
    elif truth_label == "OUTDATED" and actual_verdict == "OUTDATED":
        is_truth_resolved = True
        
    is_abstention = actual_verdict in {"UNVERIFIED", "INSUFFICIENT_EVIDENCE"}
    expected_abstention = any(v in {"UNVERIFIED", "INSUFFICIENT_EVIDENCE"} for v in expected_verdicts)
    
    correct_abstention = is_abstention and expected_abstention
    incorrect_abstention = is_abstention and not expected_abstention
    
    false_positive = (actual_verdict == "SUPPORTED") and (
        truth_label.startswith("FALSE") or truth_label == "INSUFFICIENT_EVIDENCE" or "REFUTED" in expected_verdicts
    )
    false_negative = (actual_verdict == "REFUTED") and (
        truth_label.startswith("TRUE") or truth_label == "INSUFFICIENT_EVIDENCE" or "SUPPORTED" in expected_verdicts
    )
    
    # Entailment / Contradiction check
    entailment_aligned = False
    citation_valid = False
    if evaluated_claim.evidence_citations:
        citation_valid = True
        cit = evaluated_claim.evidence_citations[0]
        if actual_verdict == "SUPPORTED" and cit.get("relation") == "SUPPORT":
            entailment_aligned = True
        elif actual_verdict == "REFUTED" and cit.get("relation") == "CONTRADICT":
            entailment_aligned = True
            
    return {
        "id": case["id"],
        "category": case.get("category", ""),
        "domain": case.get("domain", ""),
        "claim": case["claim"],
        "entity": case.get("entity", ""),
        "truth_label": truth_label,
        "expected_verdicts": expected_verdicts,
        "actual_verdict": actual_verdict,
        "confidence": evaluated_claim.confidence,
        "rationale": evaluated_claim.rationale,
        "citations_count": len(evaluated_claim.evidence_citations),
        "citation_valid": citation_valid,
        "entailment_aligned": entailment_aligned,
        "is_acceptable": is_acceptable,
        "is_truth_resolved": is_truth_resolved,
        "is_abstention": is_abstention,
        "correct_abstention": correct_abstention,
        "incorrect_abstention": incorrect_abstention,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "elapsed_ms": elapsed_ms,
    }


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes comprehensive accuracy and epistemic metrics from evaluation results."""
    total = len(results)
    if total == 0:
        return {}
        
    acceptable_count = sum(r["is_acceptable"] for r in results)
    resolved_count = sum(r["is_truth_resolved"] for r in results)
    
    truth_eligible = [r for r in results if r["truth_label"] in {"TRUE", "FALSE", "PARTIALLY_TRUE", "OUTDATED"}]
    truth_eligible_count = len(truth_eligible)
    
    abstentions = sum(r["is_abstention"] for r in results)
    correct_abstentions = sum(r["correct_abstention"] for r in results)
    incorrect_abstentions = sum(r["incorrect_abstention"] for r in results)
    
    fp_count = sum(r["false_positive"] for r in results)
    fn_count = sum(r["false_negative"] for r in results)
    
    citation_valid_count = sum(r["citation_valid"] for r in results)
    entailment_aligned_count = sum(r["entailment_aligned"] for r in results)
    avg_latency = round(sum(r["elapsed_ms"] for r in results) / total, 2)
    
    # Calculate Precision, Recall, F1 for Definitive Claims (TRUE vs FALSE)
    true_cases = [r for r in results if r["truth_label"] == "TRUE"]
    false_cases = [r for r in results if r["truth_label"] == "FALSE"]
    
    tp = sum(r["actual_verdict"] == "SUPPORTED" for r in true_cases)
    fp = sum(r["actual_verdict"] == "SUPPORTED" for r in false_cases)
    fn = sum(r["actual_verdict"] != "SUPPORTED" for r in true_cases)
    
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    
    verdict_distribution: Dict[str, int] = {}
    for r in results:
        v = r["actual_verdict"]
        verdict_distribution[v] = verdict_distribution.get(v, 0) + 1
        
    return {
        "case_count": total,
        "acceptable_safe_outcomes": acceptable_count,
        "acceptable_rate": round(acceptable_count / total, 4),
        "truth_eligible_cases": truth_eligible_count,
        "truth_resolved_count": resolved_count,
        "truth_resolution_rate": round(resolved_count / truth_eligible_count, 4) if truth_eligible_count > 0 else 0.0,
        "total_abstentions": abstentions,
        "abstention_rate": round(abstentions / total, 4),
        "correct_abstentions": correct_abstentions,
        "incorrect_abstentions": incorrect_abstentions,
        "false_positives": fp_count,
        "false_negatives": fn_count,
        "precision_support": precision,
        "recall_support": recall,
        "f1_support": f1,
        "citation_valid_count": citation_valid_count,
        "entailment_aligned_count": entailment_aligned_count,
        "average_latency_ms": avg_latency,
        "verdict_distribution": verdict_distribution,
    }


def generate_markdown_report(metrics: Dict[str, Any], split_name: str, results: List[Dict[str, Any]]) -> str:
    """Renders a clean GitHub-flavored markdown report summarizing benchmark results."""
    lines = [
        f"# Phase 9 Misinformation Benchmark Evaluation Report — Split: `{split_name.upper()}`",
        "",
        f"**Evaluated Cases:** {metrics['case_count']} | **Acceptable Rate:** {metrics['acceptable_rate'] * 100:.1f}% | **Truth Resolution Rate:** {metrics['truth_resolution_rate'] * 100:.1f}%",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value | Description |",
        "| :--- | :--- | :--- |",
        f"| **Total Cases** | `{metrics['case_count']}` | Number of verified reference cases evaluated |",
        f"| **Acceptable Safe Outcomes** | `{metrics['acceptable_safe_outcomes']} / {metrics['case_count']}` ({metrics['acceptable_rate'] * 100:.1f}%) | Actual verdict is within expected ground truth |",
        f"| **Truth Resolved Cases** | `{metrics['truth_resolved_count']} / {metrics['truth_eligible_cases']}` ({metrics['truth_resolution_rate'] * 100:.1f}%) | Definite factual claims correctly resolved (SUPPORTED/REFUTED) |",
        f"| **Abstention Rate** | `{metrics['total_abstentions']} / {metrics['case_count']}` ({metrics['abstention_rate'] * 100:.1f}%) | Proportion of claims returned as UNVERIFIED or INSUFFICIENT |",
        f"| **Correct Abstentions** | `{metrics['correct_abstentions']}` | Ground-truth uncertain/insufficient cases correctly abstained |",
        f"| **Incorrect Abstentions** | `{metrics['incorrect_abstentions']}` | Resolvable claims where system failed to reach a verdict |",
        f"| **False Positives** | `{metrics['false_positives']}` | False/insufficient claims incorrectly labeled SUPPORTED |",
        f"| **False Negatives** | `{metrics['false_negatives']}` | True/insufficient claims incorrectly labeled REFUTED |",
        f"| **Precision (SUPPORT)** | `{metrics['precision_support']}` | TP / (TP + FP) for affirmative verdicts |",
        f"| **Recall (SUPPORT)** | `{metrics['recall_support']}` | TP / (TP + FN) for affirmative verdicts |",
        f"| **F1 Score** | `{metrics['f1_support']}` | Harmonic mean of precision and recall |",
        f"| **Average Latency** | `{metrics['average_latency_ms']} ms` | Mean evaluation latency per case |",
        "",
        "## Verdict Distribution",
        "",
        "| Verdict | Count | Share |",
        "| :--- | :--- | :--- |",
    ]
    for v, c in sorted(metrics["verdict_distribution"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{v}` | `{c}` | {c / metrics['case_count'] * 100:.1f}% |")
        
    lines.extend([
        "",
        "## Case-by-Case Breakdown (Failures & Non-Resolutions)",
        "",
        "| Case ID | Category | Truth Label | Expected | Actual | Rationale |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for r in results:
        if not r["is_truth_resolved"] and not r["correct_abstention"]:
            exp = ", ".join(r["expected_verdicts"])
            lines.append(f"| `{r['id']}` | {r['category']} | `{r['truth_label']}` | `{exp}` | **`{r['actual_verdict']}`** | {r['rationale'][:80]}... |")
            
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=Path(__file__).resolve().parents[2] / "tests/evaluation/phase9_benchmark")
    parser.add_argument("--split", choices=["dev", "regression", "held_out", "all"], default="dev")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "artifacts/phase9_evaluation")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    
    from backend.services.research.claim_intelligence import ClaimIntelligenceEngine
    from backend.services.research.source_quality import SourceQualityEngine
    from backend.services.research.research_models import AtomicClaim, EvidenceItem
    
    claim_intel = ClaimIntelligenceEngine()
    source_quality = SourceQualityEngine()
    
    cases = load_benchmark_split(args.benchmark_dir, args.split)
    print(f"Running Phase 9 Benchmark Evaluation on split: {args.split} ({len(cases)} cases)...")
    
    results = [
        evaluate_benchmark_case(c, claim_intel, source_quality, AtomicClaim, EvidenceItem)
        for c in cases
    ]
    
    metrics = compute_metrics(results)
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.output_dir / f"benchmark_{args.split}_results.json"
    out_md = args.output_dir / f"benchmark_{args.split}_report.md"
    
    payload = {
        "split": args.split,
        "engine_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "dirty_source": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
        "metrics": metrics,
        "results": results,
    }
    
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_md = generate_markdown_report(metrics, args.split, results)
    out_md.write_text(report_md, encoding="utf-8")
    
    print("\n" + report_md)
    print(f"\nArtifacts saved to:\n  {out_json}\n  {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
