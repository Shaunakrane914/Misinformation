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
