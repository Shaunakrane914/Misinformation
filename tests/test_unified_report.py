"""
Tests for Unified Investigation Report Schema (v3.8.0) and ReportBuilder.
Validates structural conformity across all 5 verification agents:
- Claims Verification (claim_verifier)
- Scout Financial Intelligence (scout)
- Trending Narrative Scan (trending)
- BrandShield Asset Protection (brandshield)
- Personal Watch Identity Audit (personal)
"""

import pytest
from backend.schemas.unified_report import (
    UnifiedReport,
    UnifiedQualityTensor,
    UnifiedEvidenceSet,
    UnifiedEvidenceItem,
    UnifiedEvidenceSource,
    RetrievalLineageEntry,
    TimelineEvent,
    QueryTelemetry,
    TrustMetadata,
    classify_evidence_items,
    build_trust_metadata,
)
from backend.services.report_builder import ReportBuilder


def test_unified_quality_tensor_defaults():
    qt = UnifiedQualityTensor()
    assert qt.relevance is None
    assert qt.source_quality is None
    d = qt.to_dict()
    assert "relevance" in d
    assert "independence" in d
    assert "freshness" in d


def test_unified_quality_tensor_custom():
    qt = UnifiedQualityTensor(
        relevance=0.9,
        source_quality=0.85,
        independence=0.95,
        primary_weight=1.0,
        freshness=0.8,
        contradiction=0.1,
    )
    d = qt.to_dict()
    assert d["relevance"] == 0.9
    assert d["source_quality"] == 0.85
    assert d["primary_weight"] == 1.0


def test_unified_report_minimal():
    report = UnifiedReport(
        summary="Claim is **FALSE**. Official records contradict the claim.",
        findings=["Fact-checking agencies found no evidence.", "Official press office refuted statement."],
        disagreements=["Social post claimed declaration, while bulletin lists normal monitoring."],
        changes=["Initial social claims retracted by author."],
        timeline=[
            TimelineEvent(timestamp="2026-10-01T10:00:00Z", description="Viral post published"),
            TimelineEvent(timestamp="2026-10-01T12:00:00Z", description="Official refutation released"),
        ],
        agent="claim_verifier",
        query="WHO declared emergency",
    )
    dumped = report.to_dict()
    assert dumped["_meta"]["schema_version"] == "3.8.0"
    assert dumped["_meta"]["agent"] == "claim_verifier"
    assert dumped["_meta"]["query"] == "WHO declared emergency"
    assert len(dumped["findings"]) == 2
    assert len(dumped["timeline"]) == 2
    assert "evidence" in dumped
    assert "trust" in dumped


def test_report_builder_from_claim_result():
    verdict_data = {
        "verdict": "FALSE",
        "confidence": 0.94,
        "reasoning": "Official government release confirms no such policy exists. Several independent fact checkers investigated.",
        "explanation": "Official statements from accredited agencies verify the post is completely fabricated.",
        "key_finding": "Primary government source directly contradicts viral post."
    }

    report = ReportBuilder.from_claim_result(
        claim_text="New nationwide lockdown declared",
        verdict=verdict_data,
        corpus=None,
        execution_log=[
            {"channel": "news", "status": "SUCCESS", "retrieved_count": 5},
            {"channel": "web", "status": "SUCCESS", "retrieved_count": 3},
        ],
        queries_planned=2
    )

    assert isinstance(report, UnifiedReport)
    d = report.to_dict()
    assert d["_meta"]["agent"] == "claim_verifier"
    assert "FALSE" in d["summary"]
    assert len(d["findings"]) >= 1
    assert d["trust"]["query_telemetry"]["queries_succeeded"] == 2


