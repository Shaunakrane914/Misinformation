"""Read-only HTTP/admission observations for an explicitly authorized local audit.

Delegates every call unchanged. Admissions are not proof a server received a
request; retries/redirects remain controlled by the original transport.
"""
from contextlib import ExitStack
from contextvars import ContextVar
from datetime import datetime, timezone
import threading
import time
import traceback
from unittest.mock import patch
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import uuid


def public_locator(url):
    parsed = urlsplit(str(url))
    host = parsed.hostname or ""
    if parsed.port:
        host += ":" + str(parsed.port)
    sensitive = {"key", "api_key", "apikey", "token", "access_token", "secret", "signature"}
    query = [(key, "[REDACTED]" if key.lower() in sensitive else value)
             for key, value in parse_qsl(parsed.query, keep_blank_values=True)]
    return urlunsplit((parsed.scheme, host, parsed.path, urlencode(query), ""))


class WebsiteYieldObserver:
    def __init__(self):
        self.http = []
        self.admissions = []
        self.lock = threading.Lock()
        self.current = ContextVar("audit_http_operation", default=None)
        self.stack = ExitStack()
        self.pools = []
        self.pipeline_errors = []

    def __enter__(self):
        from backend.infrastructure.acquisition.network import http, budget
        from backend.services.research.raw_pool import RawAcquisitionPool
        from backend.services.research.research_engine import ResearchEngine
        original_fetch, original_reserve = http._fetch_public_http, budget.PublicRequestBudget.reserve
        original_init = RawAcquisitionPool.__init__
        original_investigate = ResearchEngine.investigate

        def pool_init(instance, *args, **kwargs):
            original_init(instance, *args, **kwargs)
            self.pools.append(instance)

        def investigate(instance, *args, **kwargs):
            try:
                return original_investigate(instance, *args, **kwargs)
            except Exception as error:
                self.pipeline_errors.append({"error_type": type(error).__name__,
                    "frames": [{"file": frame.filename.replace("\\", "/").split("/backend/")[-1],
                                "line": frame.lineno, "function": frame.name}
                               for frame in traceback.extract_tb(error.__traceback__)]})
                raise

        def reserve(instance, url):
            row = {"url": public_locator(url), "host": urlsplit(url).hostname,
                   "http_operation_id": self.current.get(), "phase": budget._request_phase.get(),
                   "admitted": False}
            try:
                result = original_reserve(instance, url)
                row["admitted"] = True
                return result
            finally:
                with self.lock:
                    self.admissions.append(row)

        def fetch(url, **kwargs):
            row = {"operation_id": uuid.uuid4().hex, "requested_url": public_locator(url),
                   "started_at": datetime.now(timezone.utc).isoformat(), "http_status": None,
                   "final_url": None, "outcome": "FAILED", "failure_kind": None}
            token = self.current.set(row["operation_id"])
            started = time.monotonic()
            try:
                result = original_fetch(url, **kwargs)
                row.update(outcome="RECEIVED", final_url=public_locator(result.endpoint),
                           http_status=result.status_code, wire_bytes=len(result.body),
                           transport_attempts=result.attempts,
                           redirect_chain=[public_locator(u) for u in result.redirect_chain])
                return result
            except Exception as error:
                row.update(failure_kind=http.transport_failure_kind(error),
                           http_status=getattr(error, "status_code", None),
                           network_observed=getattr(error, "network_observed", None))
                raise
            finally:
                row["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
                self.current.reset(token)
                with self.lock:
                    self.http.append(row)

        self.stack.enter_context(patch.object(http, "_fetch_public_http", fetch))
        self.stack.enter_context(patch.object(budget.PublicRequestBudget, "reserve", reserve))
        self.stack.enter_context(patch.object(RawAcquisitionPool, "__init__", pool_init))
        self.stack.enter_context(patch.object(ResearchEngine, "investigate", investigate))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def export(self):
        with self.lock:
            return {"scope": "SHARED_BOUNDED_HTTP_AND_NATIVE_ADMISSIONS_NOT_ALL_PROVIDER_QUOTAS",
                    "http_operations": list(self.http), "admissions": list(self.admissions),
                    "native_http_admissions": sum(row["admitted"] for row in self.admissions),
                    "admission_rejections": sum(not row["admitted"] for row in self.admissions),
                    "pipeline_errors": list(self.pipeline_errors)}

    def captured_pools(self):
        """Temporary native captures survive a later pipeline exception."""
        return [pool.export(include_text=True) for pool in self.pools]
