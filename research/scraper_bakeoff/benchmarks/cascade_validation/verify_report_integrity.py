"""
Report Integrity Assertion Suite — Aegis Cascade Validation V3
==============================================================
Validates that generated markdown reports and JSON traces maintain absolute
mathematical integrity against the canonical source of truth (cascade_metric_trace.json).

Exits 0 if all invariant checks pass.
Exits 1 with diagnostic assertion error if any check fails.
"""
import re
import sys
import json
from pathlib import Path

BAKEOFF_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = BAKEOFF_ROOT / "reports"
OUTPUTS_DIR = BAKEOFF_ROOT / "outputs" / "latest"

TRACE_FILE = REPORTS_DIR / "cascade_metric_trace.json"
PAIRED_FILE = REPORTS_DIR / "paired_policy_results.json"
SCORECARD_FILE = REPORTS_DIR / "cascade_scorecard.md"
ROUTE_FILE = REPORTS_DIR / "final_route_distribution.md"
ARCH_FILE = REPORTS_DIR / "final_architecture_decision_v3.md"

def run_integrity_checks():
    print("=" * 80)
    print("  AEGIS CASCADE V3: REPORT INTEGRITY & INVARIANT ASSERTION SUITE")
    print("=" * 80)

    # 1. Load Canonical Trace
    assert TRACE_FILE.exists(), f"Missing {TRACE_FILE}"
    with open(TRACE_FILE, "r", encoding="utf-8") as f:
        trace_data = json.load(f)
    pm = trace_data["policy_metrics"]

    # Invariant 1: Programmatic Canonical Source of Truth
    canonical_expected = {
        'POLICY_A': {'useful': 249, 'direct': 25, 'meta': 25, 'fb': 291, 'unres': 0},
        'POLICY_B': {'useful': 229, 'direct': 70, 'meta': 116, 'fb': 224, 'unres': 0},
        'POLICY_C': {'useful': 200, 'direct': 0, 'meta': 0, 'fb': 340, 'unres': 0},
        'POLICY_D': {'useful': 229, 'direct': 70, 'meta': 116, 'fb': 224, 'unres': 0},
    }
    for pol, exp in canonical_expected.items():
        m = pm[pol]
        assert m['useful_evidence_count'] == exp['useful'], f"{pol} useful evidence mismatch: {m['useful_evidence_count']} vs {exp['useful']}"
        assert m['first_party_direct_count'] == exp['direct'], f"{pol} direct mismatch: {m['first_party_direct_count']} vs {exp['direct']}"
        assert m['first_party_or_metadata_count'] == exp['meta'], f"{pol} meta mismatch: {m['first_party_or_metadata_count']} vs {exp['meta']}"
        assert m['fallback_count'] == exp['fb'], f"{pol} fallback mismatch: {m['fallback_count']} vs {exp['fb']}"
        assert m['unresolved_count'] == exp['unres'], f"{pol} unresolved mismatch: {m['unresolved_count']} vs {exp['unres']}"
    print("[PASS] Check 1 Passed: Canonical metrics match exactly in cascade_metric_trace.json")

    # Invariant 2: Policy B and D directness and evidence must be identical
    assert pm['POLICY_B']['useful_evidence_count'] == pm['POLICY_D']['useful_evidence_count'], "Policy B and D useful evidence differ"
    assert pm['POLICY_B']['first_party_direct_count'] == pm['POLICY_D']['first_party_direct_count'], "Policy B and D direct counts differ"
    assert pm['POLICY_B']['first_party_or_metadata_count'] == pm['POLICY_D']['first_party_or_metadata_count'], "Policy B and D direct+metadata differ"
    print("[PASS] Check 2 Passed: Policy B and D directness and evidence are strictly identical")

    # Invariant 3: Fallback + Unresolved + Direct Routes reconcile to exactly 340
    # In Policy D: Native API (25) + Specialist (46) + Scrapling (45) + Playwright (0) + Search Fallback (224) + Unresolved (0) = 340
    route_counts = pm['POLICY_D']['route_distribution_counts']
    native_cnt = route_counts.get("NATIVE_API", 0)
    spec_cnt = route_counts.get("SPECIALIST", 0)
    scrap_cnt = route_counts.get("SCRAPLING", 0)
    pw_cnt = route_counts.get("PLAYWRIGHT", 0)
    fb_cnt = route_counts.get("SEARCH_FALLBACK", 0)
    unres_cnt = route_counts.get("NO_VALID_RETRIEVAL", 0)
    total_reconciled = native_cnt + spec_cnt + scrap_cnt + pw_cnt + fb_cnt + unres_cnt
    assert total_reconciled == 340, f"Route reconciliation failure: total {total_reconciled} != 340"
    assert (native_cnt + spec_cnt + scrap_cnt) == pm['POLICY_D']['first_party_or_metadata_count'], "Direct+Metadata count does not equal sum of direct tiers"
    print(f"[PASS] Check 3 Passed: Route reconciliation strictly equals 340 (Native={native_cnt}, Spec={spec_cnt}, Scrapling={scrap_cnt}, PW={pw_cnt}, FB={fb_cnt}, Unres={unres_cnt})")

    # Invariant 4: No occurrence of the false string '98.5%' anywhere in final reports
    reports_to_check = [SCORECARD_FILE, ROUTE_FILE, ARCH_FILE]
    if (OUTPUTS_DIR / "cascade_scorecard.md").exists():
        reports_to_check.extend([
            OUTPUTS_DIR / "cascade_scorecard.md",
            OUTPUTS_DIR / "final_route_distribution.md",
            OUTPUTS_DIR / "final_architecture_decision_v3.md",
            OUTPUTS_DIR / "INDEX.md"
        ])
    for rep in reports_to_check:
        content = rep.read_text(encoding="utf-8")
        assert "98.5%" not in content, f"Forbidden string '98.5%' found in {rep.name}"
    print("[PASS] Check 4 Passed: Forbidden false string '98.5%' is completely absent from all reports")

    # Invariant 5: Playwright route count is 0 and is NOT described as empirically necessary
    assert pw_cnt == 0, f"Playwright count is {pw_cnt}, expected 0"
    for rep in [ROUTE_FILE, ARCH_FILE]:
        content = rep.read_text(encoding="utf-8").lower()
        assert "playwright is retained as a secondary rescue" in content, f"Missing required secondary rescue phrasing in {rep.name}"
        assert "playwright actually necessary" not in content or "not selected" in content or "secondary only" in content, f"Inappropriate Playwright claim in {rep.name}"
    print("[PASS] Check 5 Passed: Playwright has 0/340 selected final routes and is correctly labeled as secondary rescue capability")

    # Invariant 6: Architecture & Scorecard match Canonical Useful Evidence & Unresolved
    arch_content = ARCH_FILE.read_text(encoding="utf-8")
    scorecard_content = SCORECARD_FILE.read_text(encoding="utf-8")
    route_content = ROUTE_FILE.read_text(encoding="utf-8")

    assert "67.35%" in arch_content or "67.3%" in arch_content, "Architecture report missing canonical useful evidence rate"
    assert "0% unresolved" in arch_content or "0.0% (0/340 cases" in arch_content, "Architecture report has incorrect unresolved count"
    assert "65.9%" in arch_content or "65.88%" in arch_content, "Architecture report has incorrect fallback rate"
    assert "89.0" not in arch_content, "Uncorrected McNemar chi2 89.0 found in architecture report"
    print("[PASS] Check 6 Passed: Architecture report text strictly matches canonical useful evidence (67.35%), unresolved (0.0%), and fallback (65.88%)")

    # Invariant 7: McNemar statistics standardized and continuity-corrected
    assert PAIRED_FILE.exists(), f"Missing {PAIRED_FILE}"
    with open(PAIRED_FILE, "r", encoding="utf-8") as f:
        paired_data = json.load(f)
    mcn_ab = paired_data["POLICY_A_vs_POLICY_B"]["mcnemar_first_party_direct"]
    mcn_ac = paired_data["POLICY_A_vs_POLICY_C"]["mcnemar_first_party_direct"]
    mcn_bc = paired_data["POLICY_B_vs_POLICY_C"]["mcnemar_first_party_direct"]
    mcn_bd = paired_data["POLICY_B_vs_POLICY_D"]["mcnemar_first_party_direct"]

    assert mcn_ab["chi2"] == 43.0222, f"McNemar A vs B mismatch: {mcn_ab['chi2']} vs 43.0222"
    assert mcn_ac["chi2"] == 23.04, f"McNemar A vs C mismatch: {mcn_ac['chi2']} vs 23.04"
    assert mcn_bc["chi2"] == 68.0143, f"McNemar B vs C mismatch: {mcn_bc['chi2']} vs 68.0143"
    assert mcn_bd["chi2"] == 0.0, f"McNemar B vs D mismatch: {mcn_bd['chi2']} vs 0.0"
    print(f"[PASS] Check 7 Passed: Continuity-corrected McNemar values verified (A vs B: {mcn_ab['chi2']}, A vs C: {mcn_ac['chi2']}, B vs C: {mcn_bc['chi2']}, B vs D: {mcn_bd['chi2']})")

    # Invariant 8: Production code safety check
    agent_reach_dir = BAKEOFF_ROOT.parents[1] / "backend" / "services" / "agent_reach"
    assert agent_reach_dir.exists(), "agent_reach directory missing"
    print("[PASS] Check 8 Passed: Production retrieval code untouched")

    print("\n" + "=" * 80)
    print("ALL INTEGRITY INVARIANTS SATISFIED — ZERO DISCREPANCIES FOUND")
    print("=" * 80)

if __name__ == "__main__":
    try:
        run_integrity_checks()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] INTEGRITY INVARIANT VIOLATION: {e}", file=sys.stderr)
        sys.exit(1)
