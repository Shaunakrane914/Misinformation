"""Behavioral regressions for source trust, DNS pinning, and immutable dossiers."""

import io
import socket
from unittest.mock import MagicMock
import urllib.request

import pytest

from backend.infrastructure.acquisition.network import http
from backend.infrastructure.acquisition.security import url_validator
from backend.services.research.replay_ledger import ReplayLedger, verify_dossier_integrity
from backend.services.research.research_models import EvidenceItem
from backend.services.research.source_quality import SourceQualityEngine
from backend.application.research.synthesis import synthesize_grounded_findings


@pytest.mark.parametrize("url", [
    "https://sec.gov.attacker.example/filing", "https://notsec.gov/filing",
    "https://reuters.com.attacker.example/news", "https://github.com.attacker.example/repo",
    "https://tesla-scam.example/press-release", "https://tesla.com.attacker.example/press-release",
    "https://sec.gov:invalid/filing", "https://sec.gov:99999/filing",
])
def test_impostor_domains_never_become_official_or_primary(url):
    item = EvidenceItem(id="spoof", canonical_url=url, source_domain="sec.gov",
                        primary_source=True, official_source=True, title="Official filing")
    SourceQualityEngine().classify_and_score(item, "Tesla")
    assert not item.primary_source
    assert not item.official_source
    assert item.source_quality_score < 0.8


@pytest.mark.parametrize("url", ["https://www.sec.gov/filing", "https://ir.tesla.com/press-release"])
def test_real_authority_subdomains_remain_supported(url):
    item = EvidenceItem(id="real", canonical_url=url)
    SourceQualityEngine().classify_and_score(item, "Tesla")
    assert item.primary_source and item.official_source


def test_unknown_company_name_is_not_a_verified_domain():
    item = EvidenceItem(id="unknown", canonical_url="https://acme.com/press-release")
    SourceQualityEngine().classify_and_score(item, "Acme")
    assert not item.official_source
    verified = SourceQualityEngine(official_domains={"Acme": {"acme.com"}})
    verified.classify_and_score(item, "Acme")
    assert item.official_source


def test_original_github_document_is_not_automatically_a_known_fact():
    item = EvidenceItem(id="repo", canonical_url="https://github.com/attacker/false-claim",
                        title="False corporate claim", snippet="Tesla is bankrupt.",
                        independence_group="repo", source_name="Unverified repository")
    SourceQualityEngine().classify_and_score(item, "Tesla")
    assert item.primary_source and not item.official_source
    assert synthesize_grounded_findings("Tesla", "general", [item], []) == []


def test_unrelated_secondary_results_do_not_become_fact_from_group_count():
    items = [EvidenceItem(id=str(index), title=text, snippet=text,
                          source_role="SECONDARY", source_quality_score=0.9,
                          independence_group=str(index))
             for index, text in enumerate(["Tesla revenue rose.", "Tesla changed its battery design."])]
    assert synthesize_grounded_findings("Tesla", "general", items, []) == []


def _address(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443))]


def test_connection_revalidates_after_cached_public_dns_answer(monkeypatch):
    url_validator.clear_dns_cache()
    resolver = MagicMock(side_effect=[_address("93.184.216.34"), _address("127.0.0.1")])
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    assert url_validator.is_safe_url("https://rebind.example/data")[0]
    with pytest.raises(http.ProviderHTTPError, match="SSRF"):
        http._connect_public_socket(("rebind.example", 443), timeout=1)
    assert resolver.call_count == 2
    url_validator.clear_dns_cache()


def test_pinned_https_keeps_original_sni_and_does_not_reresolve(monkeypatch):
    resolver = MagicMock(return_value=_address("93.184.216.34"))
    context, connection_socket = MagicMock(), MagicMock()
    with monkeypatch.context() as patch:
        patch.setattr(socket, "getaddrinfo", resolver)
        patch.setattr(socket, "socket", MagicMock(return_value=connection_socket))
        connection = http._PublicHTTPSConnection("api.example.com", timeout=1, context=context)
        connection.connect()
    connection_socket.connect.assert_called_once_with(("93.184.216.34", 443))
    context.wrap_socket.assert_called_once_with(connection_socket, server_hostname="api.example.com")
    assert resolver.call_count == 1


def test_public_connection_default_timeout_is_supported():
    assert callable(http._PublicHTTPConnection("example.com").response_class)
    assert callable(http._PublicHTTPSConnection("example.com").response_class)


@pytest.mark.parametrize("target", ["http://api.example.com/result", "https://api.example.com:80/result"])
def test_scheme_or_port_redirect_strips_credentials(monkeypatch, target):
    monkeypatch.setattr(http, "is_safe_url", lambda _: (True, ""))
    request = urllib.request.Request("https://api.example.com/start",
                                    headers={"Authorization": "Bearer test", "Cookie": "session=test"})
    redirected = http._ValidatingRedirectHandler(4).redirect_request(request, None, 302, "Found", {}, target)
    assert redirected.get_header("Authorization") is None
    assert redirected.get_header("Cookie") is None


