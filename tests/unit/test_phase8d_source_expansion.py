"""
Unit and integration tests for Phase 8D Source Expansion:
Authoritative adapters (SEC EDGAR, NIST NVD, arXiv, Fact Check ClaimReview),
runtime capability assessment, standard routing dispatch, and source planning.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.infrastructure.acquisition.adapters.authoritative.arxiv_preprints import (
    fetch_arxiv_preprints,
    normalize_arxiv_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.fact_check import (
    fetch_fact_check_claims,
    normalize_fact_check_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.nist_nvd import (
    fetch_nist_cve,
    normalize_nist_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import (
    fetch_sec_submissions,
    normalize_sec_items,
    resolve_cik,
)
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.native.channel_capabilities import (
    AUTHORITATIVE_CAPABILITY_MATRIX,
    get_capability,
)
from backend.services.agent_reach.native.operation_capabilities import (
    EXECUTABLE_CAPABILITIES,
    OPERATION_DEPTHS,
    PUBLIC_UNAUTHENTICATED_OPERATIONS,
    runtime_operation_capabilities,
)
from backend.services.agent_reach.native.router import NativeRouter
from backend.services.agent_reach.source_planner import SourcePlanningEngine


def _make_http_response(body: bytes, endpoint: str = "https://example.internal", content_type: str = "application/json") -> BoundedHTTPResponse:
    return BoundedHTTPResponse(
        body=body,
        endpoint=endpoint,
        status_code=200,
        content_type=content_type,
        headers={"content-type": content_type},
        latency_ms=10,
        attempts=1,
    )


# ── 1. SEC EDGAR Primary Source Adapter ──────────────────────────────────────

def test_sec_edgar_resolve_cik():
    assert resolve_cik("NVDA") == "0001045810"
    assert resolve_cik("aapl") == "0000320193"
    assert resolve_cik("MSFT") == "0000789019"
    assert resolve_cik("320193") == "0000320193"
    assert resolve_cik("unknown_xyz_random_corp_99999") is None


def test_sec_edgar_fetch_and_normalize():
    mock_payload = {
        "cik": "0001045810",
        "entityType": "Operating",
        "sic": "3674",
        "sicDescription": "Semiconductors",
        "name": "NVIDIA CORP",
        "tickers": ["NVDA"],
        "filings": {
            "recent": {
                "accessionNumber": ["0001045810-24-000029", "0001045810-24-000015"],
                "filingDate": ["2024-02-21", "2024-01-10"],
                "reportDate": ["2024-01-28", "2023-12-31"],
                "acceptanceDateTime": ["2024-02-21T16:30:00.000Z", "2024-01-10T16:00:00.000Z"],
                "act": ["34", "34"],
                "form": ["10-K", "8-K"],
                "fileNumber": ["000-23985", "000-23985"],
                "filmNumber": ["24658092", "24658091"],
                "items": ["", "5.02"],
                "size": [1048576, 52428],
                "isXBRL": [1, 1],
                "isInlineXBRL": [1, 1],
                "primaryDocument": ["nvda-20240128.htm", "nvda-20240110.htm"],
                "primaryDocDescription": ["10-K ANNUAL REPORT", "8-K CURRENT REPORT"],
            }
        }
    }

    def mock_fetcher(url, **kwargs):
        return _make_http_response(json.dumps(mock_payload).encode("utf-8"), endpoint=url)

    res = fetch_sec_submissions("NVDA", limit=5, http_fetcher=mock_fetcher)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) == 2
    assert res["items"][0]["form"] == "10-K"
    assert res["items"][0]["cik"] == "0001045810"

    fragments = normalize_sec_items(res["items"], query_id="q1", query_class="financial", query_text="NVDA")
    assert len(fragments) == 2
    frag10k = fragments[0]
    assert frag10k.platform == "sec_edgar"
    assert frag10k.content_depth == "DIRECT_METADATA"
    assert frag10k.source_authority == "OFFICIAL_REGULATORY"
    assert "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm" in frag10k.canonical_url
    assert frag10k.reliability_score == 0.98


def test_sec_edgar_form_filter():
    mock_payload = {
        "cik": "0001045810",
        "entityType": "Operating",
        "name": "NVIDIA CORP",
        "tickers": ["NVDA"],
        "filings": {
            "recent": {
                "accessionNumber": ["0001-24-1", "0001-24-2"],
                "filingDate": ["2024-02-21", "2024-01-10"],
                "form": ["10-K", "8-K"],
                "primaryDocument": ["doc1.htm", "doc2.htm"],
                "primaryDocDescription": ["10-K", "8-K"],
            }
        }
    }

    def mock_fetcher(url, **kwargs):
        return _make_http_response(json.dumps(mock_payload).encode("utf-8"), endpoint=url)

    res = fetch_sec_submissions("NVDA", limit=5, form_filter="8-K", http_fetcher=mock_fetcher)
    assert len(res["items"]) == 1
    assert res["items"][0]["form"] == "8-K"


# ── 2. NIST NVD CVE Primary Source Adapter ───────────────────────────────────

def test_nist_nvd_fetch_and_normalize():
    mock_payload = {
        "resultsPerPage": 1,
        "startIndex": 0,
        "totalResults": 1,
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2024-21626",
                    "sourceIdentifier": "security-advisories@github.com",
                    "published": "2024-01-31T22:15:54.120",
                    "lastModified": "2024-02-07T19:15:08.520",
                    "vulnStatus": "Modified",
                    "descriptions": [
                        {"lang": "en", "value": "runc is a CLI tool for spawning and running containers according to the OCI specification. In runc 1.1.11 and earlier, due to an internal file descriptor leak, an attacker can construct a malicious container image to achieve host container breakout."}
                    ],
                    "metrics": {
                        "cvssMetricV31": [
                            {
                                "source": "nvd@nist.gov",
                                "type": "Primary",
                                "cvssData": {
                                    "version": "3.1",
                                    "vectorString": "CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:H",
                                    "baseScore": 8.6,
                                    "baseSeverity": "HIGH"
                                }
                            }
                        ]
                    },
                    "references": [
                        {"url": "https://github.com/opencontainers/runc/security/advisories/GHSA-xr7r-f8xq-vfvv", "source": "security-advisories@github.com"}
                    ]
                }
            }
        ]
    }

    def mock_fetcher(url, **kwargs):
        return _make_http_response(json.dumps(mock_payload).encode("utf-8"), endpoint=url)

    res = fetch_nist_cve("CVE-2024-21626", limit=2, http_fetcher=mock_fetcher)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["cve_id"] == "CVE-2024-21626"
    assert item["cvss_score"] == 8.6
    assert item["severity"] == "HIGH"

    fragments = normalize_nist_items(res["items"], query_id="q_cve", query_class="security", query_text="CVE-2024-21626")
    assert len(fragments) == 1
    frag = fragments[0]
    assert frag.platform == "nist_cve"
    assert frag.content_depth == "DIRECT_CONTENT"
    assert frag.source_authority == "OFFICIAL_ADVISORY"
    assert "https://nvd.nist.gov/vuln/detail/CVE-2024-21626" == frag.canonical_url
    assert frag.reliability_score == 0.95
    assert "CVSS 8.6" in frag.title
    assert "Score: 8.6" in frag.snippet


# ── 3. arXiv Academic Preprints Adapter ───────────────────────────────────────

def test_arxiv_fetch_and_normalize():
    atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.07041v1</id>
    <updated>2023-01-17T18:00:00Z</updated>
    <published>2023-01-17T18:00:00Z</published>
    <title>A Formal Verification of Misinformation Detection Pipelines</title>
    <summary>We present a rigorous framework for decomposing claims and assessing contradictions.</summary>
    <author>
      <name>Alice Turing</name>
    </author>
    <author>
      <name>Bob Shannon</name>
    </author>
    <arxiv:doi>10.1000/182</arxiv:doi>
    <arxiv:primary_category term="cs.AI"/>
    <link title="pdf" href="http://arxiv.org/pdf/2301.07041v1" rel="related" type="application/pdf"/>
  </entry>
</feed>"""

    def mock_fetcher(url, **kwargs):
        return _make_http_response(atom_xml.encode("utf-8"), endpoint=url, content_type="application/atom+xml")

    res = fetch_arxiv_preprints("2301.07041", limit=2, http_fetcher=mock_fetcher)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["title"] == "A Formal Verification of Misinformation Detection Pipelines"
    assert "Alice Turing" in item["authors"]
    assert item["doi"] == "10.1000/182"
    assert item["category"] == "cs.AI"

    fragments = normalize_arxiv_items(res["items"], query_id="q_arxiv", query_class="academic", query_text="2301.07041")
    assert len(fragments) == 1
    frag = fragments[0]
    assert frag.platform == "arxiv"
    assert frag.content_depth == "DIRECT_ABSTRACT"
    assert frag.source_authority == "ACADEMIC_PREPRINT"
    assert frag.author == "Alice Turing, Bob Shannon"
    assert frag.reliability_score == 0.90


