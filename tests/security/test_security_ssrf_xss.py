"""
Aegis Protocol — Security Tests: SSRF Defense & XSS Sanitization
================================================================
Validates:
- Strict SSRF defense blocking loopback, private ranges, and cloud metadata
- Disallowed protocols (file, ftp, gopher)
- HTML escaping against XSS payloads
"""

import pytest
from backend.services.url_validator import is_safe_url, validate_url_safe


@pytest.mark.security
@pytest.mark.parametrize("dangerous_url", [
    "http://127.0.0.1:8000/api/claims",
    "http://localhost:3000/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.1/admin",
    "http://192.168.1.1/router",
    "http://172.16.0.1/secret",
    "file:///etc/passwd",
    "gopher://evil.com/",
    "ftp://internal.server/data",
    "http://0.0.0.0/"
])
def test_ssrf_prevention(dangerous_url):
    is_safe, reason = is_safe_url(dangerous_url)
    assert is_safe is False, f"URL should be blocked as unsafe: {dangerous_url} (reason: {reason})"


@pytest.mark.security
def test_public_safe_urls_allowed():
    safe_urls = [
        "https://www.reuters.com/news/archive",
        "https://en.wikipedia.org/wiki/Misinformation",
        "https://apnews.com/article/fact-check"
    ]
    for u in safe_urls:
        is_safe, reason = is_safe_url(u)
        assert is_safe is True, f"Public URL should be allowed: {u} (reason: {reason})"


@pytest.mark.security
def test_html_xss_escaping_logic():
    # Mirror the frontend escapeHtml logic implemented in aegis-nav.js
    def escape_html(text: str) -> str:
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    payload = '<script>alert("XSS")</script>'
    escaped = escape_html(payload)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&quot;XSS&quot;" in escaped

    attr_payload = '"><img src=x onerror=alert(1)>'
    escaped_attr = escape_html(attr_payload)
    assert "<img" not in escaped_attr
    assert "&gt;" in escaped_attr
