"""Offline role, passage, attribution, currency/period and citation controls."""
import pytest
from backend.agents.brandshield.assessment import synthesize_brand_threats
from backend.services.research.passage_records import captured_passages
from backend.services.research.financial_observations import financial_observations
from backend.services.research.research_models import EvidenceItem
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.passage_extractor import passage_extractor
from backend.schemas.evidence_inspection import inspect_evidence, public_capture_metadata


@pytest.mark.parametrize("brand,text", [
    ("Nike", "Nike running shoes. Shop all shoes. Add to cart. Free shipping."),
    ("Apple", "Apple iPhone Pro. Shop now. Add to cart. Size guide."),
    ("Tata Motors", "Tata Motors warning: beware of fake job offers and recruitment scams. We never charge applicants."),
    ("Apple", "Apple announced a new office building and a public product launch."),
])
def test_background_and_warnings_not_attacker_findings(brand, text):
    record = {"evidence_id": "original", "title": brand, "content": text, "snippet": text,
              "url": "https://publisher.example/article", "platform": "Web", "content_depth": "PARTIAL_CONTENT"}
    result = synthesize_brand_threats({"brand": brand, "resolved_entity": brand}, [record])
    assert result["threats"] == []
    assert record["content"] == text
    assert all(text[p["start"]:p["end"]] == p["text"] for p in record["passages"])


@pytest.mark.parametrize("text,kind", [
    ("Nike customer complaint: I ordered shoes and never received them. My refund has not arrived.", "CUSTOMER_COMPLAINT"),
    ("Nike customers report counterfeit replicas offered by an unauthorized seller. The allegation is not independently verified.", "COUNTERFEIT"),
])
def test_relevant_allegations_and_complaints_preserve_citations(text, kind):
    record = {"evidence_id": "canonical", "title": "Nike public report", "content": text, "snippet": text,
              "url": "https://publisher.example/report", "platform": "Web", "content_depth": "PARTIAL_CONTENT"}
    result = synthesize_brand_threats({"brand": "Nike", "resolved_entity": "Nike"}, [record])
    matches = [t for t in result["threats"] if t.get("type") == kind or t.get("threat_type") == kind]
    assert matches
    assert all("canonical" in t["evidence_ids"] for t in matches)
    assert all(t["epistemic_state"] == "UNVERIFIED" and t["confidence_is_heuristic"] for t in matches)


def test_attributed_first_person_feed_body_qualifies_without_name_in_body():
    text = "We are releasing a new public research preview. It is not a general availability launch."
    item = EvidenceItem(id="canonical", title="Research preview", content=text, snippet=text,
        canonical_url="https://blog.samaltman.com/research-preview", source_name="Sam Altman",
        query_class="public_statement_discovery", content_depth="FEED_ENTRY_CONTENT")
    assert relevance_gate.evaluate_item(item, "Sam Altman", domain="personal").is_accepted
    passage_extractor.extract_passages([item], "Sam Altman", domain="personal")
    assert "not a general availability" in item.relevant_excerpt
    passages = captured_passages(item, "personal", "Sam Altman")
    assert passages[0]["content_role"] == "PUBLIC_STATEMENT"
    assert passages[0]["claim_status"] == "UNVERIFIED"
    assert item.content[passages[0]["start"]:passages[0]["end"]] == text


def test_financial_measurements_have_period_currency_page_and_exact_span():
    text = "[PDF page 1]\nFor the quarter ended June 30, 2026\nInfosys reported revenues at $5,082 million. Operating margin was at 21.1%."
    facts = financial_observations(text, "pdf-original")
    revenue = next(f for f in facts if f["metric"] == "REVENUE")
    assert revenue["normalized_value"] == "5082000000"
    assert revenue["period_end"] == "2026-06-30"
    assert revenue["currency"] == "DOLLAR_SYMBOL_UNSPECIFIED" and revenue["source_page"] == 1
    assert text[revenue["start"]:revenue["end"]] == revenue["text"]
    item = EvidenceItem(id="pdf-original", content=text, canonical_url="https://issuer.example/result.pdf", content_depth="PARTIAL_CONTENT",
        metadata={"financial_observations": facts})
    public = public_capture_metadata(item)
    inspection = inspect_evidence({"content": text, "content_depth": "PARTIAL_CONTENT", "metadata": public})
    assert inspection["financial_observations"][0]["evidence_id"] == "pdf-original"


def test_multiple_periods_do_not_guess_table_alignment():
    facts = financial_observations("For the quarter ended June 30, 2026\nFor the quarter ended June 30, 2025\nRevenues at $500 million.", "pdf")
    assert facts[0]["period_end"] is None
    assert facts[0]["period_alignment"] == "AMBIGUOUS_OR_UNKNOWN"
    assert facts[0]["table_alignment_verified"] is False


