"""
Local Agent JSON Audit Script
=============================
Directly invokes all Aegis intelligence agents in a local Python process:
1. TrendingAgent
2. ScoutAgent
3. BrandShieldAgent
4. PersonalWatchAgent
5. Claim Verification Pipeline (Truth Dossier)

Captures:
- Raw Python dicts
- Clean JSON serialization
- Deep schema analysis (types, nested keys, array item counts)
- Monitored channels, external signals, and evidence provenance
- Latency (seconds / ms)
- Detected warnings, empty fields, or fallback states

Saves all outputs to: artifacts/local_json_audit/
"""

import os
import sys
import time
import json
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Reconfigure console output for Windows UTF-8
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, "backend", ".env"))

ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "local_json_audit")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def infer_schema(val: Any, depth: int = 0, max_depth: int = 4) -> Any:
    """Infer structural schema recursively from any python data structure."""
    if depth > max_depth:
        return {"type": type(val).__name__, "truncated": True}

    if isinstance(val, dict):
        properties = {}
        for k, v in val.items():
            properties[k] = infer_schema(v, depth + 1, max_depth)
        return {
            "type": "object",
            "field_count": len(val),
            "properties": properties
        }
    elif isinstance(val, list):
        if not val:
            return {"type": "array", "item_count": 0, "items": None}
        sample = val[0]
        return {
            "type": "array",
            "item_count": len(val),
            "sample_item_type": type(sample).__name__,
            "items_schema": infer_schema(sample, depth + 1, max_depth)
        }
    elif isinstance(val, (str, int, float, bool)) or val is None:
        return {
            "type": type(val).__name__ if val is not None else "null",
            "sample": str(val)[:80] if val is not None else None
        }
    else:
        return {"type": str(type(val))}


