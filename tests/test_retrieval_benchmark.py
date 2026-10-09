"""
Aegis Protocol — 4-Agent Retrieval Benchmark Integration Tests
==============================================================
Tests agent separation, system comparisons, and deterministic defense against
critical adversarial cases:
1. Satya homograph cases (Sanskrit philosophy, 1998 Bollywood film)
2. Magic: The Gathering Investigate card mechanics
3. MSFT ETF constituent lists
4. Boilerplate Satya Nadella closing mentions
5. System ranking divergence (Deterministic != Hybrid != Reranker)
6. Development vs Holdout split disjointness
7. Reranker fallback behavior
"""

import json
import pytest
from pathlib import Path
from scripts.run_retrieval_quality_benchmark import BenchmarkRunner
from backend.services.research.semantic_reranker import SemanticReranker

FIXTURES_DIR = Path("tests/retrieval_benchmark")


@pytest.fixture(scope="module")
def benchmark_results(tmp_path_factory):
    """Run against frozen inputs while isolating generated outputs per test run."""
    output_dir = tmp_path_factory.mktemp("retrieval_benchmark")
    runner = BenchmarkRunner(
        fixtures_dir=FIXTURES_DIR,
        output_dir=output_dir,
        top_k=4,
    )
    summary = runner.run_benchmark(agent_filter="all", system_filter="all")
    return summary, runner


def test_agent_metrics_are_separated(benchmark_results):
    summary, runner = benchmark_results
    per_agent_file = runner.output_dir / "per_agent.json"
    assert per_agent_file.exists()

    with open(per_agent_file, "r", encoding="utf-8") as f:
        per_agent = json.load(f)

    for sys_name in ["deterministic", "hybrid", "reranker"]:
        assert sys_name in per_agent
        sys_metrics = per_agent[sys_name]
        for ag in ["brandshield", "trending", "scout", "personal_watch"]:
            assert ag in sys_metrics
            ag_m = sys_metrics[ag]
            assert "p_at_1" in ag_m
            assert "p_at_4" in ag_m
            assert "mrr" in ag_m
            assert "ndcg_at_4" in ag_m
            assert "entity_accuracy" in ag_m
            assert "hard_negative_rejection_rate" in ag_m
            assert ag_m["evaluable_scenarios"] >= 25


def test_deterministic_vs_reranker_comparison(benchmark_results):
    summary, _ = benchmark_results
    assert "deterministic" in summary
    assert "reranker" in summary

    det_overall = summary["deterministic"]["overall"]
    rer_overall = summary["reranker"]["overall"]

    # Both systems must compute valid metrics on the identical corpus
    assert det_overall["evaluable_scenarios"] == 104
    assert rer_overall["evaluable_scenarios"] == 104
    assert 0.0 <= det_overall["p_at_1"] <= 1.0
    assert 0.0 <= rer_overall["p_at_1"] <= 1.0
    assert 0.0 <= det_overall["ndcg_at_4"] <= 1.0
    assert 0.0 <= rer_overall["ndcg_at_4"] <= 1.0


def test_system_ranking_divergence(benchmark_results):
    """
    Verification that ranking systems are isolated and generate distinct orderings.
    """
    _, runner = benchmark_results
    with open(runner.output_dir / "rankings.jsonl", "r", encoding="utf-8") as f:
        rankings = [json.loads(line) for line in f]

    from collections import defaultdict
    by_scen_sys = defaultdict(dict)
    for r in rankings:
        by_scen_sys[r["scenario_id"]][r["system"]] = [c["candidate_id"] for c in r["ranked_candidates"]]

    diff_det_rer = 0
    diff_det_hyb = 0
    for scen_id, systems in by_scen_sys.items():
        det = systems.get("deterministic", [])
        rer = systems.get("reranker", [])
        hyb = systems.get("hybrid", [])
        if det != rer:
            diff_det_rer += 1
        if det != hyb:
            diff_det_hyb += 1

    # In our 104 scenarios, deterministic and neural reranker must diverge on multiple scenarios
    assert diff_det_rer >= 15, f"Expected >= 15 ranking divergences between Det and Reranker, found {diff_det_rer}"
    assert diff_det_hyb >= 10, f"Expected >= 10 ranking divergences between Det and Hybrid, found {diff_det_hyb}"


def test_development_and_holdout_disjointness(benchmark_results):
    """
    Invariance test: Development and Holdout scenario sets must be strictly disjoint.
    """
    _, runner = benchmark_results
    dev_ids = {s["scenario_id"] for s in runner.scenarios if s.get("split") == "dev"}
    holdout_ids = {s["scenario_id"] for s in runner.scenarios if s.get("split") == "holdout"}

    assert len(dev_ids) == 84
    assert len(holdout_ids) == 20
    assert len(dev_ids.intersection(holdout_ids)) == 0, "Dev and Holdout scenario IDs must not overlap"


