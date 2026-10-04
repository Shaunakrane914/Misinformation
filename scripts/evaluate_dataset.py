"""
Aegis Protocol — Scientific Benchmark & Evaluation CLI
======================================================
Unified entry point for reproducible, leak-free evaluations across the taxonomy:
- classical_ml  : Supervised TF-IDF + L2 Logistic Regression on held-out test split
- reranker      : Learned evidence reranker vs raw retrieval on multi-candidate pools
- llm_only      : Direct Gemini inference without evidence retrieval
- india_track   : Multilingual gold evaluation (Hindi, Marathi, Hinglish, English)
- ablation      : Multi-stage component ablation study

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
        choices=["classical_ml", "reranker", "llm_only", "india_track", "averitec_status", "all_offline"],
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
        default=None,
        help="Optional ceiling on number of test samples to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/evaluation/results",
        help="Directory to save machine-readable JSON evaluation results",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 80)
    print("           AEGIS PROTOCOL — SCIENTIFIC BENCHMARK SUITE")
    print("=" * 80)

    # 1. Dataset Accounting & Audit
    if args.dataset == "welfake" or args.mode in ("classical_ml", "all_offline"):
        ds = WelfakeDataset()
        stats = ds.get_dataset_statistics()
        print("\n[DATASET AUDIT] WELFake Dataset Accounting:")
        print(f"  • File path:            {stats['filepath']}")
        print(f"  • Raw rows:             {stats['raw_rows']:,}")
        print(f"  • Clean usable rows:    {stats['clean_rows']:,}")
        print(f"  • Excluded rows (null): {stats['excluded_missing_or_invalid_rows']:,}")
        print(f"  • Duplicate titles:     {stats['duplicate_titles']:,}")
        print(f"  • Class distribution:   Real (0) = {stats['class_distribution'].get(0, 0):,}, "
              f"Fake (1) = {stats['class_distribution'].get(1, 0):,}")
        print(f"  • Note:                 {stats['task_scope_note']}")

    harness = EvaluationHarness(output_dir=args.output_dir)

    # 2. Mode Execution
    if args.mode == "classical_ml":
        print("\n[RUNNING] Supervised Classical ML Baseline (TF-IDF + Logistic Regression)...")
        res = harness.run_classical_ml_benchmark(seed=args.seed)
        test_metrics = res["results"]["test"]["metrics"]
        calib = res["results"]["test"]["calibration"]

        print("\n" + "=" * 80)
        print("          CLASSICAL ML BASELINE RESULTS (HELD-OUT TEST SET)")
        print("=" * 80)
        acc_ci = test_metrics.get("accuracy_95ci", [0.0, 0.0])
        f1_ci = test_metrics.get("macro_f1_95ci", [0.0, 0.0])
        print(f"  • Accuracy:        {test_metrics.get('accuracy', 0.0):.4f} "
              f"(95% CI: [{acc_ci[0]:.4f}, {acc_ci[1]:.4f}])")
        print(f"  • Macro-F1:        {test_metrics.get('macro_f1', 0.0):.4f} "
              f"(95% Bootstrap CI: [{f1_ci[0]:.4f}, {f1_ci[1]:.4f}])")
        print(f"  • Macro-Precision: {test_metrics.get('macro_precision', 0.0):.4f}")
        print(f"  • Macro-Recall:    {test_metrics.get('macro_recall', 0.0):.4f}")
        print(f"  • ECE:             {calib.get('ece', 0.0):.4f}")
        print(f"  • Brier Score:     {calib.get('brier_score', 0.0):.4f}")
        print(f"  • Test Samples:    {test_metrics.get('sample_count', 0):,}")
        print(f"  • Throughput:      {res['results']['test']['throughput_samples_per_sec']} samples/sec")

        git_short = res["git_commit"][:7]
        art_path = os.path.join(args.output_dir, f"welfake_classical_ml_{git_short}.json")
        print(f"  • Artifact:        {art_path}")
        print("=" * 80)

    elif args.mode == "reranker":
        print("\n[RUNNING] Learned Evidence Reranker Benchmark...")
        res = harness.run_reranker_benchmark(seed=args.seed)
        eval_data = res["reranker"]
        raw = eval_data["raw_retrieval"]
        reranked = eval_data["reranked_retrieval"]
        deltas = eval_data["deltas"]

        print("\n" + "=" * 80)
        print("          EVIDENCE RETRIEVAL: RAW VS LEARNED RERANKER")
        print("=" * 80)
        print(f"  * MRR:             Raw = {raw['mrr']:.4f}  ->  Reranked = {reranked['mrr']:.4f}  (delta {deltas['mrr_delta']:+.4f})")
        print(f"  * Recall@5:        Raw = {raw['recall@5']:.4f}  ->  Reranked = {reranked['recall@5']:.4f}  (delta {deltas['recall_at_5_delta']:+.4f})")
        print(f"  * Recall@10:       Raw = {raw['recall@10']:.4f}  ->  Reranked = {reranked['recall@10']:.4f}  (delta {deltas['recall_at_10_delta']:+.4f})")
        print(f"  * Latency (p50):   {eval_data['performance']['latency_p50_ms']} ms")
        print(f"  * Model Footprint: {eval_data['performance']['memory_footprint_bytes']} bytes (sub-kilobyte)")


        rerank_short = res["git_commit"][:7]
        rerank_art = os.path.join(args.output_dir, f"reranker_benchmark_{rerank_short}.json")
        print(f"  • Artifact:        {rerank_art}")
        print("=" * 80)

    elif args.mode == "india_track":
        print("\n[RUNNING] India Multilingual Track Evaluation...")
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
            print(f"  • Accuracy: {m['accuracy']:.4f}")
            print(f"  • Macro-F1: {m['macro_f1']:.4f}")

    elif args.mode == "averitec_status":
        print("\n[CHECKING] AVeriTeC Benchmark Adapter Status...")
        av = AVeriTeCDataset()
        status = av.get_status()
        print(f"  • Status:     {status['status']}")
        print(f"  • Reason:     {status['reason']}")
        print(f"  • Repository: {status['official_repository']}")
        print(f"  • Paper:      {status['paper']}")
        print(f"  • Protocol:   {status['official_protocol_summary']}")

    elif args.mode == "all_offline":
        print("\n[RUNNING] All Offline ML Benchmarks (Zero Network / Zero Mock)...")
        print("1/2: Classical ML (TF-IDF + Logistic Regression on WELFake)...")
        harness.run_classical_ml_benchmark(seed=args.seed)
        print("2/2: Learned Evidence Reranker...")
        harness.run_reranker_benchmark(seed=args.seed)
        print("\nOffline ML evaluation complete. Results written to docs/evaluation/results/.")


if __name__ == "__main__":
    main()
