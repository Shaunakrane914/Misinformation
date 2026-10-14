"""
Aegis Protocol — Phase 8D Authoritative Source Live Probe
=========================================================
Executes independent, real-network live requests to verify the 4 new authoritative
source integrations:
  1. SEC EDGAR (data.sec.gov submission metadata only)
  2. NIST NVD (services.nvd.nist.gov CVE 2.0 API)
  3. arXiv Preprints (export.arxiv.org Atom API)
  4. Google FactCheck (factchecktools.googleapis.com ClaimReview API)

Records real provider observations, latency, extracted fields, errors,
authentication requirements, and provenance without mocks.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import argparse
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import (
    fetch_sec_submissions,
    normalize_sec_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.nist_nvd import (
    fetch_nist_cve,
    normalize_nist_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.arxiv_preprints import (
    fetch_arxiv_preprints,
    normalize_arxiv_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.fact_check import (
    fetch_fact_check_claims,
    normalize_fact_check_items,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase8d_live_probe")


def run_live_probe() -> Dict[str, Any]:
    results: Dict[str, Any] = {
        "suite": "Phase 8D Authoritative Source Live Verification",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "probes": {},
    }

    # ── 1. SEC EDGAR ─────────────────────────────────────────────────────────
    logger.info("Executing live probe 1/4: SEC EDGAR Submissions API...")
    t0 = time.time()
    try:
        sec_res = fetch_sec_submissions("AAPL", limit=5)
        lat_sec = round((time.time() - t0) * 1000, 2)
        items_sec = sec_res.get("items", [])
        frags_sec = normalize_sec_items(items_sec, query_text="AAPL")
        sample_sec = None
        if frags_sec:
            f = frags_sec[0]
            sample_sec = {
                "title": f.title,
                "url": f.url,
                "author": f.author,
                "published": f.published,
                "content_depth": f.content_depth,
                "retrieval_mode": f.retrieval_mode,
                "snippet": f.snippet[:150],
            }
        results["probes"]["sec_edgar"] = {
            "target": "SEC EDGAR Submissions",
            "query": "AAPL (CIK 0000320193)",
            "status": sec_res.get("status"),
            "latency_ms": lat_sec,
            "raw_items_count": len(items_sec),
            "fragment_count": len(frags_sec),
            "auth_required": False,
            "error": sec_res.get("error"),
            "extracted_fields": ["cik", "company_name", "form", "filing_date", "report_date", "accession_number", "doc_url"],
            "sample_fragment": sample_sec,
        }
    except Exception as exc:
        results["probes"]["sec_edgar"] = {
            "status": "FAILED",
            "latency_ms": round((time.time() - t0) * 1000, 2),
            "error": str(exc),
        }

    # ── 2. NIST NVD ──────────────────────────────────────────────────────────
    logger.info("Executing live probe 2/4: NIST NVD CVE 2.0 API...")
    t0 = time.time()
    try:
        nvd_res = fetch_nist_cve("CVE-2021-44228", limit=3)
        lat_nvd = round((time.time() - t0) * 1000, 2)
        items_nvd = nvd_res.get("items", [])
        frags_nvd = normalize_nist_items(items_nvd, query_text="CVE-2021-44228")
        sample_nvd = None
        if frags_nvd:
            f = frags_nvd[0]
            sample_nvd = {
                "title": f.title,
                "url": f.url,
                "author": f.author,
                "published": f.published,
                "content_depth": f.content_depth,
                "retrieval_mode": f.retrieval_mode,
                "snippet": f.snippet[:150],
            }
        results["probes"]["nist_nvd"] = {
            "target": "NIST NVD CVE 2.0",
            "query": "CVE-2021-44228",
            "status": nvd_res.get("status"),
            "latency_ms": lat_nvd,
            "raw_items_count": len(items_nvd),
            "fragment_count": len(frags_nvd),
            "auth_required": False,
            "error": nvd_res.get("error"),
            "extracted_fields": ["cve_id", "cvss_score", "severity", "description", "references", "published", "nvd_url"],
            "sample_fragment": sample_nvd,
        }
    except Exception as exc:
        results["probes"]["nist_nvd"] = {
            "status": "FAILED",
            "latency_ms": round((time.time() - t0) * 1000, 2),
            "error": str(exc),
        }

    # ── 3. arXiv Preprints ───────────────────────────────────────────────────
    logger.info("Executing live probe 3/4: arXiv Atom API...")
    t0 = time.time()
    try:
        arxiv_res = fetch_arxiv_preprints("quantum computing", limit=3)
        lat_arxiv = round((time.time() - t0) * 1000, 2)
        items_arxiv = arxiv_res.get("items", [])
        frags_arxiv = normalize_arxiv_items(items_arxiv, query_text="quantum computing")
        sample_arxiv = None
        if frags_arxiv:
            f = frags_arxiv[0]
            sample_arxiv = {
                "title": f.title,
                "url": f.url,
                "author": f.author,
                "published": f.published,
                "content_depth": f.content_depth,
                "retrieval_mode": f.retrieval_mode,
                "snippet": f.snippet[:150],
            }
        results["probes"]["arxiv"] = {
            "target": "arXiv Academic Preprints",
            "query": "quantum computing",
            "status": arxiv_res.get("status"),
            "latency_ms": lat_arxiv,
            "raw_items_count": len(items_arxiv),
            "fragment_count": len(frags_arxiv),
            "auth_required": False,
            "error": arxiv_res.get("error"),
            "extracted_fields": ["arxiv_id", "title", "authors", "summary", "category", "published", "abs_url", "pdf_url"],
            "sample_fragment": sample_arxiv,
        }
    except Exception as exc:
        results["probes"]["arxiv"] = {
            "status": "FAILED",
            "latency_ms": round((time.time() - t0) * 1000, 2),
            "error": str(exc),
        }

    # ── 4. Google FactCheck ClaimReview ──────────────────────────────────────
    logger.info("Executing live probe 4/4: Google FactCheck Tools API...")
    t0 = time.time()
    try:
        fc_res = fetch_fact_check_claims("moon landing", limit=3)
        lat_fc = round((time.time() - t0) * 1000, 2)
        items_fc = fc_res.get("items", [])
        frags_fc = normalize_fact_check_items(items_fc, query_text="moon landing")
        err = fc_res.get("error") or ""
        # 403 Forbidden indicates Google requires an active API key on this endpoint
        is_auth = fc_res.get("status") == "AUTH_REQUIRED" or "403" in err or "key" in err.lower()
        results["probes"]["google_factcheck"] = {
            "target": "Google FactCheck ClaimReview",
            "query": "moon landing",
            "status": "AUTH_REQUIRED" if is_auth else fc_res.get("status"),
            "latency_ms": lat_fc,
            "raw_items_count": len(items_fc),
            "fragment_count": len(frags_fc),
            "auth_required": is_auth,
            "error": fc_res.get("error"),
            "extracted_fields": ["claim_text", "claimant", "publisher", "rating", "review_url", "review_date"],
            "sample_fragment": None,
            "honest_disclosure": "Requires GOOGLE_FACTCHECK_API_KEY; missing credentials abstain without a network request.",
        }
    except Exception as exc:
        results["probes"]["google_factcheck"] = {
            "status": "FAILED",
            "latency_ms": round((time.time() - t0) * 1000, 2),
            "error": str(exc),
        }

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    out_dir = args.output_root or REPO_ROOT / "artifacts" / "phase8_independent_sources" / (time.strftime("%Y-%m-%d_%H-%M-%SZ", time.gmtime()) + "_" + uuid.uuid4().hex[:8])
    out_dir.mkdir(parents=True, exist_ok=False)
    res = run_live_probe()
    res["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    res["dirty_source"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True).strip())
    from scripts.audits.run_realworld_investigation_audit import sanitize_audit_data
    res = sanitize_audit_data(res)
    out_file = out_dir / "summary.json"
    with open(out_file, "x", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("\n" + json.dumps(res, indent=2))
    print(f"\nWritten real machine-readable probe evidence to {out_file}")
