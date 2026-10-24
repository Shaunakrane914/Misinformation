"""Synthetic contract checks, not human-reviewed research acceptance cases."""
import hashlib
import json

import pytest

from scripts.evaluation.reviewer_acceptance import main, summarize_reviews


@pytest.fixture
def packet():
    text = "Synthetic recorded source passage."
    observations = [{"case_id": "contract-one", "verdict": "SUPPORTED", "sources": [{
        "evidence_id": "canonical", "url": "https://example.org/recorded", "content": text,
        "content_sha256": hashlib.sha256(text.encode()).hexdigest()}], "citations": [{
            "evidence_id": "canonical", "start": 0, "end": len(text), "text": text}]}]
    labels = {"label_origin": "AGENT_CALIBRATION", "cases": [{
        "case_id": "contract-one", "agent": "scout", "verdict": "SUPPORTED",
        "relevant_urls": ["https://example.org/recorded"]}]}
    reviews = {"review_origin": "PENDING_INDEPENDENT_HUMAN_REVIEW", "reviewer": None,
               "reviewed_at": None, "cases": []}
    return observations, labels, reviews


def bound(packet):
    observations, labels, reviews = packet
    label_digest = hashlib.sha256(json.dumps(labels).encode()).hexdigest()
    observation_digest = hashlib.sha256(json.dumps(observations).encode()).hexdigest()
    reviews["labels_sha256"] = label_digest
    reviews["observations_sha256"] = observation_digest
    return {"labels_sha256": label_digest, "observations_sha256": observation_digest}


def judge(status="PASS"):
    return {"status": status, "rationale": "Synthetic contract judgment, not a reviewed answer."}


def complete_review(packet):
    reviews = packet[2]
    reviews.update(review_origin="INDEPENDENT_HUMAN_REVIEW", reviewer="synthetic-test-reviewer",
                   reviewed_at="2026-10-21T12:00:00+05:30")
    reviews["cases"] = [{"case_id": "contract-one", "dimensions": {
        "acquisition_quality": judge(), "citation_entailment": judge(), "usefulness": judge()},
        "citations": [{"citation_index": 0, **judge()}]}]
    return reviews["cases"][0]


def test_unreviewed_exact_spans_never_become_human_acceptance(packet):
    result = summarize_reviews(*packet, **bound(packet))
    assert result["status"] == "NOT_VERIFIED"
    assert result["automated"]["citation_span_validity"] == 1
    assert result["human_review"]["dimensions"]["citation_entailment"]["NOT_VERIFIED"] == 1
    assert result["human_review"]["citation_entailment"]["NOT_VERIFIED"] == 1
    assert result["release_acceptance"] == "NOT_VERIFIED"
    assert result["live_ai_generation_requests"] == 0


def test_complete_review_remains_distinct_from_accuracy_and_release_acceptance(packet):
    complete_review(packet)
    result = summarize_reviews(*packet, **bound(packet))
    assert result["status"] == "DECLARED_INDEPENDENT_REVIEW_COMPLETE"
    assert result["research_quality_acceptance"].startswith("NOT_VERIFIED")
    assert result["automated"]["status"] == "CALIBRATION_ONLY_NOT_ACCEPTANCE"
    assert result["per_agent"]["scout"]["automated"]["counts"]["cases"] == 1
    assert result["per_agent"]["trending"]["automated"] is None


def test_failed_human_entailment_does_not_change_valid_span_metric(packet):
    row = complete_review(packet)
    row["dimensions"]["citation_entailment"] = judge("FAIL")
    row["citations"][0]["status"] = "FAIL"
    result = summarize_reviews(*packet, **bound(packet))
    assert result["automated"]["citation_span_validity"] == 1
    assert result["human_review"]["dimensions"]["citation_entailment"]["FAIL"] == 1
    assert result["human_review"]["citation_entailment"]["FAIL"] == 1
    assert result["release_acceptance"] == "NOT_VERIFIED"


def test_missing_dimensions_remain_unverified(packet):
    row = complete_review(packet)
    del row["dimensions"]["usefulness"]
    result = summarize_reviews(*packet, **bound(packet))
    assert result["status"] == "NOT_VERIFIED"
    assert result["human_review"]["dimensions"]["usefulness"]["NOT_VERIFIED"] == 1


def test_partial_case_judgment_with_unreviewed_citation_is_not_complete(packet):
    row = complete_review(packet)
    row["dimensions"]["citation_entailment"] = judge("PARTIAL")
    row["citations"] = []
    result = summarize_reviews(*packet, **bound(packet))
    assert result["status"] == "NOT_VERIFIED"
    assert result["human_review"]["citation_entailment"]["NOT_VERIFIED"] == 1


def test_missing_observation_is_not_silently_removed_from_denominator(packet):
    packet[0].clear()
    with pytest.raises(ValueError, match="case IDs must match exactly"):
        summarize_reviews(*packet, **bound(packet))


@pytest.mark.parametrize("status", ["pass", "SUPPORTED", True, None])
def test_unknown_human_status_is_not_normalized(packet, status):
    complete_review(packet)["dimensions"]["usefulness"]["status"] = status
    with pytest.raises(ValueError, match="explicit supported status"):
        summarize_reviews(*packet, **bound(packet))


def test_misspelled_dimension_cannot_be_ignored(packet):
    complete_review(packet)["dimensions"]["usefulnes"] = judge()
    with pytest.raises(ValueError, match="human review dimensions"):
        summarize_reviews(*packet, **bound(packet))


@pytest.mark.parametrize("kind", ["label", "observation", "review"])
def test_duplicate_case_ids_rejected(packet, kind):
    complete_review(packet)
    collection = {"label": packet[1]["cases"], "observation": packet[0],
                  "review": packet[2]["cases"]}[kind]
    collection.append(dict(collection[0]))
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_reviews(*packet, **bound(packet))


