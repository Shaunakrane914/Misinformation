"""Targeted synthetic capture controls; no live scraping or publisher approval."""
import codecs
import gzip
import hashlib
from datetime import datetime, timezone

import pytest

from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.infrastructure.acquisition.network.http import ResponseTooLargeError
from backend.services.agent_reach.native import executor as native
from backend.services.research.source_registry import SourceRegistry


URL = 'https://globalvoices.org/2026/10/26/synthetic-observed-article/'
LICENCE = 'https://creativecommons.org/licenses/by/3.0/'
PARAGRAPH = ('The research team published the complete statement on Monday and '
             'described its observations with attribution and limitations. ')


def article(*, footer=''):
    return ('<!doctype html><html lang="hi-IN"><head><title>Synthetic observed article</title>'
            '<meta name="author" content="Synthetic Reporter"></head><body><article>'
            '<h1>Synthetic observed article</h1><p>' + PARAGRAPH + '</p><p>' + PARAGRAPH + '</p>'
            '</article><footer><a rel="license" href="' + LICENCE + '">Licence</a>'
            + footer + '</footer></body></html>')


def read(monkeypatch, content, content_type='text/html; charset=UTF-8'):
    response = BoundedHTTPResponse(body=content, endpoint=URL, status_code=200,
        content_type=content_type, headers={'Content-Type': content_type}, latency_ms=2, attempts=1)
    calls = []
    monkeypatch.setattr(native, 'is_safe_url', lambda url: (True, ''))
    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return response
    monkeypatch.setattr(native, 'fetch_public_http', fetch)
    result = object.__new__(native.NativeExecutor).execute_web_read(URL)
    assert len(calls) == 1 and calls[0][0] == URL
    assert calls[0][1]['max_bytes'] == 1_000_000
    assert calls[0][1]['timeout'] == 5.0
    return result


@pytest.mark.parametrize('encoding,label,text', [
    ('utf-8', 'UTF-8', 'café — exact statement'),
    ('utf-8-sig', 'utf-8-sig', 'café — exact statement'),
    ('cp1252', 'windows-1252', 'café — exact statement'),
    ('latin-1', 'ISO-8859-1', 'café année exact statement'),
])
def test_observed_charset_preserves_native_text_without_fallback(monkeypatch, encoding, label, text):
    html = article().replace(PARAGRAPH, PARAGRAPH + text)
    result = read(monkeypatch, html.encode(encoding), 'text/html; charset="' + label + '"')
    assert result['status'] == 'SUCCESS' and result['backend'] == 'native_http_reader'
    assert text in result['content'] and '\ufffd' not in result['content']


def test_native_reader_preserves_captured_permission_and_language_observations(monkeypatch):
    result = read(monkeypatch, article().encode('utf-8'))
    page = result['page_metadata']
    assert page['author'] == 'Synthetic Reporter'
    assert page['language'] == 'hi-IN' and page['language_basis'] == 'CAPTURED_HTML_LANG'
    assert page['licence_urls'] == [LICENCE]
    assert page['readable_text_sha256'] == hashlib.sha256(result['content'].encode('utf-8')).hexdigest()
    registry = SourceRegistry(clock=lambda: datetime(2026, 10, 26, tzinfo=timezone.utc))
    assert registry.excerpt_decision(URL, page)['eligible']
    assert not registry.excerpt_decision(URL, dict(page, licence_urls=[]))['eligible']


@pytest.mark.parametrize('footer,blocked', [('All rights reserved', False), ('Third-party content: All rights reserved', True)])
def test_native_reader_preserves_notice_scope_and_explicit_exception(monkeypatch, footer, blocked):
    result = read(monkeypatch, article(footer=footer).encode('utf-8'))
    assert 'All rights reserved' not in result['content']
    assert 'All rights reserved' in result['raw_capture']['text']
    page = result['page_metadata']
    assert page['rights_notice_observed'] is True
    assert bool(page.get('rights_exception_observed')) is blocked
    registry = SourceRegistry(clock=lambda: datetime(2026, 10, 26, tzinfo=timezone.utc))
    decision = registry.excerpt_decision(URL, page)
    assert decision['eligible'] is not blocked
    if blocked:
        assert decision['reason'] == 'ARTICLE_RIGHTS_EXCEPTION_REVIEW_REQUIRED'


@pytest.mark.parametrize('body,content_type', [
    (b'caf\xe9', 'text/html'),
    (b'caf\xe9', 'text/html; charset=UTF-8'),
    (b'caf\x81', 'text/html; charset=windows-1252'),
    (b'header\x00binary', 'text/html; charset=ISO-8859-1'),
    (b'header\x85control', 'text/html; charset=ISO-8859-1'),
    ('text'.encode('utf-16'), 'text/html; charset=utf-16'),
    (b'text', 'text/html; charset=unknown-codec'),
])
def test_invalid_or_undeclared_non_utf8_and_binary_never_become_replacement_prose(body, content_type):
    with pytest.raises((ValueError, UnicodeError)):
        native._decode_web_text(body, content_type)


def test_utf8_bom_without_charset_is_handled_as_observed_utf8_signature():
    assert native._decode_web_text(codecs.BOM_UTF8 + 'exact café'.encode('utf-8'), 'text/plain') == 'exact café'


def test_compressed_html_above_old_decoded_limit_uses_normal_bounded_native_path(monkeypatch):
    html = article().replace('</head>', '<style>' + ' ' * 1_000_000 + '</style></head>').encode('utf-8')
    wire = gzip.compress(html)
    assert len(wire) < native.MAX_OUTPUT_BYTES < len(html) < native.MAX_HTML_DECODED_BYTES
    response = BoundedHTTPResponse(body=wire, endpoint=URL, status_code=200,
        content_type='text/html; charset=UTF-8', headers={'Content-Encoding': 'gzip'}, latency_ms=2, attempts=1)
    calls = []
    monkeypatch.setattr(native, 'is_safe_url', lambda url: (True, ''))
    def fetch(url, **kwargs):
        calls.append(kwargs)
        return response
    monkeypatch.setattr(native, 'fetch_public_http', fetch)
    result = object.__new__(native.NativeExecutor).execute_web_read(URL)
    assert result['status'] == 'SUCCESS' and PARAGRAPH.strip() in result['content']
    assert calls == [{'headers': {'User-Agent': native._USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate'}, 'timeout': 5.0, 'max_bytes': 1_000_000}]
    assert result['transport']['raw_body_bytes'] == len(wire)
    assert result['transport']['decoded_body_bytes'] == len(html)


def test_expanded_html_limit_never_expands_wire_or_non_html_limits(monkeypatch):
    monkeypatch.setattr(native, 'is_safe_url', lambda url: (True, ''))
    # One test covers the three distinct boundaries without any provider call.
    cases = [(b'x' * 1_000_001, 'text/html'),
             (gzip.compress(b'x' * 1_000_001), 'application/json'),
             (gzip.compress(b'x' * 4_000_001), 'application/xhtml+xml')]
    for wire, kind in cases:
        response = BoundedHTTPResponse(body=wire, endpoint=URL, status_code=200,
            content_type=kind, headers={'Content-Encoding': 'gzip'}, latency_ms=2, attempts=1)
        monkeypatch.setattr(native, 'fetch_public_http', lambda *args, **kwargs: response)
        with pytest.raises(ResponseTooLargeError):
            object.__new__(native.NativeExecutor).execute_web_read(URL)
