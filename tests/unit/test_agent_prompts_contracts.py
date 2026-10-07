"""
Tests for Aegis Protocol Agent Prompt Specifications and Output Contracts
===========================================================================
Validates that Scout, Trending, BrandShield, and Personal Watch agents strictly
adhere to their output contracts and epistemic models specified in backend/Prompts/:
- scout_agent.md (Section 17)
- trending_agent.md (Section 14)
- brandshield_agent.md (Section 14)
- personal_watch_agent.md (Section 16)
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.agents.scout_agent import scout_agent
from backend.agents.trending_agent import trending_agent
from backend.agents.brandshield_agent import brandshield_agent
from backend.agents.personal_agent import personal_watch_agent


# ── 1. SCOUT AGENT CONTRACT VERIFICATION ─────────────────────────────────────

def test_scout_agent_output_contract():
    """Verify Scout produces the Section 17 Output Contract from scout_agent.md."""
    # Mock stock impact and acquisition to test contract deterministically
    with patch.object(scout_agent, "check_stock_impact") as mock_impact, \
         patch.object(scout_agent, "acquire_market_intelligence") as mock_acq:

        mock_impact.return_value = {
            "current_price": 185.50,
            "volatility_analysis": {
                "mean": 180.0,
                "std_dev": 2.5,
                "z_score": 2.2,
                "volatility_status": "RALLY"
            },
            "prediction": {
                "catalyst_direction": "bullish"
            }
        }
        mock_acq.return_value = {
            "query": "Apple earnings guidance",
            "entity": "Apple Inc.",
            "ticker": "AAPL",
            "epistemic_status": "OFFICIAL",
            "primary_source_present": True,
            "independent_source_count": 3,
            "financial_facts": [
                {
                    "metric": "revenue",
                    "raw_value": "$94.9B",
                    "currency": "USD",
                    "direction": "up"
                }
            ],
            "events": [
                {
                    "event_type": "EARNINGS",
                    "summary": "Apple reported record quarterly revenue"
                }
            ],
            "clusters": [{"cluster_id": "C-1", "primary_source": "https://apple.com/ir"}],
            "contradictions": [],
            "evidence": [
                {
                    "url": "https://apple.com/ir/q4.html",
                    "title": "Q4 Results",
                    "platform": "primary",
                    "authenticated": False
                }
            ],
            "telemetry": {"fallback_rate": 0.0}
        }

        res = scout_agent.generate_scout_intelligence(subject="AAPL")

        # Validate required contract keys
        required_keys = [
            "agent", "subject", "market_context", "observed", "inferred",
            "uncertain", "events", "sources", "corroboration", "contradictions",
            "price_context", "market_impact", "risk_flags", "retrieval"
        ]
        for key in required_keys:
            assert key in res, f"Missing key '{key}' in Scout output contract"

        assert res["agent"] == "scout"
        assert res["subject"] == "AAPL"
        assert isinstance(res["observed"], list)
        assert len(res["observed"]) > 0
        assert isinstance(res["inferred"], list)
        assert isinstance(res["uncertain"], list)
        assert isinstance(res["events"], list)
        assert isinstance(res["sources"], list)
        assert isinstance(res["corroboration"], list)
        assert isinstance(res["contradictions"], list)
        assert isinstance(res["price_context"], dict)
        assert isinstance(res["market_impact"], dict)
        assert res["market_impact"]["direction"] in ("bullish", "bearish", "mixed", "neutral", "unknown")
        assert res["market_impact"]["horizon"] in ("intraday", "days", "weeks", "long_term", "unknown")
        assert isinstance(res["market_impact"]["confidence"], (int, float))
        assert isinstance(res["risk_flags"], list)
        assert isinstance(res["retrieval"], dict)
        assert res["retrieval"]["direct"] is True
        assert res["retrieval"]["fallback_used"] is False


# ── 2. TRENDING AGENT CONTRACT VERIFICATION ──────────────────────────────────

def test_trending_agent_output_contract():
    """Verify Trending produces the Section 14 Output Contract from trending_agent.md."""
    with patch.object(trending_agent, "scan_trends") as mock_scan:
        mock_scan.return_value = {
            "entity_resolution": {
                "resolved_entity": "Deepika Padukone",
                "confidence": 0.95,
                "category": "entertainment"
            },
            "evidence": [
                {
                    "evidence_id": "EV-1",
                    "platform": "news",
                    "source": "Variety",
                    "title": "Deepika Padukone Announced as Festival Juror",
                    "url": "https://variety.com/deepika",
                    "published_at": "2026-10-06T12:00:00Z"
                }
            ],
            "trends": [
                {
                    "trend_id": "T-1",
                    "topic": "Festival Jury Announcement",
                    "category": "entertainment",
                    "sentiment": "POSITIVE",
                    "misinformation_risk": "LOW",
                    "misinformation_rationale": "Direct official festival announcement",
                    "velocity": {"label": "HIGH_MOMENTUM"},
                    "platform_count": 3,
                    "narratives": [
                        {
                            "narrative_id": "N-1",
                            "title": "Global Jury Role",
                            "summary": "Deepika joins international film festival jury"
                        }
                    ]
                }
            ],
            "box_office": {},
            "timeline": [
                {"timestamp": "2026-10-06T12:00:00Z", "event": "Announcement"}
            ],
            "findings": [{"id": "F-1"}],
            "contradictions": [],
            "retrieval_trace": {"fallback_rate": 0.0}
        }

        res = trending_agent.generate_trending_intelligence(person="Deepika Padukone")

        required_keys = [
            "agent", "person", "identity_confidence", "trend_window", "top_trends",
            "narrative_clusters", "timeline", "observed", "inferred", "uncertain",
            "sentiment", "sources", "corroboration", "contradictions", "retrieval"
        ]
        for key in required_keys:
            assert key in res, f"Missing key '{key}' in Trending output contract"

        assert res["agent"] == "trending"
        assert res["person"] == "Deepika Padukone"
        assert res["identity_confidence"] == 0.95
        assert isinstance(res["top_trends"], list)
        assert isinstance(res["narrative_clusters"], list)
        assert isinstance(res["timeline"], list)
        assert isinstance(res["observed"], list)
        assert len(res["observed"]) > 0
        assert isinstance(res["inferred"], list)
        assert isinstance(res["uncertain"], list)
        assert isinstance(res["sentiment"], dict)
        assert res["sentiment"]["direction"] in ("positive", "negative", "mixed", "neutral", "unknown")
        assert isinstance(res["sentiment"]["confidence"], (int, float))
        assert "sample_basis" in res["sentiment"]
        assert isinstance(res["sources"], list)
        assert isinstance(res["corroboration"], list)
        assert isinstance(res["contradictions"], list)
        assert isinstance(res["retrieval"], dict)
        assert res["retrieval"]["direct"] is True


# ── 3. BRANDSHIELD AGENT CONTRACT VERIFICATION ───────────────────────────────

def test_brandshield_agent_output_contract():
    """Verify BrandShield produces the Section 14 Output Contract from brandshield_agent.md."""
    with patch.object(brandshield_agent, "scan") as mock_scan:
        mock_scan.return_value = {
            "brand": "Nike",
            "entity": {
                "brand": "Nike",
                "entity_type": "brand",
                "confidence": 0.95
            },
            "threats": [
                {
                    "threat_type": "COUNTERFEIT",
                    "threat_name": "Counterfeit Shoes Listing",
                    "description": "Unauthorized replica Air Max listing discovered",
                    "severity": "high",
                    "platform": "marketplace"
                }
            ],
            "evidence": [
                {
                    "evidence_id": "EV-B1",
                    "platform": "web",
                    "title": "Discount Nike Air Max Knockoff",
                    "url": "https://suspicious-store.example/shoes"
                }
            ],
            "narratives": [{"title": "Replica shoes campaign"}],
            "timeline": [{"event": "First observed"}],
            "counterfeits": [{"title": "Knockoff Air Max", "platform": "web"}],
            "impersonations": [],
            "recommendations": [{"action": "Issue DMCA Takedown Notice"}],
            "findings_structured": [],
            "contradictions": [],
            "platforms": ["web", "marketplace"],
            "retrieval_trace": {"fallback_rate": 0.0}
        }

        res = brandshield_agent.generate_brandshield_intelligence(entity_input="Nike")

        required_keys = [
            "agent", "entity", "entity_type", "identity_confidence", "threats",
            "risk_level", "observed", "inferred", "uncertain", "narrative_clusters",
            "timeline", "sources", "corroboration", "contradictions",
            "recommended_attention", "retrieval"
        ]
        for key in required_keys:
            assert key in res, f"Missing key '{key}' in BrandShield output contract"

        assert res["agent"] == "brandshield"
        assert res["entity"] == "Nike"
        assert res["entity_type"] in ("brand", "company", "product", "domain", "account")
        assert res["risk_level"] in ("low", "moderate", "high", "critical", "unknown")
        assert isinstance(res["threats"], list)
        assert isinstance(res["observed"], list)
        assert len(res["observed"]) > 0
        assert isinstance(res["inferred"], list)
        assert isinstance(res["uncertain"], list)
        assert isinstance(res["narrative_clusters"], list)
        assert isinstance(res["timeline"], list)
        assert isinstance(res["sources"], list)
        assert isinstance(res["recommended_attention"], list)
        assert isinstance(res["retrieval"], dict)
        assert res["retrieval"]["direct"] is True


# ── 4. PERSONAL WATCH AGENT CONTRACT VERIFICATION ────────────────────────────

def test_personal_watch_agent_output_contract():
    """Verify Personal Watch produces the Section 16 Output Contract from personal_watch_agent.md."""
    with patch.object(personal_watch_agent, "scan") as mock_scan:
        mock_scan.return_value = {
            "subject": {
                "canonical_name": "Sam Altman",
                "category": "executive",
                "confidence": 0.95
            },
            "evidence": [
                {
                    "evidence_id": "EV-P1",
                    "platform": "news",
                    "source": "TechCrunch",
                    "title": "Sam Altman Announces New Research Initiative",
                    "url": "https://techcrunch.com/sama-research"
                }
            ],
            "threats": [],
            "claims": [
                {
                    "claim_text": "Sam Altman spoke at global AI summit",
                    "status": "verified"
                }
            ],
            "suspected_impersonations": [],
            "changes": {"has_changes": True, "new_threats": [], "resolved_threats": []},
            "timeline": [{"event": "Keynote address"}],
            "findings": [],
            "contradictions": [],
            "retrieval_trace": {"fallback_rate": 0.0}
        }

        res = personal_watch_agent.generate_personal_watch_intelligence(person="Sam Altman")

        required_keys = [
            "agent", "person", "identity_confidence", "monitoring_scope", "status",
            "updates", "observed", "inferred", "uncertain", "timeline", "sources",
            "corroboration", "contradictions", "privacy_flags", "retrieval"
        ]
        for key in required_keys:
            assert key in res, f"Missing key '{key}' in Personal Watch output contract"

        assert res["agent"] == "personal_watch"
        assert res["person"] == "Sam Altman"
        assert res["identity_confidence"] == 0.95
        assert isinstance(res["monitoring_scope"], list)
        assert res["status"] in ("new_information", "material_change", "confirmed", "contradicted", "no_material_change", "unknown")
        assert isinstance(res["updates"], list)
        assert isinstance(res["observed"], list)
        assert len(res["observed"]) > 0
        assert isinstance(res["inferred"], list)
        assert isinstance(res["uncertain"], list)
        assert isinstance(res["timeline"], list)
        assert isinstance(res["sources"], list)
        assert isinstance(res["corroboration"], list)
        assert isinstance(res["contradictions"], list)
        assert isinstance(res["privacy_flags"], list)
        assert any("PII_GUARD_ACTIVE" in f for f in res["privacy_flags"])
        assert isinstance(res["retrieval"], dict)
        assert res["retrieval"]["direct"] is True
