"""Offline transport controls; saved DNS observations are not live recovery proof."""
import socket
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from backend.infrastructure.acquisition.network import http
from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, acquisition_deadline, public_request_budget
from backend.infrastructure.acquisition.security import url_validator as validator
from backend.services.agent_reach.native.operation_capabilities import RuntimeOperationCapabilities
from backend.services.research.deep_reader import DeepReader
from backend.services.research.research_models import EvidenceItem


def addresses(ip="93.184.216.34"):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443))]


def test_saved_dns_11001_observation_is_not_a_private_ip_block(monkeypatch):
    # Genuine 2026-10-21 Apple/BrandShield log reason, sanitized to its host.
    reason = "DNS resolution failed for hostname 'www.helpnetsecurity.com': [Errno 11001] getaddrinfo failed"
    from backend.infrastructure.acquisition.routing import router
    monkeypatch.setattr(router, "is_safe_url", lambda _: (False, reason))
    native = router.NativeRouter()
    native.executor = Mock()
    result = native.execute_channel_read("https://www.helpnetsecurity.com/report")
    assert result["status"] == "failed"
    assert result["failure_kind"] == "DNS_ERROR"
    assert result["rejection_layer"] == "DNS"
    assert not result["transport"]["network_observed_this_attempt"]
    native.executor.execute_web_read.assert_not_called()


@pytest.mark.parametrize("reason,kind", [
    ("DNS resolution failed: DNS validation timed out", "DNS_TIMEOUT"),
    ("DNS resolution failed: DNS validation capacity exhausted", "DNS_CAPACITY"),
    ("DNS resolution failed: Acquisition chain deadline exhausted", "BUDGET_EXHAUSTED"),
    ("Hostname resolved to restricted IP address 127.0.0.1", "SSRF_BLOCKED"),
    ("DNS resolved to a private, reserved, or empty address set", "SSRF_BLOCKED"),
    ("URLs containing embedded user credentials are not permitted", "SSRF_BLOCKED"),
])
def test_validation_categories_preserve_the_deny_result(reason, kind):
    assert validator.validation_failure_kind(reason) == kind


def test_only_os_declared_transient_dns_failure_retries_once(monkeypatch):
    resolver = Mock(side_effect=[socket.gaierror(socket.EAI_AGAIN, "temporary"), addresses()])
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    assert validator.resolve_public_addresses("public.example", 443) == addresses()
    assert resolver.call_count == 2


@pytest.mark.parametrize("code", [socket.EAI_NONAME, 11001])
def test_name_not_found_does_not_retry_or_become_ssrf_violation(monkeypatch, code):
    resolver = Mock(side_effect=socket.gaierror(code, "not found"))
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    with pytest.raises(validator.DNSResolutionError) as exc:
        validator.resolve_public_addresses("missing.example", 443)
    assert exc.value.failure_kind == "DNS_ERROR"
    assert resolver.call_count == 1


def test_transient_retry_never_accepts_mixed_public_private_addresses(monkeypatch):
    resolver = Mock(side_effect=[socket.gaierror(socket.EAI_AGAIN, "temporary"),
                                 addresses() + addresses("127.0.0.1")])
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    with pytest.raises(ValueError, match="private"):
        validator.resolve_public_addresses("rebound.example", 443)
    assert resolver.call_count == 2


