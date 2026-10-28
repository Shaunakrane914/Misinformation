"""Captured report allegations are not direct actor observations or calibrated risk."""
import copy
import json
from pathlib import Path

import pytest

from backend.agents.personal_watch.assessment import synthesize_personal_threats


@pytest.mark.parametrize('text,threat', [
    ('CEO Aria Vale received a compensation increase. Critics call the stock buyback a scam that benefits shareholders.', False),
    ('A phishing scam targeted Aria Vale through a fake account that solicited money from victims.', True),
    ('A publisher reported that Aria Vale was charged with investment fraud involving victims.', True),
])
def test_rhetorical_scam_criticism_is_context_but_reported_incidents_remain(text, threat):
    record = {'evidence_id':'context_control', 'title':'Aria Vale report',
        'url':'https://publisher.test/observed-report', 'content_depth':'PARTIAL_CONTENT', 'content':text,
        'metadata':{'read_success':True,'page_metadata':{'body_kind':'ARTICLE_BODY'}}}
    result = synthesize_personal_threats({'canonical_name':'Aria Vale'}, [record])
    assert bool(result['threats']) is threat
    assert result['identity_risk'] == ('UNVERIFIED_ALLEGATIONS' if threat else 'UNASSESSED')
    assert not result['public_statements']


@pytest.fixture
def wion_report():
    path = Path(__file__).parent / "fixtures" / "wion_personal_report_20261022.json"
    return json.loads(path.read_text(encoding="utf-8"))["record"]


def test_genuine_fake_stream_report_is_one_unverified_observation(wion_report):
    result = synthesize_personal_threats({"canonical_name": "Tim Cook"}, [wion_report])
    assert len(result["threats"]) == 1
    report = result["threats"][0]
    assert report["threat_type"] == "IMPERSONATION"
    assert report["risk_level"] == "UNASSESSED"
    assert report["confidence"] is None
    assert report["confidence_basis"] == "NOT_ASSESSED"
    assert report["assessment_status"] == "SOURCE_REPORT_ONLY"
    assert report["epistemic_state"] == "UNVERIFIED"
    assert report["technical_forensics_run"] is False
    assert report["direct_actor_capture"] is False
    assert report["indicators"] == []
    assert report["source_report_url"] == wion_report["url"]
    assert report["source_published_at"] == "Mon, 09 Sep 2024 07:33:00 GMT"
    assert report["temporal_state"] == "CURRENT_ACTIVITY_NOT_ESTABLISHED"
    assert report["source_date_status"] == "DECLARED_SOURCE_DATE_UNVERIFIED"
    for passage in report["source_passages"]:
        assert passage["evidence_id"] == wion_report["evidence_id"]
        assert wion_report["content"][passage["start"]:passage["end"]] == passage["text"]
    assert result["identity_authenticated"] is False
    assert result["public_statements"] == []


def test_publisher_author_cannot_become_a_suspect_handle(wion_report):
    wion_report["author"] = "WION Reporter"
    result = synthesize_personal_threats({"canonical_name": "Tim Cook"}, [wion_report])
    suspect = result["suspected_impersonations"][0]
    assert suspect["handle"] is None
    assert suspect["observed_actor_url"] is None
    assert suspect["source_report_url"] == wion_report["url"]
    assert suspect["indicators"] == []
    assert "Lookalike" not in json.dumps(result)


def test_duplicate_source_cannot_count_as_two_incidents(wion_report):
    result = synthesize_personal_threats({"canonical_name": "Tim Cook"},
                                       [wion_report, copy.deepcopy(wion_report)])
    assert len(result["threats"]) == len(result["claims"]) == 1
    assert len(result["suspected_impersonations"]) == 1
    passages = result["threats"][0]["source_passages"]
    assert len({p["passage_id"] for p in passages}) == len(passages) == 2


def test_fake_speech_cannot_become_a_genuine_public_statement():
    record = {"evidence_id": "synthetic_quote", "title": "Fake Tim Cook livestream",
              "url": "https://publisher.test/fake-stream", "content_depth": "PARTIAL_CONTENT",
              "content": 'The fake video impersonated Tim Cook, who said "Send money to double your crypto."',
              "metadata": {"read_success": True, "page_metadata": {"body_kind": "ARTICLE_BODY"}}}
    result = synthesize_personal_threats({"canonical_name": "Tim Cook"}, [record])
    assert result["public_statements"] == []
    assert result["threats"][0]["assessment_status"] == "SOURCE_REPORT_ONLY"


def test_real_public_statement_remains_inspectable_without_threat():
    record = {"evidence_id": "statement", "title": "Aria Vale statement",
              "url": "https://publisher.test/interview", "content_depth": "PARTIAL_CONTENT",
              "content": 'Aria Vale said "We need to preserve the full source context before sharing quotations."',
              "metadata": {"read_success": True, "page_metadata": {"body_kind": "ARTICLE_BODY"}}}
    result = synthesize_personal_threats({"canonical_name": "Aria Vale"}, [record])
    assert not result["threats"] and not result["suspected_impersonations"]
    assert result["public_statements"][0]["evidence_id"] == "statement"
    assert result["public_statements"][0]["identity_authenticated"] is False


