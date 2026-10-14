"""Replay separately adjudicated short primary excerpts against claim intelligence.

This is a component holdout, not live retrieval, human annotation or an API E2E test.
Counterfactual controls are labeled as such. Do not tune on the resulting failures.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=False)
    root = args.engine_root.resolve()
    sys.path.insert(0, str(root))
    from backend.services.research.claim_intelligence import ClaimIntelligenceEngine
    from backend.services.research.research_models import AtomicClaim, EvidenceItem
    from backend.services.research.source_quality import SourceQualityEngine
    manifest = Path(__file__).resolve().parents[2] / "tests/evaluation/phase8_reference_holdout.json"
    raw = manifest.read_bytes()
    data = json.loads(raw)
    results = []
    for case in data["cases"]:
        ref = data["references"][case["reference"]]
        item = EvidenceItem(id=case["id"], title=ref["claim_context"], content=ref["passage"],
                            canonical_url=case.get("replace_url", ref["url"]), content_depth=case.get("depth", "DIRECT_CONTENT"))
        SourceQualityEngine().classify_and_score(item, case["entity"])
        claim = ClaimIntelligenceEngine().evaluate_claim(AtomicClaim(claim_id=case["id"], entity=case["entity"], claim_text=case["claim"]), [item])
        results.append({**case, "actual_verdict": claim.verdict, "confidence": claim.confidence,
                        "citations": claim.evidence_citations, "rationale": claim.rationale,
                        "reference_passage": ref["passage"], "retrieved_in_this_run": False,
                        "acceptable_safe_outcome": claim.verdict in case["expected"],
                        "truth_resolved": (case["truth_label"].startswith("TRUE") and claim.verdict == "SUPPORTED") or (case["truth_label"].startswith("FALSE") and claim.verdict == "REFUTED")})
    labeled = [r for r in results if r["truth_label"] != "NOT_ESTABLISHED"]
    payload = {"scope": data["scope"], "engine_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
               "dirty_source": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
               "manifest_sha256": hashlib.sha256(raw).hexdigest(), "cases": results,
               "safe_outcomes": sum(r["acceptable_safe_outcome"] for r in results), "case_count": len(results),
               "labeled_truth_cases": len(labeled), "truth_resolved": sum(r["truth_resolved"] for r in labeled),
               "false_positive_supports": sum(r["actual_verdict"] == "SUPPORTED" and r["truth_label"] in {"FALSE", "FALSE_AT_OBSERVATION", "NOT_ESTABLISHED"} for r in results),
               "precision": None, "recall": None, "population_accuracy": None,
               "limitations": "Small manually source-adjudicated component set; abstention is safe but not successful truth resolution. No human annotation, retrieval recall, speaker verification or prevalence estimates."}
    (args.output_root / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "cases"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