def serialize_safe(obj: Any) -> Any:
    """Safely convert any python object (dataclass, pydantic, datetime) to JSON-serializable."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): serialize_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [serialize_safe(i) for i in obj]
    return obj


def save_json_and_schema(name: str, data: Dict[str, Any]):
    """Save payload and its inferred schema to artifacts directory."""
    clean_data = serialize_safe(data)
    json_path = os.path.join(ARTIFACTS_DIR, f"{name}.json")
    schema_path = os.path.join(ARTIFACTS_DIR, f"{name}_schema.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)

    schema = infer_schema(clean_data)
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    size_kb = round(os.path.getsize(json_path) / 1024, 2)
    print(f"  [SAVED] {json_path} ({size_kb} KB)")
    print(f"  [SAVED] {schema_path}")
    return json_path, schema_path, size_kb


# ==============================================================================
# AUDIT RUNNERS
# ==============================================================================

def run_trending_audit() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("▶ AUDITING: TrendingAgent")
    print("=" * 70)
    start = time.perf_counter()
    test_query = "AI regulation rumors"

    try:
        from backend.agents.trending_agent import TrendingAgent
        agent = TrendingAgent()
        print(f"  [INFO] Invoking TrendingAgent.scan(asset_name='{test_query}', mode='auto')...")
        res = agent.scan(asset_name=test_query, mode="auto")
        latency = round(time.perf_counter() - start, 3)

        # Telemetry metrics
        trends = res.get("trends", [])
        evidence = res.get("evidence", [])
        threats = res.get("threats", [])
        sources = res.get("sources", {})
        counts = res.get("counts", {})
        telemetry = res.get("telemetry", {})
        limitations = res.get("limitations", [])

        print(f"  [SUCCESS] Completed in {latency}s")
        print(f"  - Discovered Trends: {len(trends)}")
        print(f"  - Total Evidence Signals: {len(evidence)}")
        print(f"  - Monitored Threats: {len(threats)}")
        print(f"  - Platforms Scanned: {list(res.get('platform_breakdown', {}).keys())}")
        print(f"  - News Articles: {counts.get('news', 0)} | Fan Wars / Social: {counts.get('fan_wars', 0)}")
        if limitations:
            print(f"  - Limitations noted: {limitations}")

        save_json_and_schema("trending", res)

        return {
            "status": "PASS",
            "latency_s": latency,
            "input": test_query,
            "trends_count": len(trends),
            "evidence_count": len(evidence),
            "threats_count": len(threats),
            "platforms": list(res.get("platform_breakdown", {}).keys()),
            "limitations": limitations,
            "error": None
        }
    except Exception as e:
        latency = round(time.perf_counter() - start, 3)
        err_msg = str(e)
        print(f"  [FAIL] Error after {latency}s: {err_msg}")
        traceback.print_exc()
        res = {"status": "ERROR", "error": err_msg, "traceback": traceback.format_exc()}
        save_json_and_schema("trending", res)
        return {"status": "FAIL", "latency_s": latency, "error": err_msg}


def run_scout_audit() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("▶ AUDITING: ScoutAgent")
    print("=" * 70)
    start = time.perf_counter()
    test_ticker = "NVDA"
    test_query = "Nvidia Blackwell AI chip delay packaging defect"

    try:
        from backend.agents.scout_agent import ScoutAgent
        scout = ScoutAgent()
        print(f"  [INFO] Invoking ScoutAgent.analyze_stock(ticker='{test_ticker}', query='{test_query}')...")
        res = scout.analyze_stock(ticker=test_ticker, query=test_query)
        latency = round(time.perf_counter() - start, 3)

        stock = res.get("stock", {})
        catalysts = res.get("catalysts", {})
        narratives = res.get("narratives", [])
        contradictions = res.get("contradictions", {})
        misinfo = res.get("misinformation", {})
        short_attack = res.get("short_attack", {})
        sources = res.get("sources", [])

        print(f"  [SUCCESS] Completed in {latency}s")
        print(f"  - Price: ${stock.get('current_price')} | Drop: {stock.get('drop_percent')}% | Z-Score: {stock.get('z_score')}")
        print(f"  - Short Attack Risk: {short_attack.get('risk_level', 'N/A')} (Correlated: {short_attack.get('short_attack_correlated')})")
        print(f"  - Positive Catalysts: {len(catalysts.get('positive', []))} | Negative: {len(catalysts.get('negative', []))}")
        print(f"  - Total Evidence Sources: {len(sources)}")
        print(f"  - Manipulation Risk: {misinfo.get('manipulation_risk')}")

        save_json_and_schema("scout", res)

        return {
            "status": "PASS",
            "latency_s": latency,
            "input": {"ticker": test_ticker, "query": test_query},
            "current_price": stock.get("current_price"),
            "drop_percent": stock.get("drop_percent"),
            "z_score": stock.get("z_score"),
            "sources_count": len(sources),
            "catalysts_count": len(catalysts.get("positive", [])) + len(catalysts.get("negative", [])),
            "short_attack_risk": short_attack.get("risk_level"),
            "error": None
        }
    except Exception as e:
        latency = round(time.perf_counter() - start, 3)
        err_msg = str(e)
        print(f"  [FAIL] Error after {latency}s: {err_msg}")
        traceback.print_exc()
        res = {"status": "ERROR", "error": err_msg, "traceback": traceback.format_exc()}
        save_json_and_schema("scout", res)
        return {"status": "FAIL", "latency_s": latency, "error": err_msg}


def run_brandshield_audit() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("▶ AUDITING: BrandShieldAgent")
    print("=" * 70)
    start = time.perf_counter()
    brand_name = "Nike"
    query = "Nike Air Max counterfeit fake store"

    try:
        from backend.agents.brandshield_agent import BrandShieldAgent
        agent = BrandShieldAgent()
        print(f"  [INFO] Invoking BrandShieldAgent.scan(brand_name='{brand_name}', query='{query}')...")
        res = agent.scan(brand_name=brand_name, query=query)
        latency = round(time.perf_counter() - start, 3)

        threats = res.get("threats", [])
        claims = res.get("claims", [])
        counterfeits = res.get("counterfeits", [])
        impersonations = res.get("impersonations", [])
        review_intel = res.get("review_intel", {})
        dossiers = res.get("dossiers", [])
        findings = res.get("findings", [])

        print(f"  [SUCCESS] Completed in {latency}s")
        print(f"  - Total Findings: {len(findings)} | Threat Count: {res.get('threat_count')} | Safe: {res.get('safe_count')}")
        print(f"  - Categorized Threats: {len(threats)} | Dossiers: {len(dossiers)}")
        print(f"  - Counterfeits Spotted: {len(counterfeits)} | Impersonations: {len(impersonations)}")
        print(f"  - Review Manipulation Detected: {review_intel.get('review_manipulation_detected')}")
        print(f"  - Platforms Scanned: {res.get('platforms', [])}")

        save_json_and_schema("brandshield", res)

        return {
            "status": "PASS",
            "latency_s": latency,
            "input": {"brand_name": brand_name, "query": query},
            "findings_count": len(findings),
            "threat_count": res.get("threat_count"),
            "safe_count": res.get("safe_count"),
            "counterfeits_count": len(counterfeits),
            "dossiers_count": len(dossiers),
            "review_manipulation": review_intel.get("review_manipulation_detected"),
            "platforms": res.get("platforms", []),
            "error": None
        }
    except Exception as e:
        latency = round(time.perf_counter() - start, 3)
        err_msg = str(e)
        print(f"  [FAIL] Error after {latency}s: {err_msg}")
        traceback.print_exc()
        res = {"status": "ERROR", "error": err_msg, "traceback": traceback.format_exc()}
        save_json_and_schema("brandshield", res)
        return {"status": "FAIL", "latency_s": latency, "error": err_msg}


def run_personal_watch_audit() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("▶ AUDITING: PersonalWatchAgent")
    print("=" * 70)
    start = time.perf_counter()
    vip_profile = {
        "name": "Sam Altman",
        "official_handles": {"twitter": "@sama"},
        "category": "executive",
        "aliases": ["Sama"]
    }

    try:
        from backend.agents.personal_agent import process_personal_watch
        print(f"  [INFO] Invoking process_personal_watch(vip_profile={vip_profile['name']})...")
        res = process_personal_watch(vip_profile)
        latency = round(time.perf_counter() - start, 3)

        summary = res.get("summary", {})
        mentions = res.get("mentions", [])
        threats = res.get("threats", [])
        alerts = res.get("alerts", [])
        deepfakes = res.get("deepfake_claims", [])
        impersonations = res.get("suspected_impersonations", [])
        dossiers = res.get("dossiers", [])
        spread = res.get("spread_analysis", {})

        print(f"  [SUCCESS] Completed in {latency}s")
        print(f"  - Sources Scanned: {summary.get('sources_scanned', len(mentions))}")
        print(f"  - Unique Sources: {summary.get('unique_sources')}")
        print(f"  - Threats Discovered: {len(threats)} (High: {res.get('high_risk_count')}, Med: {res.get('medium_risk_count')})")
        print(f"  - Active Alerts: {len(alerts)}")
        print(f"  - Suspected Impersonations: {len(impersonations)} | Deepfake Claims: {len(deepfakes)}")
        print(f"  - Dossiers: {len(dossiers)}")

        save_json_and_schema("personal_watch", res)

        return {
            "status": "PASS",
            "latency_s": latency,
            "input": vip_profile,
            "sources_scanned": summary.get("sources_scanned", len(mentions)),
            "threats_discovered": len(threats),
            "alerts_count": len(alerts),
            "impersonations_count": len(impersonations),
            "deepfakes_count": len(deepfakes),
            "dossiers_count": len(dossiers),
            "error": None
        }
    except Exception as e:
        latency = round(time.perf_counter() - start, 3)
        err_msg = str(e)
        print(f"  [FAIL] Error after {latency}s: {err_msg}")
        traceback.print_exc()
        res = {"status": "ERROR", "error": err_msg, "traceback": traceback.format_exc()}
        save_json_and_schema("personal_watch", res)
        return {"status": "FAIL", "latency_s": latency, "error": err_msg}


def run_claim_verification_audit() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("▶ AUDITING: Claim Verification Pipeline (Truth Dossier)")
    print("=" * 70)
    start = time.perf_counter()
    test_claim = "WhatsApp has introduced three red ticks that mean a government agency has registered a case against you."

    try:
        from backend.api.claims import verify_claim_sync, ClaimVerifyRequest
        req = ClaimVerifyRequest(claim_text=test_claim)
        print(f"  [INFO] Invoking verify_claim_sync('{test_claim[:50]}...')...")
        res = asyncio.run(verify_claim_sync(req))
        latency = round(time.perf_counter() - start, 3)

        verdict = res.get("verdict")
        confidence = res.get("confidence")
        status = res.get("status")
        truth_dossier = res.get("truth_dossier", {})
        evidence_chain = res.get("evidence_chain", [])
        lineage_dag = res.get("source_lineage_dag", {})
        bayesian = res.get("bayesian_tensor", {})

        print(f"  [SUCCESS] Completed in {latency}s")
        print(f"  - Verdict: {verdict} | Confidence: {confidence} | Status: {status}")
        print(f"  - Truth Dossier Sections: {list(truth_dossier.keys()) if isinstance(truth_dossier, dict) else 'Generated'}")
        print(f"  - Evidence Chain Items: {len(evidence_chain)}")
        print(f"  - Lineage DAG Nodes: {len(lineage_dag.get('nodes', []))} | Edges: {len(lineage_dag.get('edges', []))}")

        save_json_and_schema("claim_verification", res)

        return {
            "status": "PASS",
            "latency_s": latency,
            "input": test_claim,
            "verdict": verdict,
            "confidence": confidence,
            "evidence_chain_count": len(evidence_chain),
            "dag_nodes": len(lineage_dag.get("nodes", [])),
            "error": None
        }
    except Exception as e:
        latency = round(time.perf_counter() - start, 3)
        err_msg = str(e)
        print(f"  [FAIL] Error after {latency}s: {err_msg}")
        traceback.print_exc()
        res = {"status": "ERROR", "error": err_msg, "traceback": traceback.format_exc()}
        save_json_and_schema("claim_verification", res)
        return {"status": "FAIL", "latency_s": latency, "error": err_msg}


def generate_report_md(summary: Dict[str, Any]):
    """Generate comprehensive markdown audit report."""
    md_path = os.path.join(ARTIFACTS_DIR, "report.md")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    content = f"""# Aegis Protocol — Local Agent JSON Audit Report
