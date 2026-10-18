"""Calibration regressions, deliberately NOT independent holdout acceptance."""
from backend.agents.brandshield.assessment import synthesize_brand_threats
from backend.services.research.passage_extractor import passage_extractor
from backend.services.research.passage_records import captured_passages, public_statement_attribution
from backend.services.research.research_models import EvidenceItem
from backend.services.research.relevance_gate import relevance_gate


def record(text, url="https://publisher.example/report"):
    return {"evidence_id": "canonical", "title": "Nike report", "content": text,
            "snippet": text, "url": url, "platform": "Web", "content_depth": "PARTIAL_CONTENT"}


def test_protective_notice_does_not_erase_separate_complaint():
    source = record("Nike warning: beware of scams. We never charge applicants.\n\nNike customer complaint: I ordered shoes and never received them. My refund has not arrived.")
    original = source["content"]
    result = synthesize_brand_threats({"brand": "Nike"}, [source])
    assert any(t.get("type") == "CUSTOMER_COMPLAINT" for t in result["threats"])
    assert not any(t.get("type") == "PHISHING_SCAM" for t in result["threats"])
    assert source["content"] == original


def test_counterfeit_report_is_not_a_phishing_publisher():
    source = record("Customs officers seized counterfeit Nike shoes, according to the enforcement report.")
    result = synthesize_brand_threats({"brand": "Nike"}, [source])
    assert result["threats"]
    assert all(t["source_relation"] == "REPORTS_ENFORCEMENT" and t["actor_url"] is None for t in result["threats"])
    assert all(t["epistemic_state"] == "UNVERIFIED" for t in result["threats"])


def test_disputed_accusation_does_not_become_observed_counterfeit():
    source = record("A fabricated claim alleged Nike sold counterfeit shoes. The allegation was debunked.")
    assert synthesize_brand_threats({"brand": "Nike"}, [source])["threats"] == []


def test_explicit_replica_offer_is_not_lost_as_generic_merchandising():
    source = record("Replica Nike sneakers for sale. Add to cart. These are offered by an unauthorized seller.")
    result = synthesize_brand_threats({"brand": "Nike"}, [source])
    assert any(t.get("type") == "COUNTERFEIT" for t in result["threats"])
    assert all(t["epistemic_state"] == "UNVERIFIED" for t in result["threats"])


def test_encyclopedia_history_is_not_a_current_customer_complaint():
    source = record("Nike history includes customer complaints and counterfeit merchandise disputes.", "https://en.wikipedia.org/wiki/Nike")
    assert synthesize_brand_threats({"brand": "Nike"}, [source])["threats"] == []


def test_support_homepage_recall_menu_is_not_a_safety_incident():
    source = record("Apple Support\n\nBeware of counterfeit parts\n\nSome counterfeit batteries may be unsafe.\n\nApple Service Programs\n\nBattery Recall Program", "https://support.apple.com/")
    source["title"] = "Official Apple Support"
    assert synthesize_brand_threats({"brand": "Apple"}, [source])["threats"] == []


def test_fei_given_name_cannot_qualify_an_equestrian_site():
    item = EvidenceItem(id="horse", title="Inside.FEI.org", snippet="FEI rules revision, FEI annual report and dressage world cup.",
                        canonical_url="https://inside.fei.org/", content_depth="PARTIAL_CONTENT")
    assert not relevance_gate.evaluate_item(item, "Fei-Fei Li", domain="personal").is_accepted


def test_joint_statement_keeps_speakers_separate():
    first = "We are announcing a public leadership transition and it is not effective until next year."
    second = "We are changing our consumer product roadmap and have published the details."
    body = "SATYA NADELLA MESSAGE\n\n" + first + "\n\nRYAN ROSLANSKY MESSAGE\n\n" + second
    item = EvidenceItem(id="statement", content=body, title="Leadership update", source_name="Publisher",
                        query_class="public_statement_discovery", content_depth="FEED_ENTRY_CONTENT")
    assert public_statement_attribution(item, first, "Satya Nadella") == "OBSERVED_SPEAKER_SECTION"
    assert public_statement_attribution(item, second, "Satya Nadella") is None
    passage_extractor.extract_passages([item], "Satya Nadella", domain="personal")
    assert item.relevant_excerpt == first
    assert next(p for p in captured_passages(item, "personal", "Satya Nadella") if p["text"] == first)["content_role"] == "PUBLIC_STATEMENT"


