"""Opt-in live model-list and minimal structured inference, without secret output.

Does not change credentials/models, scrape sites, deploy, or assert research
accuracy. Output must be a new file. Requires explicit --allow-live.
"""
import argparse
import json
import logging
from pathlib import Path
import re
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
    from backend.core.settings import Settings
    from backend.infrastructure.llm.gateway import DefaultLLMGateway
    from backend.infrastructure.acquisition.network.http import fetch_public_http, decode_bounded_http_body, ProviderHTTPError
    from backend.services.research.evidence_advisor import PassageAdvice, bounded_advice_call
    values = dotenv_values(args.env_file)
    keys = [str(v).strip() for k, v in values.items() if k.startswith(("GEMINI_API_KEY", "GEMINI_KEY_")) and v and str(v).strip()]
    settings = Settings(_env_file=args.env_file, environment="development", aegis_mock_llm=False, gemini_api_keys=keys)
    result = {"scope": "Minimal live configuration diagnostic, not research-quality acceptance",
              "credential_count": len(keys), "model_list_http_status": None, "configured_models_listed": [],
              "inference": "UNAVAILABLE", "inference_http_statuses": [], "synthetic": False}
    class StatusOnly(logging.Handler):
        def emit(self, record):
            for status in re.findall(r"HTTP (\d{3})", record.getMessage()):
                result["inference_http_statuses"].append(int(status))
    logger = logging.getLogger("backend.infrastructure.llm.providers.gemini")
    logger.handlers = [StatusOnly()]
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    if keys:
        try:
            response = fetch_public_http("https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": keys[0]}, timeout=5, max_bytes=1_000_000, max_redirects=0, max_attempts=1)
            result["model_list_http_status"] = response.status_code
            models = json.loads(decode_bounded_http_body(response)).get("models", [])
            available = {str(model.get("name", "")).removeprefix("models/") for model in models
                         if isinstance(model, dict) and "generateContent" in model.get("supportedGenerationMethods", [])}
            result["configured_models_listed"] = [name for name in settings.gemini_models if name in available]
        except ProviderHTTPError as error:
            result["model_list_http_status"] = error.status_code
        except Exception:
            pass
        gateway = DefaultLLMGateway(settings)
        try:
            bounded_advice_call(lambda: gateway.generate_structured('Return exactly JSON: {"selections": []}',
                PassageAdvice, allow_mock=False, timeout=2, total_timeout=2, max_attempts=1,
                max_output_tokens=200, json_mode=True), 2.5)
            result["inference"] = "PASS_STRUCTURED_LIVE"
        except Exception as error:
            result["error_type"] = type(error).__name__
    encoded = json.dumps(result, indent=2)
    for secret in keys:
        encoded = encoded.replace(secret, "[REDACTED]")
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    print(encoded)
    return 0 if result["inference"] == "PASS_STRUCTURED_LIVE" else 2


if __name__ == "__main__":
    sys.exit(main())
