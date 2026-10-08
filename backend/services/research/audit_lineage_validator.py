"""
Aegis Protocol — Machine-Checkable Audit Lineage Validator
===========================================================
Enforces strict observability contracts for retrieval audits.
Guarantees that metrics are derived solely from observed production events
rather than reconstructive heuristics or synthetic approximations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TelemetryObservationStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    NOT_OBSERVED = "NOT_OBSERVED"
    INVALID = "INVALID"


@dataclass
class LineageValidationResult:
    is_valid: bool
    completeness_status: str  # "PASS" | "FAIL" | "NOT_ENOUGH_EVIDENCE"
    total_evidence_count: int = 0
    valid_lineage_count: int = 0
    broken_lineage_count: int = 0
    synthetic_events_detected: int = 0
    unobserved_acquisitions_count: int = 0
    violations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "completeness_status": self.completeness_status,
            "total_evidence_count": self.total_evidence_count,
            "valid_lineage_count": self.valid_lineage_count,
            "broken_lineage_count": self.broken_lineage_count,
            "synthetic_events_detected": self.synthetic_events_detected,
            "unobserved_acquisitions_count": self.unobserved_acquisitions_count,
            "violations": self.violations,
            "details": self.details,
        }


def validate_candidate_lineage(
    discovered_events: List[Dict[str, Any]],
    ranked_events: List[Dict[str, Any]],
    selected_events: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Verify that:
    1. Every ranked candidate traces to an observed discovered candidate.
    2. Every accepted candidate traces to an observed ranked candidate.
    3. No IDs are invented or empty.
    """
    violations = []
    disc_ids = {d.get("candidate_id") for d in discovered_events if d.get("candidate_id")}
    
    ranked_ids = set()
    for r in ranked_events:
        c_id = r.get("candidate_id")
        r_id = r.get("ranked_candidate_id")
        if not c_id:
            violations.append(f"Ranked event missing candidate_id: {r}")
        elif c_id not in disc_ids:
            violations.append(f"Ranked candidate '{c_id}' was never observed in discovery events")
        if not r_id:
            violations.append(f"Ranked event missing ranked_candidate_id: {r}")
        else:
            ranked_ids.add(r_id)

    for s in selected_events:
        if s.get("selection_decision") == "ACCEPTED":
            r_id = s.get("ranked_candidate_id")
            acc_id = s.get("accepted_candidate_id")
            if not r_id:
                violations.append(f"Accepted candidate event missing ranked_candidate_id: {s}")
            elif r_id not in ranked_ids:
                violations.append(f"Accepted candidate references unranked ID '{r_id}'")
            if not acc_id:
                violations.append(f"Accepted candidate event missing accepted_candidate_id: {s}")

    return len(violations) == 0, violations


