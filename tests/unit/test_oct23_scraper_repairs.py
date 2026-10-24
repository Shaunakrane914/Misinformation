"""Offline adversarial controls, not live scraper/accuracy measurements."""
import io
import json
import time
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

from backend.infrastructure.acquisition.adapters.web import firecrawl, jina
from backend.infrastructure.acquisition.network import http
from backend.infrastructure.acquisition.network.budget import (
    PublicRequestBudget, acquisition_deadline, public_request_budget,
)
from backend.services.research.financial_context import (
    extract_financial_metrics_and_scales, financial_passage_context, reconcile_period_and_filing,
)


def _response(markdown=None, metadata=None):
    return http.BoundedHTTPResponse(
        body=json.dumps({"success": True, "data": {
            "markdown": markdown or "Observed source text " * 20, "metadata": metadata or {}}}).encode(),
        endpoint="https://api.firecrawl.dev/v1/scrape", status_code=200,
        content_type="application/json", headers={}, latency_ms=1, attempts=1)


@pytest.fixture
def permitted(monkeypatch):
    # Tests the adapter boundary with an injected transport; never resolves DNS.
    monkeypatch.setattr(firecrawl, "is_safe_url", lambda _url: (True, "safe"))
    monkeypatch.setattr(jina, "is_safe_url", lambda _url: (True, "safe"))


def test_post_reuses_pinned_handlers_budget_and_never_retries(monkeypatch):
    calls, handlers_seen = [], []
    monkeypatch.setattr(http, "is_safe_url", lambda _url: (True, "safe"))

    class Response(io.BytesIO):
        status, url, headers = 200, "https://provider.example/scrape", {}

    def build(*handlers):
        handlers_seen.extend(handlers)
        def open_request(request, timeout):
            calls.append((request, timeout))
            return Response(b'{"ok": true}')
        return SimpleNamespace(open=open_request)

    monkeypatch.setattr(urllib.request, "build_opener", build)
    budget = PublicRequestBudget(total=1)
    with public_request_budget(budget):
        result = http.post_public_http("https://provider.example/scrape", body=b'{}')
        with pytest.raises(TimeoutError):
            http.post_public_http("https://provider.example/scrape", body=b'{}')
    assert result.body == b'{"ok": true}'
    assert len(calls) == 1 and calls[0][0].method == "POST"
    assert calls[0][0].data == b'{}'
    assert any(isinstance(h, http._PublicHTTPSHandler) for h in handlers_seen)
    assert any(isinstance(h, urllib.request.ProxyHandler) and h.proxies == {} for h in handlers_seen)
    assert budget.snapshot()["native_http_admissions"] == 1


@pytest.mark.parametrize("status", [429, 503])
def test_paid_post_http_errors_have_exactly_one_attempt(monkeypatch, status):
    calls = []
    monkeypatch.setattr(http, "is_safe_url", lambda _url: (True, "safe"))
    def open_request(request, **kwargs):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url, status, "unavailable", {}, io.BytesIO())
    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: SimpleNamespace(open=open_request))
    with pytest.raises(http.ProviderHTTPError) as error:
        http.post_public_http("https://provider.example/scrape", body=b'{}')
    assert error.value.status_code == status
    assert len(calls) == 1


def test_paid_post_rejects_redirect_before_any_forward(monkeypatch):
    monkeypatch.setattr(http, "is_safe_url", lambda _url: (True, "safe"))
    request = urllib.request.Request("https://provider.example/scrape", data=b'{}',
                                     headers={"Authorization": "Bearer offline-placeholder"})
    with pytest.raises(http.ProviderHTTPError):
        http._ValidatingRedirectHandler(0).redirect_request(
            request, None, 302, "Found", {}, "https://other.example/collect")


def test_paid_post_rejects_oversize_instead_of_truncating(monkeypatch):
    monkeypatch.setattr(http, "is_safe_url", lambda _url: (True, "safe"))
    class Response(io.BytesIO):
        status, url, headers = 200, "https://provider.example/scrape", {}
    monkeypatch.setattr(urllib.request, "build_opener", lambda *args:
                        SimpleNamespace(open=lambda *a, **k: Response(b'abcdef')))
    with pytest.raises(http.ResponseTooLargeError):
        http.post_public_http("https://provider.example/scrape", body=b'{}', max_bytes=3)


