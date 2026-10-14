"""Compatibility Scout paths must preserve the canonical bounded HTTP boundary."""

from backend.agents.scout.sources.adapters.primary_adapter import PrimaryFilingAdapter
from backend.agents.scout.sources.models import CandidateSource
from backend.agents.scout.sources.transport import ScoutTransport
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse


def test_primary_lead_hint_cannot_authenticate_attacker_domain():
    candidate = CandidateSource(url="https://sec.gov.attacker.example/filing.htm",
                                canonical_url="https://sec.gov.attacker.example/filing.htm",
                                platform="primary_filing", source_type="filing", external_id="fake",
                                metadata={"is_primary_lead": True})
    assert not PrimaryFilingAdapter().can_handle(candidate)


def test_legacy_transport_uses_bounded_shared_fetch(monkeypatch):
    observed = {}
    def fetch(url, **kwargs):
        observed.update(kwargs)
        return BoundedHTTPResponse(body=b"Source text", endpoint="https://other.example/final",
                                   status_code=200, content_type="text/plain", headers={},
                                   latency_ms=1, attempts=1)
    monkeypatch.setattr("backend.infrastructure.acquisition.network.http.fetch_public_http", fetch)
    transport = ScoutTransport()
    monkeypatch.setattr(transport.rate_limiter, "wait_for_domain", lambda domain: None)
    status, text, headers, _, error = transport.get("https://source.example/start", timeout=20, max_retries=20)
    assert status == 200 and error is None
    assert text == "Source text"
    assert observed["timeout"] == 5
    assert observed["max_bytes"] == 1_000_000
    assert observed["max_attempts"] == 3
    assert headers["X-Aegis-Observed-Endpoint"] == "https://other.example/final"
