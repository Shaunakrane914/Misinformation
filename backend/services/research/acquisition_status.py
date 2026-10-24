"""Transport outcome is distinct from the epistemic verdict of acquired evidence."""


def acquisition_outcome(records, acquired_count=0, read_attempts=0, read_failure_reason=None,
                        *, raw_capture_count=None, qualified_count=None):
    """Separate transport failure from captured-but-ineligible source content.

    Legacy callers use acquired_count. Acquisition-first callers should also
    supply raw_capture_count and qualified_count, so a filtered evidence list
    cannot erase successful homepage/background/article captures.
    """
    rows = [r.to_dict() if hasattr(r, "to_dict") else r for r in records]
    rows = [r for r in rows if isinstance(r, dict)]
    succeeded = sum(r.get("status") == "SUCCESS" for r in rows)
    counts = {status: sum(r.get("status") == status for r in rows) for status in
              ("SUCCESS", "TIMEOUT", "QUEUE_TIMEOUT", "NOT_SUBMITTED", "SKIPPED", "FAILED", "AUTH_REQUIRED", "RATE_LIMITED")}
    missed_read_window = read_failure_reason == "READING_DEADLINE_EXHAUSTED"
    captured = acquired_count if raw_capture_count is None else raw_capture_count
    qualified = acquired_count if qualified_count is None else qualified_count
    failed = not captured and (not succeeded or read_attempts > 0 or missed_read_window)
    message = ("Unable to retrieve evidence: " + ", ".join(f"{count} {status.lower()}" for status, count in counts.items() if count)
               + ("; selected source reads did not acquire a body" if read_attempts else "")
               + ("; reading deadline exhausted before a source read could start" if missed_read_window and succeeded and not read_attempts else "")
               + ". This does not mean no information exists about the subject.") if failed else ""
    if not failed and captured and not qualified:
        message = (f"Acquisition retained {captured} raw capture(s), but no source qualified as task-relevant evidence. "
                   "Inspect source structure, relevance, dates and passage decisions; this does not establish an absence of information.")
    result = {"status": "ACQUISITION_FAILED" if failed else "COMPLETED" if qualified else "INSUFFICIENT_EVIDENCE",
            "message": message, "query_counts": counts, "acquired_sources": acquired_count,
            "read_attempts": read_attempts}
    if raw_capture_count is not None:
        result["raw_capture_count"] = raw_capture_count
    if qualified_count is not None:
        result["qualified_sources"] = qualified_count
    return result
