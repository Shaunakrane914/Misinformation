"""Synthetic development controls for raw -> readable -> display, not live proof."""
import hashlib

import pytest
from bs4 import BeautifulSoup

from backend.schemas.evidence_inspection import inspect_evidence


def test_article_selection_keeps_raw_navigation_and_financial_context():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    soup = BeautifulSoup("""<html><head><title>Issuer release</title></head><body>
    <nav>Store Careers Search</nav><main><article><header><h1>Quarterly results</h1>
    <p>Published 2026-10-17 by Finance</p></header><nav>Share Subscribe</nav>
    <p>Net income was <strong>not</strong> $900 billion in Q1 2024.</p>
    <table><tr><th>Period</th><th>Net income</th></tr>
    <tr><td>Q1 2024</td><td>$33,916 million</td></tr></table>
    <aside><p>Correction: the prior total was incorrect.</p></aside>
    <a href='/statements.pdf'>Consolidated financial statements</a>
    </article></main><footer>Privacy Careers</footer></body></html>""", "html.parser")
    result = extract_readable_page(soup)
    assert "Store Careers Search" in result["raw_text"]
    assert "Store Careers Search" not in result["text"]
    assert "Share Subscribe" not in result["text"]
    assert "not $900 billion in Q1 2024." in result["text"]
    assert "Q1 2024 $33,916 million" in result["text"]
    assert "Correction: the prior total was incorrect." in result["text"]
    assert "Consolidated financial statements" in result["text"]
    assert result["content_scope"] == "article"
    # Parsing does not destroy the caller's original DOM / observed metadata.
    assert soup.nav is not None and soup.article.header is not None


def test_multiple_articles_do_not_discard_the_rest_of_a_main_document():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    soup = BeautifulSoup("<main><article><p>First observed account.</p></article>"
                         "<article><p>Second conflicting account.</p></article></main>", "html.parser")
    result = extract_readable_page(soup)
    assert "First observed account." in result["text"]
    assert "Second conflicting account." in result["text"]
    assert result["content_scope"] == "main"


def test_plain_body_and_short_legitimate_notice_are_not_discarded():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    result = extract_readable_page(BeautifulSoup("<body><p>Service is unavailable today.</p></body>", "html.parser"))
    assert result["text"] == "Service is unavailable today."
    assert result["content_scope"] == "body_fallback"


@pytest.mark.parametrize("depth", ["PROFILE_METADATA", "VIDEO_METADATA", "INDEX_SNIPPET", "DIRECT_METADATA"])
def test_text_counts_never_upgrade_metadata(depth):
    item = {"content": "Observed public profile. " * 100, "content_depth": depth}
    inspected = inspect_evidence(item)
    assert inspected["evidentiary_use"] == "DISCOVERY_ONLY"
    assert inspected["text_metrics"]["quality_assessment"] == "NOT_ASSESSED"
    assert inspected["text_metrics"]["raw_words"] == 300


def test_raw_capture_and_readable_measurements_are_distinct_unicode_safe():
    raw = "Navigation Data. Original body."
    content = "Original body. नमस्ते"
    inspected = inspect_evidence({"content": content, "raw_metadata": {"raw_capture": {
        "text": raw, "truncated": False, "selection_method": "DOM_MAIN_TEXT",
    }}})
    metrics = inspected["text_metrics"]
    assert metrics["raw_text_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert metrics["readable_utf8_bytes"] == len(content.encode())
    assert metrics["readable_words"] == 3
    assert inspected["captured_text_sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert inspected["passages"][0]["text"] == content


def test_every_executable_operation_has_a_fixed_probe():
    from scripts.audits.run_phase9_extraction_cycle import probe_specs
    from backend.services.agent_reach.native.operation_capabilities import EXECUTABLE_CAPABILITIES
    specs = probe_specs(all_operations=True)
    names = [name for name, _ in specs]
    assert len(names) == len(set(names))
    assert set(names) == {f"{channel}.{action}" for channel, actions in EXECUTABLE_CAPABILITIES.items() for action in actions}


def test_source_fields_are_bounded_allowlisted_not_arbitrary_provider_metadata():
    inspection = inspect_evidence({"content": "Observed answer", "metadata": {
        "question_id": 123, "content_license": "CC BY-SA 4.0", "cookie": "private",
        "authorization": "private", "answer_lookup_status": "x" * 500,
    }})
    fields = inspection["source_observations"]
    assert fields["question_id"] == 123
    assert fields["content_license"] == "CC BY-SA 4.0"
    assert len(fields["answer_lookup_status"]) == 300
    assert "private" not in str(inspection)


def test_native_reader_selects_body_before_limit_and_retains_raw(monkeypatch):
    import socket
    from backend.services.agent_reach.native.executor import NativeExecutor
    from backend.infrastructure.acquisition.adapters.web.jina import execute_web_read
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))])
    html = "<html><body><nav>" + "Shop Career Menu " * 1000 + "</nav><article><p>" + (
        "Actual issuer text says net income was not $900 billion. " * 10
    ) + "</p></article></body></html>"
    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", lambda url, **kw:
        BoundedHTTPResponse(html.encode(), url, 200, "text/html", {}, 1, 1))
    result = execute_web_read("https://example.org/results", max_chars=200, executor=object.__new__(NativeExecutor))
    assert result["content"].startswith("Actual issuer text")
    assert len(result["content"]) == 200 and result["truncated"] is True
    assert "Shop Career Menu" in result["raw_capture"]["text"]
    assert "Shop Career Menu" not in result["content"]
    assert result["page_metadata"]["content_scope"] == "article"


def test_claim_read_preserves_raw_and_page_contract(monkeypatch):
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.research_models import EvidenceItem
    raw = {"text": "Navigation then observed body.", "truncated": False}
    monkeypatch.setattr("backend.services.agent_reach.agent_reach_service.read", lambda *a, **kw: {
        "status": "success", "content": "Observed body with enough context for inspection.",
        "raw_capture": raw, "page_metadata": {"content_scope": "article"}, "truncated": True,
    })
    item = EvidenceItem(id="capture", canonical_url="https://example.org/results")
    items, _ = DeepReader().deep_read([item], max_reads=1, timeout_per_read=2)
    assert items[0].metadata["raw_capture"] == raw
    inspection = inspect_evidence(items[0])
    assert inspection["text_metrics"]["content_scope"] == "article"
    assert inspection["provider_truncated"] is True


@pytest.mark.parametrize("source", ["arxiv", "nist"])
def test_authoritative_transport_does_not_call_injected_fixtures_live(source):
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    if source == "arxiv":
        from backend.infrastructure.acquisition.adapters.authoritative.arxiv_preprints import fetch_arxiv_preprints as fetch
        body = b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
    else:
        from backend.infrastructure.acquisition.adapters.authoritative.nist_nvd import fetch_nist_cve as fetch
        body = b'{"vulnerabilities":[]}'
    result = fetch("example", http_fetcher=lambda *a, **kw:
                   BoundedHTTPResponse(body, "https://example.org/observed", 200, "text/plain", {}, 1, 1))
    transport = result["transport"]
    assert transport["endpoint"] == "https://example.org/observed"
    assert transport["raw_body_sha256"] == hashlib.sha256(body).hexdigest()
    assert transport["http_status"] == 200
    assert transport["network_observed_this_attempt"] is False
