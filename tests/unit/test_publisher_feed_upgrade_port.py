"""Targeted offline controls for the bounded IDE-to-release feed repair."""
from types import SimpleNamespace

from backend.infrastructure.acquisition.adapters import expanded_catalog
from backend.infrastructure.acquisition.adapters.news import wires_adapter
from backend.services.agent_reach.channels import CandidateSource


def test_direct_bbc_feed_port_retains_date_author_and_deduplicates(monkeypatch):
    xml = b'''<rss version="2.0"><channel><title>Synthetic BBC feed</title><item>
      <title>Technology report</title><link>https://www.bbc.com/news/articles/synthetic-123</link>
      <description>Technology development reported; effects remain unverified.</description>
      <pubDate>Tue, 27 Oct 2026 08:00:00 GMT</pubDate><author>Synthetic author</author>
      </item></channel></rss>'''
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=200, body=xml)
    monkeypatch.setattr(wires_adapter, 'fetch_public_http', fetch)
    monkeypatch.setattr('backend.infrastructure.acquisition.adapters.expansion_safety.validate_url_safe',
                        lambda _: (True, 'Synthetic offline URL'))
    adapter = wires_adapter.NewswireAdapter()
    candidate, = adapter.discover('technology', limit=3)
    assert len(calls) == 3 and all(url.startswith('https://feeds.bbci.co.uk/') for url in calls)
    assert candidate.metadata['publication_time_basis'] == 'PUBLISHER_FEED_DECLARATION'
    assert candidate.metadata['published'] == 'Tue, 27 Oct 2026 08:00:00 GMT'
    assert candidate.metadata['author'] == 'Synthetic author'


def test_feed_publisher_date_survives_discovery_without_becoming_body(monkeypatch):
    lead = CandidateSource(url='https://www.bbc.com/news/articles/synthetic', title='Observed article',
        metadata={'published': '2026-10-27T08:00:00Z', 'author': 'Observed author',
                  'publication_time_basis': 'PUBLISHER_FEED_DECLARATION'})
    adapter = SimpleNamespace(discover=lambda *a, **kw: [lead], backend_id='synthetic-feed')
    monkeypatch.setattr(expanded_catalog, 'get_expanded_adapters', lambda: {'news_wires': adapter})
    fragment, = expanded_catalog.ExpandedSourceChannel().search('news_wires|technology')
    assert fragment.published == '2026-10-27T08:00:00Z' and fragment.author == 'Observed author'
    assert fragment.content == '' and fragment.content_depth == 'INDEX_SNIPPET'
    assert fragment.raw_metadata['discovery_date_requires_body_recheck'] is True
    assert fragment.raw_metadata['linked_article_retrieved'] is False


def test_index_times_and_issue_dates_do_not_become_publisher_dates():
    for adapter in ['gdelt', 'cpsc_recalls', 'wikidata_exec']:
        assert not expanded_catalog._publisher_observation(adapter, {
            'published': '2026-10-27', 'gdelt_seen_at': '2026-10-27',
            'cpsc_issue_date': '2026-10-27', 'publication_time_basis': 'PUBLISHER_FEED_DECLARATION'})
    assert not expanded_catalog._publisher_observation('news_wires', {
        'published': '2026-10-27', 'publication_time_basis': 'UNKNOWN_UNTIL_PUBLISHER_CONTENT'})


def section_feed(items):
    return ('<rss version="2.0"><channel><title>Publisher section</title>' + ''.join(
        '<item><title>' + title + '</title><link>https://www.bbc.com/news/articles/synthetic-' + str(index)
        + '</link><description>Reported development.</description></item>'
        for index, title in enumerate(items)) + '</channel></rss>').encode()


def install_section_fetch(monkeypatch, items):
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=200, body=section_feed(items))
    monkeypatch.setattr(wires_adapter, 'fetch_public_http', fetch)
    monkeypatch.setattr('backend.infrastructure.acquisition.adapters.expansion_safety.validate_url_safe',
                        lambda _: (True, 'Synthetic offline URL'))
    return calls


def test_generic_category_uses_observed_publisher_section_not_literal_word(monkeypatch):
    calls = install_section_fetch(monkeypatch, ['Device maker replaces faulty screens'] * 20)
    candidates = wires_adapter.NewswireAdapter().discover('Technology', limit=3)
    assert len(candidates) == 3 and len(calls) == 1
    assert calls[0].endswith('/technology/rss.xml')
    assert all(c.metadata['discovery_match_basis'] == 'PUBLISHER_TOPIC_SECTION' for c in candidates)
    assert all(c.metadata['discovery_only'] and not c.metadata['linked_article_retrieved'] for c in candidates)
    assert all('technology' not in c.title.casefold() for c in candidates)


def test_named_subject_cannot_match_only_its_generic_section_word(monkeypatch):
    calls = install_section_fetch(monkeypatch, ['Technology report about unrelated devices'] * 20)
    assert wires_adapter.NewswireAdapter().discover('Unseen Corporation technology', limit=3) == []
    assert len(calls) == 3


def test_named_subject_requires_all_meaningful_name_tokens(monkeypatch):
    install_section_fetch(monkeypatch, ['Aster company announces release', 'Cedar Aster announces release'])
    candidates = wires_adapter.NewswireAdapter().discover('Cedar Aster technology', limit=3)
    assert len(candidates) == 1 and candidates[0].title.startswith('Cedar Aster')
    assert candidates[0].metadata['discovery_match_basis'] == 'TITLE_OR_SNIPPET_TOKENS'


def test_empty_section_has_no_invented_article_leads(monkeypatch):
    calls = install_section_fetch(monkeypatch, [])
    assert wires_adapter.NewswireAdapter().discover('Technology', limit=3) == []
    assert len(calls) == 3