def test_dns_failure_cache_expires_without_waiting_a_minute(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(validator.time, "monotonic", lambda: clock[0])
    resolver = Mock(side_effect=[socket.gaierror(11001, "not found"), addresses()])
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    assert not validator.is_safe_url("https://recover.example/a")[0]
    assert not validator.is_safe_url("https://recover.example/b")[0]
    assert resolver.call_count == 1  # burst bounded by brief negative cache
    clock[0] += 1.01
    assert validator.is_safe_url("https://recover.example/c")[0]
    assert resolver.call_count == 2


def test_dns_capacity_failure_never_starts_another_resolver(monkeypatch):
    semaphore = Mock()
    semaphore.acquire.return_value = False
    monkeypatch.setattr(validator, "_DNS_SLOTS", semaphore)
    resolver = Mock()
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    with pytest.raises(validator.DNSResolutionError) as exc:
        validator.resolve_public_addresses("public.example", 443)
    assert exc.value.failure_kind == "DNS_CAPACITY"
    resolver.assert_not_called()


def test_transient_retry_cannot_extend_original_lookup_deadline(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(validator.time, "monotonic", lambda: clock[0])
    def slow_lookup(*_):
        clock[0] += 2.5
        raise socket.gaierror(socket.EAI_AGAIN, "temporary")
    resolver = Mock(side_effect=slow_lookup)
    monkeypatch.setattr(validator, "_resolve_once", resolver)
    with pytest.raises(validator.DNSResolutionError):
        validator.resolve_public_addresses("public.example", 443, timeout=2.5)
    assert resolver.call_count == 1


def test_unsafe_destination_remains_blocked_before_reader(monkeypatch):
    from backend.infrastructure.acquisition.routing import router
    monkeypatch.setattr(router, "is_safe_url", lambda _: (False, "Direct access to private IP is blocked"))
    native = router.NativeRouter()
    native.executor = Mock()
    result = native.execute_channel_read("http://127.0.0.1/data")
    assert result["status"] == "blocked_ssrf"
    assert result["failure_kind"] == "SSRF_BLOCKED"
    assert result["rejection_layer"] == "SSRF"
    native.executor.execute_web_read.assert_not_called()


def test_dns_validation_failure_transmits_no_http_request(monkeypatch):
    monkeypatch.setattr(http, "is_safe_url", lambda _: (False, "DNS resolution failed: [Errno 11001] getaddrinfo failed"))
    opener = Mock()
    monkeypatch.setattr(http.urllib.request, "build_opener", opener)
    with pytest.raises(http.ProviderHTTPError) as exc:
        http.fetch_public_http("https://publisher.example/article")
    assert exc.value.failure_kind == "DNS_ERROR"
    assert exc.value.attempts == 0
    assert not exc.value.network_observed
    opener.assert_not_called()


@pytest.mark.parametrize("cause,kind", [
    (socket.gaierror(11001, "not found"), "DNS_ERROR"),
    (TimeoutError("connection timed out"), "TIMEOUT"),
    (validator.DNSResolutionError("DNS_TIMEOUT", "lookup timed out"), "DNS_TIMEOUT"),
    (ConnectionRefusedError("connection refused"), "CONNECTION_FAILURE"),
])
def test_wrapped_urllib_causes_remain_distinct(cause, kind):
    assert http.transport_failure_kind(urllib.error.URLError(cause)) == kind


@pytest.mark.parametrize("code,kind", [(401, "AUTH_REQUIRED"), (403, "ACCESS_DENIED"), (429, "RATE_LIMITED"), (503, "HTTP_FAILURE")])
def test_http_status_is_distinct_from_dns_and_security(code, kind):
    error = http.ProviderHTTPError("Provider response", endpoint="https://publisher.example", status_code=code)
    assert error.failure_kind == kind


def test_provider_dns_error_is_not_multiplied_by_http_retry(monkeypatch):
    monkeypatch.setattr(http, "is_safe_url", lambda _: (True, ""))
    opener = Mock()
    opener.open.side_effect = urllib.error.URLError(validator.DNSResolutionError("DNS_ERROR", "lookup failed"))
    monkeypatch.setattr(http.urllib.request, "build_opener", lambda *_: opener)
    budget = PublicRequestBudget(total=2, per_host=2)
    with public_request_budget(budget), pytest.raises(http.ProviderHTTPError) as exc:
        http.fetch_public_http("https://publisher.example/article", max_attempts=2)
    assert exc.value.failure_kind == "DNS_ERROR"
    assert opener.open.call_count == 1
    assert budget.snapshot()["native_http_admissions"] == 1


def test_http_retries_share_original_deadline(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(http, "is_safe_url", lambda _: (True, ""))
    opener = Mock()
    def first(*_, **__):
        clock[0] += 4.9
        raise urllib.error.URLError(TimeoutError("connection timed out"))
    opener.open.side_effect = first
    monkeypatch.setattr(http.urllib.request, "build_opener", lambda *_: opener)
    sleep = Mock()
    with pytest.raises(http.ProviderHTTPError) as exc:
        http.fetch_public_http("https://publisher.example/article", timeout=5, sleep=sleep, jitter=lambda *_: 0)
    assert exc.value.failure_kind == "TIMEOUT"
    assert opener.open.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize("kind", ["DNS_ERROR", "DNS_TIMEOUT", "DNS_CAPACITY", "SSRF_BLOCKED", "ACCESS_DENIED", "RATE_LIMITED"])
def test_deep_reader_preserves_failure_categories_and_tries_other_publisher(kind):
    candidates = [EvidenceItem(id="bad", canonical_url="https://bad.example/article", title="Example incident"),
                  EvidenceItem(id="good", canonical_url="https://good.example/article", title="Example incident")]
    def read(url, **_):
        if "bad.example" in url:
            return {"status": "failed", "failure_kind": kind, "error": "sanitized category"}
        return {"status": "success", "markdown": "Example incident is described in this observed publisher passage with adequate source body text."}
    service = SimpleNamespace(read=Mock(side_effect=read))
    records, telemetry = DeepReader().deep_read(candidates, max_reads=2, timeout_per_read=1, service=service)
    assert len(records) == 1 and records[0].id == "good"
    failure = next(row for row in telemetry["acquisition_attempts"] if row["candidate_id"] == "bad")
    assert failure["failure_kind"] == kind
    assert failure["rejection_layer"] == ("DNS" if kind.startswith("DNS_") else None)
    assert service.read.call_count == 2


def test_destination_failure_does_not_defer_all_web_reads():
    capabilities = RuntimeOperationCapabilities()
    capabilities.record_observation("web", "read", {"outcome": "FAILED", "failure_scope": "DESTINATION",
                                                      "failure_kind": "DNS_ERROR", "network_observed": False})
    result = capabilities.assess("web", "read")
    assert result["decision"] == "ELIGIBLE_UNVERIFIED"
    assert result["reason"] == "RECENT_DESTINATION_FAILURE_NOT_CHANNEL_OUTAGE"


@pytest.mark.parametrize("statuses,error", [([429], "Provider HTTP 429"), ([], "Rate limit observed")])
def test_destination_failure_does_not_weaken_rate_limit_cooldown(statuses, error):
    capabilities = RuntimeOperationCapabilities()
    capabilities.record_observation("web", "read", {"outcome": "FAILED", "failure_scope": "DESTINATION",
                                                      "http_statuses": statuses, "error": error})
    assert capabilities.assess("web", "read")["decision"] == "DEFER_TEMPORARY"


def test_channel_wide_transport_failure_still_uses_existing_cooldown():
    capabilities = RuntimeOperationCapabilities()
    capabilities.record_observation("news", "search", {"outcome": "FAILED"})
    assert capabilities.assess("news", "search")["decision"] == "DEFER_TEMPORARY"


@pytest.mark.parametrize("late", [
    {"outcome": "FAILED", "failure_scope": "DESTINATION", "failure_kind": "DNS_ERROR"},
    {"outcome": "DIRECT_CONTENT", "network_observed": True},
    {"outcome": "EMPTY", "network_observed": True},
])
def test_late_inflight_outcome_cannot_erase_or_extend_active_rate_limit(late):
    clock = [10.0]
    capabilities = RuntimeOperationCapabilities(clock=lambda: clock[0])
    capabilities.record_observation("web", "read", {
        "outcome": "FAILED", "http_statuses": [429], "network_observed": True,
        "retry_after_seconds": 60,
    })
    clock[0] = 40.0
    capabilities.record_observation("web", "read", late)
    current = capabilities.assess("web", "read")
    assert current["decision"] == "DEFER_TEMPORARY"
    assert current["last_outcome"] == "RATE_LIMITED"
    assert current["observation_age_seconds"] == 30.0
    clock[0] = 70.01
    assert capabilities.assess("web", "read")["decision"] == "ELIGIBLE_UNVERIFIED"
    capabilities.record_observation("web", "read", {
        "outcome": "FAILED", "failure_scope": "DESTINATION", "failure_kind": "DNS_ERROR",
    })
    assert capabilities.assess("web", "read")["reason"] == "RECENT_DESTINATION_FAILURE_NOT_CHANNEL_OUTAGE"


def test_new_shorter_rate_observation_does_not_shorten_existing_fence():
    clock = [10.0]
    capabilities = RuntimeOperationCapabilities(clock=lambda: clock[0])
    capabilities.record_observation("web", "read", {"http_statuses": [429], "retry_after_seconds": 60})
    clock[0] = 40.0
    capabilities.record_observation("web", "read", {"http_statuses": [429], "retry_after_seconds": 2})
    clock[0] = 45.0
    assert capabilities.assess("web", "read")["decision"] == "DEFER_TEMPORARY"
    clock[0] = 70.01
    assert capabilities.assess("web", "read")["decision"] == "ELIGIBLE_UNVERIFIED"


def test_zero_retry_after_is_not_replaced_with_default_cooldown():
    clock = [10.0]
    capabilities = RuntimeOperationCapabilities(clock=lambda: clock[0])
    capabilities.record_observation("web", "read", {"http_statuses": [429], "retry_after_seconds": 0})
    clock[0] += 0.01
    assert capabilities.assess("web", "read")["decision"] == "ELIGIBLE_UNVERIFIED"


def test_rate_limit_is_scoped_to_operation_not_unrelated_channel():
    capabilities = RuntimeOperationCapabilities()
    capabilities.record_observation("web", "read", {"http_statuses": [429], "retry_after_seconds": 60})
    assert capabilities.assess("web", "read")["decision"] == "DEFER_TEMPORARY"
    assert capabilities.assess("web", "search")["decision"] == "ELIGIBLE_UNVERIFIED"
    assert capabilities.assess("rss", "read")["decision"] == "ELIGIBLE_UNVERIFIED"


def test_tcp_elapsed_time_is_removed_from_tls_socket_allowance(monkeypatch):
    clock = [10.0]
    sock = Mock()
    sock.connect.side_effect = lambda _: clock.__setitem__(0, 14.9)
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(http, "resolve_public_addresses", lambda *_, **__: addresses())
    monkeypatch.setattr(socket, "socket", lambda *_: sock)
    with acquisition_deadline(15.0):
        assert http._connect_public_socket(("publisher.example", 443), timeout=5) is sock
    assert sock.settimeout.call_args_list[0].args[0] == 5.0
    assert sock.settimeout.call_args_list[-1].args[0] == pytest.approx(0.1)


def test_connect_that_exhausts_deadline_never_reaches_tls(monkeypatch):
    clock = [10.0]
    sock = Mock()
    sock.connect.side_effect = lambda _: clock.__setitem__(0, 15.1)
    context = MagicMock()
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(http, "resolve_public_addresses", lambda *_, **__: addresses())
    monkeypatch.setattr(socket, "socket", lambda *_: sock)
    with acquisition_deadline(15.0), pytest.raises(TimeoutError):
        http._PublicHTTPSConnection("publisher.example", timeout=5, context=context).connect()
    context.wrap_socket.assert_not_called()
    sock.close.assert_called_once()


def test_tls_elapsed_time_is_removed_before_header_transmission(monkeypatch):
    clock = [10.0]
    sock = Mock()
    context = MagicMock()
    def handshake(connection, **_):
        clock[0] += 4.8
        return connection
    context.wrap_socket.side_effect = handshake
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(http, "resolve_public_addresses", lambda *_, **__: addresses())
    monkeypatch.setattr(socket, "socket", lambda *_: sock)
    with acquisition_deadline(15.0):
        http._PublicHTTPSConnection("publisher.example", timeout=5, context=context).connect()
    assert sock.settimeout.call_args_list[-1].args[0] == pytest.approx(0.2)


def test_expired_tls_handshake_closes_before_http_headers(monkeypatch):
    clock = [10.0]
    sock = Mock()
    context = MagicMock()
    def handshake(connection, **_):
        clock[0] = 15.1
        return connection
    context.wrap_socket.side_effect = handshake
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(http, "resolve_public_addresses", lambda *_, **__: addresses())
    monkeypatch.setattr(socket, "socket", lambda *_: sock)
    with acquisition_deadline(15.0), pytest.raises(TimeoutError):
        http._PublicHTTPSConnection("publisher.example", timeout=5, context=context).connect()
    sock.close.assert_called_once()
    sock.sendall.assert_not_called()


@pytest.mark.parametrize("cause", [OSError(10055, "OS resources unavailable"), PermissionError(13, "resolver denied")])
def test_getaddrinfo_os_errors_are_dns_failures_not_ssrf_blocks(monkeypatch, cause):
    resolver = Mock(side_effect=cause)
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    safe, reason = validator.is_safe_url("https://publisher.example/article")
    assert not safe
    assert validator.validation_failure_kind(reason) == "DNS_ERROR"
    assert resolver.call_count == 1


def test_received_429_is_preserved_when_original_deadline_is_exhausted(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(http, "is_safe_url", lambda _: (True, ""))
    def rate_limited(*_, **__):
        clock[0] = 15.1
        raise urllib.error.HTTPError("https://publisher.example/article", 429, "Limited", {}, None)
    opener = Mock()
    opener.open.side_effect = rate_limited
    monkeypatch.setattr(http.urllib.request, "build_opener", lambda *_: opener)
    sleep = Mock()
    with pytest.raises(http.ProviderHTTPError) as exc:
        http.fetch_public_http("https://publisher.example/article", timeout=5, sleep=sleep, jitter=lambda *_: 0)
    assert exc.value.status_code == 429
    assert exc.value.failure_kind == "RATE_LIMITED"
    assert exc.value.network_observed
    assert opener.open.call_count == 1
    sleep.assert_not_called()


def test_response_read_uses_shorter_active_acquisition_deadline(monkeypatch):
    monkeypatch.setattr(http.time, "monotonic", lambda: 10.0)
    raw, sock = Mock(), Mock()
    stream = http._DeadlineStream(raw, sock, deadline=15.0)
    with acquisition_deadline(10.25):
        stream.readinto(bytearray(1))
    sock.settimeout.assert_called_once_with(0.25)