**Timestamp:** `{now}`  
**Execution Mode:** Local Python Process (Direct Agent Class Invocations)  
**Render Quota Usage:** 0 instance-hours (Zero production compute consumed)

---

## Executive Summary

| Agent | Status | Latency (s) | Core Signals / Findings | Primary Schema Output |
| :--- | :---: | :---: | :--- | :--- |
| **TrendingAgent** | `{summary['trending']['status']}` | `{summary['trending']['latency_s']}s` | {summary['trending'].get('trends_count', 0)} trends, {summary['trending'].get('evidence_count', 0)} evidence items | `artifacts/local_json_audit/trending.json` |
| **ScoutAgent** | `{summary['scout']['status']}` | `{summary['scout']['latency_s']}s` | {summary['scout'].get('catalysts_count', 0)} catalysts, {summary['scout'].get('sources_count', 0)} sources (Short risk: {summary['scout'].get('short_attack_risk', 'N/A')}) | `artifacts/local_json_audit/scout.json` |
| **BrandShieldAgent** | `{summary['brandshield']['status']}` | `{summary['brandshield']['latency_s']}s` | {summary['brandshield'].get('findings_count', 0)} findings, {summary['brandshield'].get('counterfeits_count', 0)} counterfeits, {summary['brandshield'].get('dossiers_count', 0)} dossiers | `artifacts/local_json_audit/brandshield.json` |
| **PersonalWatchAgent** | `{summary['personal_watch']['status']}` | `{summary['personal_watch']['latency_s']}s` | {summary['personal_watch'].get('sources_scanned', 0)} sources, {summary['personal_watch'].get('threats_discovered', 0)} threats, {summary['personal_watch'].get('alerts_count', 0)} alerts | `artifacts/local_json_audit/personal_watch.json` |
| **Claim Verification** | `{summary['claim_verification']['status']}` | `{summary['claim_verification']['latency_s']}s` | Verdict: `{summary['claim_verification'].get('verdict')}` (Conf: {summary['claim_verification'].get('confidence')}) | `artifacts/local_json_audit/claim_verification.json` |