# ── 4. Fact Check Tools ClaimReview Adapter ──────────────────────────────────

def test_fact_check_fetch_and_normalize():
    mock_payload = {
        "claims": [
            {
                "text": "The company announced it will shut down all operations worldwide next Monday.",
                "claimant": "Social Media Posts",
                "claimDate": "2024-03-01T00:00:00Z",
                "claimReview": [
                    {
                        "publisher": {
                            "name": "PolitiFact",
                            "site": "politifact.com"
                        },
                        "url": "https://www.politifact.com/factchecks/2024/mar/01/shutdown-claim/",
                        "title": "False: Company is not shutting down operations next week",
                        "reviewDate": "2024-03-02T12:00:00Z",
                        "textRating": "False"
                    }
                ]
            }
        ]
    }

    def mock_fetcher(url, **kwargs):
        return _make_http_response(json.dumps(mock_payload).encode("utf-8"), endpoint=url)

    res = fetch_fact_check_claims("shut down operations next Monday", limit=2, http_fetcher=mock_fetcher)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["publisher_name"] == "PolitiFact"
    assert item["text_rating"] == "False"
    assert item["review_url"] == "https://www.politifact.com/factchecks/2024/mar/01/shutdown-claim/"

    fragments = normalize_fact_check_items(res["items"], query_id="q_fc", query_class="factcheck", query_text="shutdown")
    assert len(fragments) == 1
    frag = fragments[0]
    assert frag.platform == "fact_check"
    assert frag.source_authority == "INDEPENDENT_FACT_CHECKER"
    assert frag.reliability_score == 0.92
    assert "PolitiFact Fact Check: False" in frag.title


