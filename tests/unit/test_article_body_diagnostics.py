"""Offline structural and real reader-boundary controls, never publisher proof."""
from types import SimpleNamespace
from unittest.mock import Mock

from bs4 import BeautifulSoup
import pytest

from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
from backend.infrastructure.acquisition.adapters.web.response_diagnostics import diagnose_response, safe_diagnostics
from backend.infrastructure.acquisition.adapters.web import jina
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError
from backend.services.agent_reach.native import executor as native
from backend.services.research.deep_reader import DeepReader
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem


URL = 'https://example.com/story'


@pytest.mark.parametrize('url,html,expected', [
    (URL, '<div id="root"></div><script src="app.js"></script>', 'JAVASCRIPT_SHELL'),
    ('https://example.com/', '<body><h1>News</h1><p>Welcome to the site.</p></body>', 'HOMEPAGE'),
    ('https://example.com/search?q=test', '<p>Search results</p>', 'SEARCH_OR_INDEX'),
    (URL, '<h1>Verify you are human</h1>', 'CHALLENGE_OR_RESTRICTED'),
    (URL, '<form><input type="password"></form>', 'CHALLENGE_OR_RESTRICTED'),
    (URL, '<h1>Page not found</h1>', 'INCORRECT_URL'),
    (URL, '', 'EMPTY_DOCUMENT'),
    (URL, '<div><p>Short text without article structure.</p></div>', 'UNCLASSIFIED_PAGE'),
])
def test_http_200_is_not_equivalent_to_article_acquisition(url, html, expected):
    soup = BeautifulSoup(html, 'html.parser')
    result = diagnose_response(html.encode(), url, 'text/html', soup=soup, extracted=extract_readable_page(soup))
    assert result['http_status'] == 200 and result['classification'] == expected
    assert result['evidence_qualified'] is False
    assert all(key not in result for key in ['text', 'html', 'headers', 'url', 'cookies'])


def test_substantive_article_structure_is_observation_not_relevance():
    text = 'Unrelated subject reported an announcement with detailed facts and context for readers. '
    html = '<article><h1>Unrelated subject</h1><p>' + text * 3 + '</p><p>' + text * 3 + '</p></article>'
    soup = BeautifulSoup(html, 'html.parser')
    result = diagnose_response(html.encode(), URL, 'text/html', soup=soup, extracted=extract_readable_page(soup))
    assert result['classification'] == 'ARTICLE_BODY'
    assert result['evidence_qualified'] is False


def test_diagnostic_projection_drops_text_headers_private_fields_and_unbounded_values():
    assert safe_diagnostics({'classification': ['ARTICLE_BODY']}) == {}
    clean = safe_diagnostics({'classification': 'JAVASCRIPT_SHELL', 'readable_words': -1,
        'decoded_bytes': 9_000_000, 'response_sha256': 'secret', 'http_status': '200',
        'headers': {'Cookie': 'secret'}, 'text': 'private contact data', 'script': 'token'})
    assert set(clean) == {'classification', 'basis', 'evidence_qualified', 'sample_policy'}


def test_missing_body_diagnostic_survives_real_native_outer_reader_and_failed_pool(monkeypatch):
    monkeypatch.setattr(native, 'is_safe_url', lambda _: (True, 'OFFLINE'))
    monkeypatch.setattr(jina, 'is_safe_url', lambda _: (True, 'OFFLINE'))
    html = b'<div id="root"></div><script src="app.js"></script>'
    fetch = Mock(side_effect=[BoundedHTTPResponse(html, URL, 200, 'text/html', {}, 1, 1),
        ProviderHTTPError('Private response text', endpoint='https://r.jina.ai/' + URL, failure_kind='TIMEOUT')])
    monkeypatch.setattr(native, 'fetch_public_http', fetch)
    result = jina.execute_web_read(URL, executor=object.__new__(native.NativeExecutor),
        firecrawl_adapter=SimpleNamespace(is_configured=lambda: False))
    assert result['native_response_diagnostics']['classification'] == 'JAVASCRIPT_SHELL'
    item = EvidenceItem(id='failure', canonical_url=URL, title='Example statement', channel='web',
                        metadata={'candidate_score': .8})
    captures, trace = DeepReader().deep_read([item], max_reads=1, timeout_per_read=1,
        service=SimpleNamespace(read=lambda *a, **k: result))
    assert not captures and fetch.call_count == 2
    attempt = trace['acquisition_attempts'][0]
    diagnostic = attempt['native_response_diagnostics']
    pool = RawAcquisitionPool('diagnostic-control')
    pool.add_failure(item, attempt['failure_kind'], response_diagnostics=diagnostic)
    record = pool.export()['sources'][0]
    assert record['errors'][0]['native_response_diagnostics'] == diagnostic
    assert record['source_type'] == 'BLOCKED_OR_FAILED'
    assert 'Private response' not in str(record)
