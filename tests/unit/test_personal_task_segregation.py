"""Fictional offline Personal Watch controls; no live accuracy claim."""
import copy

import pytest

from backend.agents.personal_watch.assessment import synthesize_personal_threats


SUBJECT = "Mira Solano"


def article(text, identity="heldout_article", **changes):
    record = {
        "evidence_id": identity,
        "title": "Mira Solano public reporting",
        "url": "https://publisher.test/reports/fictional-control",
        "content_depth": "PARTIAL_CONTENT",
        "content": text,
        "metadata": {"read_success": True, "layer2_eligible": True,
                     "page_metadata": {"body_kind": "ARTICLE_BODY"}},
    }
    record.update(changes)
    return record


def assess(records):
    return synthesize_personal_threats({"canonical_name": SUBJECT}, records)


@pytest.mark.parametrize("text", [
    "Mira Solano reviewed an authentic transcript of remarks from the forum.",
    'Mira Solano listened while Leon Park said "The authentic transcript preserves my own words."',
])
def test_role_or_target_mention_alone_cannot_attribute_speech(text):
    result = assess([article(text)])
    assert result["public_statements"] == []
    assert result["threats"] == []


def test_observed_quote_remains_source_attributed_not_authenticated():
    record = article('Mira Solano said "We must retain the full context before circulating any quotation."')
    result = assess([record])
    statement = result["public_statements"][0]
    assert statement["speaker"] == SUBJECT
    assert statement["attribution"] == "REPORTED_QUOTATION"
    assert statement["identity_authenticated"] is False
    assert statement["claim_status"] == "UNVERIFIED"
    assert record["content"][statement["start"]:statement["end"]] == statement["text"]
    assert not result["threats"] and not result["disputed_claims"]


@pytest.mark.parametrize("text", [
    'A fabricated quote claims Mira Solano said "I endorse this investment scheme." The publisher disputes its attribution.',
    'Mira Solano never said "I endorse this investment scheme," according to this report; no original recording is supplied.',
    'The quotation was falsely attributed to Mira Solano; the publisher has not supplied the original interview.',
    'A misattributed quotation concerning Mira Solano circulated online, according to this article; its provenance remains unknown.',
])
def test_disputed_attribution_is_separate_exact_unverified_source_context(text):
    record = article(text)
    result = assess([record])
    assert result["public_statements"] == []
    assert result["threats"] == result["suspected_impersonations"] == []
    claim = result["disputed_claims"][0]
    assert claim["text"] == text
    assert claim["speaker"] is None
    assert claim["claim_type"] == "DISPUTED_ATTRIBUTION"
    assert claim["claim_status"] == claim["epistemic_state"] == "UNVERIFIED"
    assert claim["assessment_status"] == "SOURCE_REPORT_ONLY"
    assert claim["evidence_ids"] == [record["evidence_id"]]
    assert claim["source_report_url"] == record["url"]
    assert claim["identity_authenticated"] is False
    passage = claim["source_passages"][0]
    assert passage["passage_id"]
    assert record["content"][passage["start"]:passage["end"]] == passage["text"] == text


def test_dispute_about_other_speaker_not_assigned_to_subject_from_title():
    record = article('A false quote claims Leon Park endorsed a product. The report does not concern the monitored speaker.')
    assert assess([record])["disputed_claims"] == []


@pytest.mark.parametrize("variant", ["profile", "snippet", "feed", "raw_feed", "ineligible"])
def test_metadata_indexes_and_rejected_records_do_not_become_task_observations(variant):
    record = article('A false quote claims Mira Solano said "I endorse this product."')
    if variant == "profile":
        record["content_depth"] = "PROFILE_METADATA"
    elif variant == "snippet":
        record["content_depth"] = "SEARCH_SNIPPET"
    elif variant in {"feed", "raw_feed"}:
        record["metadata"]["page_metadata"]["content_scope"] = "FEED_INDEX"
        if variant == "raw_feed":
            record["raw_metadata"] = record.pop("metadata")
    else:
        record["metadata"]["layer2_eligible"] = False
    result = assess([record])
    assert result["public_statements"] == result["disputed_claims"] == result["threats"] == []


def test_inputs_and_existing_passages_remain_unchanged():
    record = article('Mira Solano said "We must retain source context when investigating identity allegations."')
    record["passages"] = [{"sentinel": {"untouched": True}}]
    before = copy.deepcopy(record)
    result = assess([record])
    result["public_statements"][0]["speaker"] = "modified output"
    assert record == before


def test_disputes_are_deduplicated_and_bounded_without_mutating_context():
    records = [article(f'A false quote claims Mira Solano endorsed campaign {index}; original attribution remains unverified.',
                       identity=f"heldout_{index}") for index in range(20)]
    records.insert(1, copy.deepcopy(records[0]))
    before = copy.deepcopy(records)
    claims = assess(records)["disputed_claims"]
    assert len(claims) == 16
    assert len({claim["claim_id"] for claim in claims}) == 16
    assert records == before


def test_empty_results_have_separate_empty_disputed_collection():
    assert assess([])["disputed_claims"] == []