# ── 5. Capability Matrix & Runtime Capabilities Assessment ───────────────────

def test_authoritative_capability_matrix_registered():
    for plat in ("sec_edgar", "nist_cve", "arxiv", "fact_check"):
        assert plat in AUTHORITATIVE_CAPABILITY_MATRIX
        cap = get_capability(plat)
        assert cap.platform == plat
        assert cap.tier == 0
        assert cap.cloud_safe is True
        assert cap.auth_mode == "none"

    for plat in ("sec_edgar", "nist_cve", "arxiv", "fact_check"):
        assert plat in EXECUTABLE_CAPABILITIES
        assert "search" in EXECUTABLE_CAPABILITIES[plat]


def test_runtime_capabilities_assess_authoritative_sources():
    sec_assess = runtime_operation_capabilities.assess("sec_edgar", "search")
    assert sec_assess["handler_available"] is True
    assert sec_assess["declared"] is True
    assert sec_assess["decision"] in {"ELIGIBLE_UNVERIFIED", "PREFER"}

    nvd_assess = runtime_operation_capabilities.assess("nist_cve", "read")
    assert nvd_assess["handler_available"] is True
    assert nvd_assess["declared"] is True
    assert nvd_assess["decision"] in {"ELIGIBLE_UNVERIFIED", "PREFER"}

    arxiv_assess = runtime_operation_capabilities.assess("arxiv", "search")
    assert arxiv_assess["handler_available"] is True
    assert arxiv_assess["declared"] is True

    fc_assess = runtime_operation_capabilities.assess("fact_check", "search")
    assert fc_assess["handler_available"] is True
    assert fc_assess["declared"] is True

    inv = runtime_operation_capabilities.inventory()
    assert "sec_edgar" in inv
    assert "nist_cve" in inv
    assert "arxiv" in inv
    assert "fact_check" in inv


