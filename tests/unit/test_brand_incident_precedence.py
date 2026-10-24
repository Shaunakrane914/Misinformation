"""Saved-source excerpt controls; not fresh acquisition or independent truth labels."""
import copy

import pytest

from backend.agents.brandshield.intelligence import classify_brand_source, contextualize_brand_threat


def genuine_excerpt_records():
    # These are exact, explicitly selected paragraphs from the approved Oct22
    # local Apple capture, not complete articles. Joined paragraphs are replay
    # inputs only; full original records remain in the audit's saved response.
    return [
        {"evidence_id": "ev_hv_6e806704335e19a66774",
         "url": "https://www.financialexpress.com/life/technology-apple-sued-over-1-8-mn-crypto-scam-accused-of-ignoring-fraud-warnings-4304340/",
         "title": "Apple sued over $1.8 mn crypto scam, accused of ignoring fraud warnings - Technology News | The Financial Express",
         "content": "A federal lawsuit filed in California has accused tech giant Apple of failing to protect its users.\n\nThe legal case was filed after a fraudulent app slipped through its App Store review process, costing three cryptocurrency investors a combined $1.835 million in stolen Bitcoin.\n\nWhen Raw tried to submit a official \u201cplaceholder\u201d app, containing screenshots explicitly warning users that Sparrow Wallet was desktop-only, Apple\u2019s review team initially flagged his developer account for termination over \u201cdishonest activity\u201d before reversing course.",
         "content_depth": "PARTIAL_CONTENT", "expected": "REPORTED_ALLEGATION"},
        {"evidence_id": "ev_hv_bf8f5945fe9ff28266c1",
         "url": "https://cryptoslate.com/apples-app-store-security-promise-faces-test-as-fake-crypto-wallets-keep-getting-through/",
         "title": "Apple\u2019s App Store promoted fake Bitcoin wallet that stole $1.8M after developer spent a year warning them",
         "content": "Apple\u2019s tightly controlled App Store is facing renewed scrutiny after three Bitcoin holders alleged they lost $1.8 million to a fake crypto wallet , adding to a growing list of malicious wallet apps that have reached users despite the company\u2019s screening process.\n\nThe lawsuit , filed July 24 in California, accuses Apple of failing to adequately review and remove applications impersonating Sparrow Wallet while promoting the App Store as a safe and trusted source for software.",
         "content_depth": "PARTIAL_CONTENT", "expected": "REPORTED_ALLEGATION"},
        {"evidence_id": "ev_hv_7bb4855d80991eb50b9b",
         "url": "https://www.asiaone.com/singapore/apple-imessage-courier-phishing-scams-losses-hit-22-million",
         "title": "Apple iMessage courier phishing scams: Losses up by $1m to $2.2m in 2 weeks",
         "content": "Phishing scams involving the impersonation of courier companies via Apple iMessage have surged over the past two weeks, with losses now estimated to be around $2.2 million, up from the $1.2 million reported on Aug 5 .\n\nPolice said in an updated news release on Thursday (Aug 20) that their Cyber Command disrupted over 30,000 Apple iMessage accounts linked to the scam campaign since June this year.",
         "content_depth": "PARTIAL_CONTENT", "expected": "HISTORICAL_ENFORCEMENT"},
    ]


@pytest.mark.parametrize("source", genuine_excerpt_records(), ids=lambda row: row["evidence_id"])
def test_genuine_reported_incident_context_overrides_warning_language(source):
    original = copy.deepcopy(source)
    result = classify_brand_source(source, "Apple")
    assert result["classification"] == source["expected"]
    assert result["actor_url"] is None and result["epistemic_state"] == "UNVERIFIED"
    threat = contextualize_brand_threat({"type": "SAFETY_ADVISORY"}, [source], "Apple")
    assert threat["classification"] == threat["evidence_class"] == source["expected"]
    assert threat["type"] == ("ENFORCEMENT_REPORT" if source["expected"] == "HISTORICAL_ENFORCEMENT" else "REPORTED_ALLEGATION")
    assert not threat["is_threat"] and threat["actor_url"] is None
    assert source == original


@pytest.mark.parametrize("guidance", [
    "Cedar warns customers to avoid phishing scams. A lawsuit could be filed if an impersonator steals money.",
    "Beware of fake Cedar pages. If a complaint is filed, keep a copy of the correspondence for your records.",
    "Cedar publishes tips to avoid scams and protect yourself from phishing messages. Police warn that scams can disrupt accounts.",
])
def test_hypothetical_legal_or_disruption_advice_is_not_reported_incident(guidance):
    source = {"evidence_id": "guide", "title": "Cedar fraud guidance", "content": guidance,
        "content_depth": "PARTIAL_CONTENT", "url": "https://publisher.example/advice"}
    result = classify_brand_source(source, "Cedar")
    assert result["classification"] == "WARNING_ADVISORY"
    assert result["actor_url"] is None


def test_actual_held_out_reported_lawsuit_is_not_lost_when_advice_is_also_present():
    source = {"evidence_id": "legal-report", "title": "Beryl class action and account security",
        "content": "A complaint filed on Monday alleges that Beryl hosted a fraudulent sign-in application. The publisher also warns readers to protect yourself from phishing scams.",
        "content_depth": "PARTIAL_CONTENT", "url": "https://publisher.example/legal-report"}
    result = classify_brand_source(source, "Beryl")
    assert result["classification"] == "REPORTED_ALLEGATION"
    assert result["epistemic_state"] == "UNVERIFIED" and result["actor_url"] is None


def test_preventive_seller_instructions_without_warning_keyword_remain_advice():
    source = {"evidence_id": "preventive-guide", "title": "How Cedar scams target buyers",
        "content": "Fake webstores may offer counterfeit Cedar sets. Buyers should inspect seller details before buying.",
        "content_depth": "PARTIAL_CONTENT", "url": "https://publisher.example/guide"}
    result = classify_brand_source(source, "Cedar")
    assert result["classification"] == "WARNING_ADVISORY"
    assert result["actor_url"] is None
    threat = contextualize_brand_threat({"type": "COUNTERFEIT"}, [source], "Cedar")
    assert threat["type"] == "SAFETY_ADVISORY" and not threat["is_threat"]