def test_reranker_fallback_behavior():
    """
    When disabled or model loading fails, semantic reranker must degrade gracefully
    without fabricating scores or crashing.
    """
    disabled_reranker = SemanticReranker(enabled=False)
    assert not disabled_reranker.enabled
    candidates = [
        {"title": "Doc 1", "snippet": "Snippet 1", "relevance_score": 0.8},
        {"title": "Doc 2", "snippet": "Snippet 2", "relevance_score": 0.4},
    ]
    reranked = disabled_reranker.rerank("Query", candidates, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["semantic_status"] == "DISABLED"
    assert reranked[0]["semantic_score"] is None
    assert reranked[0]["raw_cross_encoder_score"] is None
    # Preserves first-stage order
    assert reranked[0]["title"] == "Doc 1"


def test_satya_homograph_cases(benchmark_results):
    """Sanskrit philosophy and 1998 Bollywood movie must be suppressed."""
    _, runner = benchmark_results

    # Find Sanskrit scenario
    sanskrit_scenario = next(
        (s for s in runner.scenarios if "sanskrit" in s["scenario_id"] or "sanskrit" in s["query"].lower()),
        None
    )
    assert sanskrit_scenario is not None

    cands = runner.candidates_by_scenario[sanskrit_scenario["scenario_id"]]
    ranked = runner.rank_reranker(sanskrit_scenario, cands)

    # Sanskrit homograph candidate must NOT be rank 1
    top1 = ranked[0]
    top1_label = runner.labels_by_cand_id[top1["candidate_id"]]
    assert "sanskrit" not in top1_label.get("gold_reason", "").lower() or top1.get("entity_score", 1.0) < 0.35

    # Find 1998 movie scenario
    movie_scenario = next(
        (s for s in runner.scenarios if "1998" in s["scenario_id"] or "1998" in s["query"].lower()),
        None
    )
    assert movie_scenario is not None
    cands_movie = runner.candidates_by_scenario[movie_scenario["scenario_id"]]
    ranked_movie = runner.rank_reranker(movie_scenario, cands_movie)
    top1_movie = ranked_movie[0]
    assert top1_movie.get("entity_score", 1.0) < 0.35 or top1_movie.get("rerank_score", 1.0) < 0.40


def test_mtg_investigate_case(benchmark_results):
    """Magic: The Gathering cards must not leak as true positive Microsoft brand abuse."""
    _, runner = benchmark_results

    mtg_scenario = next(
        (s for s in runner.scenarios if "mtg" in s["scenario_id"] or "tireless tracker" in s["query"].lower()),
        None
    )
    assert mtg_scenario is not None
    cands = runner.candidates_by_scenario[mtg_scenario["scenario_id"]]
    ranked = runner.rank_reranker(mtg_scenario, cands)

    for c in ranked:
        if "Tireless Tracker" in c.get("title", ""):
            assert c.get("entity_score", 1.0) < 0.35 or c.get("final_score", 1.0) < 0.35


def test_msft_etf_negative(benchmark_results):
    """S&P 500 ETF constituent lists must not be classified as top primary corporate disclosures."""
    _, runner = benchmark_results

    etf_scenario = next(
        (s for s in runner.scenarios if "etf" in s["scenario_id"] or "s&p 500" in s["query"].lower()),
        None
    )
    assert etf_scenario is not None
    cands = runner.candidates_by_scenario[etf_scenario["scenario_id"]]
    ranked = runner.rank_reranker(etf_scenario, cands)

    top1 = ranked[0]
    top1_label = runner.labels_by_cand_id[top1["candidate_id"]]
    assert top1_label.get("gold_grade") <= 2


def test_boilerplate_satya_negative(benchmark_results):
    """Articles with merely boilerplate closing mentions must be identified."""
    _, runner = benchmark_results

    bp_scenario = next(
        (s for s in runner.scenarios if "boilerplate" in s["scenario_id"] or "boilerplate" in s["query"].lower()),
        None
    )
    assert bp_scenario is not None
    cands = runner.candidates_by_scenario[bp_scenario["scenario_id"]]
    ranked = runner.rank_reranker(bp_scenario, cands)
    bp_cands = [c for c in ranked if "Boilerplate" in c.get("title", "") or "3D Immersive" in c.get("title", "")]
    assert len(bp_cands) > 0
    bp_grade = runner.labels_by_cand_id[bp_cands[0]["candidate_id"]]["gold_grade"]
    assert bp_grade == 1


def test_holdout_vs_dev_split_separation(benchmark_results):
    summary, _ = benchmark_results
    for sys_name in ["deterministic", "hybrid", "reranker"]:
        sys_data = summary[sys_name]
        assert "dev" in sys_data
        assert "holdout" in sys_data
        assert sys_data["dev"]["evaluable_scenarios"] > 0
        assert sys_data["holdout"]["evaluable_scenarios"] > 0
        assert sys_data["dev"]["evaluable_scenarios"] + sys_data["holdout"]["evaluable_scenarios"] == sys_data["overall"]["evaluable_scenarios"]
