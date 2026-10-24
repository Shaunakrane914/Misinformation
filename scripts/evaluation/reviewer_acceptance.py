"""Summarize human reviews of frozen observations; never grant release acceptance.

Reuses evaluate_research_quality for verdicts, source hashes and exact spans.
Human acquisition quality, citation entailment and usefulness are distinct from
those mechanical checks. This script makes no model or network requests.

Reviews bind to the SHA-256 of the exact label AND observation file bytes. Each
case may provide ``dimensions`` with acquisition_quality, citation_entailment
and usefulness, each containing status and rationale, plus ``citations`` with
citation_index, status and rationale. Unreviewed dimensions/citations remain
NOT_VERIFIED. Independence and review timing are declarations, not proven facts.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.evaluation.evaluate_research_quality import score

AGENTS = ("scout", "trending", "brandshield", "personal_watch")
DIMENSIONS = ("acquisition_quality", "citation_entailment", "usefulness")
STATUSES = ("PASS", "PARTIAL", "FAIL", "NOT_VERIFIED")
INDEPENDENT = "INDEPENDENT_HUMAN_REVIEW"


def _identifier(value, context):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{context} must be a nonempty, unpadded string")
    return value


def _index(rows, context):
    if not isinstance(rows, list):
        raise ValueError(f"{context} must be an array")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{context} entries must be objects")
        identity = _identifier(row.get("case_id"), f"{context} case_id")
        if identity in result:
            raise ValueError(f"Duplicate {context} case ID: {identity}")
        result[identity] = row
    return result


def _judgment(value):
    if value is None:
        return "NOT_VERIFIED"
    if not isinstance(value, dict) or value.get("status") not in STATUSES:
        raise ValueError("Human judgment must contain an explicit supported status")
    if value["status"] != "NOT_VERIFIED":
        _identifier(value.get("rationale"), "Human judgment rationale")
    return value["status"]


def _review_declaration(reviews):
    origin = reviews.get("review_origin")
    if origin not in (INDEPENDENT, "PENDING_INDEPENDENT_HUMAN_REVIEW", "AGENT_CALIBRATION"):
        raise ValueError("Explicit supported review_origin required")
    if origin == INDEPENDENT:
        _identifier(reviews.get("reviewer"), "reviewer")
        timestamp = _identifier(reviews.get("reviewed_at"), "reviewed_at")
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("reviewed_at must be an ISO timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("reviewed_at must include a timezone")
    return origin == INDEPENDENT


def summarize_reviews(observations, labels, reviews, *, labels_sha256, observations_sha256):
    """Validate a bound human review sheet and retain unreviewed denominators.

    Digest arguments must come from the actual file bytes, as in ``main``.
    No user-provided expected answer or judgment is inferred by this function.
    """
    if not isinstance(labels, dict) or not isinstance(reviews, dict):
        raise ValueError("Labels and reviews must be objects")
    for field, actual in (("labels_sha256", labels_sha256),
                          ("observations_sha256", observations_sha256)):
        if reviews.get(field) != actual:
            raise ValueError(f"Human reviews are not bound to the actual {field}")
    independent = _review_declaration(reviews)
    expected = _index(labels.get("cases"), "label")
    observed = _index(observations, "observation")
    reviewed = _index(reviews.get("cases"), "review")
    if set(reviewed) - set(expected):
        raise ValueError("Review contains unknown case IDs")
    automated = score(observations, labels)
    counts = {dimension: Counter({status: 0 for status in STATUSES}) for dimension in DIMENSIONS}
    citation_counts = Counter({status: 0 for status in STATUSES})
    rows = []
    for identity, label in expected.items():
        if label.get("agent") not in AGENTS:
            raise ValueError("Each label requires an explicit supported agent")
        review = reviewed.get(identity, {})
        dimensions = review.get("dimensions", {})
        if not isinstance(dimensions, dict) or set(dimensions) - set(DIMENSIONS):
            raise ValueError("Unknown or malformed human review dimensions")
        statuses = {dimension: _judgment(dimensions.get(dimension)) for dimension in DIMENSIONS}
        citations = observed[identity].get("citations", [])
        citation_reviews = review.get("citations", [])
        if not isinstance(citation_reviews, list):
            raise ValueError("Citation reviews must be an array")
        by_index = {}
        for citation_review in citation_reviews:
            if not isinstance(citation_review, dict):
                raise ValueError("Citation review must be an object")
            index = citation_review.get("citation_index")
            if type(index) is not int or not 0 <= index < len(citations) or index in by_index:
                raise ValueError("Duplicate or out-of-range citation_index")
            by_index[index] = _judgment(citation_review)
        citation_statuses = [by_index.get(index, "NOT_VERIFIED") for index in range(len(citations))]
        case_score = score([observed[identity]], {**labels, "cases": [label]})
        if statuses["citation_entailment"] == "PASS":
            if any(status != "PASS" for status in citation_statuses):
                raise ValueError("Case entailment PASS contradicts missing or non-PASS citation reviews")
            if case_score["counts"]["valid_citation_spans"] != len(citations):
                raise ValueError("Entailment PASS cannot validate a broken citation span")
            if not citations and observed[identity]["verdict"] != "INSUFFICIENT_EVIDENCE":
                raise ValueError("A decisive verdict without citations cannot have entailment PASS")
        if (statuses["citation_entailment"] == "NOT_VERIFIED"
                and any(status != "NOT_VERIFIED" for status in citation_statuses)):
            raise ValueError("Reviewed citations require an explicit case entailment judgment")
        for dimension, status in statuses.items():
            counts[dimension][status] += 1
        citation_counts.update(citation_statuses)
        rows.append({"case_id": identity, "agent": label["agent"], "dimensions": statuses,
                     "citation_reviews": dict(Counter(citation_statuses))})
    if reviews["review_origin"] == "PENDING_INDEPENDENT_HUMAN_REVIEW" and any(
            count[status] for count in counts.values() for status in ("PASS", "PARTIAL", "FAIL")):
        raise ValueError("Completed judgments cannot declare pending human review")
    per_agent = {}
    for agent in AGENTS:
        cases = [case for case in expected.values() if case["agent"] == agent]
        agent_rows = [row for row in rows if row["agent"] == agent]
        per_agent[agent] = {
            "cases": len(cases),
            "automated": score([observed[case["case_id"]] for case in cases],
                               {**labels, "cases": cases}) if cases else None,
            "human_dimensions": {dimension: dict(Counter(
                row["dimensions"][dimension] for row in agent_rows)) for dimension in DIMENSIONS},
        }
    complete = (all(count["NOT_VERIFIED"] == 0 for count in counts.values())
                and citation_counts["NOT_VERIFIED"] == 0)
    return {
        "status": ("DECLARED_INDEPENDENT_REVIEW_COMPLETE" if complete and independent
                   else "NOT_VERIFIED" if independent or not reviewed
                   else "CALIBRATION_REVIEW_ONLY"),
        "research_quality_acceptance": "NOT_VERIFIED_THRESHOLDS_AND_OWNER_DECISION_REQUIRED",
        "release_acceptance": "NOT_VERIFIED",
        "independence": "DECLARED_BY_REVIEWER_NOT_PROVABLE_BY_SCRIPT",
        "review_origin": reviews["review_origin"],
        "reviewer": reviews.get("reviewer"), "reviewed_at": reviews.get("reviewed_at"),
        "automated": automated,
        "human_review": {"cases": len(expected), "case_records_provided": len(reviewed),
                         "dimensions": {key: dict(value) for key, value in counts.items()},
                         "citation_entailment": dict(citation_counts)},
        "per_agent": per_agent, "cases": rows,
        "labels_sha256": labels_sha256, "observations_sha256": observations_sha256,
        "live_ai_generation_requests": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--labels-sha256", required=True,
                        help="Digest frozen independently before observations or tuning")
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    label_bytes, observation_bytes = args.labels.read_bytes(), args.observations.read_bytes()
    review_bytes = args.reviews.read_bytes()
    label_digest = hashlib.sha256(label_bytes).hexdigest()
    observation_digest = hashlib.sha256(observation_bytes).hexdigest()
    if label_digest != args.labels_sha256.lower():
        parser.error("Label digest does not match the separately frozen manifest")
    try:
        result = summarize_reviews(json.loads(observation_bytes), json.loads(label_bytes),
                                   json.loads(review_bytes), labels_sha256=label_digest,
                                   observations_sha256=observation_digest)
    except (KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    result["reviews_sha256"] = hashlib.sha256(review_bytes).hexdigest()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
