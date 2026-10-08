"""
Aegis Protocol — Retrieval Benchmark Schema Test Suite
======================================================
Tests schema compliance, 0-3 grading scale, agent balance, dev/holdout split,
and fail-closed invariants for the frozen golden benchmark dataset.
"""

import json
import pytest
from pathlib import Path
from scripts.validate_retrieval_benchmark import (
    validate_benchmark,
    VALID_AGENTS,
    VALID_CLASSIFICATIONS,
    VALID_GRADES,
)

FIXTURES_DIR = Path("tests/retrieval_benchmark")

def test_benchmark_files_exist():
    assert (FIXTURES_DIR / "scenarios.jsonl").exists()
    assert (FIXTURES_DIR / "candidates.jsonl").exists()
    assert (FIXTURES_DIR / "labels.jsonl").exists()
    assert (FIXTURES_DIR / "README.md").exists()

def test_benchmark_schema_validation():
    res = validate_benchmark(FIXTURES_DIR)
    assert res["status"] == "PASS"
    assert len(res["errors"]) == 0
    assert res["scenarios_count"] >= 100
    assert res["candidates_count"] >= 100
    assert res["labels_count"] == res["candidates_count"]

def test_benchmark_minimum_scenarios():
    scenarios_file = FIXTURES_DIR / "scenarios.jsonl"
    count = 0
    with open(scenarios_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    assert count >= 100, f"Expected at least 100 scenarios, found {count}"

def test_benchmark_four_agents_balance():
    scenarios_file = FIXTURES_DIR / "scenarios.jsonl"
    agent_counts = {}
    with open(scenarios_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            agent = item["agent"]
            assert agent in VALID_AGENTS
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

    for agent in VALID_AGENTS:
        assert agent_counts.get(agent, 0) >= 25, f"Agent {agent} must have >= 25 scenarios"

def test_benchmark_dev_holdout_split():
    scenarios_file = FIXTURES_DIR / "scenarios.jsonl"
    dev_count = 0
    holdout_count = 0
    with open(scenarios_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            split = item.get("split")
            assert split in ("dev", "holdout")
            if split == "dev":
                dev_count += 1
            else:
                holdout_count += 1

    total = dev_count + holdout_count
    holdout_ratio = holdout_count / total
    assert 0.15 <= holdout_ratio <= 0.25, f"Holdout ratio should be ~20%, got {holdout_ratio:.2f}"

def test_benchmark_gold_grades_scale():
    labels_file = FIXTURES_DIR / "labels.jsonl"
    grade_distribution = {0: 0, 1: 0, 2: 0, 3: 0}
    with open(labels_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            grade = item["gold_grade"]
            assert grade in VALID_GRADES
            grade_distribution[grade] += 1

    # Must have both positive (3, 2) and negative/distractor (1, 0) candidates
    assert grade_distribution[3] > 0, "Must have grade 3 (true positives)"
    assert grade_distribution[0] > 0, "Must have grade 0 (hard negatives)"
    assert grade_distribution[1] > 0, "Must have grade 1 (distractors)"

def test_empty_fixture_fails_closed(tmp_path):
    empty_dir = tmp_path / "empty_bench"
    empty_dir.mkdir()
    res = validate_benchmark(empty_dir)
    assert res["status"] == "NOT_EVALUABLE"
    assert len(res["errors"]) > 0

def test_unlabeled_candidate_fails_validation(tmp_path):
    bench_dir = tmp_path / "broken_bench"
    bench_dir.mkdir()
    # Write a scenario and candidate but omit the label
    with open(bench_dir / "scenarios.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "scenario_id": "test_001",
            "agent": "brandshield",
            "query": "test query",
            "classification": "TRUE_POSITIVE",
            "expected_entity": {"canonical": "Test", "aliases": []},
            "expected_intent": "test",
            "expected_decision": "ACCEPT",
            "priority": "high",
            "split": "dev"
        }) + "\n")
    with open(bench_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "candidate_id": "cand_missing_label",
            "scenario_id": "test_001",
            "title": "Title",
            "snippet": "Snippet",
            "url": "https://example.com",
            "source": "web",
            "published_at": "2026-10-01T00:00:00Z"
        }) + "\n")
    with open(bench_dir / "labels.jsonl", "w", encoding="utf-8") as f:
        pass  # empty labels

    res = validate_benchmark(bench_dir)
    assert res["status"] in ("FAIL", "NOT_EVALUABLE")
    assert any("missing gold labels" in e or "zero labels" in e.lower() for e in res["errors"])
