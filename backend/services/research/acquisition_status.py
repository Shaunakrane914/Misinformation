"""Transport outcome is distinct from the epistemic verdict of acquired evidence."""


def acquisition_outcome(records, acquired_count=0, read_attempts=0):
    rows = [r.to_dict() if hasattr(r, "to_dict") else r for r in records]
    rows = [r for r in rows if isinstance(r, dict)]
    succeeded = sum(r.get("status") == "SUCCESS" for r in rows)
    counts = {status: sum(r.get("status") == status for r in rows) for status in
              ("SUCCESS", "TIMEOUT", "QUEUE_TIMEOUT", "NOT_SUBMITTED", "SKIPPED", "FAILED", "AUTH_REQUIRED", "RATE_LIMITED")}
    failed = not acquired_count and (not succeeded or read_attempts > 0)
    message = ("Unable to retrieve evidence: " + ", ".join(f"{count} {status.lower()}" for status, count in counts.items() if count)
               + ("; selected source reads did not acquire a body" if read_attempts else "")
               + ". This does not mean no information exists about the subject.") if failed else ""
    return {"status": "ACQUISITION_FAILED" if failed else "COMPLETED" if acquired_count else "INSUFFICIENT_EVIDENCE",
            "message": message, "query_counts": counts, "acquired_sources": acquired_count,
            "read_attempts": read_attempts}
