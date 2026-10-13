"""
Aegis Protocol — NIST NVD / CVE Authoritative Vulnerability Acquisition Adapter
================================================================================
Acquires verified vulnerability disclosures, CVSS scores, and official advisories
directly from the National Institute of Standards and Technology (NVD) CVE 2.0 API.
Enforces 15-point source contract, SSRF safety, and bounded payload limits.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.network.http import (
    decode_bounded_http_body,
    fetch_public_http,
    BoundedHTTPResponse,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode

logger = logging.getLogger(__name__)

CVE_PATTERN = re.compile(r'\bCVE-(?:19|20)\d{2}-\d{4,}\b', re.I)


def fetch_nist_cve(
    query_or_cve: str,
    limit: int = 5,
    http_fetcher: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Acquire verified vulnerability records from NIST NVD CVE 2.0 API.
    URL: https://services.nvd.nist.gov/rest/json/cves/2.0
    """
    fetcher = http_fetcher if http_fetcher is not None else fetch_public_http
    clean = query_or_cve.strip()
    cve_match = CVE_PATTERN.search(clean)

    if cve_match:
        cve_id = cve_match.group(0).upper()
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
    else:
        encoded_kw = urllib.parse.quote(clean)
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={encoded_kw}&resultsPerPage={min(limit, 10)}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "AegisProtocol MisinfoResearch/1.0",
        "Accept-Encoding": "identity",
    }

    try:
        response: BoundedHTTPResponse = fetcher(
            url,
            headers=headers,
            timeout=5.0,
            max_bytes=1_000_000,
        )
        raw_bytes = decode_bounded_http_body(response, max_bytes=1_000_000)
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        logger.warning(f"[NIST NVD] Fetch failure for '{clean}': {e}")
        return {
            "status": "FAILED",
            "error": str(e),
            "items": [],
            "transport": {"endpoint": url}
        }

    vulns = data.get("vulnerabilities", [])
    parsed_items: List[Dict[str, Any]] = []

    for entry in vulns[:limit]:
        cve_dict = entry.get("cve", {})
        cid = cve_dict.get("id", "")
        published = cve_dict.get("published", "")
        last_modified = cve_dict.get("lastModified", "")
        status = cve_dict.get("vulnStatus", "")

        # Extract English description
        desc = "No description provided."
        for d in cve_dict.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", desc)
                break

        # Extract CVSS metric
        cvss_score = None
        severity = "UNKNOWN"
        metrics = cve_dict.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [])
        if cvss_v31:
            data_v31 = cvss_v31[0].get("cvssData", {})
            cvss_score = data_v31.get("baseScore")
            severity = data_v31.get("baseSeverity", "UNKNOWN")
        elif metrics.get("cvssMetricV30"):
            data_v30 = metrics["cvssMetricV30"][0].get("cvssData", {})
            cvss_score = data_v30.get("baseScore")
            severity = data_v30.get("baseSeverity", "UNKNOWN")

        refs = [r.get("url", "") for r in cve_dict.get("references", []) if r.get("url")]

        parsed_items.append({
            "cve_id": cid,
            "published": published,
            "last_modified": last_modified,
            "vuln_status": status,
            "description": desc,
            "cvss_score": cvss_score,
            "severity": severity,
            "references": refs[:5],
            "nvd_url": f"https://nvd.nist.gov/vuln/detail/{cid}" if cid else "https://nvd.nist.gov",
        })

    return {
        "status": "SUCCESS",
        "total_results": data.get("totalResults", len(parsed_items)),
        "items": parsed_items,
        "transport": {
            "endpoint": url,
            "status_code": response.status_code,
            "latency_ms": response.latency_ms,
        }
    }


def normalize_nist_items(
    items: List[Dict[str, Any]],
    query_id: str = "",
    query_class: str = "",
    query_text: str = ""
) -> List[EvidenceFragment]:
    """Normalize NIST NVD items into typed EvidenceFragments."""
    fragments: List[EvidenceFragment] = []
    for item in items:
        cid = item["cve_id"]
        sev = item["severity"]
        score = item["cvss_score"]
        title = f"{cid} Official Advisory: {sev} (CVSS {score})" if score else f"{cid} Vulnerability Advisory"
        snippet = (
            f"NIST National Vulnerability Database Official Record: {cid}. "
            f"Severity: {sev} (Score: {score}). Status: {item['vuln_status']}. "
            f"Description: {item['description'][:240]}"
        )
        frag = EvidenceFragment(
            platform="nist_cve",
            title=title,
            content=item["description"],
            snippet=snippet,
            url=item["nvd_url"],
            author="National Institute of Standards and Technology (NIST NVD)",
            published=item["published"],
            score=95.0,
            retrieval_method="nist_nvd_rest",
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id="nist-nvd-cve-api",
            channel_name="nist_cve",
            requested_channel="nist_cve",
            actual_retrieval_channel="nist_cve",
            content_depth="DIRECT_CONTENT",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            raw_metadata={
                "cve_id": cid,
                "cvss_score": score,
                "severity": sev,
                "vuln_status": item["vuln_status"],
                "references": item["references"],
                "source_role": "PRIMARY",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_authority": "OFFICIAL_ADVISORY",
                "primary_source": True,
                "reliability_score": 0.95,
                "canonical_url": item["nvd_url"],
            }
        )
        fragments.append(frag)
    return fragments
