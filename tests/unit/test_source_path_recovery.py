"""Narrow controls for observed October 29 source-path failures; no live I/O."""
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from backend.application.research.acquisition import _observed_issuer_documents
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details, extract_reader_markdown
from backend.services.research.passage_records import _reported_quote_has_speaker
from backend.services.research.publisher_links import observed_publisher_articles
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem


def test_reader_index_retains_observed_documents_without_trusting_dates():
    raw = ('Title: Investor Relations - Apple\nURL Source: https://investor.apple.com/\n'
           'Markdown Content:\n# News and Results\n'
           '[Press Release](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)\n'
           '[unsafe](https://name:password@example.org/report)\n'
           '[script](javascript:alert)')
    page = extract_reader_markdown(raw)['page_metadata']
    assert len(page['observed_links']) == 1
    assert page['observed_links'][0]['verification'] == 'UNVERIFIED_READER_LINK'
    assert 'published' not in page


def issuer():
    return EvidenceItem(id='index', canonical_url='https://investor.apple.com/investor-relations/default.aspx',
        channel='web', query_class='issuer_documents', metadata={'read_success': True,
        'observed_final_endpoint': 'https://r.jina.ai/https://investor.apple.com/investor-relations/default.aspx',
        'page_metadata': {'observed_links': [
            {'url': 'https://www.apple.com/newsroom/results/', 'text': 'Quarterly Press Release',
             'published': '2026-07-30', 'publication_time_source': 'RSS:pubDate'},
            {'url': 'https://www.apple.com.evil.example/results/', 'text': 'Quarterly Press Release'},
            {'url': 'https://other.example/results/', 'text': 'Quarterly Press Release'}]}})


def test_issuer_continuation_uses_existing_registered_root_not_reader_host():
    children = _observed_issuer_documents(issuer())
    assert len(children) == 1
    assert children[0].canonical_url == 'https://www.apple.com/newsroom/results/'
    assert children[0].published_at == '2026-07-30'
    assert children[0].metadata['publication_time_source'] == 'RSS:pubDate'
    assert not children[0].metadata.get('read_success')


def test_unregistered_sibling_domain_does_not_gain_issuer_scope():
    parent = issuer()
    parent.canonical_url = 'https://investor.unknown.example/'
    parent.metadata['observed_final_endpoint'] = parent.canonical_url
    parent.metadata['page_metadata']['observed_links'] = [
        {'url': 'https://www.unknown.example/results/', 'text': 'Quarterly results'}]
    assert not _observed_issuer_documents(parent)


def test_search_form_preserves_task_and_outranks_generic_brand_menu():
    parent = EvidenceItem(id='hub', canonical_url='https://example.org/', query_text='Apple phishing',
        metadata={'read_success': True, 'page_metadata': {'search_forms': [
            {'action': 'https://example.org/', 'parameter': 's'}], 'observed_links': [
            {'url': 'https://example.org/apple-products', 'text': 'Apple products'}]}})
    children = observed_publisher_articles(parent, 'brand', [], 'Apple', max_children=1)
    assert len(children) == 1
    assert children[0].canonical_url == 'https://example.org/?s=Apple+phishing'
    assert not children[0].metadata.get('read_success')


@pytest.mark.parametrize('action', ['https://other.example/', 'https://name:secret@example.org/'])
def test_search_form_cannot_expand_authorization(action):
    parent = EvidenceItem(id='hub', canonical_url='https://example.org/', metadata={
        'read_success': True, 'page_metadata': {'search_forms': [{'action': action, 'parameter': 's'}]}})
    assert not observed_publisher_articles(parent, 'brand', [], 'Apple')


@pytest.mark.parametrize('text,expected', [
    ('Barra said there’s no negotiating future work guarantees, “Job security is something that you earn,” she told the gathering.', True),
    ('Barra said John wrote in his response: “Job security is something that you earn.”', False),
    ('Someone discussed Barra while John said, “Job security is something that you earn.”', False),
])
def test_bounded_reported_quote_clause(text, expected):
    assert _reported_quote_has_speaker(text, 'Barra') is expected


def newsroom(date='October 27, 2026', extra=''):
    return BeautifulSoup('<div class="article"><h1 class="article-title">An actual announcement</h1>'
        f'<div class="article-date">{date}</div>{extra}<div class="article-body">'
        '<p>The company today announced a specific development with several details and attributed statements.</p>'
        '<p>The second substantive paragraph preserves additional source context and explains the reported development.</p>'
        '</div></div>', 'html.parser')


def test_visible_publisher_date_requires_article_header_structure():
    page = extract_observed_page_details(newsroom(), 'https://nvidianews.nvidia.com/news/observed')
    assert page['published'] == '2026-10-27'
    assert page['publication_time_source'] == 'HTML_ARTICLE_HEADER:article-date'


@pytest.mark.parametrize('change', ['updated', 'duplicate', 'no_body'])
def test_unqualified_visible_dates_remain_unknown(change):
    soup = newsroom('Updated October 27, 2026' if change == 'updated' else 'October 27, 2026',
        '<div class="article-date">October 28, 2026</div>' if change == 'duplicate' else '')
    if change == 'no_body':
        soup.select_one('.article-body').decompose()
    assert 'published' not in extract_observed_page_details(soup, 'https://example.org/story')


def test_observed_redirect_keeps_reserved_source_identity_and_roundtrips():
    parent = EvidenceItem(id='reserved', canonical_url='https://example.org/feed/rss/', channel='web')
    pool = RawAcquisitionPool('actual-redirect')
    pool.add_candidate(parent)
    capture = deepcopy(parent)
    capture.canonical_url = 'https://example.org/feed/'
    capture.content = 'Observed feed bytes remain discovery only and do not become article evidence.'
    capture.content_depth = 'PARTIAL_CONTENT'
    capture.metadata = {'read_success': True, 'transport': {'http_status': 200,
        'network_observed_this_attempt': True, 'requested_endpoint': parent.canonical_url,
        'endpoint': capture.canonical_url, 'redirect_chain': [parent.canonical_url, capture.canonical_url]},
        'page_metadata': {'content_scope': 'FEED_INDEX'}}
    assert pool.add_capture(capture) == 'reserved'
    restored = RawAcquisitionPool.from_export(pool.export(include_text=True))
    assert restored.stats()['source_count'] == 1
    assert restored.stats()['article_bodies'] == 0


def test_reused_id_without_transport_proof_does_not_merge_different_sources():
    pool = RawAcquisitionPool('unproved-redirect')
    pool.add_candidate(EvidenceItem(id='reserved', canonical_url='https://example.org/one'))
    assert pool.add_candidate(EvidenceItem(id='reserved', canonical_url='https://other.example/two',
        metadata={'read_success': True})) != 'reserved'
