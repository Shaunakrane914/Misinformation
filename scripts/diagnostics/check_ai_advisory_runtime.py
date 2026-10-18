"""Explicit account model-list check only; never generates or probes quota.

Requires --allow-live. Ordinary checks and tests must not invoke this command.
A listed model is capability observation, not quota or inference acceptance.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; use a fresh location")
    from dotenv import dotenv_values
    from backend.infrastructure.llm.advisory_policy import MODEL
    from backend.infrastructure.acquisition.network.http import fetch_public_http, decode_bounded_http_body, ProviderHTTPError
    values = dotenv_values(args.env_file)
    keys = [str(v).strip() for k, v in values.items()
            if k.startswith(("GEMINI_API_KEY", "GEMINI_KEY_")) and v and str(v).strip()]
    result = {"scope": "Explicit model-list observation only; no generation or quota probing",
              "generation_requests": 0, "http_status": None, "model": MODEL, "model_listed": False}
    if keys:
        try:
            response = fetch_public_http("https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": keys[0]}, timeout=5, max_bytes=1_000_000,
                max_redirects=0, max_attempts=1)
            result["http_status"] = response.status_code
            models = json.loads(decode_bounded_http_body(response)).get("models", [])
            result["model_listed"] = any(isinstance(m, dict)
                and m.get("name") == "models/" + MODEL
                and "generateContent" in m.get("supportedGenerationMethods", []) for m in models)
        except ProviderHTTPError as error:
            result["http_status"] = error.status_code
        except Exception as error:
            result["error_type"] = type(error).__name__
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    return 0 if result["model_listed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
