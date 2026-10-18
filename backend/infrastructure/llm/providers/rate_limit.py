"""Allowlisted Gemini quota diagnostics; never export provider messages/IDs."""
import math
import re
from collections.abc import Mapping


class GeminiRateLimitError(RuntimeError):
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__("Gemini HTTP 429: " + diagnostics["category"])


def quota_diagnostics(response):
    result = {"http_status": 429, "category": "RATE_OR_QUOTA_LIMIT", "retry_after_seconds": None}
    delays = []
    headers = getattr(response, "headers", {})
    header = headers.get("Retry-After") if isinstance(headers, Mapping) else None
    if isinstance(header, str) and re.fullmatch(r"\d+(?:\.\d+)?", header):
        delays.append(float(header))
    try:
        error = response.json().get("error", {})
        details = error.get("details", []) if isinstance(error, dict) else []
        for detail in details[:10] if isinstance(details, list) else []:
            if not isinstance(detail, dict):
                continue
            if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                delay = detail.get("retryDelay")
                if isinstance(delay, str) and re.fullmatch(r"\d+(?:\.\d+)?s", delay):
                    delays.append(float(delay[:-1]))
            if detail.get("@type") == "type.googleapis.com/google.rpc.QuotaFailure":
                violations = detail.get("violations", [])
                for violation in violations[:10] if isinstance(violations, list) else []:
                    if not isinstance(violation, dict):
                        continue
                    quota_id = violation.get("quotaId", "")
                    if str(violation.get("quotaValue")) == "0":
                        result["category"] = "ZERO_CONFIGURED_QUOTA"
                    elif result["category"] != "ZERO_CONFIGURED_QUOTA" and isinstance(quota_id, str):
                        if "PerDay" in quota_id:
                            result["category"] = "DAILY_QUOTA_EXHAUSTED"
                        elif "PerMinute" in quota_id and result["category"] == "RATE_OR_QUOTA_LIMIT":
                            result["category"] = "PER_MINUTE_LIMIT"
    except Exception:
        pass
    finite = [delay for delay in delays if math.isfinite(delay) and 0 <= delay <= 86400]
    if finite:
        result["retry_after_seconds"] = max(finite)
    return result
