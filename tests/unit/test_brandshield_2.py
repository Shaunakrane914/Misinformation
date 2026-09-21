"""
Aegis Protocol — Unit Tests: BrandShield 2.0
==============================================
Tests:
- Entity resolution (brand vs product distinction)
- Multi-class brand query planning
- 12-class threat taxonomy mapping
- Claim vs. threat separation
- Evidence URL preservation and absence of fake links
- Grounded synthesis refusing to hallucinate on empty retrieval
- Heuristic fallback resilience when AI enrichment is offline
"""

import pytest
from backend.agents.brandshield_agent import BrandShieldAgent, THREAT_TAXONOMY
from backend.services.agent_reach.planner import RetrievalPlanner


def test_brand_entity_resolution():
    agent = BrandShieldAgent()

    res_brand = agent.resolve_brand_entity("Nike")
    assert res_brand["brand"] == "Nike"
    assert res_brand["entity_type"] == "brand"
    assert res_brand["product"] is None

    res_prod = agent.resolve_brand_entity("Nike Air Max")
    assert res_prod["brand"] == "Nike"
    assert res_prod["product"] == "Air Max"
    assert res_prod["entity_type"] == "product"
    assert res_prod["resolved_entity"] == "Nike Air Max"

    res_samsung = agent.resolve_brand_entity("Samsung Galaxy S24")
    assert res_samsung["brand"] == "Samsung"
    assert "Galaxy S24" in res_samsung["product"]
    assert res_samsung["entity_type"] == "product"


def test_brand_query_classes():
    planner = RetrievalPlanner()
    classes = planner.build_brand_query_classes("Nike", "Air Max")

    assert "general_reputation" in classes
    assert "counterfeit" in classes
    assert "phishing_scam" in classes
    assert "impersonation" in classes
    assert "reviews" in classes
    assert "regulatory_legal" in classes

    assert any("counterfeit" in q for q in classes["counterfeit"])
    assert any("scam" in q for q in classes["phishing_scam"])
    assert any("impersonation" in q for q in classes["impersonation"])
    assert any("reviews" in q for q in classes["reviews"])
    assert any("lawsuit" in q for q in classes["regulatory_legal"])


def test_threat_taxonomy_coverage():
    assert len(THREAT_TAXONOMY) == 12
    assert "COUNTERFEIT" in THREAT_TAXONOMY
    assert "FAKE_REVIEW" in THREAT_TAXONOMY
    assert "BRAND_IMPERSONATION" in THREAT_TAXONOMY
    assert "PHISHING_SCAM" in THREAT_TAXONOMY
    assert "REPUTATION_ATTACK" in THREAT_TAXONOMY
    assert "CUSTOMER_COMPLAINT" in THREAT_TAXONOMY
    assert "PRODUCT_SAFETY" in THREAT_TAXONOMY


def test_empty_retrieval_no_synthetic_hallucination():
    agent = BrandShieldAgent()
    brand_info = {"brand": "GhostCorp123", "resolved_entity": "GhostCorp123", "entity_type": "brand"}
    synthesis = agent._synthesize_brand_threats(brand_info, evidence_list=[])

    assert synthesis["threats"] == []
    assert synthesis["claims"] == []
    assert synthesis["narratives"] == []
    assert synthesis["counterfeits"] == []
    assert synthesis["impersonations"] == []
    assert synthesis["review_intel"]["review_manipulation_detected"] is False
    assert "Insufficient evidence" in synthesis["review_intel"]["assessment"]


def test_claim_vs_threat_separation_and_complaint_distinction():
    agent = BrandShieldAgent()
    brand_info = {"brand": "TestBrand", "resolved_entity": "TestBrand", "entity_type": "brand"}

    evidence = [
        {
            "evidence_id": "ev_001",
            "title": "Delivery delayed for 3 days by courier service",
            "snippet": "Package delivery took longer than expected.",
            "url": "https://consumer-forum.org/complaint/123",
            "platform": "Web",
            "source_role": "COMMUNITY",
            "author": "User1",
            "published_at": "Recent"
        },
        {
            "evidence_id": "ev_002",
            "title": "Major safety hazard reported: battery overheated",
            "snippet": "Recall investigation requested for defective battery cells.",
            "url": "https://safety-portal.gov/report/456",
            "platform": "News",
            "source_role": "SECONDARY",
            "author": "Journalist",
            "published_at": "Recent"
        }
    ]

    synthesis = agent._heuristic_threat_synthesis(brand_info, evidence)
    threat_types = [t["type"] for t in synthesis["threats"]]

    assert "CUSTOMER_COMPLAINT" in threat_types
    assert "PRODUCT_SAFETY" in threat_types

    # Legitimate customer complaint has severity low and is not an attack
    complaint_threat = next(t for t in synthesis["threats"] if t["type"] == "CUSTOMER_COMPLAINT")
    assert complaint_threat["severity"] == "low"

    # Product safety generates a tracked substantive claim
    assert len(synthesis["claims"]) >= 1
    assert any("battery" in c["claim_text"].lower() or "safety" in c["claim_text"].lower() for c in synthesis["claims"])


def test_url_preservation_and_dossier_linking():
    agent = BrandShieldAgent()
    brand_info = {"brand": "ShoeBrand", "resolved_entity": "ShoeBrand", "entity_type": "brand"}

    evidence = [
        {
            "evidence_id": "ev_001",
            "title": "Fake ShoeBrand replica store offering 90% discount",
            "snippet": "Counterfeit listings detected on scam domain.",
            "url": "https://fake-shoebuyer-discount.com/item",
            "has_url": True,
            "platform": "Web",
            "source_role": "DISCOVERY",
            "author": "ScamRegistry",
            "published_at": "2026-09-18"
        }
    ]

    synthesis = agent._heuristic_threat_synthesis(brand_info, evidence)
    dossiers = synthesis.get("dossiers", [])
    assert len(dossiers) >= 1

    dos = dossiers[0]
    assert dos["threat_type"] == "COUNTERFEIT"
    assert dos["origin"]["has_url"] is True
    assert dos["origin"]["url"] == "https://fake-shoebuyer-discount.com/item"
    assert len(dos["evidence_chain"]) == 1
    assert dos["evidence_chain"][0]["url"] == "https://fake-shoebuyer-discount.com/item"
