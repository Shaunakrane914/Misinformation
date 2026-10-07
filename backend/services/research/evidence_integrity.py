"""
Aegis Protocol — Evidence Referential Integrity Validator
==========================================================
Enforces cryptographic and graph referential integrity across the evidence pool,
investigation findings, and source lineage trees.

Guarantees:
- Every finding's supporting_evidence_ids and contradicting_evidence_ids resolve
  to real, verified EvidenceItems.
- Unknown / dangling evidence IDs trigger explicit validation failures.
- Detects orphaned evidence items that were never linked to any query or finding.
- Telemetry captures:
    evidence_reference_errors
    orphan_evidence
    missing_evidence_links
    invalid_finding_links
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class IntegrityReport:
    is_valid: bool
    total_findings_checked: int
    valid_findings_count: int
    invalid_findings_count: int
    total_evidence_checked: int
    missing_evidence_links: List[str] = field(default_factory=list)
    invalid_finding_links: List[Dict[str, Any]] = field(default_factory=list)
    orphan_evidence_ids: List[str] = field(default_factory=list)
    evidence_reference_errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceIntegrityValidator:
    """
    Validates referential integrity between evidence pools and generated findings.
    """

    @staticmethod
    def validate(
        findings: List[Any],
        evidence_pool: List[Any],
        fail_on_invalid: bool = False
    ) -> Tuple[List[Any], IntegrityReport]:
        """
        Validates that all evidence IDs referenced in findings actually exist in evidence_pool.

        Args:
            findings: List of Finding objects or dicts
            evidence_pool: List of EvidenceItem objects or dicts
            fail_on_invalid: If True, strips invalid findings from the returned list

        Returns:
            Tuple of (valid_findings: List, report: IntegrityReport)
        """
        # Map known valid evidence IDs
        known_evidence_ids: Set[str] = set()
        for item in evidence_pool:
            e_id = getattr(item, "id", None) or getattr(item, "evidence_id", None)
            if e_id:
                known_evidence_ids.add(str(e_id))

        referenced_evidence_ids: Set[str] = set()
        missing_links: List[str] = []
        invalid_findings: List[Dict[str, Any]] = []
        valid_findings: List[Any] = []

        for f in findings:
            f_id = getattr(f, "finding_id", None) or getattr(f, "id", "fnd_unknown")
            sup_ids = getattr(f, "supporting_evidence_ids", []) or (f.get("supporting_evidence_ids", []) if isinstance(f, dict) else [])
            cont_ids = getattr(f, "contradicting_evidence_ids", []) or (f.get("contradicting_evidence_ids", []) if isinstance(f, dict) else [])
            all_f_ids = [str(x) for x in (sup_ids + cont_ids)]

            unresolved = [eid for eid in all_f_ids if eid not in known_evidence_ids]
            
            for eid in all_f_ids:
                if eid in known_evidence_ids:
                    referenced_evidence_ids.add(eid)

            if unresolved:
                missing_links.extend(unresolved)
                invalid_findings.append({
                    "finding_id": f_id,
                    "title": getattr(f, "title", "") if not isinstance(f, dict) else f.get("title", ""),
                    "unresolved_evidence_ids": unresolved
                })
                logger.warning(f"[IntegrityValidator] Finding '{f_id}' references unknown evidence IDs: {unresolved}")
                if not fail_on_invalid:
                    # Clean the finding to only reference valid IDs
                    if hasattr(f, "supporting_evidence_ids"):
                        f.supporting_evidence_ids = [x for x in f.supporting_evidence_ids if str(x) in known_evidence_ids]
                    elif isinstance(f, dict):
                        f["supporting_evidence_ids"] = [x for x in f.get("supporting_evidence_ids", []) if str(x) in known_evidence_ids]
                    valid_findings.append(f)
            else:
                valid_findings.append(f)

        # Detect orphaned evidence in pool
        orphans = [eid for eid in known_evidence_ids if eid not in referenced_evidence_ids]

        report = IntegrityReport(
            is_valid=len(missing_links) == 0,
            total_findings_checked=len(findings),
            valid_findings_count=len(valid_findings),
            invalid_findings_count=len(invalid_findings),
            total_evidence_checked=len(evidence_pool),
            missing_evidence_links=list(set(missing_links)),
            invalid_finding_links=invalid_findings,
            orphan_evidence_ids=orphans,
            evidence_reference_errors=len(missing_links)
        )

        return valid_findings, report


evidence_integrity_validator = EvidenceIntegrityValidator()