# ── 6. Router and StandardChannelHandlers Dispatch ───────────────────────────

def test_router_executes_authoritative_sec_edgar(monkeypatch):
    router = NativeRouter()
    mock_payload = {
        "cik": "0001045810",
        "entityType": "Operating",
        "name": "NVIDIA CORP",
        "tickers": ["NVDA"],
        "filings": {
            "recent": {
                "accessionNumber": ["0001-24-1"],
                "filingDate": ["2024-02-21"],
                "form": ["10-K"],
                "primaryDocument": ["nvda.htm"],
                "primaryDocDescription": ["10-K"],
            }
        }
    }

    import backend.infrastructure.acquisition.adapters.authoritative.sec_edgar as sec_mod
    monkeypatch.setattr(
        sec_mod,
        "fetch_public_http",
        lambda url, **kw: _make_http_response(json.dumps(mock_payload).encode("utf-8"), endpoint=url)
    )

    fragments, telemetry = router.execute_channel_query(
        "sec_edgar", "NVDA", limit=2, operation="search"
    )
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["backend"] == "sec-edgar-data-api"
    assert len(fragments) == 1
    assert fragments[0].platform == "sec_edgar"


def test_router_executes_authoritative_nist_cve(monkeypatch):
    router = NativeRouter()
    mock_payload = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2023-9999",
                    "descriptions": [{"lang": "en", "value": "Flaw in library"}],
                    "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 7.5, "baseSeverity": "HIGH"}}]}
                }
            }
        ]
    }

    import backend.infrastructure.acquisition.adapters.authoritative.nist_nvd as nvd_mod
    monkeypatch.setattr(
        nvd_mod,
        "fetch_public_http",
        lambda url, **kw: _make_http_response(json.dumps(mock_payload).encode("utf-8"), endpoint=url)
    )

    fragments, telemetry = router.execute_channel_query(
        "nist_cve", "CVE-2023-9999", limit=1, operation="search"
    )
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["backend"] == "nist-nvd-cve-api"
    assert len(fragments) == 1
    assert fragments[0].platform == "nist_cve"


# ── 7. SourcePlanningEngine Integration ──────────────────────────────────────

def test_source_planning_engine_plans_sec_edgar_for_financial_claim():
    planner = SourcePlanningEngine()
    plan = planner.plan(
        claim="NVIDIA fabricated quarterly revenue numbers",
        entity="NVIDIA",
        domain="financial",
        agent="scout",
        allowed_channels=["sec_edgar", "web", "news"],
    )
    actions = [a for a in plan.actions if a.channel == "sec_edgar"]
    assert len(actions) >= 1
    assert actions[0].operation == "search"
    assert actions[0].authoritative is True


def test_source_planning_engine_plans_nist_cve_for_vulnerability_claim():
    planner = SourcePlanningEngine()
    plan = planner.plan(
        claim="Critical unpatched zero-day CVE vulnerability in Linux kernel runc",
        entity="runc",
        domain="security",
        agent="brandshield",
        allowed_channels=["nist_cve", "web"],
    )
    actions = [a for a in plan.actions if a.channel == "nist_cve"]
    assert len(actions) >= 1
    assert actions[0].authoritative is True


def test_source_planning_engine_plans_arxiv_for_preprint_claim():
    planner = SourcePlanningEngine()
    plan = planner.plan(
        claim="New research paper preprint proves P=NP with novel algorithm proof",
        entity="research",
        domain="science",
        agent="trending",
        allowed_channels=["arxiv", "web"],
    )
    actions = [a for a in plan.actions if a.channel == "arxiv"]
    assert len(actions) >= 1
    assert actions[0].authoritative is True


def test_source_planning_engine_plans_fact_check_when_allowed():
    planner = SourcePlanningEngine()
    plan = planner.plan(
        claim="Viral claim that drinking bleach cures all known viral infections",
        domain="health",
        agent="trending",
        allowed_channels=["fact_check", "web", "news"],
    )
    actions = [a for a in plan.actions if a.channel == "fact_check"]
    assert len(actions) >= 1
    assert actions[0].authoritative is True
