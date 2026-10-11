"""Security and reliability contracts for the shared acquisition transport."""

import io
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import Message

import pytest

from backend.infrastructure.acquisition.network.http import (
    ProviderHTTPError,
    ResponseTooLargeError,
    _ValidatingRedirectHandler,
    fetch_public_http,
    parse_retry_after,
)


class _Response:
    def __init__(self, body=b"ok", *, url="https://example.com/final", status=200, headers=None):
        self._body = io.BytesIO(body)
        self.url = url
        self.status = status
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def read(self, size=-1):
        return self._body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Opener:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = 0

    def open(self, _request, timeout):
        assert timeout > 0
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _http_error(status, *, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError(
        "https://example.com/data", status, "failure", headers, None
    )


def test_retry_after_parses_seconds_and_http_date():
    assert parse_retry_after("3") == 3.0
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert parse_retry_after("Thu, 01 Jan 2026 00:00:05 GMT", now=now) == 5.0
    assert parse_retry_after("invalid") is None


def test_unsafe_redirect_is_rejected_before_followup_request(monkeypatch):
    handler = _ValidatingRedirectHandler(max_redirects=3)
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.network.http.is_safe_url",
        lambda url: (False, "private address") if "169.254.169.254" in url else (True, ""),
    )
    request = urllib.request.Request("https://example.com/start")
    with pytest.raises(ProviderHTTPError, match="Redirect blocked"):
        handler.redirect_request(
            request, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data"
        )


def test_cross_origin_redirect_strips_authorization(monkeypatch):
    handler = _ValidatingRedirectHandler(max_redirects=3)
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.network.http.is_safe_url", lambda _url: (True, "")
    )
    request = urllib.request.Request(
        "https://api.example.com/start", headers={"Authorization": "Bearer secret"}
    )
    redirected = handler.redirect_request(
        request, None, 302, "Found", {}, "https://cdn.example.net/result"
    )
    assert redirected.get_header("Authorization") is None


def test_oversized_response_is_rejected(monkeypatch):
    opener = _Opener([_Response(b"x" * 11)])
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.network.http.is_safe_url", lambda _url: (True, "")
    )
    with pytest.raises(ResponseTooLargeError):
        fetch_public_http("https://example.com/data", max_bytes=10, max_attempts=1)


def test_retryable_failure_retries_once_with_bounded_delay(monkeypatch):
    opener = _Opener([_http_error(503), _Response(b"recovered")])
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.network.http.is_safe_url", lambda _url: (True, "")
    )
    sleeps = []
    result = fetch_public_http(
        "https://example.com/data", max_attempts=2,
        sleep=sleeps.append, jitter=lambda _a, _b: 0.0,
    )
    assert result.body == b"recovered"
    assert result.attempts == 2
    assert sleeps == [0.2]


def test_long_retry_after_is_exposed_without_blocking_worker(monkeypatch):
    opener = _Opener([_http_error(429, retry_after=60)])
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.network.http.is_safe_url", lambda _url: (True, "")
    )
    with pytest.raises(ProviderHTTPError) as exc_info:
        fetch_public_http("https://example.com/data", max_attempts=2)
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_seconds == 60.0
    assert opener.calls == 1


@pytest.mark.parametrize("status", [401, 403])
def test_auth_and_policy_failures_are_never_retried(monkeypatch, status):
    opener = _Opener([_http_error(status)])
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.network.http.is_safe_url", lambda _url: (True, "")
    )
    with pytest.raises(ProviderHTTPError) as exc_info:
        fetch_public_http("https://example.com/data", max_attempts=3)
    assert exc_info.value.status_code == status
    assert opener.calls == 1