def test_reported_quote_is_attributed_not_authenticated():
    text = '“We are publishing an update, not a completed investigation,” said Tim Cook.'
    item = EvidenceItem(id="quote", content=text, source_name="Reporter", query_class="public_statement_discovery",
                        content_depth="FULL_ARTICLE", canonical_url="https://publisher.example/quote")
    assert public_statement_attribution(item, text, "Tim Cook") == "REPORTED_QUOTATION"
    passages = captured_passages(item, "personal", "Tim Cook")
    assert passages[0]["attribution"] == "REPORTED_QUOTATION"
    assert passages[0]["claim_status"] == "UNVERIFIED"


def test_relevant_passage_after_navigation_is_not_lost_to_display_cap():
    body = "\n\n".join("Navigation section number " + str(i) + " with general information." for i in range(30))
    substantive = "Customs officers seized counterfeit Nike shoes according to court documents."
    source = record(body + "\n\n" + substantive)
    passages = captured_passages(source, "brand", "Nike")
    assert len(passages) == 16
    assert any(p["text"] == substantive and source["content"][p["start"]:p["end"]] == substantive for p in passages)
    assert synthesize_brand_threats({"brand": "Nike"}, [source])["threats"]


def test_financial_scale_conversion_is_not_currency_conversion():
    from backend.services.research.financial_observations import financial_observations, compare_financial_observations
    source = financial_observations("For the quarter ended June 30, 2026. Revenue was $5,082 million.", "issuer")
    same = compare_financial_observations("For the quarter ended June 30, 2026. Revenue was $5.082 billion.", source)
    assert same[0]["status"] == "MATCHES_SOURCE_ASSERTION"
    different = compare_financial_observations("For the quarter ended June 30, 2026. Revenue was INR5.082 billion.", source)
    assert different[0]["status"] == "INSUFFICIENT_COMPARABLE_CONTEXT"


def test_reader_wrapper_title_and_url_are_not_an_incident():
    source = record("Title: Nike counterfeit goods seized\n\nURL Source: https://publisher.example/Nike-counterfeit\n\nMarkdown Content:\n[Skip to main content](https://publisher.example/Nike-counterfeit#main)\n\n[Counterfeit report](https://publisher.example/Nike-counterfeit)")
    assert synthesize_brand_threats({"brand": "Nike"}, [source])["threats"] == []
    assert all(p["content_role"] in {"SOURCE_METADATA", "NAVIGATION"} for p in source["passages"])


def test_surname_quote_requires_unambiguous_full_name_in_capture():
    quote = '“It has been a privilege and we have published an update,” said Cook.'
    item = EvidenceItem(id="quote", content="Tim Cook and John Ternus announced a transition.\n\n" + quote,
                        query_class="explicit_url", content_depth="PARTIAL_CONTENT")
    assert public_statement_attribution(item, quote, "Tim Cook") == "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"
    assert public_statement_attribution(item, quote, "tim cook") == "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"
    item.content += "\n\nJames Cook also attended."
    assert public_statement_attribution(item, quote, "Tim Cook") is None


def test_trending_publisher_label_or_debunk_word_does_not_adjudicate_claim():
    from backend.agents.trending.clustering import extract_claims_from_cluster
    from backend.agents.trending.models import TrendEvidence
    items = [TrendEvidence(evidence_id="issuer", platform="web", title="Issuer announces a product", content="Captured publisher text", source="Issuer", source_role="PRIMARY", source_tier="TIER_1"),
             TrendEvidence(evidence_id="report", platform="web", title="Fake product allegation debunked", content="Captured reporter text", source="Reporter", source_role="SECONDARY")]
    claims = extract_claims_from_cluster(items)
    assert all(c["status"] == "UNVERIFIED" and c["supporting_sources"] == c["contradicting_sources"] == 0 for c in claims)


def test_specialist_brief_counts_observed_statement_without_calling_it_abuse():
    from backend.services.research.specialist_brief import specialist_brief
    source = {"evidence_id": "statement", "url": "https://publisher.example/statement", "query_class": "explicit_url",
              "content_depth": "PARTIAL_CONTENT", "content": 'Tim Cook issued an update.\n\n“We have published the details and it is not final,” said Cook.'}
    status, summary, _ = specialist_brief({"evidence": [source], "subject": {"canonical_name": "Tim Cook"}}, "personal_watch", "https://publisher.example/statement", 0)
    assert status["task_text_candidates"] == 1
    assert "1 public statement record(s)" in summary
    assert "not authenticated identity or evidence of abuse" in summary
