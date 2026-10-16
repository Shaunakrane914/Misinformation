"""Minimum citation and uncertainty boundary for specialist model extractions.

Valid IDs are not entailment. Only a separate adjudicator may verify a claim.
"""


def constrain_model_extractions(parsed, evidence_list):
    valid = {e.get("evidence_id") for e in evidence_list if e.get("evidence_id")}
    for key in ("threats", "claims", "narratives", "suspected_impersonations", "suspected_scams", "deepfake_claims"):
        records = parsed.get(key)
        if not isinstance(records, list):
            continue
        retained = []
        for record in records:
            if not isinstance(record, dict):
                continue
            ids = record.get("evidence_ids", [])
            ids = [eid for eid in ids if isinstance(eid, str) and eid in valid] if isinstance(ids, list) else []
            if not ids:
                continue
            record["evidence_ids"] = ids
            record["status"] = "unverified"
            record["citation_entailment_verified"] = False
            retained.append(record)
        parsed[key] = retained
    parsed["model_assertions_verified"] = False
    return parsed


def constrain_financial_extractions(parsed, evidence_list):
    """Retain cited model observations, never promote them to financial verdicts.

    ID validity is a minimum join check, not proof that generated prose follows
    from its passage. Uncited global risk/contradiction claims are not retained.
    """
    valid = {e.get("evidence_id") for e in evidence_list if e.get("evidence_id")}
    catalysts = {}
    for direction in ("positive", "negative", "unresolved"):
        retained = []
        records = (parsed.get("catalysts") or {}).get(direction, [])
        for record in records if isinstance(records, list) else []:
            if not isinstance(record, dict):
                continue
            ids = record.get("evidence_ids")
            if not isinstance(ids, list) or not ids or not all(isinstance(eid, str) and eid in valid for eid in ids):
                continue
            retained.append({**record, "status": "unverified", "citation_entailment_verified": False})
        catalysts[direction] = retained
    safe = constrain_model_extractions({"narratives": parsed.get("narratives", [])}, evidence_list)
    return {
        "catalysts": catalysts, "narratives": safe["narratives"], "risks": [],
        "contradictions": {"for": [], "against": [], "unresolved": []},
        "misinformation": {"status": "UNVERIFIED", "rumors_detected": [],
                           "manipulation_risk": "UNASSESSED", "evidence_quality_score": None,
                           "primary_corroboration": False,
                           "notes": "Model observations are cited but not independently entailment-verified; threat absence is not established."},
        "model_assertions_verified": False,
    }
