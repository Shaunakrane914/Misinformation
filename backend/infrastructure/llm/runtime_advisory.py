"""Explicit runtime admission for strict, small advisory suggestions only.

Generation still passes the existing purpose, investigation, token, timeout,
cooldown and atomic SQLite reservation checks. Capability metadata is never a
generation request or evidence, and unavailable advice leaves native work usable.
"""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import threading
import time

import requests

from backend.infrastructure.llm import advisory_policy as policy


MAX_METADATA_BYTES = 100_000
MODEL_CACHE_SECONDS = 300.0
UNAVAILABLE_CACHE_SECONDS = 30.0
_MODEL_CACHE = {}
_MODEL_CACHE_LOCK = threading.Lock()


def _metadata_support(first_key):
    """One bounded exact-model lookup; no redirects, pagination or key rotation."""
    key = (policy.MODEL, hashlib.sha256(first_key.encode("utf-8")).hexdigest())
    with _MODEL_CACHE_LOCK:
        now = time.monotonic()
        cached = _MODEL_CACHE.get(key)
        if cached is not None and now < cached[0]:
            return {**cached[1], "cached": True}
        result = {"supported": False, "reason": "MODEL_METADATA_UNAVAILABLE", "cached": False}
        response = None
        started = time.monotonic()
        try:
            response = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models/" + policy.MODEL,
                headers={"x-goog-api-key": first_key}, timeout=2.0,
                allow_redirects=False, stream=True,
            )
            status = response.status_code
            result["http_status"] = status
            if status == 200:
                headers = response.headers or {}
                declared = headers.get("Content-Length")
                if declared is not None and (int(declared) < 0 or int(declared) > MAX_METADATA_BYTES):
                    raise ValueError("Metadata response exceeds byte allowance")
                body = bytearray()
                for chunk in response.iter_content(chunk_size=8192):
                    if time.monotonic() - started > 2.0:
                        raise TimeoutError("Metadata response deadline exhausted")
                    if not isinstance(chunk, bytes):
                        raise ValueError("Unexpected metadata response chunk")
                    if len(body) + len(chunk) > MAX_METADATA_BYTES:
                        raise ValueError("Metadata response exceeds byte allowance")
                    body.extend(chunk)
                if time.monotonic() - started > 2.0:
                    raise TimeoutError("Metadata response deadline exhausted")
                metadata = json.loads(bytes(body))
                if (isinstance(metadata, dict) and metadata.get("name") == "models/" + policy.MODEL
                        and isinstance(metadata.get("supportedGenerationMethods"), list)
                        and "generateContent" in metadata["supportedGenerationMethods"]):
                    result.update(supported=True, reason="PROVIDER_DECLARED_SUPPORTED")
                else:
                    result["reason"] = "STRICT_MODEL_NOT_DECLARED_SUPPORTED"
        except Exception as error:
            # Provider messages, URLs and headers may contain credentials.
            result.update(reason="MODEL_METADATA_UNAVAILABLE", error_type=type(error).__name__)
        finally:
            if response is not None:
                response.close()
        ttl = MODEL_CACHE_SECONDS if result["supported"] else UNAVAILABLE_CACHE_SECONDS
        if len(_MODEL_CACHE) >= 16 and key not in _MODEL_CACHE:
            _MODEL_CACHE.clear()
        _MODEL_CACHE[key] = (time.monotonic() + ttl, dict(result))
        return result


@contextmanager
def runtime_advisory_scope(settings=None):
    """Reuse an explicit run, or admit an explicitly enabled UTC-day runtime run.

    The safe summary contains no keys, prompts or provider response bodies.
    The configured runtime allowance per UTC day is shared through the policy DB;
    entering a new request or worker never resets that persisted count.
    """
    existing = policy._run.get()
    if existing is not None:
        yield {"status": "DISABLED" if existing.get("closed") else "REUSED_EXPLICIT_RUN",
               "model": policy.MODEL, "reason": "RUN_CLOSED" if existing.get("closed") else "EXISTING_ADVISORY_SCOPE"}
        return
    summary = {"status": "DISABLED", "model": policy.MODEL, "reason": "RUNTIME_ADVISORY_NOT_ENABLED"}
    if os.getenv("AEGIS_LIVE_ADVISORY_ENABLED", "false").strip().lower() not in {"1", "true", "yes"}:
        yield summary
        return
    scope_stack = ExitStack()
    try:
        if settings is None:
            from backend.core.settings import get_settings
            settings = get_settings()
        if (getattr(settings, "aegis_mock_llm", False) or getattr(settings, "is_mock_llm", False)
                or getattr(settings, "is_test_environment", False)
                or str(getattr(settings, "environment", "")).lower() in {"test", "testing"}):
            summary["reason"] = "MOCK_OR_TEST_ENVIRONMENT"
        elif getattr(settings, "llm_advisory_model", None) != policy.MODEL:
            summary["reason"] = "STRICT_MODEL_REQUIRED"
        elif (str(getattr(settings, "environment", "")).lower() == "production"
                and not os.getenv("AEGIS_AI_POLICY_DB", "").strip()):
            summary["reason"] = "RUNTIME_POLICY_DB_REQUIRED"
        elif os.getenv("AEGIS_AI_POLICY_DB", "").strip() == ":memory:":
            summary["reason"] = "PERSISTENT_POLICY_DB_REQUIRED"
        else:
            keys = getattr(settings, "gemini_api_keys", ()) or ()
            keys = keys if isinstance(keys, (list, tuple)) else ()
            first_key = next((value.strip() for value in keys if isinstance(value, str) and value.strip()), None)
            if not first_key:
                summary["reason"] = "NO_ADVISORY_CREDENTIAL"
            else:
                now = datetime.now(timezone.utc)
                identity = "runtime-utc-" + now.date().isoformat()
                budget = policy.advisory_budget_status(identity=identity)
                if not budget["allowed"]:
                    summary.update(status="BUDGET_BLOCKED", reason=budget["reason"], calls_reserved=budget["calls"])
                else:
                    support = _metadata_support(first_key)
                    summary.update(status="UNAVAILABLE", reason=support["reason"],
                                   capability_cached=support["cached"])
                    if "http_status" in support:
                        summary["capability_http_status"] = support["http_status"]
                    if support["supported"]:
                        state = scope_stack.enter_context(policy.advisory_run(verified_models=(policy.MODEL,), identity=identity))
                        # A scope opened before midnight cannot spend yesterday's
                        # allowance after a new day has started.
                        state["expires_at"] = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                                               + timedelta(days=1)).timestamp()
                        summary.update(status="ENABLED", reason="STRICT_DAILY_RUNTIME_SCOPE",
                                       calls_reserved=budget["calls"], daily_request_cap=budget["daily_request_limit"])
    except Exception as error:
        scope_stack.close()
        summary.update(status="UNAVAILABLE", reason="RUNTIME_ADVISORY_SETUP_FAILED", error_type=type(error).__name__)
    if summary["status"] == "ENABLED":
        with scope_stack:
            yield summary
    else:
        scope_stack.close()
        yield summary