def test_profile_metadata_cannot_satisfy_allegation_acquisition(wion_report):
    wion_report["content_depth"] = "PROFILE_METADATA"
    result = synthesize_personal_threats({"canonical_name": "Tim Cook"}, [wion_report])
    assert not result["threats"] and not result["suspected_impersonations"]
    assert result["identity_risk"] == "UNASSESSED"


@pytest.mark.parametrize("body,kind,key", [
    ("Aria Vale was targeted by a phishing scam, according to a publisher report.", "SCAM", "suspected_scams"),
    ("A publisher reports a deepfake AI voice clone of Aria Vale with no supplied recording.", "DEEPFAKE", "deepfake_claims"),
])
def test_other_report_types_also_preserve_uncertainty(body, kind, key):
    record = {"evidence_id": "reported", "title": "Aria Vale report", "content": body,
              "url": "https://publisher.test/report", "content_depth": "PARTIAL_CONTENT"}
    result = synthesize_personal_threats({"canonical_name": "Aria Vale"}, [record])
    assert result["threats"][0]["threat_type"] == kind
    assert result["threats"][0]["risk_level"] == "UNASSESSED"
    assert result[key][0]["assessment_status"] == "SOURCE_REPORT_ONLY"


def _recovered_wion_record(tail="", metadata_key="metadata"):
    """Use the genuine navigation-bearing capture and actual recovery gate."""
    from backend.services.research.body_context import reconcile_captured_context
    from backend.services.research.research_models import EvidenceItem
    path = Path(__file__).parents[1] / "fixtures" / "acquisition" / "2026-10-22_wion_text_capture.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    item = EvidenceItem(id=saved["source_id"], canonical_url=saved["url"], title=saved["title"],
                        content=saved["readable_text"] + tail, content_depth="FULL_TEXT", read_status="SUCCESS",
                        metadata={"read_success": True, "page_metadata": copy.deepcopy(saved["page_metadata"])})
    reconcile_captured_context(item)
    return {"evidence_id": item.id, "url": item.canonical_url, "title": item.title,
            "content": item.content, "content_depth": item.content_depth,
            metadata_key: copy.deepcopy(item.metadata)}


@pytest.mark.parametrize("metadata_key", ["metadata", "raw_metadata"])
def test_specialist_brief_counts_scoped_genuine_wion_allegation(metadata_key):
    from backend.services.research.passage_extractor import has_usable_passage
    from backend.services.research.specialist_brief import specialist_brief
    record = _recovered_wion_record(metadata_key=metadata_key)
    assert not has_usable_passage(record)  # Raw buffer also contains navigation.
    before = copy.deepcopy(record)
    status, summary, _ = specialist_brief({"evidence": [record]}, "personal_watch", "Tim Cook", 0)
    assert status["task_text_candidates"] == 1
    assert status["entailment_verified"] is False
    assert "does not confirm a threat" in summary
    assert record == before


@pytest.mark.parametrize("failure", ["profile", "snippet", "ineligible", "empty", "invalid_scope"])
def test_specialist_brief_cannot_promote_rejected_or_metadata_capture(failure):
    from backend.services.research.specialist_brief import specialist_brief
    record = _recovered_wion_record()
    if failure == "profile":
        record["content_depth"] = "PROFILE_METADATA"
    elif failure == "snippet":
        record["content_depth"] = "SEARCH_SNIPPET"
    elif failure == "ineligible":
        record["metadata"]["layer2_eligible"] = False
    elif failure == "empty":
        record["content"] = ""
    else:
        record["metadata"]["page_metadata"]["article_body_recovery"]["source_text_sha256"] = "0" * 64
    status, _, _ = specialist_brief({"evidence": [record]}, "personal_watch", "Tim Cook", 0)
    assert status["task_text_candidates"] == 0


def test_specialist_brief_does_not_count_outside_related_story_incident():
    from backend.services.research.specialist_brief import specialist_brief
    card = ("Contoso reported that investigators uncovered a counterfeit operation where its products were sold "
            "by an unauthorized online store. This synthetic related card is outside the acquired article scope.")
    record = _recovered_wion_record("\n\n" + card)
    # The underlying article concerns Apple/Tim Cook. An outside card must not
    # become Contoso's brand-abuse evidence merely because it matches keywords.
    from backend.services.research.passage_records import captured_passages
    assert not any(card == p["text"] for p in captured_passages(record, "brand", "Contoso"))
    status, _, _ = specialist_brief({"evidence": [record]}, "brandshield", "Contoso", 0)
    assert status["task_text_candidates"] == 0
