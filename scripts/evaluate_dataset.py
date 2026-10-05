"""
Aegis Protocol — Scientific Benchmark & Evaluation CLI
======================================================
Unified entry point for reproducible, leak-free evaluations across the taxonomy:
- classical_ml  : Supervised TF-IDF + L2 Logistic Regression on deduplicated held-out split
- reranker      : Supervised trained linear evidence reranker on held-out candidate pools
- llm_only      : Direct Gemini inference without evidence retrieval
- retrieval_llm : Live retrieval + single-prompt Gemini synthesis
- aegis         : Full multi-agent pipeline with source grouping & contradiction analysis
- ablation      : Component-wise ablation study
- india_track   : Multilingual gold evaluation (Research prototype: EN, HI, MR, Hinglish)
- averitec_status: Official AVeriTeC benchmark adapter status check
- all_offline   : Run all non-network offline ML benchmarks

SCIENTIFIC INTEGRITY GUARANTEES:
1. Ground truth is NEVER accessible during feature extraction, query generation, or inference.
2. In scientific mode, missing API keys or external services report 'BLOCKED'/'NOT RUN'
   rather than silently falling back to deterministic mock providers.
3. Offline regression tests using MockGeminiProvider are explicitly marked as 'OFFLINE REGRESSION'.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.evaluation.datasets.averitec import AVeriTeCDataset
from backend.evaluation.datasets.india_track import IndiaMultilingualTrack
from backend.evaluation.datasets.welfake import WelfakeDataset
from backend.evaluation.harness import EvaluationHarness

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aegis_eval")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aegis Protocol — Scientific Benchmark & Evaluation Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=[
            "classical_ml",
            "reranker",
            "llm_only",
            "retrieval_llm",
            "aegis",
            "ablation",
            "india_track",
            "averitec_status",
            "fever_status",
            "all_offline",
        ],
        default="classical_ml",
        help="Evaluation benchmark mode to run",
    )
    parser.add_argument(
        "--dataset",
        choices=["welfake", "india_track", "averitec"],
        default="welfake",
        help="Dataset to evaluate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for splits and bootstrapping",
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Allow MockGeminiProvider (STRICTLY for OFFLINE REGRESSION tests; invalid for scientific claims)",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=50,
        help="Optional ceiling on number of test samples to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/evaluation/results",
        help="Directory to save machine-readable JSON evaluation results",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Optional single target claim to run empirical verification on (CI compatibility)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="general",
        help="Domain classification context (general, financial, health)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 80)
    print("           AEGIS PROTOCOL - SCIENTIFIC BENCHMARK SUITE")
    print("=" * 80)

    # 0. CI Single Target Claim Verification Mode
    if args.target:
        print(f"\n[Aegis Benchmark] Targeted Claim Evaluation: \"{args.target}\"")
        from backend.agents.claim_ingestion_agent import get_claim_ingestion_agent
        from backend.agents.investigator_agent import get_investigator_agent
        from backend.agents.research_agent import ResearchAgent

        ingestion = get_claim_ingestion_agent()
        investigator = get_investigator_agent()
        research = ResearchAgent()

        claim_rec = ingestion.ingest(claim_text=args.target)
        norm_text = claim_rec.get("normalized_text", args.target)
        evidence_json = research.gather_evidence_structured(norm_text)
        raw_v = investigator.determine_verdict(claim_text=norm_text, evidence_json=evidence_json)
        verdict = investigator.extract_verdict(raw_v)
        print(f"  Target:     {args.target}")
        print(f"  Domain:     {args.domain}")
        print(f"  Verdict:    {verdict.get('verdict')}")
        print(f"  Confidence: {verdict.get('confidence')}")
        print(f"  Severity:   {verdict.get('severity')}")
        print("\nTargeted claim verification complete.")
        return

    # 1. Dataset Accounting & Audit
    if args.dataset == "welfake" or args.mode in ("classical_ml", "all_offline"):
        ds = WelfakeDataset(deduplicate=True)
        stats = ds.get_dataset_statistics()
        print("\n[DATASET AUDIT] WELFake Dataset Accounting (Content-Deduplicated):")
        print(f"  * File path:                  {stats['filepath']}")
        print(f"  * Raw rows:                   {stats['raw_rows']:,}")
        print(f"  * Clean usable rows:          {stats['clean_rows']:,}")
        print(f"  * Duplicate titles removed:   {stats['duplicate_titles_removed']:,}")
        print(f"  * Excluded rows (null/inv):   {stats['excluded_missing_or_invalid_rows']:,}")
        print(f"  * Class distribution:         Real (0) = {stats['class_distribution'].get(0, 0):,}, "
              f"Fake (1) = {stats['class_distribution'].get(1, 0):,}")
        print(f"  * Note:                       {stats['task_scope_note']}")

    harness = EvaluationHarness(output_dir=args.output_dir)

    # 2. Mode Execution
    if args.mode == "classical_ml":
        print("\n[RUNNING] Supervised Classical ML Baseline (TF-IDF + Logistic Regression on Deduplicated Split)...")
        res = harness.run_classical_ml_benchmark(seed=args.seed)
        test_metrics = res["results"]["test"]["metrics"]
        calib = res["results"]["test"]["calibration"]

        print("\n" + "=" * 80)
        print("          CLASSICAL ML BASELINE RESULTS (HELD-OUT TEST SET)")
        print("=" * 80)
        acc_ci = test_metrics.get("accuracy_95ci", [0.0, 0.0])
        f1_ci = test_metrics.get("macro_f1_95ci", [0.0, 0.0])
        print(f"  * Accuracy:        {test_metrics.get('accuracy', 0.0):.4f} "
              f"(95% CI: [{acc_ci[0]:.4f}, {acc_ci[1]:.4f}])")
        print(f"  * Macro-F1:        {test_metrics.get('macro_f1', 0.0):.4f} "
              f"(95% Bootstrap CI: [{f1_ci[0]:.4f}, {f1_ci[1]:.4f}])")
        print(f"  * Macro-Precision: {test_metrics.get('macro_precision', 0.0):.4f}")
        print(f"  * Macro-Recall:    {test_metrics.get('macro_recall', 0.0):.4f}")
        print(f"  * ECE:             {calib.get('ece', 0.0):.4f}")
        print(f"  * Brier Score:     {calib.get('brier_score', 0.0):.4f}")
        print(f"  * Test Samples:    {test_metrics.get('sample_count', 0):,}")
        print(f"  * Throughput:      {res['results']['test']['throughput_samples_per_sec']} samples/sec")
        git_short = res["git_commit"][:7]
        art_path = os.path.join(args.output_dir, f"welfake_classical_ml_{git_short}.json")
        print(f"  * Artifact:        {art_path}")
        print("=" * 80)

    elif args.mode == "reranker":
        print("\n[RUNNING] Supervised Evidence Reranker Benchmark (Trained on Train Pairs, Evaluated on Held-Out Queries)...")
        res = harness.run_reranker_benchmark(seed=args.seed)
        eval_data = res["reranker"]
        raw = eval_data["raw_retrieval"]
        reranked = eval_data["reranked_retrieval"]
        deltas = eval_data["deltas"]

        print("\n" + "=" * 80)
        print("          EVIDENCE RETRIEVAL: RAW VS TRAINED RERANKER (HELD-OUT)")
        print("=" * 80)
        print(f"  * MRR:             Raw = {raw['mrr']:.4f}  ->  Reranked = {reranked['mrr']:.4f}  (delta {deltas['mrr_delta']:+.4f})")
        print(f"  * Recall@1:        Raw = {raw['recall@1']:.4f}  ->  Reranked = {reranked['recall@1']:.4f}")
        print(f"  * Recall@5:        Raw = {raw['recall@5']:.4f}  ->  Reranked = {reranked['recall@5']:.4f}  (delta {deltas['recall_at_5_delta']:+.4f})")
        print(f"  * Recall@10:       Raw = {raw['recall@10']:.4f}  ->  Reranked = {reranked['recall@10']:.4f}  (delta {deltas['recall_at_10_delta']:+.4f})")
        print(f"  * Latency (p50):   {eval_data['performance']['latency_p50_ms']} ms")
        print(f"  * Model Footprint: {eval_data['performance']['memory_footprint_bytes']} bytes")
        print(f"  * Trained Pairs:   {res['training']['training_pairs_count']} pairs in {res['training']['train_time_sec']}s")
        rerank_short = res["git_commit"][:7]
        rerank_art = os.path.join(args.output_dir, f"reranker_benchmark_{rerank_short}.json")
        print(f"  * Artifact:        {rerank_art}")
        print("=" * 80)

    elif args.mode == "llm_only":
        print(f"\n[RUNNING] LLM-Only Benchmark on {args.dataset} (sample_limit={args.sample_limit})...")
        res = harness.run_llm_only_benchmark(
            dataset_name=args.dataset,
            sample_limit=args.sample_limit,
            seed=args.seed,
            allow_mock=args.allow_mock,
        )
        if res.get("status") == "BLOCKED":
            print(f"\n[BLOCKED] {res['reason']}")
            print("  Scientific benchmark requires real GEMINI_API_KEY. (Pass --allow-mock ONLY for OFFLINE REGRESSION testing).")
        else:
            print(f"\nCompleted {res['sample_count']} samples. Provider: {res['provider']}")
            m = res["metrics"]
            print(f"  * Accuracy: {m.get('accuracy', 0.0):.4f}")
            print(f"  * Macro-F1: {m.get('macro_f1', 0.0):.4f}")

    elif args.mode == "retrieval_llm":
        print("\n[RUNNING] Retrieval + LLM Benchmark...")
        res = harness.run_retrieval_llm_benchmark(
            dataset_name=args.dataset,
            sample_limit=args.sample_limit,
            seed=args.seed,
            allow_mock=args.allow_mock,
        )
        print(f"  * Status: {res.get('status')}")
        print(f"  * Reason: {res.get('reason')}")

    elif args.mode == "aegis":
        print("\n[RUNNING] Full Aegis Multi-Agent Pipeline Benchmark...")
        res = harness.run_aegis_benchmark(
            dataset_name=args.dataset,
            sample_limit=args.sample_limit,
            seed=args.seed,
            allow_mock=args.allow_mock,
        )
        print(f"  * Status: {res.get('status')}")
        print(f"  * Reason: {res.get('reason')}")

    elif args.mode == "ablation":
        print("\n[RUNNING] Component-Wise Ablation Study...")
        res = harness.run_ablation_study(
            dataset_name=args.dataset,
            sample_limit=args.sample_limit,
            seed=args.seed,
            allow_mock=args.allow_mock,
        )
        print(f"  * Status: {res.get('status')}")
        print(f"  * Reason: {res.get('reason')}")

    elif args.mode == "india_track":
        print("\n[RUNNING] India Multilingual Track Evaluation (Research Prototype Set)...")
        res = harness.run_india_multilingual_track(
            mode="llm_only",
            allow_mock=args.allow_mock,
            sample_limit=args.sample_limit,
        )
        if res.get("status") == "BLOCKED":
            print(f"\n[BLOCKED] {res['reason']}")
            print("  Scientific benchmark requires real GEMINI_API_KEY. (Pass --allow-mock ONLY for OFFLINE REGRESSION testing).")
        else:
            print(f"\nCompleted {res['sample_count']} samples. Provider: {res['provider']}")
            m = res["metrics"]
            print(f"  * Accuracy: {m.get('accuracy', 0.0):.4f}")
            print(f"  * Macro-F1: {m.get('macro_f1', 0.0):.4f}")

    elif args.mode == "averitec_status":
        print("\n[CHECKING] AVeriTeC Benchmark Adapter Status...")
        av = AVeriTeCDataset()
        status = av.get_status()
        print(f"  * Status:     {status['status']}")
        print(f"  * Reason:     {status['reason']}")
        print(f"  * Repository: {status['official_repository']}")
        print(f"  * Paper:      {status['paper']}")
        print(f"  * Protocol:   {status['official_protocol_summary']}")

    elif args.mode == "fever_status":
        print("\n[CHECKING] FEVER Benchmark Adapter Status...")
        from backend.evaluation.datasets.fever import FEVERAdapter
        fev = FEVERAdapter()
        status = fev.status()
        print(f"  * Status:     {status['status']}")
        print(f"  * Reason:     {status['reason']}")
        print(f"  * URL:        {status.get('official_url', 'https://fever.ai/')}")
        print(f"  * Paper:      {status.get('paper', '')}")
        print(f"  * Tasks:      {', '.join(status.get('task_decomposition', []))}")

    elif args.mode == "all_offline":
        print("\n[RUNNING] All Offline ML Benchmarks (Zero Network / Zero Mock)...")
        print("1/2: Classical ML (TF-IDF + Logistic Regression on Deduplicated WELFake)...")
        harness.run_classical_ml_benchmark(seed=args.seed)
        print("2/2: Supervised Evidence Reranker (Trained on Train Pairs, Evaluated on Held-Out Queries)...")
        harness.run_reranker_benchmark(seed=args.seed)
        print("\nOffline ML evaluation complete. Results written to docs/evaluation/results/.")


if __name__ == "__main__":
    main()
