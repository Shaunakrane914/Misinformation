"""Offline projection regressions for newly acquired article-shaped records."""
import pytest

from backend.agents.brandshield.dossier import build_investigation_dossiers
from backend.agents.brandshield.assessment import heuristic_threat_synthesis
from backend.agents.scout.assessment import _financial_direction, synthesize_financial_intelligence


@pytest.mark.parametrize("field,value", [("claim_text", "Observed legacy statement"), ("text", "Observed text field"),
                                         ("claim", "Observed claim field"), ("statement", "Observed structured statement"),
                                         ("claim", {"text": "Observed nested statement"})])
def test_brand_dossier_accepts_observed_claim_shapes_and_preserves_citations(field, value):
    evidence = [{"evidence_id": "canonical-id", "platform": "Web", "url": "https://publisher.example/report",
                 "title": "Captured report", "snippet": "Observed source text"}]
    threats = [{"threat_id": "threat-1", "evidence_ids": ["canonical-id"], "type": "PRODUCT_SAFETY"}]
    claims = [{field: value, "claim_id": "claim-1", "evidence_ids": ["canonical-id", "unrelated"]},
              {"statement": "Unrelated", "evidence_ids": ["other-id"]},
              {"claim_id": "missing-text", "evidence_ids": ["canonical-id"]}]
    dossier = build_investigation_dossiers({}, threats, claims, evidence)[0]
    expected = value["text"] if isinstance(value, dict) else value
    assert dossier["related_claims"] == [expected]
    assert dossier["related_claim_records"] == [{"text": expected, "claim_id": "claim-1", "evidence_ids": ["canonical-id"]}]
    assert dossier["evidence_chain"][0]["evidence_id"] == "canonical-id"


@pytest.mark.parametrize("text,direction", [
    ("Cedar profit dropped 36 per cent in the financial year.", "negative"),
    ("Cedar revenue increased 12% and operating profit rose 8%.", "positive"),
    ("Cedar profit dropped 36% despite revenue increasing 1.2%.", "unresolved"),
    ("Cedar reported profit of USD 12 million for the quarter.", "unresolved"),
    ("Cedar expects profit to increase next year.", "unresolved"),
    ("Cedar did not report a profit decline.", "unresolved"),
    ("Cedar announced new growth opportunities and a commercial deal.", "unresolved"),
])
def test_financial_direction_requires_directional_not_merely_profit_keywords(text, direction):
    assert _financial_direction(text)[0] == direction


def test_scout_publishes_negative_decrease_without_positive_profit_keyword_override():
    source = {"evidence_id": "financial-capture", "title": "Cedar profit dropped 36%",
              "content": "Cedar reported that operating profit dropped 36 per cent in the financial year, according to its published results.",
              "snippet": "Cedar operating profit dropped 36 per cent in the year.", "content_depth": "PARTIAL_CONTENT",
              "published_at": "2026-04-20T12:00:00Z", "retrieved_at": "2026-04-21T12:00:00Z",
              "source_role": "SECONDARY", "url": "https://publisher.example/results"}
    report = synthesize_financial_intelligence("Cedar", "", {}, [source])
    assert not report["catalysts"]["positive"]
    assert report["catalysts"]["negative"][0]["evidence_ids"] == ["financial-capture"]
    assert report["catalysts"]["negative"][0]["assessment_is_heuristic"]


def test_promotional_giveaway_article_is_not_a_phishing_vector_without_abuse_context():
    record = {"evidence_id": "promotion", "platform": "Web", "title": "Orion collaboration launches limited-edition giveaway",
              "content": "Orion and a confectionery brand announced a sweepstakes for limited-edition cleats. The public promotion describes eligibility dates and how winners will be selected.",
              "url": "https://publisher.example/collaboration-giveaway", "content_depth": "PARTIAL_CONTENT"}
    result = heuristic_threat_synthesis({"brand": "Orion", "resolved_entity": "Orion"}, [record])
    assert not result["threats"] and record["intelligence_class"] == "PROMOTIONAL_REFERENCE"


def test_alleged_phishing_giveaway_remains_investigable_not_authenticated():
    record = {"evidence_id": "allegation", "platform": "Web", "title": "Orion fake giveaway asks for credentials",
              "content": "A fake Orion giveaway instructed users to enter passwords on an unauthorized phishing page. The report identifies a suspicious offer, not an independently adjudicated fraud finding.",
              "url": "https://publisher.example/phishing-report", "content_depth": "PARTIAL_CONTENT"}
    result = heuristic_threat_synthesis({"brand": "Orion", "resolved_entity": "Orion"}, [record])
    assert result["threats"]
    assert all("allegation" in threat.get("evidence_ids", []) for threat in result["threats"])


def test_crypto_double_return_promotion_is_not_suppressed_as_product_sweepstakes():
    record = {"evidence_id": "crypto-offer", "platform": "Twitter", "title": "Orion official 5000 BTC giveaway",
              "content": "Send 1 ETH to the Orion official promotion wallet and receive 2 ETH back immediately.",
              "snippet": "Send 1 ETH to the Orion official promotion wallet and receive 2 ETH back immediately.",
              "url": "https://twitter.com/orion_giveaway/status/123", "content_depth": "FULL_ARTICLE",
              "source_role": "ADVERSARIAL"}
    result = heuristic_threat_synthesis({"brand": "Orion", "resolved_entity": "Orion"}, [record])
    assert any(row.get("type") == "PHISHING_SCAM" for row in result["threats"])
    assert record.get("intelligence_class") != "PROMOTIONAL_REFERENCE"