def test_firecrawl_default_post_delegates_to_shared_transport(monkeypatch):
    calls = []
    monkeypatch.setattr(firecrawl, "post_public_http", lambda *a, **k: calls.append((a, k)))
    firecrawl.FirecrawlAdapter._default_post("https://provider.example/scrape", headers={},
                                            body=b'{}', timeout=2, max_bytes=100)
    assert calls[0][1] == {"headers": {}, "body": b'{}', "timeout": 2, "max_bytes": 100}


def test_firecrawl_expired_budget_never_calls_transport(permitted):
    calls = []
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder", http_fetcher=lambda *a, **k: calls.append(a))
    # The deadline is admitted first; expiration occurs within the same chain.
    with acquisition_deadline(time.monotonic() + 1):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("backend.infrastructure.acquisition.network.budget.time.monotonic", lambda: float('inf'))
            result = adapter.scrape_article("https://publisher.example/article")
    assert result["failure_kind"] == "BUDGET_EXHAUSTED" and calls == []


@pytest.mark.parametrize("status", [401, 403, 429])
def test_no_alternate_after_native_denial_or_throttle(permitted, monkeypatch, status):
    fc = SimpleNamespace(is_configured=lambda: True, scrape_article=lambda *a, **k: pytest.fail("alternate called"))
    monkeypatch.setattr(jina, "read_article_via_jina", lambda *a, **k: pytest.fail("alternate called"))
    executor = SimpleNamespace(execute_web_read=lambda _url: {"status": "failed", "transport": {"http_status": status}})
    result = jina.execute_web_read("https://publisher.example/article", executor=executor, firecrawl_adapter=fc)
    assert result["transport"]["http_status"] == status


@pytest.mark.parametrize("status", [403, 429])
def test_no_jina_after_firecrawl_observed_denial(permitted, monkeypatch, status):
    fc = firecrawl.FirecrawlAdapter(api_key="offline-placeholder",
        http_fetcher=lambda *a, **k: _response(metadata={"statusCode": status}))
    monkeypatch.setattr(jina, "read_article_via_jina", lambda *a, **k: pytest.fail("denial bypass"))
    assert jina.execute_web_read("https://publisher.example/article", firecrawl_adapter=fc)["transport"]["http_status"] == status


def test_firecrawl_keeps_raw_text_and_unverified_canonical_metadata(permitted):
    body = "Observed source text with bounded provenance " * 20
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder", http_fetcher=lambda *a, **k:
        _response(body, {"canonicalURL": "http://127.0.0.1/private"}))
    result = adapter.scrape_article("https://publisher.example/article")
    assert result["status"] == "success"
    assert result["canonical_url"] == "https://publisher.example/article"
    assert result["raw_capture"]["text"] == body.strip()


def test_background_firecrawl_job_is_not_admitted(permitted):
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder",
        http_fetcher=lambda *a, **k: pytest.fail("unbounded job submitted"))
    assert adapter.crawl_permitted_domain("https://publisher.example")["failure_kind"] == "UNSUPPORTED_OPERATION"


def test_firecrawl_html_uses_existing_structure_not_markdown_length(permitted):
    paragraph = "The source describes the reported financial amount and preserves its reporting period without independent verification. " * 5
    html = "<nav>Unrelated menu</nav><article><h1>Maple Sensors quarterly report</h1>" + "".join(
        "<p>" + paragraph + "</p>" for _ in range(3)) + "</article>"
    payload = {"success": True, "data": {"markdown": paragraph, "html": html,
                                        "metadata": {"title": "Maple Sensors quarterly report"}}}
    response = http.BoundedHTTPResponse(body=json.dumps(payload).encode(), endpoint="https://api.firecrawl.dev/v1/scrape",
        status_code=200, content_type="application/json", headers={}, latency_ms=1, attempts=1)
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder", http_fetcher=lambda *a, **k: response)
    result = adapter.scrape_article("https://publisher.example/maple-quarterly-report")
    assert result["status"] == "success"
    assert "Unrelated menu" not in result["content"] and "Unrelated menu" in result["raw_capture"]["text"]
    assert result["page_metadata"]["body_quality"]["body_kind"] == "ARTICLE_BODY"
    assert result["page_metadata"]["body_quality"]["evidence_qualified"] is False