---

## Detailed Agent Diagnostics

### 1. Trending Agent (`TrendingAgent.scan`)
- **Input:** `{summary['trending'].get('input')}`
- **Discovered Trends:** `{summary['trending'].get('trends_count')}`
- **Evidence Gathered:** `{summary['trending'].get('evidence_count')}`
- **Platforms Scanned:** `{summary['trending'].get('platforms')}`
- **Limitations / Fallbacks:** `{summary['trending'].get('limitations')}`
- **Error:** `{summary['trending'].get('error') or 'None'}`

### 2. Scout Agent (`ScoutAgent.analyze_stock`)
- **Input:** `{summary['scout'].get('input')}`
- **Current Price:** `${summary['scout'].get('current_price')} (Drop: {summary['scout'].get('drop_percent')}%, Z-score: {summary['scout'].get('z_score')})`
- **Discovered Catalysts:** `{summary['scout'].get('catalysts_count')}`
- **Evidence Sources:** `{summary['scout'].get('sources_count')}`
- **Short Attack Risk:** `{summary['scout'].get('short_attack_risk')}`
- **Error:** `{summary['scout'].get('error') or 'None'}`

### 3. BrandShield Agent (`BrandShieldAgent.scan`)
- **Input:** `{summary['brandshield'].get('input')}`
- **Total Findings:** `{summary['brandshield'].get('findings_count')} (Threats: {summary['brandshield'].get('threat_count')}, Safe: {summary['brandshield'].get('safe_count')})`
- **Counterfeit Detections:** `{summary['brandshield'].get('counterfeits_count')}`
- **Investigation Dossiers:** `{summary['brandshield'].get('dossiers_count')}`
- **Review Manipulation:** `{summary['brandshield'].get('review_manipulation')}`
- **Platforms Covered:** `{summary['brandshield'].get('platforms')}`
- **Error:** `{summary['brandshield'].get('error') or 'None'}`