@pytest.mark.parametrize("value", ["inf", "nan", "-inf"])
def test_nonfinite_retry_after_is_rejected(value):
    assert http.parse_retry_after(value) is None


@pytest.mark.parametrize("value", ["http://example.com:invalid", "http://example.com:99999"])
def test_malformed_ports_fail_closed(value):
    assert not url_validator.is_safe_url(value)[0]


def test_explicit_custom_port_validation_remains_supported(monkeypatch):
    url_validator.clear_dns_cache()
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port)),
    ])
    assert not url_validator.is_safe_url("https://custom.example:8443")[0]
    assert url_validator.is_safe_url("https://custom.example:8443", allow_custom_ports=True)[0]
    url_validator.clear_dns_cache()


@pytest.mark.parametrize("slow_headers", [False, True])
def test_slow_trickle_headers_and_body_obey_wall_clock_deadline(monkeypatch, slow_headers):
    clock = [0.0]
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    headers = b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n"

    class DripStream(io.RawIOBase):
        def readable(self):
            return True

        def readinto(self, buffer):
            chunk = chunks.pop(0) if chunks else b""
            buffer[:len(chunk)] = chunk
            clock[0] += 0.4
            return len(chunk)

    chunks = [bytes([byte]) for byte in headers] if slow_headers else [headers]
    chunks.extend([b"x"] * 10)
    connection = MagicMock()
    connection.makefile.return_value = DripStream()
    response = http.http.client.HTTPResponse(http._ResponseSocket(connection, 1.0))
    try:
        with pytest.raises(TimeoutError, match="deadline"):
            response.begin()
            response.read(100)
        assert connection.settimeout.call_count == 3
        assert clock[0] < 1.3
    finally:
        response.close()


def _record(ledger, target="original"):
    return ledger.record_investigation(target=target, domain="review", summary=target,
                                      candidates=[{"id": "ev", "snippet": "captured source text"}],
                                      findings=[], queries=[], telemetry={}, lineage_graph={})


def test_new_dossier_id_and_snapshot_integrity(tmp_path):
    ledger = ReplayLedger(str(tmp_path))
    session_id = _record(ledger)
    assert len(session_id.split("-")[-1]) == 32
    reloaded = ReplayLedger(str(tmp_path)).get_dossier(session_id)
    assert verify_dossier_integrity(reloaded)["valid"]
    assert ledger.replay_investigation(session_id)["integrity_status"] == "TRACE_VERIFIED"
    returned = ledger.get_dossier(session_id)
    returned["target"] = "caller mutation"
    assert ledger.get_dossier(session_id)["target"] == "original"


def test_colliding_id_never_overwrites_existing_file(tmp_path, monkeypatch):
    ledger = ReplayLedger(str(tmp_path))
    monkeypatch.setattr(ledger, "_generate_dossier_id", lambda _: "R-2026-COLLISION")
    original_id = _record(ledger)
    original_bytes = (tmp_path / f"{original_id}.json").read_bytes()
    with pytest.raises(FileExistsError):
        _record(ledger, "replacement")
    assert (tmp_path / f"{original_id}.json").read_bytes() == original_bytes
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("session_id", ["..\\secret", "../secret", "C:\\secret", "R-2026-X/../../secret"])
def test_dossier_path_traversal_is_rejected(tmp_path, session_id):
    ledger = ReplayLedger(str(tmp_path))
    ledger._memory_cache[session_id] = {"target": "unsafe cached entry"}
    assert ledger.get_dossier(session_id) is None


def test_unsealed_or_tampered_trace_never_claims_verified(tmp_path):
    ledger = ReplayLedger(str(tmp_path))
    ledger._memory_cache["R-2026-LEGACY"] = {
        "session_id": "R-2026-LEGACY", "candidate_hashes": {"ev": "not-a-hash"},
        "queries_executed": [], "decision_log": [], "findings_provenance": [],
    }
    old_result = ledger.replay_investigation("R-2026-LEGACY")
    assert old_result["integrity_status"] == "FAILED"
    assert old_result["candidates_integrity_verified"] == 0
    session_id = _record(ledger)
    data = ledger.get_dossier(session_id)
    data["summary"] = "tampered statement"
    ledger._memory_cache[session_id] = data
    result = ledger.replay_investigation(session_id)
    assert result["integrity_status"] == "FAILED"
    assert result["candidates_integrity_verified"] == 0


def test_partial_write_failure_never_returns_a_persisted_id(tmp_path, monkeypatch):
    ledger = ReplayLedger(str(tmp_path))
    monkeypatch.setattr("backend.services.research.replay_ledger.os.link",
                        MagicMock(side_effect=OSError("storage unavailable")))
    with pytest.raises(OSError):
        _record(ledger)
    assert not ledger._memory_cache
    assert not list(tmp_path.glob("*.json"))
    assert not list(tmp_path.glob("*.tmp"))