@pytest.mark.parametrize("identity", [None, "", " padded ", "unknown-case"])
def test_missing_or_unknown_case_id_rejected(packet, identity):
    complete_review(packet)["case_id"] = identity
    with pytest.raises(ValueError):
        summarize_reviews(*packet, **bound(packet))


@pytest.mark.parametrize("index", [True, -1, 1, "0"])
def test_invalid_citation_indices_rejected(packet, index):
    complete_review(packet)["citations"][0]["citation_index"] = index
    with pytest.raises(ValueError, match="citation_index"):
        summarize_reviews(*packet, **bound(packet))


def test_duplicate_citation_reviews_rejected(packet):
    row = complete_review(packet)
    row["citations"].append(dict(row["citations"][0]))
    with pytest.raises(ValueError, match="citation_index"):
        summarize_reviews(*packet, **bound(packet))


@pytest.mark.parametrize("status", ["PARTIAL", "FAIL", "NOT_VERIFIED"])
def test_entailment_pass_cannot_hide_incomplete_or_failed_citation_reviews(packet, status):
    complete_review(packet)["citations"][0]["status"] = status
    with pytest.raises(ValueError, match="Case entailment PASS"):
        summarize_reviews(*packet, **bound(packet))


def test_broken_spans_cannot_have_entailment_pass(packet):
    complete_review(packet)
    packet[0][0]["citations"][0]["text"] = "Not the exact source."
    with pytest.raises(ValueError, match="broken citation span"):
        summarize_reviews(*packet, **bound(packet))


def test_decisive_verdict_without_citations_cannot_pass(packet):
    row = complete_review(packet)
    packet[0][0]["citations"] = []
    row["citations"] = []
    with pytest.raises(ValueError, match="decisive verdict without citations"):
        summarize_reviews(*packet, **bound(packet))


def test_wrong_decisions_and_justified_abstentions_use_existing_scorer(packet):
    packet[0][0]["verdict"] = "REFUTED"
    result = summarize_reviews(*packet, **bound(packet))
    assert result["automated"]["counts"]["incorrect_decisive_verdicts"] == 1
    packet[0][0]["verdict"] = packet[1]["cases"][0]["verdict"] = "INSUFFICIENT_EVIDENCE"
    packet[0][0]["citations"] = []
    row = complete_review(packet)
    row["citations"] = []
    result = summarize_reviews(*packet, **bound(packet))
    assert result["automated"]["counts"]["justified_abstentions"] == 1
    assert result["human_review"]["citation_entailment"]["PASS"] == 0


@pytest.mark.parametrize("value", [None, "", "2026-10-21", "not-a-date"])
def test_independent_review_requires_timezone_timestamp(packet, value):
    complete_review(packet)
    packet[2]["reviewed_at"] = value
    with pytest.raises(ValueError):
        summarize_reviews(*packet, **bound(packet))


def test_independent_review_requires_reviewer_and_judgment_rationale(packet):
    row = complete_review(packet)
    packet[2]["reviewer"] = None
    with pytest.raises(ValueError, match="reviewer"):
        summarize_reviews(*packet, **bound(packet))
    packet[2]["reviewer"] = "synthetic-test-reviewer"
    row["dimensions"]["usefulness"]["rationale"] = ""
    with pytest.raises(ValueError, match="rationale"):
        summarize_reviews(*packet, **bound(packet))


def test_pending_origin_cannot_include_completed_judgments(packet):
    complete_review(packet)
    packet[2]["review_origin"] = "PENDING_INDEPENDENT_HUMAN_REVIEW"
    with pytest.raises(ValueError, match="pending human review"):
        summarize_reviews(*packet, **bound(packet))


def test_body_hash_validation_is_not_bypassed(packet):
    packet[0][0]["sources"][0]["content"] += "Changed."
    with pytest.raises(ValueError, match="source hash mismatch"):
        summarize_reviews(*packet, **bound(packet))


def test_cli_binds_exact_bytes_and_never_overwrites(tmp_path, packet, capsys):
    digests = bound(packet)
    paths = {name: tmp_path / f"{name}.json" for name in ("labels", "observations", "reviews")}
    for name, value in zip(("observations", "labels", "reviews"), packet):
        paths[name].write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "new-score.json"
    args = ["--observations", str(paths["observations"]), "--labels", str(paths["labels"]),
            "--labels-sha256", digests["labels_sha256"], "--reviews", str(paths["reviews"]),
            "--output", str(output)]
    assert main(args) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["reviews_sha256"] == hashlib.sha256(paths["reviews"].read_bytes()).hexdigest()
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        main(args)
    assert output.read_bytes() == original
    paths["observations"].write_bytes(paths["observations"].read_bytes() + b"\n")
    with pytest.raises(SystemExit) as error:
        main(args[:-1] + [str(tmp_path / "invalid-score.json")])
    assert error.value.code == 2
    assert not (tmp_path / "invalid-score.json").exists()
    assert "actual observations_sha256" in capsys.readouterr().err


def test_cli_rejects_unfrozen_labels(tmp_path, packet):
    bound(packet)
    paths = []
    for name, value in zip(("observations", "labels", "reviews"), packet):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    with pytest.raises(SystemExit) as error:
        main(["--observations", str(paths[0]), "--labels", str(paths[1]),
              "--labels-sha256", "0" * 64, "--reviews", str(paths[2]),
              "--output", str(tmp_path / "never-written.json")])
    assert error.value.code == 2
    assert not (tmp_path / "never-written.json").exists()
