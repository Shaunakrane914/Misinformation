"""
Aegis Protocol — Retrieval Benchmark Dataset Validator
======================================================
Validates golden benchmark fixtures in tests/retrieval_benchmark/ for:
1. Scenario schema completeness and valid agent names / classifications.
2. Candidate mapping and ID uniqueness.
3. Gold label presence and grading scale validity (0, 1, 2, 3).
4. Candidate balance and zero-empty fail-closed constraints.
Exits with 0 on success, non-zero on failure.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

VALID_AGENTS = {"brandshield", "trending", "scout", "personal_watch"}

VALID_CLASSIFICATIONS = {
    "TRUE_POSITIVE",
    "SECONDARY_RELEVANT",
    "BOUNDARY_NEGATIVE",
    "HARD_NEGATIVE",
    "BENIGN_DISTRACTOR",
    "OUT_OF_DOMAIN",
    "TEMPORAL_NEGATIVE",
    "HOMOGRAPH_NEGATIVE",
    "DEDUPLICATION",
    "ENTITY_DISTRACTOR",
}

VALID_GRADES = {0, 1, 2, 3}

def validate_benchmark(fixtures_dir: Path = Path("tests/retrieval_benchmark")) -> Dict[str, Any]:
    scenarios_path = fixtures_dir / "scenarios.jsonl"
    candidates_path = fixtures_dir / "candidates.jsonl"
    labels_path = fixtures_dir / "labels.jsonl"

    errors = []

    if not scenarios_path.exists():
        errors.append(f"Missing scenarios file: {scenarios_path}")
    if not candidates_path.exists():
        errors.append(f"Missing candidates file: {candidates_path}")
    if not labels_path.exists():
        errors.append(f"Missing labels file: {labels_path}")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}")
        return {"status": "NOT_EVALUABLE", "errors": errors}

    # Load scenarios
    scenarios: List[Dict[str, Any]] = []
    with open(scenarios_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                scenarios.append(json.loads(line))
            except json.JSONDecodeError as ex:
                errors.append(f"Invalid JSON on {scenarios_path}:{line_num}: {ex}")

    # Load candidates
    candidates: List[Dict[str, Any]] = []
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError as ex:
                errors.append(f"Invalid JSON on {candidates_path}:{line_num}: {ex}")

    # Load labels
    labels: List[Dict[str, Any]] = []
    with open(labels_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                labels.append(json.loads(line))
            except json.JSONDecodeError as ex:
                errors.append(f"Invalid JSON on {labels_path}:{line_num}: {ex}")

    if len(scenarios) == 0:
        errors.append("Dataset is empty: zero scenarios found. Result is NOT_EVALUABLE.")
    if len(candidates) == 0:
        errors.append("Dataset is empty: zero candidates found. Result is NOT_EVALUABLE.")
    if len(labels) == 0:
        errors.append("Dataset is empty: zero labels found. Result is NOT_EVALUABLE.")

    scenario_ids = set()
    agent_counts = {}
    for s in scenarios:
        s_id = s.get("scenario_id")
        if not s_id:
            errors.append(f"Scenario missing 'scenario_id': {s}")
            continue
        if s_id in scenario_ids:
            errors.append(f"Duplicate scenario_id: {s_id}")
        scenario_ids.add(s_id)

        agent = s.get("agent")
        if agent not in VALID_AGENTS:
            errors.append(f"Scenario {s_id} has invalid agent '{agent}'. Must be one of {VALID_AGENTS}")
        else:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

        cls_type = s.get("classification")
        if cls_type not in VALID_CLASSIFICATIONS:
            errors.append(f"Scenario {s_id} has unsupported classification '{cls_type}'. Must be one of {VALID_CLASSIFICATIONS}")

        expected_entity = s.get("expected_entity")
        if not isinstance(expected_entity, dict) or not expected_entity.get("canonical"):
            errors.append(f"Scenario {s_id} missing valid 'expected_entity.canonical'")

        if not s.get("expected_intent"):
            errors.append(f"Scenario {s_id} missing 'expected_intent'")
        if not s.get("expected_decision"):
            errors.append(f"Scenario {s_id} missing 'expected_decision'")
        if s.get("split") not in ("dev", "holdout"):
            errors.append(f"Scenario {s_id} split must be 'dev' or 'holdout', got '{s.get('split')}'")

    candidate_ids = set()
    scenario_to_candidates: Dict[str, List[str]] = {}
    for c in candidates:
        c_id = c.get("candidate_id")
        if not c_id:
            errors.append(f"Candidate missing 'candidate_id': {c}")
            continue
        if c_id in candidate_ids:
            errors.append(f"Duplicate candidate_id found: {c_id}")
        candidate_ids.add(c_id)

        s_id = c.get("scenario_id")
        if not s_id or s_id not in scenario_ids:
            errors.append(f"Candidate {c_id} references non-existent scenario_id: '{s_id}'")
        else:
            scenario_to_candidates.setdefault(s_id, []).append(c_id)

        if not c.get("title") and not c.get("snippet"):
            errors.append(f"Candidate {c_id} has empty title and snippet")
        if not c.get("url"):
            errors.append(f"Candidate {c_id} missing url")

    labeled_candidate_ids = set()
    for lb in labels:
        c_id = lb.get("candidate_id")
        if not c_id:
            errors.append(f"Label missing 'candidate_id': {lb}")
            continue
        if c_id in labeled_candidate_ids:
            errors.append(f"Duplicate label for candidate_id: {c_id}")
        labeled_candidate_ids.add(c_id)

        if c_id not in candidate_ids:
            errors.append(f"Label references unknown candidate_id: {c_id}")

        grade = lb.get("gold_grade")
        if grade not in VALID_GRADES:
            errors.append(f"Candidate {c_id} has invalid gold_grade '{grade}'. Must be in {VALID_GRADES}")

        if not lb.get("gold_entity"):
            errors.append(f"Label for {c_id} missing 'gold_entity'")
        if not lb.get("gold_intent"):
            errors.append(f"Label for {c_id} missing 'gold_intent'")
        if not lb.get("gold_reason"):
            errors.append(f"Label for {c_id} missing 'gold_reason'")

    # Check that all candidates have labels
    missing_labels = candidate_ids - labeled_candidate_ids
    if missing_labels:
        errors.append(f"{len(missing_labels)} candidates are missing gold labels: {list(missing_labels)[:5]}...")

    # Check that all scenarios have candidates
    for s_id in scenario_ids:
        cands = scenario_to_candidates.get(s_id, [])
        if len(cands) == 0:
            errors.append(f"Scenario {s_id} has ZERO candidates. Empty evaluation is forbidden.")

    # Check minimum requirements
    if len(scenarios) < 100:
        errors.append(f"Expected at least 100 scenarios, found {len(scenarios)}")
    for agent in VALID_AGENTS:
        count = agent_counts.get(agent, 0)
        if count < 25:
            errors.append(f"Agent '{agent}' has {count} scenarios; minimum required is 25")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "scenarios_count": len(scenarios),
        "candidates_count": len(candidates),
        "labels_count": len(labels),
        "agent_counts": agent_counts,
        "errors": errors,
    }

    if errors:
        print(f"\n[VALIDATION FAILED] {len(errors)} error(s) discovered:")
        for err in errors[:20]:
            print(f"  ❌ {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        return result

    print("\n[VALIDATION PASSED] Benchmark dataset satisfies all integrity invariants:")
    print(f"  [+] {len(scenarios)} total scenarios across all 4 agents:")
    for ag, cnt in agent_counts.items():
        print(f"     - {ag}: {cnt} scenarios")
    print(f"  [+] {len(candidates)} total candidates independently represented")
    print(f"  [+] {len(labels)} gold labels with explicit 0-3 grading scale and rationales")
    print("  [+] Zero orphan candidates, zero missing labels, zero duplicate IDs")
    print("  [+] Fail-closed empty-corpus invariants verified")
    return result

if __name__ == "__main__":
    res = validate_benchmark()
    if res["status"] != "PASS":
        sys.exit(1)
    sys.exit(0)
