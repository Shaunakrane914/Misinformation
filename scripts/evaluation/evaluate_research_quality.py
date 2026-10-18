"""Offline scoring against separately frozen, human-adjudicated case labels.

No model calls, provider reads, fixture generation or claim-truth inference.
Acquisition success, exact citation spans and human support judgments are
separate measurements. Never report agent-authored calibration as acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path

VERDICTS = {"SUPPORTED", "REFUTED", "INSUFFICIENT_EVIDENCE"}


def score(observations, labels):
    if not labels.get("cases"):
        raise ValueError("No reviewed cases; an empty packet cannot establish acceptance")
    expected = {case["case_id"]: case for case in labels["cases"]}
    if len(expected) != len(labels["cases"]):
        raise ValueError("Duplicate label case IDs")
    observed = {case["case_id"]: case for case in observations}
    if len(observed) != len(observations) or set(observed) != set(expected):
        raise ValueError("Observation/label case IDs must match exactly")
    counts = dict(cases=len(expected), correct_verdicts=0, incorrect_decisive_verdicts=0,
                  abstentions=0, justified_abstentions=0, relevant_urls_acquired=0,
                  expected_relevant_urls=0, valid_citation_spans=0, citation_spans=0)
    for identity, label in expected.items():
        row = observed[identity]
        prediction = row["verdict"]
        truth = label["verdict"]
        if prediction not in VERDICTS or truth not in VERDICTS:
            raise ValueError("Unsupported verdict; normalize explicitly, never silently")
        counts["correct_verdicts"] += prediction == truth
        counts["incorrect_decisive_verdicts"] += prediction != truth and prediction != "INSUFFICIENT_EVIDENCE"
        counts["abstentions"] += prediction == "INSUFFICIENT_EVIDENCE"
        counts["justified_abstentions"] += prediction == truth == "INSUFFICIENT_EVIDENCE"
        sources = {}
        for source in row.get("sources", []):
            if source["evidence_id"] in sources:
                raise ValueError("Duplicate source ID")
            if hashlib.sha256(source["content"].encode("utf-8")).hexdigest() != source["content_sha256"]:
                raise ValueError("Captured source hash mismatch")
            sources[source["evidence_id"]] = source
        relevant = set(label.get("relevant_urls", []))
        counts["expected_relevant_urls"] += len(relevant)
        counts["relevant_urls_acquired"] += len(relevant & {s["url"] for s in sources.values()})
        for citation in row.get("citations", []):
            counts["citation_spans"] += 1
            source = sources.get(citation.get("evidence_id"))
            start, end, text = citation.get("start"), citation.get("end"), citation.get("text")
            valid = (source is not None and type(start) is int and type(end) is int
                     and isinstance(text, str) and bool(text)
                     and 0 <= start < end <= len(source["content"])
                     and source["content"][start:end] == text)
            counts["valid_citation_spans"] += valid
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None
    independent = (labels.get("label_origin") == "INDEPENDENT_HUMAN_REVIEW"
                   and bool(labels.get("reviewer")) and bool(labels.get("frozen_at")))
    return {"status": "SCORED_INDEPENDENT_LABELS" if independent else "CALIBRATION_ONLY_NOT_ACCEPTANCE",
            "counts": counts, "correct_verdict_rate": ratio(counts["correct_verdicts"], counts["cases"]),
            "abstention_precision": ratio(counts["justified_abstentions"], counts["abstentions"]),
            "relevant_source_recall": ratio(counts["relevant_urls_acquired"], counts["expected_relevant_urls"]),
            "citation_span_validity": ratio(counts["valid_citation_spans"], counts["citation_spans"]),
            "citation_entailment": "NOT_VERIFIED_BY_SPAN_MATCH",
            "label_independence": "DECLARED_BY_REVIEWER_NOT_PROVABLE_BY_SCRIPT",
            "live_ai_generation_requests": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--labels-sha256", required=True, help="Label digest frozen before observation/tuning")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.labels.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.labels_sha256.lower():
        parser.error("Label digest does not match the separately frozen manifest")
    result = score(json.loads(args.observations.read_text(encoding="utf-8")),
                   json.loads(raw.decode("utf-8")))
    result["labels_sha256"] = args.labels_sha256.lower()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
