"""Bounded structural diagnostics from bytes already fetched by safe transport.

No page prose, HTML, headers, URLs, scripts or credentials enter this projection.
Classifications explain extraction observations; they never qualify evidence.
"""
import hashlib
import re
from urllib.parse import urlsplit


KINDS = frozenset({'ARTICLE_BODY', 'SEARCH_OR_INDEX', 'HOMEPAGE', 'JAVASCRIPT_SHELL',
    'CHALLENGE_OR_RESTRICTED', 'INCORRECT_URL', 'UNSUPPORTED_CONTENT_TYPE',
    'EXTRACTION_FAILURE', 'EMPTY_DOCUMENT', 'UNCLASSIFIED_PAGE'})
_COUNTS = ('decoded_bytes', 'readable_words', 'paragraph_count', 'script_count',
           'article_element_count', 'heading_count', 'observed_link_count')


def safe_diagnostics(value):
    if not isinstance(value, dict) or not isinstance(value.get('classification'), str) or value['classification'] not in KINDS:
        return {}
    result = {'classification': value['classification'], 'basis': 'OBSERVED_RESPONSE_STRUCTURE',
              'evidence_qualified': False, 'sample_policy': 'METADATA_ONLY_NO_PAGE_TEXT_OR_HEADERS'}
    for key in _COUNTS:
        if type(value.get(key)) is int and 0 <= value[key] <= 4_000_000:
            result[key] = value[key]
    digest = value.get('response_sha256')
    if isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest):
        result['response_sha256'] = digest
    if type(value.get('http_status')) is int and 100 <= value['http_status'] <= 599:
        result['http_status'] = value['http_status']
    return result


def diagnose_response(body, url, content_type, *, soup=None, extracted=None, status=200, extraction_failed=False):
    extracted = extracted or {}
    text = str(extracted.get('text') or '')
    opening = re.sub(r'\s+', ' ', text[:400]).strip().casefold()
    media = (content_type or '').split(';', 1)[0].lower().strip()
    is_html = soup is not None
    scripts = len(soup.find_all('script', limit=2000)) if is_html else 0
    paragraphs = len(soup.find_all('p', limit=2000)) if is_html else 0
    words = len(text.split())
    kind = (extracted.get('body_quality') or {}).get('body_kind')
    path = urlsplit(url).path.strip('/').lower()
    restricted = status in {401, 403, 429} or bool(re.match(
        r'^(?:#{1,3}\s*)?(?:just a moment|verify (?:that )?you are human|attention required|access denied|403 forbidden|checking your browser)', opening))
    login = is_html and soup.find('input', attrs={'type': 'password'}) is not None and words < 80
    if restricted or login:
        classification = 'CHALLENGE_OR_RESTRICTED'
    elif status in {404, 410} or words < 80 and re.match(r'^(?:404\b|page not found\b)', opening):
        classification = 'INCORRECT_URL'
    elif media and not (media.startswith('text/') or media in {
            'application/xhtml+xml', 'application/xml', 'application/rss+xml', 'application/atom+xml',
            'application/json', 'application/ld+json', 'application/pdf'}):
        classification = 'UNSUPPORTED_CONTENT_TYPE'
    elif extraction_failed:
        classification = 'EXTRACTION_FAILURE'
    elif kind == 'ARTICLE_BODY':
        classification = 'ARTICLE_BODY'
    elif extracted.get('content_scope') in {'FEED_INDEX', 'SITEMAP_INDEX', 'PUBLIC_DISCOVERY_INDEX'} or re.search(
            r'(?:^|/)(?:search|category|tag|feed|sitemap)(?:/|\.|$)', path):
        classification = 'SEARCH_OR_INDEX'
    elif scripts and words < 40 and paragraphs < 2:
        classification = 'JAVASCRIPT_SHELL'
    elif not text.strip() and not body.strip():
        classification = 'EMPTY_DOCUMENT'
    elif not path:
        classification = 'HOMEPAGE'
    else:
        classification = 'UNCLASSIFIED_PAGE'
    return safe_diagnostics({'classification': classification, 'http_status': status,
        'response_sha256': hashlib.sha256(body).hexdigest(), 'decoded_bytes': len(body),
        'readable_words': words, 'paragraph_count': paragraphs, 'script_count': scripts,
        'article_element_count': len(soup.find_all('article', limit=2000)) if is_html else 0,
        'heading_count': len(soup.find_all('h1', limit=2000)) if is_html else 0,
        'observed_link_count': len(soup.find_all('a', limit=2000)) if is_html else 0})
