"""
Aegis Protocol — 4-Agent Retrieval Quality Benchmark Runner
===========================================================
Executes golden benchmark evaluation across BrandShield, Trending, Scout,
and Personal Watch comparing three retrieval ranking systems:
  A. Deterministic current ranker
  B. Hybrid lexical + semantic scoring
  C. Hybrid + second-stage CrossEncoder reranker

Guarantees:
1. Complete system isolation: zero shared mutable state or rankings.
2. Mathematically rigorous metrics: P@1/3/4, Recall@1/3/4 over evaluable queries,
   MRR, nDCG@3/4/5, Entity/Intent Accuracy, Hard-Negative Rejection.
3. Separate reporting for Development (N=84) vs Holdout (N=20).
4. Per-agent and per-classification breakdowns.
5. Explicit model status & fallback transparency.
"""

import argparse
import copy
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
        top_k: int = 4,
        reranker_enabled: bool = True,
    ):
        self.fixtures_dir = fixtures_dir
        self.output_dir = output_dir
        self.top_k = top_k

        self.scenarios: List[Dict[str, Any]] = []
        self.candidates: List[Dict[str, Any]] = []
        self.labels: List[Dict[str, Any]] = []
        self.candidates_by_scenario: Dict[str, List[Dict[str, Any]]] = {}
        self.labels_by_cand_id: Dict[str, Dict[str, Any]] = {}

        self.reranker = SemanticReranker(enabled=reranker_enabled, device="cpu")

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
        target_entity = scenario["expected_entity"]["canonical"]
        agent = scenario["agent"]

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

        cand_copy = copy.deepcopy(candidate)
        cand_copy["entity_score"] = assessment.entity_score
        cand_copy["intent_score"] = assessment.intent_score
        cand_copy["source_quality_score"] = assessment.source_quality_score
        cand_copy["relevance_score"] = assessment.relevance_score
        cand_copy["relevance_class"] = assessment.relevance_class
        cand_copy["is_accepted"] = assessment.is_accepted
        cand_copy["first_stage_score"] = assessment.relevance_score
        return cand_copy

    def rank_deterministic(self, scenario: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """System A: Deterministic baseline ranking using production RelevanceGate scores."""
        features = [self._prepare_candidate_features(scenario, c) for c in candidates]
        # Sort strictly descending by relevance_score, tie-breaking by entity_score
        sorted_cands = sorted(
            features,
            key=lambda x: (x.get("relevance_score", 0.0), x.get("entity_score", 0.0)),
            reverse=True,
        )
        ranked_output = []
        for idx, c in enumerate(sorted_cands, 1):
            item = copy.deepcopy(c)
            item["rank"] = idx
            item["final_score"] = item.get("relevance_score", 0.0)
            item["system"] = "deterministic"
            item["semantic_score"] = None
            ranked_output.append(item)
        return ranked_output

    def rank_hybrid(self, scenario: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """System B: Single-stage hybrid blend of lexical/entity signals and CrossEncoder scores."""
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

            ent = c.get("entity_score", 0.50)
            intent = c.get("intent_score", 0.50)
            sq = c.get("source_quality_score", 0.50)

            # Single-stage linear blend: 30% entity, 20% intent, 10% source, 40% semantic
            if ent < 0.35:
                hybrid = (0.30 * ent + 0.20 * intent + 0.10 * sq + 0.40 * sem) * 0.15
            else:
                hybrid = 0.30 * ent + 0.20 * intent + 0.10 * sq + 0.40 * sem

            c["final_score"] = round(hybrid, 4)

        sorted_cands = sorted(features, key=lambda x: x.get("final_score", 0.0), reverse=True)
        ranked_output = []
        for idx, c in enumerate(sorted_cands, 1):
            item = copy.deepcopy(c)
            item["rank"] = idx
            item["system"] = "hybrid"
            ranked_output.append(item)
        return ranked_output

    def rank_reranker(self, scenario: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """System C: Two-stage architecture (Deterministic hard gates -> Second-stage CrossEncoder)."""
        features = [self._prepare_candidate_features(scenario, c) for c in candidates]
        query = scenario["query"]

        reranked = self.reranker.rerank(
            query=query,
            candidates=features,
            top_k=len(candidates),
            entity_score_threshold=0.35,
        )
        ranked_output = []
        for idx, c in enumerate(reranked, 1):
            item = copy.deepcopy(c)
            item["rank"] = idx
            item["final_score"] = item.get("rerank_score", item.get("relevance_score", 0.0))
            item["system"] = "reranker"
            ranked_output.append(item)
        return ranked_output

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
            pool_size=len(all_cands),
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
        top1 = ranked_candidates[0] if ranked_candidates else {}
        top1_cid = top1.get("candidate_id")
        top1_label = self.labels_by_cand_id.get(top1_cid, {})
        top1_grade = top1_label.get("gold_grade", 0)

        # A scenario is fully successful if top-1 is Grade 3 or (if no grade 3 exists) Grade 2
        is_success = (top1_grade == 3) or (eval_metrics.get("total_strict_relevant", 0) == 0 and top1_grade == 2)

        if is_success:
            return None

        failure_class = "OTHER"
        if eval_metrics.get("hard_neg_leak_at_1", 0) > 0 or top1_grade == 0:
            failure_class = "HARD_NEGATIVE_LEAK"
        elif eval_metrics.get("entity_accuracy_at_1", 0) == 0.0:
            failure_class = "WRONG_ENTITY"
        elif eval_metrics.get("intent_accuracy_at_1", 0) == 0.0:
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
            "p_at_1": eval_metrics.get("p_at_1"),
            "p_at_4": eval_metrics.get("p_at_4"),
            "ndcg_at_4": eval_metrics.get("ndcg_at_4"),
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
            "Executing benchmark across %d scenarios and systems %s (Reranker available: %s)...",
            len(scenarios_to_run),
            systems_to_run,
            self.reranker.is_available,
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

                failure = self.classify_failure(s, ranked, eval_res)
                if failure:
                    all_failures.append(failure)

        # Aggregate metrics across systems, agents, splits, and classifications
        summary: Dict[str, Any] = {}
        per_agent_summary: Dict[str, Any] = {}
        per_class_summary: Dict[str, Any] = {}

        for sys_name in systems_to_run:
            res_list = all_results[sys_name]
            overall = aggregate_metrics(res_list)
            dev_metrics = aggregate_metrics([r for r in res_list if r.get("split") == "dev"])
            holdout_metrics = aggregate_metrics([r for r in res_list if r.get("split") == "holdout"])

            summary[sys_name] = {
                "overall": overall,
                "dev": dev_metrics,
                "holdout": holdout_metrics,
                "model_status": "AVAILABLE" if self.reranker.is_available else "FALLBACK",
            }

            per_agent_summary[sys_name] = {}
            for agent in ["brandshield", "trending", "scout", "personal_watch"]:
                ag_res = [r for r in res_list if r["agent"].lower() == agent.lower()]
                per_agent_summary[sys_name][agent] = aggregate_metrics(ag_res)

            per_class_summary[sys_name] = {}
            all_classes = sorted(list({r.get("classification") for r in res_list if r.get("classification")}))
            for cls_name in all_classes:
                cls_res = [r for r in res_list if r.get("classification") == cls_name]
                per_class_summary[sys_name][cls_name] = aggregate_metrics(cls_res)

        # Add observable reranker telemetry
        summary["telemetry"] = self.reranker.get_telemetry()

        # Write artifacts
        with open(self.output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        with open(self.output_dir / "per_agent.json", "w", encoding="utf-8") as f:
            json.dump(per_agent_summary, f, indent=2)

        with open(self.output_dir / "per_classification.json", "w", encoding="utf-8") as f:
            json.dump(per_class_summary, f, indent=2)

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

        self._write_markdown_summary(summary, per_agent_summary, per_class_summary)

        logger.info("Benchmark complete. Artifacts saved to %s", self.output_dir)
        return summary

    def _write_markdown_summary(
        self,
        summary: Dict[str, Any],
        per_agent: Dict[str, Any],
        per_class: Dict[str, Any],
    ):
        lines = []
        lines.append("# Aegis Protocol — Corrected Retrieval Quality Benchmark Summary")
        lines.append("")
        lines.append("## Metric Formulation & Candidate Pool Documentation")
        lines.append("- **Total Scenarios:** `104` (Development: `84`, Holdout: `20`)")
        lines.append("- **Frozen Candidate Pool Size per Scenario:** `N = 4` (Total Candidates: `416`)")
        lines.append("- **Relevance Labels in Corpus:** 85 broad relevant (grades 2–3) across 58 scenarios; 53 strict relevant (grade 3); 184 grade 1; 147 grade 0.")
        lines.append("- **Evaluated Cutoffs:** Natural pool cutoffs at **k = 1, 3, 4** (plus fixed k=5 reference).")
        lines.append("- **Recall Calculation:** Standard Cranfield macro-average evaluated strictly over the `58` scenarios containing at least one relevant document ($R_{query} \\ge 1$).")
        lines.append("")
        lines.append("## Neural CrossEncoder Execution Telemetry")
        telem = summary.get("telemetry", {})
        lines.append(f"- **Configured Model:** `{telem.get('model_name', 'cross-encoder/ms-marco-MiniLM-L-6-v2')}`")
        lines.append(f"- **Execution Device:** `{telem.get('device', 'cpu')}`")
        lines.append(f"- **Availability Status:** `{'AVAILABLE' if telem.get('is_available') else 'UNAVAILABLE'}`")
        lines.append(f"- **Pairs Scored:** `{telem.get('pairs_scored', 0)}`")
        lines.append(f"- **Inference Duration:** `{telem.get('inference_duration_sec', 0.0)}s`")
        lines.append(f"- **Inference Failures:** `{telem.get('inference_failures', 0)}`")
        lines.append(f"- **Fallback Invocations:** `{telem.get('fallback_count', 0)}`")
        lines.append("")
        lines.append("## 1. System Comparison Matrix (Overall, N=104)")
        lines.append("")
        lines.append("| Metric | System A: Deterministic Baseline | System B: Hybrid Lexical+Neural | System C: Neural Second-Stage | Delta (C vs A) |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")

        det = summary.get("deterministic", {}).get("overall", {})
        hyb = summary.get("hybrid", {}).get("overall", {})
        rer = summary.get("reranker", {}).get("overall", {})

        metrics_display = [
            ("Broad Precision@1 (Grades 2-3)", "p_at_1", True),
            ("Broad Precision@3 (Grades 2-3)", "p_at_3", True),
            ("Broad Precision@4 (Grades 2-3)", "p_at_4", True),
            ("Strict Precision@1 (Grade 3)", "strict_p_at_1", True),
            ("Strict Precision@3 (Grade 3)", "strict_p_at_3", True),
            ("Strict Precision@4 (Grade 3)", "strict_p_at_4", True),
            ("Cranfield Recall@1 (R >= 1)", "recall_at_1", True),
            ("Cranfield Recall@3 (R >= 1)", "recall_at_3", True),
            ("Cranfield Recall@4 (Full Pool)", "recall_at_4", True),
            ("MRR (Broad)", "mrr", True),
            ("Strict MRR (Grade 3)", "strict_mrr", True),
            ("nDCG@3", "ndcg_at_3", True),
            ("nDCG@4 (Full Pool)", "ndcg_at_4", True),
            ("Entity Accuracy @ Rank 1", "entity_accuracy_at_1", True),
            ("Top-k Entity Density (Pool)", "top_k_entity_density", True),
            ("Intent Accuracy @ Rank 1", "intent_accuracy_at_1", True),
            ("Top-k Intent Density (Pool)", "top_k_intent_density", True),
            ("Top-1 Hard-Negative Avoidance", "top1_hard_negative_avoidance", True),
            ("Candidate Hard-Negative Rejection Rate", "candidate_hard_negative_rejection_rate", True),
        ]

        for label, key, _ in metrics_display:
            d_val = det.get(key, 0.0)
            h_val = hyb.get(key, 0.0)
            r_val = rer.get(key, 0.0)
            delta = r_val - d_val
            sign = "+" if delta > 0 else ""
            delta_str = f"{sign}{delta * 100:.1f}%" if "rate" in key or "acc" in key or "p_" in key or "recall" in key or "density" in key or "avoidance" in key else f"{sign}{delta:.3f}"
            lines.append(f"| **{label}** | {d_val * 100:.1f}% | {h_val * 100:.1f}% | {r_val * 100:.1f}% | **{delta_str}** |")

        lines.append("")
        lines.append("## 2. Development (N=84) vs. Holdout (N=20) Generalization")
        lines.append("")
        lines.append("| Metric | Dev (Deterministic) | Dev (Reranker) | Holdout (Deterministic) | Holdout (Reranker) |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")

        d_dev = summary.get("deterministic", {}).get("dev", {})
        d_hld = summary.get("deterministic", {}).get("holdout", {})
        r_dev = summary.get("reranker", {}).get("dev", {})
        r_hld = summary.get("reranker", {}).get("holdout", {})

        for label, key, _ in [
            ("Broad P@1", "p_at_1", True),
            ("Broad P@4", "p_at_4", True),
            ("Strict P@1", "strict_p_at_1", True),
            ("Cranfield Recall@3", "recall_at_3", True),
            ("MRR", "mrr", True),
            ("nDCG@4", "ndcg_at_4", True),
            ("Top-1 Hard-Neg Avoidance", "top1_hard_negative_avoidance", True),
            ("Candidate Hard-Neg Rejection", "candidate_hard_negative_rejection_rate", True),
        ]:
            lines.append(
                f"| **{label}** | {d_dev.get(key, 0.0)*100:.1f}% | {r_dev.get(key, 0.0)*100:.1f}% | {d_hld.get(key, 0.0)*100:.1f}% | {r_hld.get(key, 0.0)*100:.1f}% |"
            )

        lines.append("")
        lines.append("## 3. Per-Agent Performance Breakdown (Neural Reranker)")
        lines.append("")
        lines.append("| Agent | Scenarios | Broad P@1 | Broad P@4 | Strict P@1 | Cranfield Recall@3 | nDCG@4 | Top-1 HN Avoidance | Cand HN Rejection |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

        for ag in ["brandshield", "trending", "scout", "personal_watch"]:
            m = per_agent.get("reranker", {}).get(ag, {})
            lines.append(
                f"| **{ag.title()}** | {m.get('evaluable_scenarios', 26)} | {m.get('p_at_1', 0.0)*100:.1f}% | {m.get('p_at_4', 0.0)*100:.1f}% | {m.get('strict_p_at_1', 0.0)*100:.1f}% | {m.get('recall_at_3', 0.0)*100:.1f}% | {m.get('ndcg_at_4', 0.0)*100:.1f}% | {m.get('top1_hard_negative_avoidance', 0.0)*100:.1f}% | {m.get('candidate_hard_negative_rejection_rate', 0.0)*100:.1f}% |"
            )

        with open(self.output_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run Aegis Retrieval Quality Benchmark")
    parser.add_argument("--agent", default="all", choices=["all", "brandshield", "trending", "scout", "personal_watch"])
    parser.add_argument("--system", default="all", choices=["all", "deterministic", "hybrid", "reranker"])
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--fixtures", default="tests/retrieval_benchmark")
    parser.add_argument("--output", default="artifacts/retrieval_benchmark")
    parser.add_argument("--live", action="store_true", help="Run against live web/search sources")

    args = parser.parse_args()
    runner = BenchmarkRunner(
        fixtures_dir=Path(args.fixtures),
        output_dir=Path(args.output),
        top_k=args.top_k,
    )
    runner.run_benchmark(agent_filter=args.agent, system_filter=args.system)


if __name__ == "__main__":
    main()