def test_negation_after_long_sentence_is_not_sliced_away():
    body = "Acme reported revenue is unchanged. " + "Context remains important. " * 100 + "Acme did not report a profit."
    item = EvidenceItem(id="long", content=body, canonical_url="https://example.org/article", content_depth="PARTIAL_CONTENT")
    observations = captured_passages(item, "financial", "Acme")
    assert observations[0]["text"].endswith("did not report a profit.")
    assert observations[0]["negation_present"]


def test_lookalike_is_not_verified_phishing_or_automatic_takedown():
    from backend.agents.brandshield.assessment import detect_counterfeit_domains
    result = detect_counterfeit_domains("nike.com", ["nikke.shop"])
    assert result and result[0]["epistemic_state"] == "UNVERIFIED"
    assert result[0]["ownership_verified"] is False
    assert "Review ownership" in result[0]["recommended_action"]


def test_personal_public_policy_statement_is_not_identity_attack():
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    text = "We are publishing research about deepfake video policy. It is not a report of an impersonation incident."
    result = synthesize_personal_threats({"canonical_name": "Sam Altman"}, [{
        "evidence_id": "statement", "author": "Sam Altman", "query_class": "public_statement_discovery",
        "content": text, "content_depth": "FEED_ENTRY_CONTENT", "url": "https://publisher.example/policy"}])
    assert result["threats"] == [] and result["claims"] == []


def test_personal_unlinked_deepfake_is_not_a_subject_incident():
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    result = synthesize_personal_threats({"canonical_name": "Satya Nadella"}, [{
        "evidence_id": "unlinked", "title": "Viral CEO clip", "content_depth": "PARTIAL_CONTENT",
        "content": "Synthetic audio and AI voice clone claiming a secret corporate decision deepfake circulating.",
        "url": "https://publisher.example/clip"}])
    assert result["threats"] == []


@pytest.mark.parametrize("amount,currency,period,status", [
    ("5,082", "USD", "June 30, 2026", "MATCHES_SOURCE_ASSERTION"),
    ("6,000", "USD", "June 30, 2026", "DISAGREES_WITH_SOURCE_ASSERTION"),
    ("5,082", "INR", "June 30, 2026", "INSUFFICIENT_COMPARABLE_CONTEXT"),
    ("5,082", "USD", "June 30, 2025", "INSUFFICIENT_COMPARABLE_CONTEXT"),
    ("5,082", "$", "June 30, 2026", "INSUFFICIENT_COMPARABLE_CONTEXT"),
])
def test_financial_comparisons_never_cross_currency_or_period(amount, currency, period, status):
    from backend.services.research.financial_observations import compare_financial_observations
    facts = financial_observations("For the quarter ended June 30, 2026. Infosys revenues at USD5,082 million.", "issuer")
    claim = f"For the quarter ended {period}. Infosys revenue was {currency}{amount} million."
    comparison = compare_financial_observations(claim, facts)
    assert comparison[0]["status"] == status
    assert comparison[0]["independent_verification"] is False


def test_feed_html_preserves_paragraph_context_and_not_navigation():
    from backend.services.agent_reach.native.normalizer import NativeNormalizer
    records = NativeNormalizer.normalize_rss_entries([{"title": "Public update", "link": "https://publisher.example/update",
        "feed_content": "<p>We are releasing a preview. It is not generally available.</p><p>Further research is needed.</p>"}])
    assert "preview. It is not generally available.\n\nFurther" in records[0].content


def test_financial_guidance_and_revenue_share_are_not_reported_amounts():
    text = "AI Revenues at 8.2% in Q1\nGuidance for FY27:\nOperating margin of 20%-22%\nKey highlights:\nFor the quarter ended June 30, 2026\nReported revenues at $5,082 million."
    facts = financial_observations(text, "issuer")
    assert not any(f["metric"] == "REVENUE" and f["unit"] == "percent" for f in facts)
    guidance = next(f for f in facts if f["metric"] == "OPERATING_MARGIN")
    assert guidance["scope"] == "GUIDANCE" and guidance["range_upper"] == "22"
    assert guidance["period_end"] is None


def test_trademark_footer_is_not_a_trend_passage():
    text = "2026 NVIDIA Corporation. All rights reserved. NVIDIA and the NVIDIA logo are trademarks in the U.S. and other countries."
    item = EvidenceItem(id="footer", title="NVIDIA update", content=text, content_depth="PARTIAL_CONTENT")
    passage_extractor.extract_passages([item], "NVIDIA", domain="trending")
    assert item.extraction_status == "NO_RELEVANT_PASSAGE"


def test_casual_community_chat_stays_inspectable_not_key_trend():
    from backend.application.research.synthesis import synthesize_grounded_findings
    text = "I have always heard how pet friendly NVIDIA is with their employees."
    item = EvidenceItem(id="chat", channel="reddit", content=text, relevant_excerpt=text,
                        content_depth="SOCIAL_POST", extraction_status="SUCCESS")
    assert synthesize_grounded_findings("NVIDIA", "trending", [item], []) == []
    assert item.content == text
