"""
Aegis Protocol — Phase 7.1 Isolated Release-Candidate Smoke Validation
=====================================================================
Executes isolated staging-like smoke validation across:
1. Liveness (/api/healthz) and readiness (/api/readyz) probes
2. Capability status (/api/agent-reach/capabilities) and doctor (/api/agent-reach/doctor)
3. Four agent production entrypoints (Scout, Trending, BrandShield, Personal Watch)
4. Representative investigation claims:
   - Nvidia RTX 5090 discontinuation rumor (hardware)
   - Nvidia quarterly revenue allegation (financial)
   - Anthropic official-account identity (identity)
   - Tata Sons financial news (regulatory/corporate)
   - Zero-evidence / empty claim guard
5. Frontend page availability and secret redaction invariants
"""

import sys
import json
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from starlette.testclient import TestClient
from backend.main import app
from backend.core.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("v1_rc_smoke")


def run_isolated_smoke_validation() -> dict:
    results = {
        "suite": "Phase 7.1 Isolated Release-Candidate Smoke Validation",
        "timestamp": None,
        "gates": {},
        "scenarios": {},
        "errors": []
    }
    client = TestClient(app)

    # ── 1. Probes & Health ───────────────────────────────────────────────────
    logger.info("Verifying liveness and readiness endpoints...")
    hz = client.get("/api/healthz")
    assert hz.status_code == 200, f"/api/healthz failed: {hz.status_code}"
    hz_data = hz.json()
    assert hz_data.get("status") == "ok"
    results["gates"]["healthz"] = {"status": "PASS", "data": hz_data}

    rz = client.get("/api/readyz")
    assert rz.status_code == 200, f"/api/readyz failed: {rz.status_code}"
    rz_data = rz.json()
    assert rz_data.get("status") == "ready"
    assert "Readiness does not imply" in rz_data.get("note", "")
    results["gates"]["readyz"] = {"status": "PASS", "data": rz_data}

    # ── 2. Capabilities & Doctor ─────────────────────────────────────────────
    logger.info("Verifying capability inventory and doctor diagnostics...")
    caps = client.get("/api/agent-reach/capabilities")
    assert caps.status_code == 200, f"/api/agent-reach/capabilities failed: {caps.status_code}"
    caps_data = caps.json()
    channels = caps_data.get("channels", {})
    assert "twitter" in channels and "reddit" in channels and "github" in channels
    results["gates"]["capabilities"] = {"status": "PASS", "channels_count": len(channels)}

    doc = client.get("/api/agent-reach/doctor")
    assert doc.status_code == 200, f"/api/agent-reach/doctor failed: {doc.status_code}"
    doc_data = doc.json()
    results["gates"]["doctor"] = {"status": "PASS", "summary": doc_data.get("summary")}

    # Verify no secrets in doctor output
    doc_str = json.dumps(doc_data).lower()
    for sensitive in ("aizasy", "sk-", "bearer ", "token=", "key="):
        assert sensitive not in doc_str, f"Secret leak pattern '{sensitive}' found in doctor!"
    results["gates"]["secret_redaction"] = {"status": "PASS"}

    # ── 3. Frontend Pages ────────────────────────────────────────────────────
    logger.info("Verifying four agent frontend interfaces...")
    agent_pages = ["/scout-agent", "/trending-agent", "/brandshield-agent", "/personal-watch-agent"]
    root_resp = client.get("/")
    assert root_resp.status_code == 200, f"Root / returned {root_resp.status_code}"
    for p in agent_pages:
        resp = client.get(p)
        assert resp.status_code == 200, f"Page {p} returned {resp.status_code}"
        assert "operation-health.js" in resp.text, f"Page {p} missing operation-health.js"
    results["gates"]["frontend_pages"] = {"status": "PASS", "pages_verified": len(agent_pages) + 1}

    # ── 4. Representative Investigation Scenarios ────────────────────────────
    # Scenario A: Nvidia quarterly revenue allegation (Scout)
    logger.info("Running Scenario A: Nvidia quarterly revenue (Scout)...")
    scout_resp = client.post("/api/scout/analyze", json={
        "ticker": "NVDA",
        "company_name": "Nvidia",
        "claim": "Nvidia manipulated quarterly revenue disclosures"
    })
    assert scout_resp.status_code == 200, f"Scout failed: {scout_resp.text}"
    scout_data = scout_resp.json()
    results["scenarios"]["nvidia_revenue_scout"] = {
        "status": "PASS",
        "report_id": scout_data.get("id"),
        "evidence_count": len(scout_data.get("evidence", []))
    }

    # Scenario B: Nvidia RTX 5090 discontinuation rumor (Trending)
    logger.info("Running Scenario B: Nvidia RTX 5090 rumor (Trending)...")
    trending_resp = client.post("/api/trending/scan", json={
        "query": "Nvidia RTX 5090 reportedly discontinued",
        "mode": "entity"
    })
    assert trending_resp.status_code == 200, f"Trending failed: {trending_resp.text}"
    trending_data = trending_resp.json()
    results["scenarios"]["nvidia_rtx5090_trending"] = {
        "status": "PASS",
        "trend_count": len(trending_data.get("narratives", trending_data.get("trends", [])))
    }

    # Scenario C: Tata Sons financial news (BrandShield)
    logger.info("Running Scenario C: Tata Sons financial news (BrandShield)...")
    brand_resp = client.post("/api/brandshield/scan", json={
        "brand_name": "Tata Sons",
        "query": "Tata Sons regulatory investigation and executive changes"
    })
    assert brand_resp.status_code == 200, f"BrandShield failed: {brand_resp.text}"
    brand_data = brand_resp.json()
    results["scenarios"]["tata_sons_brandshield"] = {
        "status": "PASS",
        "threats_count": len(brand_data.get("threats", []))
    }

    # Scenario D: Anthropic official identity (Personal Watch)
    logger.info("Running Scenario D: Anthropic identity (Personal Watch)...")
    pw_resp = client.post("/api/personal-watch/scan", json={
        "name": "Anthropic",
        "category": "public_figure",
        "query": "Anthropic official identity and AI security announcements"
    })
    assert pw_resp.status_code == 200, f"Personal Watch failed: {pw_resp.text}"
    pw_data = pw_resp.json()
    results["scenarios"]["anthropic_personal_watch"] = {
        "status": "PASS",
        "alerts_count": len(pw_data.get("alerts", []))
    }

    # Scenario E: Zero-evidence guard
    logger.info("Running Scenario E: Zero-evidence guard...")
    empty_resp = client.post("/api/claims/verify", json={
        "claim_text": "xyznonexistententity1239999 claimed moon is made of purple cheese",
        "force_refresh": True
    })
    assert empty_resp.status_code == 200, f"Empty claim failed: {empty_resp.text}"
    empty_data = empty_resp.json()
    assert empty_data.get("verdict") in ("UNVERIFIED", "INSUFFICIENT_EVIDENCE", "CONTESTED", "NOT_FOUND", "REFUTED")
    results["scenarios"]["zero_evidence_guard"] = {
        "status": "PASS",
        "verdict": empty_data.get("verdict")
    }

    results["verdict"] = "READY FOR OWNER DEPLOYMENT APPROVAL (SMOKE PASS)"
    return results


if __name__ == "__main__":
    res = run_isolated_smoke_validation()
    out_file = REPO_ROOT / "artifacts" / "phase7_1_smoke_validation_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSmoke validation completed successfully. Results written to {out_file}")
    print(json.dumps(res, indent=2))