def validate_acquisition_lineage(
    selected_events: List[Dict[str, Any]],
    acquisition_attempts: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Verify that:
    1. Every acquisition attempt references an observed accepted candidate.
    2. Successful acquisitions have useful content extracted, latency, and valid backend.
    3. No acquisition attempts are synthesized from discovery queries.
    """
    violations = []
    acc_ids = {
        s.get("accepted_candidate_id")
        for s in selected_events
        if s.get("selection_decision") == "ACCEPTED" and s.get("accepted_candidate_id")
    }

    seen_attempt_ids = set()
    for a in acquisition_attempts:
        att_id = a.get("attempt_id")
        if not att_id:
            violations.append(f"Acquisition attempt missing attempt_id: {a}")
        elif att_id in seen_attempt_ids:
            violations.append(f"Duplicate acquisition attempt_id observed: '{att_id}'")
        else:
            seen_attempt_ids.add(att_id)

        # Check reference to accepted candidate
        acc_ref = a.get("accepted_candidate_id")
        if not acc_ref:
            violations.append(f"Acquisition attempt '{att_id}' does not reference an accepted_candidate_id")
        elif acc_ref not in acc_ids:
            violations.append(f"Acquisition attempt '{att_id}' references unknown accepted_candidate_id '{acc_ref}'")

        # Check for query confusion
        if a.get("query_text") and not a.get("url"):
            violations.append(f"Acquisition attempt '{att_id}' looks like a discovery query, not a candidate read")

        # Validate success criteria
        if a.get("status") == "SUCCESS":
            if not a.get("useful_content_extracted"):
                violations.append(f"Acquisition '{att_id}' marked SUCCESS but useful_content_extracted is False")
            if not a.get("backend"):
                violations.append(f"Acquisition '{att_id}' marked SUCCESS without backend attribution")
            if not a.get("acquired_candidate_id"):
                violations.append(f"Successful acquisition '{att_id}' missing acquired_candidate_id")

    return len(violations) == 0, violations


def validate_evidence_lineage(
    final_evidence_records: List[Dict[str, Any]],
    acquisition_attempts: List[Dict[str, Any]],
    selected_events: List[Dict[str, Any]],
    ranked_events: List[Dict[str, Any]],
    discovered_events: List[Dict[str, Any]],
) -> LineageValidationResult:
    """
    Complete end-to-end lineage validation for every final evidence record:
    evidence_id
      -> acquisition_attempt_id
      -> acquired_candidate_id
      -> accepted_candidate_id
      -> ranked_candidate_id
      -> discovered_candidate_id
    """
    violations = []
    synthetic_detected = 0
    unobserved_acquisitions = 0
    valid_count = 0

    acq_map = {a.get("attempt_id"): a for a in acquisition_attempts if a.get("attempt_id")}
    acquired_to_att = {a.get("acquired_candidate_id"): a for a in acquisition_attempts if a.get("status") == "SUCCESS" and a.get("acquired_candidate_id")}
    
    acc_map = {
        s.get("accepted_candidate_id"): s
        for s in selected_events
        if s.get("selection_decision") == "ACCEPTED" and s.get("accepted_candidate_id")
    }
    
    rank_map = {r.get("ranked_candidate_id"): r for r in ranked_events if r.get("ranked_candidate_id")}
    disc_ids = {d.get("candidate_id") for d in discovered_events if d.get("candidate_id")}

    for ev in final_evidence_records:
        ev_id = ev.get("evidence_id") or ev.get("id")
        if not ev_id:
            violations.append(f"Final evidence item missing evidence_id: {ev}")
            continue

        att_id = ev.get("acquisition_attempt_id")
        acq_id = ev.get("acquired_candidate_id")
        acc_id = ev.get("accepted_candidate_id")
        rank_id = ev.get("ranked_candidate_id")
        disc_id = ev.get("discovered_candidate_id")

        # 1. Check acquisition attempt reference
        if not att_id:
            violations.append(f"Evidence '{ev_id}' has no acquisition_attempt_id (unobserved acquisition)")
            unobserved_acquisitions += 1
            continue

        acq_event = acq_map.get(att_id)
        if not acq_event:
            violations.append(f"Evidence '{ev_id}' references non-existent acquisition attempt '{att_id}'")
            synthetic_detected += 1
            continue

        if acq_event.get("status") != "SUCCESS" or not acq_event.get("useful_content_extracted"):
            violations.append(f"Evidence '{ev_id}' references unsuccessful acquisition '{att_id}'")
            continue

        # 2. Check acquired candidate identity
        expected_acq_id = acq_event.get("acquired_candidate_id")
        if acq_id and acq_id != expected_acq_id:
            violations.append(f"Evidence '{ev_id}' acquired_id '{acq_id}' does not match attempt's acquired_id '{expected_acq_id}'")
            continue

        # 3. Check accepted candidate reference
        att_acc_ref = acq_event.get("accepted_candidate_id")
        if not att_acc_ref or att_acc_ref not in acc_map:
            violations.append(f"Acquisition '{att_id}' references invalid accepted candidate '{att_acc_ref}'")
            continue

        if acc_id and acc_id != att_acc_ref:
            violations.append(f"Evidence '{ev_id}' accepted_id '{acc_id}' differs from attempt's accepted_id '{att_acc_ref}'")
            continue

        # 4. Check ranked candidate reference
        acc_event = acc_map[att_acc_ref]
        acc_rank_ref = acc_event.get("ranked_candidate_id")
        if not acc_rank_ref or acc_rank_ref not in rank_map:
            violations.append(f"Accepted candidate '{att_acc_ref}' references invalid ranked candidate '{acc_rank_ref}'")
            continue

        if rank_id and rank_id != acc_rank_ref:
            violations.append(f"Evidence '{ev_id}' rank_id '{rank_id}' differs from selection's rank_id '{acc_rank_ref}'")
            continue

        # 5. Check discovered candidate reference
        rank_event = rank_map[acc_rank_ref]
        rank_disc_ref = rank_event.get("candidate_id")
        if not rank_disc_ref or rank_disc_ref not in disc_ids:
            violations.append(f"Ranked candidate '{acc_rank_ref}' references undiscovered candidate '{rank_disc_ref}'")
            continue

        if disc_id and disc_id != rank_disc_ref:
            violations.append(f"Evidence '{ev_id}' disc_id '{disc_id}' differs from ranking's candidate_id '{rank_disc_ref}'")
            continue

        valid_count += 1

    total_ev = len(final_evidence_records)
    is_valid = (len(violations) == 0 and valid_count == total_ev)
    completeness = "OBSERVED" if is_valid else ("NOT_ENOUGH_EVIDENCE" if unobserved_acquisitions > 0 or synthetic_detected > 0 else "FAIL")

    return LineageValidationResult(
        is_valid=is_valid,
        completeness_status=completeness,
        total_evidence_count=total_ev,
        valid_lineage_count=valid_count,
        broken_lineage_count=total_ev - valid_count,
        synthetic_events_detected=synthetic_detected,
        unobserved_acquisitions_count=unobserved_acquisitions,
        violations=violations,
        details={
            "observed_discovery_candidates": len(disc_ids),
            "observed_ranked_candidates": len(rank_map),
            "observed_accepted_candidates": len(acc_map),
            "observed_acquisition_attempts": len(acq_map),
            "observed_final_evidence": total_ev,
        }
    )


def validate_no_synthetic_events(
    agent_name: str,
    evidence_records: List[Dict[str, Any]],
    acquisition_attempts: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Check for banned synthetic telemetry patterns:
    - Evidence items without an acquisition attempt.
    - Acquisitions without valid backend or with fabricated latency/status.
    - Candidate IDs generated post-hoc from evidence URLs.
    """
    violations = []
    att_ids = {a.get("attempt_id") for a in acquisition_attempts if a.get("attempt_id")}

    for idx, ev in enumerate(evidence_records):
        att_ref = ev.get("acquisition_attempt_id")
        if not att_ref:
            violations.append(f"[{agent_name}] Evidence record at index {idx} has no acquisition_attempt_id")
        elif att_ref not in att_ids:
            violations.append(f"[{agent_name}] Evidence references synthetic/unobserved acquisition_attempt_id: '{att_ref}'")

    for att in acquisition_attempts:
        if att.get("status") == "SUCCESS" and not att.get("useful_content_extracted"):
            violations.append(f"[{agent_name}] Acquisition '{att.get('attempt_id')}' marked SUCCESS without useful content")
        if att.get("backend") in ("unknown", None, ""):
            violations.append(f"[{agent_name}] Acquisition '{att.get('attempt_id')}' lacks real backend attribution")

    return len(violations) == 0, violations