def test_blocked_first_wave_leads_do_not_hide_readable_second_wave():
    from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    class Service:
        calls = 0
        def retrieve_many(self, plan, **kwargs):
            self.calls += 1
            hosts = ["blocked-one.example", "blocked-two.example"] if self.calls == 1 else ["readable.example"]
            return RetrievalResult(query="Maple Sensors", domain="financial", fragments=[EvidenceFragment(
                platform="web", url="https://" + host + "/maple-sensors-quarterly-earnings",
                title="Maple Sensors reports quarterly earnings", snippet="Maple Sensors revenue results") for host in hosts])
        def read(self, url, max_chars=12_000):
            if "readable.example" not in url:
                return {"status": "failed", "failure_kind": "ACCESS_DENIED", "transport": {"http_status": 403}}
            return {"status": "success", "content": "Maple Sensors reported quarterly revenue of USD 12 million. " * 20,
                    "page_metadata": {"title": "Maple Sensors quarterly earnings", "content_scope": "article",
                                      "body_quality": {"body_kind": "ARTICLE_BODY"}}}
    service = Service()
    result = HarvestingEngine(service).run("Maple Sensors", "financial", profile=QUICK)
    assert service.calls == 2
    assert result.metrics["article_bodies"] == 1
    assert result.metrics["reads_attempted"] == 3
    assert "USD 12 million" in result.captures[0].content
    assert result.retrieval_trace["staged_query_planning"]["acquired_evidence_coverage_established"] is False


@pytest.mark.parametrize("base", ["http://localhost:3002", "https://user:pass@provider.example", "https://provider.example/?token=secret"])
def test_firecrawl_unsafe_endpoint_configuration_is_unavailable(base):
    assert not firecrawl.FirecrawlAdapter(base_url=base, api_key="").is_configured()


def test_financial_growth_rate_is_not_revenue():
    source = "Revenue increased 27% to USD 59.3 billion."
    rows = extract_financial_metrics_and_scales(source)
    assert len(rows) == 1 and rows[0]["normalized_value"] == 59_300_000_000
    assert rows[0]["currency"] == "USD"
    assert source[rows[0]["start"]:rows[0]["end"]] == rows[0]["amount_text"]


def test_financial_comparison_preserves_baseline_and_ambiguous_currency():
    rows = extract_financial_metrics_and_scales("Revenue fell from $100 million to $90 million.")
    assert [r["normalized_value"] for r in rows] == [100_000_000, 90_000_000]
    assert [r["amount_role"] for r in rows] == ["COMPARATIVE_BASELINE", "REPORTED_AMOUNT"]
    assert {r["currency"] for r in rows} == {"DOLLAR_SYMBOL_UNSPECIFIED"}


@pytest.mark.parametrize("text", ["Revenue increased by 27% in 2026.", "Earnings grew 15 percent.", "Revenue in Q3 2026 improved."])
def test_financial_unlabelled_counts_and_percentages_are_not_money(text):
    assert extract_financial_metrics_and_scales(text) == []


def test_financial_period_metadata_never_verifies_amount_or_issuer():
    passage = "Revenue in Q1 2026 was USD 10 billion."
    metadata = {"form": "10-Q", "report_date": "2026-09-30"}
    assert financial_passage_context(passage, filing_record=metadata)["financial_verification_status"] == "UNVERIFIED_ASSERTION"
    metadata.update(fiscal_period="Q3", fiscal_year=2026)
    assert reconcile_period_and_filing(["Q1 2026"], [], metadata)[1] == "MISMATCH"
    metadata.update(fiscal_period="Q1")
    context = financial_passage_context(passage, filing_record=metadata)
    assert context["filing_comparison_status"] == "RECONCILED"
    assert context["financial_verification_status"] == "UNVERIFIED_ASSERTION"


def test_fiscal_year_is_not_calendar_year_and_two_digit_year_is_ambiguous():
    assert reconcile_period_and_filing(["FY25"], [], {"form": "10-K", "report_date": "2026-06-30"})[1] == "INCONCLUSIVE"
    assert reconcile_period_and_filing(["FY2025"], [], {"form": "10-K", "report_date": "2026-06-30",
        "fiscal_period": "FY", "fiscal_year": 2025})[1] == "RECONCILED"


def test_huginn_not_registered_without_operator_configuration():
    from backend.api import all_routers
    assert not any(getattr(router, "prefix", "") == "/api/events" for router in all_routers)
