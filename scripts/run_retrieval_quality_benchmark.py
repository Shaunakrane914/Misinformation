"""
Aegis Protocol — 4-Agent Retrieval Quality Benchmark Runner
===========================================================
Executes golden benchmark evaluation across BrandShield, Trending, Scout,
and Personal Watch comparing three retrieval ranking systems:
  A. Deterministic current ranker
  B. Hybrid lexical + semantic scoring
  C. Hybrid + second-stage CrossEncoder reranker

Outputs comprehensive artifacts into artifacts/retrieval_benchmark/:
- summary.json & summary.md
- per_agent.json
- per_scenario.jsonl
- rankings.jsonl
- failures.jsonl
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.research.entity_resolver import entity_resolver
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.semantic_reranker import SemanticReranker
from backend.services.research.retrieval_metrics import (
    evaluate_ranking_run,
    aggregate_metrics,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RetrievalBenchmark")


class BenchmarkRunner:
    def __init__(
        self,
        fixtures_dir: Path = Path("tests/retrieval_benchmark"),
        output_dir: Path = Path("artifacts/retrieval_benchmark"),
        top_k: int = 5,
        live_mode: bool = False,
    ):
        self.fixtures_dir = fixtures_dir
        self.output_dir = output_dir
        self.top_k = top_k
        self.live_mode = live_mode

        self.scenarios: List[Dict[str, Any]] = []
        self.candidates: List[Dict[str, Any]] = []
        self.labels: List[Dict[str, Any]] = []
        self.candidates_by_scenario: Dict[str, List[Dict[str, Any]]] = {}
        self.labels_by_cand_id: Dict[str, Dict[str, Any]] = {}

        self.reranker = SemanticReranker(enabled=True, device="cpu")

    def load_fixtures(self):
        scenarios_file = self.fixtures_dir / "scenarios.jsonl"
        candidates_file = self.fixtures_dir / "candidates.jsonl"
        labels_file = self.fixtures_dir / "labels.jsonl"

        if not scenarios_file.exists() or not candidates_file.exists() or not labels_file.exists():
            raise FileNotFoundError(f"Benchmark fixtures not found in {self.fixtures_dir}")

        with open(scenarios_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.scenarios.append(json.loads(line))

        with open(candidates_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    c = json.loads(line)
                    self.candidates.append(c)
                    self.candidates_by_scenario.setdefault(c["scenario_id"], []).append(c)

        with open(labels_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    lb = json.loads(line)
                    self.labels.append(lb)
                    self.labels_by_cand_id[lb["candidate_id"]] = lb

        logger.info(
            "Loaded %d scenarios, %d candidates, %d gold labels",
            len(self.scenarios),
            len(self.candidates),
            len(self.labels),
        )

    def _prepare_candidate_features(self, scenario: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Compute orthogonal entity, intent, source quality, and first-stage scores."""
        query = scenario["query"]
        agent = scenario["agent"]
        target_entity = scenario["expected_entity"]["canonical"]

        domain_map = {
            "brandshield": "brand",
            "trending": "trending",
            "scout": "financial",
            "personal_watch": "personal",
        }
        domain = domain_map.get(agent, "general")

        assessment = relevance_gate.evaluate_item(
            candidate,
            target_entity=target_entity,
            domain=domain,
            intent=scenario.get("expected_intent", ""),
        )

        cand_copy = dict(candidate)
        cand_copy["entity_score"] = assessment.entity_score
        cand_copy["intent_score"] = assessment.intent_score
        cand_copy["source_quality_score"] = assessment.source_quality_score
        cand_copy["relevance_score"] = assessment.relevance_score
        cand_copy["relevance_class"] = assessment.relevance_class
        cand_copy["is_accepted"] = assessment.is_accepted
        cand_copy["first_stage_score"] = assessment.relevance_score
        return cand_copy

    def rank_deterministic(self, scenario: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """System A: Deterministic current ranker."""
        features = [self._prepare_candidate_features(scenario, c) for c in candidates]
        # Sort descending by relevance_score
        sorted_cands = sorted(
            features,
            key=lambda x: (x.get("relevance_score", 0.0), x.get("entity_score", 0.0)),
            reverse=True,
        )
        for idx, c in enumerate(sorted_cands, 1):
            c["rank"] = idx
            c["final_score"] = c.get("relevance_score", 0.0)
            c["semantic_score"] = None
        return sorted_cands[: self.top_k]

    def rank_hybrid(self, scenario: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """System B: Hybrid lexical + semantic scoring."""
        features = [self._prepare_candidate_features(scenario, c) for c in candidates]
        query = scenario["query"]

        pairs = [
            (query, f"{c.get('title', '')}. {c.get('snippet', '')}".strip())
            for c in features
        ]
        semantic_scores = self.reranker.score_text_pairs(pairs)

        for idx, c in enumerate(features):
            sem = semantic_scores[idx]["semantic_score"] if idx < len(semantic_scores) else 0.0
            c["semantic_score"] = sem
            c["raw_cross_encoder_score"] = semantic_scores[idx]["raw_score"] if idx < len(semantic_scores) else 0.0

            # Single-stage hybrid blend
            ent = c.get("entity_score", 0.50)
            intent = c.get("intent_score", 0.50)
            sq = c.get("source_quality_score", 0.50)

            # If entity fails completely, suppress score
            if ent < 0.35:
                hybrid = (0.30 * ent + 0.20 * intent + 0.10 * sq + 0.40 * sem) * 0.15
            else:
                hybrid = 0.30 * ent + 0.20 * intent + 0.10 * sq + 0.40 * sem

            c["final_score"] = round(hybrid, 4)

        sorted_cands = sorted(features, key=lambda x: x.get("final_score", 0.0), reverse=True)
        for idx, c in enumerate(sorted_cands, 1):
            c["rank"] = idx
        return sorted_cands[: self.top_k]

    def rank_reranker(self, scenario: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """System C: Hybrid + second-stage CrossEncoder reranker."""
        features = [self._prepare_candidate_features(scenario, c) for c in candidates]
        query = scenario["query"]

        # Run through semantic reranker
        reranked = self.reranker.rerank(
            query=query,
            candidates=features,
            top_k=self.top_k,
            entity_score_threshold=0.35,
        )
        for idx, c in enumerate(reranked, 1):
            c["rank"] = idx
            c["final_score"] = c.get("rerank_score", c.get("relevance_score", 0.0))
        return reranked

    def evaluate_scenario(
        self,
        system_name: str,
        scenario: Dict[str, Any],
        ranked_candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute metrics for one scenario ranking."""
        all_cands = self.candidates_by_scenario.get(scenario["scenario_id"], [])
        target_canonical = scenario["expected_entity"]["canonical"]
        target_intent = scenario["expected_intent"]

        res = evaluate_ranking_run(
            ranked_candidates=ranked_candidates,
            all_candidates=all_cands,
            labels_by_cand_id=self.labels_by_cand_id,
            target_canonical=target_canonical,
            target_intent=target_intent,
            top_k=self.top_k,
        )
        res["scenario_id"] = scenario["scenario_id"]
        res["agent"] = scenario["agent"]
        res["split"] = scenario.get("split", "dev")
        res["classification"] = scenario.get("classification")
        res["system"] = system_name
        return res

    def classify_failure(
        self,
        scenario: Dict[str, Any],
        ranked_candidates: List[Dict[str, Any]],
        eval_metrics: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Identify and classify failures for low-precision or hard negative leaking cases."""
        if eval_metrics["p_at_1"] >= 1.0 and eval_metrics["false_positive_rate"] == 0:
            return None  # Success

        top1 = ranked_candidates[0] if ranked_candidates else {}
        top1_cid = top1.get("candidate_id")
        top1_label = self.labels_by_cand_id.get(top1_cid, {})
        top1_grade = top1_label.get("gold_grade", 0)

        failure_class = "OTHER"
        if eval_metrics["hard_neg_leak_at_1"] > 0 or top1_grade == 0:
            failure_class = "HARD_NEGATIVE_LEAK"
        elif eval_metrics["entity_accuracy"] < 0.50:
            failure_class = "WRONG_ENTITY"
        elif eval_metrics["intent_accuracy"] < 0.50:
            failure_class = "WRONG_INTENT"
        elif scenario.get("classification") == "TEMPORAL_NEGATIVE":
            failure_class = "STALE_RESULT"
        elif scenario.get("classification") == "DEDUPLICATION":
            failure_class = "DUPLICATE"
        else:
            failure_class = "WRONG_RANK"

        return {
            "scenario_id": scenario["scenario_id"],
            "query": scenario["query"],
            "agent": scenario["agent"],
            "system": eval_metrics["system"],
            "failure_class": failure_class,
            "expected_decision": scenario.get("expected_decision"),
            "expected_entity": scenario["expected_entity"]["canonical"],
            "expected_intent": scenario.get("expected_intent"),
            "top1_candidate_id": top1_cid,
            "top1_title": top1.get("title", ""),
            "top1_gold_grade": top1_grade,
            "top1_gold_reason": top1_label.get("gold_reason", ""),
            "p_at_1": eval_metrics["p_at_1"],
            "p_at_5": eval_metrics["p_at_5"],
            "ndcg_at_5": eval_metrics["ndcg_at_5"],
            "scores": {
                "entity": top1.get("entity_score"),
                "intent": top1.get("intent_score"),
                "semantic": top1.get("semantic_score"),
                "source": top1.get("source_quality_score"),
                "final": top1.get("final_score"),
            },
        }

    def run_benchmark(
        self,
        agent_filter: str = "all",
        system_filter: str = "all",
    ) -> Dict[str, Any]:
        self.load_fixtures()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        scenarios_to_run = self.scenarios
        if agent_filter != "all":
            scenarios_to_run = [s for s in scenarios_to_run if s["agent"].lower() == agent_filter.lower()]

        systems_to_run = ["deterministic", "hybrid", "reranker"]
        if system_filter != "all":
            systems_to_run = [s for s in systems_to_run if s.lower() == system_filter.lower()]

        all_results: Dict[str, List[Dict[str, Any]]] = {sys: [] for sys in systems_to_run}
        all_failures: List[Dict[str, Any]] = []
        all_rankings: List[Dict[str, Any]] = []

        logger.info(
            "Executing benchmark across %d scenarios and systems %s...",
            len(scenarios_to_run),
            systems_to_run,
        )

        for s in scenarios_to_run:
            cands = self.candidates_by_scenario.get(s["scenario_id"], [])

            for sys_name in systems_to_run:
                if sys_name == "deterministic":
                    ranked = self.rank_deterministic(s, cands)
                elif sys_name == "hybrid":
                    ranked = self.rank_hybrid(s, cands)
                else:  # reranker
                    ranked = self.rank_reranker(s, cands)

                eval_res = self.evaluate_scenario(sys_name, s, ranked)
                all_results[sys_name].append(eval_res)

                # Record ranking details
                all_rankings.append({
                    "scenario_id": s["scenario_id"],
                    "system": sys_name,
                    "agent": s["agent"],
                    "split": s.get("split", "dev"),
                    "ranked_candidates": [
                        {
                            "rank": c.get("rank"),
                            "candidate_id": c.get("candidate_id"),
                            "title": c.get("title"),
                            "final_score": c.get("final_score"),
                            "entity_score": c.get("entity_score"),
                            "intent_score": c.get("intent_score"),
                            "semantic_score": c.get("semantic_score"),
                            "gold_grade": self.labels_by_cand_id.get(c.get("candidate_id"), {}).get("gold_grade"),
                        }
                        for c in ranked
                    ],
                })

                # Check failure
                failure = self.classify_failure(s, ranked, eval_res)
                if failure:
                    all_failures.append(failure)

        # Aggregate metrics across systems, agents, and splits
        summary: Dict[str, Any] = {}
        per_agent_summary: Dict[str, Any] = {}

        for sys_name in systems_to_run:
            res_list = all_results[sys_name]
            overall = aggregate_metrics(res_list)
            dev_metrics = aggregate_metrics([r for r in res_list if r.get("split") == "dev"])
            holdout_metrics = aggregate_metrics([r for r in res_list if r.get("split") == "holdout"])

            summary[sys_name] = {
                "overall": overall,
                "dev": dev_metrics,
                "holdout": holdout_metrics,
            }

            per_agent_summary[sys_name] = {}
            for agent in ["brandshield", "trending", "scout", "personal_watch"]:
                ag_res = [r for r in res_list if r["agent"].lower() == agent.lower()]
                per_agent_summary[sys_name][agent] = aggregate_metrics(ag_res)

        # Save artifacts
        with open(self.output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        with open(self.output_dir / "per_agent.json", "w", encoding="utf-8") as f:
            json.dump(per_agent_summary, f, indent=2)

        with open(self.output_dir / "per_scenario.jsonl", "w", encoding="utf-8") as f:
            for sys_name, res_list in all_results.items():
                for r in res_list:
                    f.write(json.dumps(r) + "\n")

        with open(self.output_dir / "rankings.jsonl", "w", encoding="utf-8") as f:
            for r in all_rankings:
                f.write(json.dumps(r) + "\n")

        with open(self.output_dir / "failures.jsonl", "w", encoding="utf-8") as f:
            for fl in all_failures:
                f.write(json.dumps(fl) + "\n")

        # Generate markdown summary
        self._write_markdown_summary(summary, per_agent_summary)

        logger.info("Benchmark complete. Artifacts saved to %s", self.output_dir)
        return summary

    def _write_markdown_summary(self, summary: Dict[str, Any], per_agent: Dict[str, Any]):
        lines = []
        lines.append("# Aegis Protocol — Retrieval Quality Benchmark Summary")
        lines.append("")
        lines.append(f"**Total Scenarios Evaluated:** `{len(self.scenarios)}`")
        lines.append(f"**Total Evaluated Candidates:** `{len(self.candidates)}`")
        lines.append(f"**Top-k Rank Cutoff:** `{self.top_k}`")
        lines.append("")
        lines.append("## 1. System Comparison Matrix (Overall)")
        lines.append("")
        lines.append("| Metric | Deterministic Baseline | Hybrid Scoring | Neural Reranker | Reranker vs Baseline Delta |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")

        det = summary.get("deterministic", {}).get("overall", {})
        hyb = summary.get("hybrid", {}).get("overall", {})
        rer = summary.get("reranker", {}).get("overall", {})

        metrics_display = [
            ("Precision@1", "p_at_1", True),
            ("Precision@3", "p_at_3", True),
            ("Precision@5", "p_at_5", True),
            ("Recall@5", "recall_at_5", True),
            ("MRR", "mrr", True),
            ("nDCG@5", "ndcg_at_5", True),
            ("Entity Accuracy", "entity_accuracy", True),
            ("Intent Accuracy", "intent_accuracy", True),
            ("False-Positive Rate", "false_positive_rate", False),
            ("Ambiguous Rate", "ambiguous_rate", False),
            ("Hard-Negative Rejection", "hard_negative_rejection_rate", True),
        ]

        for label, key, higher_better in metrics_display:
            d_val = det.get(key, 0.0)
            h_val = hyb.get(key, 0.0)
            r_val = rer.get(key, 0.0)
            delta = r_val - d_val
            sign = "+" if delta > 0 else ""
            delta_str = f"{sign}{delta * 100:.1f}%" if "rate" in key or "acc" in key or "p_" in key else f"{sign}{delta:.3f}"
            lines.append(f"| **{label}** | {d_val * 100:.1f}% | {h_val * 100:.1f}% | {r_val * 100:.1f}% | **{delta_str}** |")

        lines.append("")
        lines.append("## 2. Development vs. Holdout Generalization")
        lines.append("")
        lines.append("| Metric | Dev (Deterministic) | Dev (Reranker) | Holdout (Deterministic) | Holdout (Reranker) |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")

        d_dev = summary.get("deterministic", {}).get("dev", {})
        d_hld = summary.get("deterministic", {}).get("holdout", {})
        r_dev = summary.get("reranker", {}).get("dev", {})
        r_hld = summary.get("reranker", {}).get("holdout", {})

        for label, key, _ in [("P@5", "p_at_5", True), ("MRR", "mrr", True), ("nDCG@5", "ndcg_at_5", True), ("Entity Acc", "entity_accuracy", True), ("FP Rate", "false_positive_rate", False)]:
            lines.append(
                f"| **{label}** | {d_dev.get(key, 0.0)*100:.1f}% | {r_dev.get(key, 0.0)*100:.1f}% | {d_hld.get(key, 0.0)*100:.1f}% | {r_hld.get(key, 0.0)*100:.1f}% |"
            )

        lines.append("")
        lines.append("## 3. Per-Agent Performance Breakdown (Neural Reranker)")
        lines.append("")
        lines.append("| Agent | P@1 | P@5 | MRR | nDCG@5 | Entity Acc | Intent Acc | FP Rate | Hard-Neg Rejection |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

        for ag in ["brandshield", "trending", "scout", "personal_watch"]:
            m = per_agent.get("reranker", {}).get(ag, {})
            lines.append(
                f"| **{ag.title()}** | {m.get('p_at_1', 0.0)*100:.1f}% | {m.get('p_at_5', 0.0)*100:.1f}% | {m.get('mrr', 0.0)*100:.1f}% | {m.get('ndcg_at_5', 0.0)*100:.1f}% | {m.get('entity_accuracy', 0.0)*100:.1f}% | {m.get('intent_accuracy', 0.0)*100:.1f}% | {m.get('false_positive_rate', 0.0)*100:.1f}% | {m.get('hard_negative_rejection_rate', 0.0)*100:.1f}% |"
            )

        with open(self.output_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run Aegis Retrieval Quality Benchmark")
    parser.add_argument("--agent", default="all", choices=["all", "brandshield", "trending", "scout", "personal_watch"])
    parser.add_argument("--system", default="all", choices=["all", "deterministic", "hybrid", "reranker"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--fixtures", default="tests/retrieval_benchmark")
    parser.add_argument("--output", default="artifacts/retrieval_benchmark")
    parser.add_argument("--live", action="store_true", help="Run against live web/search sources")

    args = parser.parse_args()
    runner = BenchmarkRunner(
        fixtures_dir=Path(args.fixtures),
        output_dir=Path(args.output),
        top_k=args.top_k,
        live_mode=args.live,
    )
    runner.run_benchmark(agent_filter=args.agent, system_filter=args.system)


if __name__ == "__main__":
    main()
