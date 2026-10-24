"""Explicitly authorized, tiny public transport probes; not research acquisition.

At most two GETs, no application retries, redirects, credentials or model calls.
Uses the same SSRF-safe pinned transport as native acquisition. Save observations
in a new file, not tracked proof. A robots response is not article availability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--url", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live or not 1 <= len(args.url) <= 2:
        parser.error("Requires explicit --allow-live and one or two authorized public URLs")
    for value in args.url:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
            parser.error("Use credential-free HTTPS URLs without queries/fragments")
    output = args.output.resolve()
    if output.exists() or any(output.is_relative_to((ROOT / name).resolve()) for name in
            ("artifacts", "research", "backend/data/dossiers", "tests/retrieval_benchmark")):
        parser.error("Output must be a new file outside protected data")
    sys.path.insert(0, str(ROOT))
    from backend.infrastructure.acquisition.network.http import fetch_public_http, ProviderHTTPError, transport_failure_kind
    observations = []
    for url in args.url:
        start = time.monotonic()
        row = {"url": url, "method": "GET", "timeout_seconds": 5, "max_wire_bytes": 65536,
               "max_attempts": 1, "max_redirects": 0}
        try:
            response = fetch_public_http(url, timeout=5.0, max_bytes=65536, max_attempts=1, max_redirects=0)
            row.update(status="RESPONSE_RECEIVED", http_status=response.status_code,
                wire_bytes=len(response.body), wire_sha256=hashlib.sha256(response.body).hexdigest(),
                attempts=response.attempts)
        except ProviderHTTPError as error:
            row.update(status="FAILED", failure_kind=error.failure_kind, http_status=error.status_code,
                network_observed=error.network_observed, attempts=error.attempts)
        except Exception as error:
            row.update(status="FAILED", failure_kind=transport_failure_kind(error), error_type=type(error).__name__)
        row["elapsed_seconds"] = round(time.monotonic() - start, 3)
        observations.append(row)
    result = {"mode": "BOUNDED_LIVE_TRANSPORT_ONLY", "model_calls": 0,
        "full_investigations": 0, "observations": observations,
        "limitations": ["A robots GET is not search health, article access or multi-agent research acceptance.",
            "Successful observations do not establish the cause of an earlier host outage."]}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    return 0 if all(row["status"] == "RESPONSE_RECEIVED" for row in observations) else 1


if __name__ == "__main__":
    raise SystemExit(main())