def test_report_builder_from_scout_result():
    scout_data = {
        "summary": "NVIDIA posted record datacenter revenue growth in Q3 filings.",
        "catalysts": [
            "Datacenter revenue rose 112% year-over-year.",
            "Gross margin sustained above 74%."
        ],
        "primary_filings": [
            {
                "title": "SEC Form 10-Q (Q3 2026)",
                "url": "https://sec.gov/edgar/nvda-10q",
                "source": "SEC EDGAR",
                "platform": "filing"
            }
        ],
        "news_articles": [
            {
                "title": "Bloomberg: NVIDIA Datacenter Surges Past Estimates",
                "url": "https://bloomberg.com/news/nvda",
                "source": "Bloomberg",
                "platform": "news"
            }
        ],
        "timeline": [
            {"timestamp": "09:00 EST", "description": "Form 10-Q filing confirmed"}
        ],
        "quality_tensor": {
            "relevance": 0.95,
            "source_quality": 0.98,
            "independence": 0.90,
            "primary_weight": 1.0,
            "freshness": 0.85
        },
        "independent_source_count": 6
    }

    report = ReportBuilder.from_scout_result(
        query="NVDA",
        scout_data=scout_data
    )

    d = report.to_dict()
    assert d["_meta"]["agent"] == "scout"
    assert d["_meta"]["query"] == "NVDA"
    assert len(d["findings"]) == 2
    assert len(d["evidence"]["primary"]) == 1
    assert len(d["evidence"]["independent"]) == 1
    assert d["trust"]["independent_source_count"] == 6
    assert d["trust"]["quality_tensor"]["primary_weight"] == 1.0


def test_report_builder_from_trending_result():
    trend_data = {
        "summary": "Deepika Padukone trending following international film festival presence.",
        "claims": [
            {"claim_text": "Jury appointment confirmed for upcoming awards edition."}
        ],
        "evidence": [
            {
                "title": "Variety Feature on Festival Jury",
                "url": "https://variety.com/festival-preview",
                "source": "Variety",
                "platform": "news"
            },
            {
                "title": "Reddit Megathread: Discussion on red carpet appearance",
                "url": "https://reddit.com/r/bollywood/comments/123",
                "source": "Reddit",
                "platform": "reddit"
            }
        ],
        "timeline": [
            {"timestamp": "10:30 UTC", "event": "Syndicated press report published"}
        ]
    }

    report = ReportBuilder.from_trending_result(
        query="Deepika Padukone",
        trend_data=trend_data
    )

    d = report.to_dict()
    assert d["_meta"]["agent"] == "trending"
    assert len(d["findings"]) >= 1
    # Check that Reddit went to community bucket and news went to independent bucket
    assert len(d["evidence"]["community"]) == 1
    assert len(d["evidence"]["independent"]) == 1


def test_report_builder_from_brandshield_result():
    brand_data = {
        "status": "Elevated Brand Risk Detected: Phishing clone domains circulating.",
        "threats": [
            {"description": "Phishing portal spoofing brand support login with credential capture."}
        ],
        "evidence": [
            {
                "title": "WHOIS registration record showing newly created lookalike domain",
                "url": "https://whois.domaintools.com/target-spoof.com",
                "platform": "web",
                "is_primary": True
            }
        ],
        "independent_source_count": 4
    }

    report = ReportBuilder.from_brandshield_result(
        query="Brand Acme",
        brand_data=brand_data
    )

    d = report.to_dict()
    assert d["_meta"]["agent"] == "brandshield"
    assert len(d["findings"]) == 1
    assert len(d["evidence"]["primary"]) == 1
    assert len(d["next_steps"]) >= 1


def test_report_builder_from_personal_result():
    personal_data = {
        "status": "Nominal: No impersonation or synthetic identity threats detected.",
        "alerts": [
            {"description": "Verified personal handles and domain profiles align with public records."}
        ],
        "documents": [
            {
                "title": "Official Institutional Faculty Directory",
                "url": "https://university.edu/directory/dr-smith",
                "platform": "web"
            }
        ]
    }

    report = ReportBuilder.from_personal_result(
        query="Dr. John Smith",
        personal_data=personal_data
    )

    d = report.to_dict()
    assert d["_meta"]["agent"] == "personal_watch"
    assert "Nominal" in d["summary"]
    assert len(d["findings"]) == 1
    assert len(d["evidence"]["primary"]) == 1