### 4. Personal Watch Agent (`process_personal_watch`)
- **Input:** `{summary['personal_watch'].get('input')}`
- **Sources Scanned:** `{summary['personal_watch'].get('sources_scanned')}`
- **Threats Identified:** `{summary['personal_watch'].get('threats_discovered')}`
- **Impersonations:** `{summary['personal_watch'].get('impersonations_count')}`
- **Deepfake Claims:** `{summary['personal_watch'].get('deepfakes_count')}`
- **Active Alerts:** `{summary['personal_watch'].get('alerts_count')}`
- **Dossiers Built:** `{summary['personal_watch'].get('dossiers_count')}`
- **Error:** `{summary['personal_watch'].get('error') or 'None'}`

### 5. Claim Verification Pipeline (`verify_claim_sync`)
- **Input Claim:** `{summary['claim_verification'].get('input')}`
- **Verdict:** `{summary['claim_verification'].get('verdict')}`
- **Calibrated Confidence:** `{summary['claim_verification'].get('confidence')}`
- **Evidence Chain Nodes:** `{summary['claim_verification'].get('evidence_chain_count')}`
- **Source Lineage DAG Nodes:** `{summary['claim_verification'].get('dag_nodes')}`
- **Error:** `{summary['claim_verification'].get('error') or 'None'}`

---

## Generated Artifacts Catalog
- `artifacts/local_json_audit/summary.json`
- `artifacts/local_json_audit/trending.json` & `trending_schema.json`
- `artifacts/local_json_audit/scout.json` & `scout_schema.json`
- `artifacts/local_json_audit/brandshield.json` & `brandshield_schema.json`
- `artifacts/local_json_audit/personal_watch.json` & `personal_watch_schema.json`
- `artifacts/local_json_audit/claim_verification.json` & `claim_verification_schema.json`
- `artifacts/local_json_audit/report.md`
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  [SAVED] {md_path}")


def main():
    print("=" * 80)
    print("  AEGIS PROTOCOL — LOCAL AGENT JSON AUDIT")
    print("=" * 80)
    total_start = time.perf_counter()

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_latency_s": 0.0,
        "all_passed": False
    }

    # 1. Trending Agent
    summary["trending"] = run_trending_audit()

    # 2. Scout Agent
    summary["scout"] = run_scout_audit()

    # 3. BrandShield Agent
    summary["brandshield"] = run_brandshield_audit()

    # 4. Personal Watch Agent
    summary["personal_watch"] = run_personal_watch_audit()

    # 5. Claim Verification Pipeline
    summary["claim_verification"] = run_claim_verification_audit()

    summary["total_latency_s"] = round(time.perf_counter() - total_start, 3)
    summary["all_passed"] = all(
        summary[k].get("status") == "PASS"
        for k in ["trending", "scout", "brandshield", "personal_watch", "claim_verification"]
    )

    summary_path = os.path.join(ARTIFACTS_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] {summary_path}")

    generate_report_md(summary)

    print("\n" + "=" * 80)
    print(f"  AUDIT COMPLETE: All Passed={summary['all_passed']} (Total Time: {summary['total_latency_s']}s)")
    print("=" * 80)


if __name__ == "__main__":
    main()
