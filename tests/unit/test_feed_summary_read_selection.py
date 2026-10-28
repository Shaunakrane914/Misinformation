"""Feed descriptions permit bounded reads, never article/evidence acceptance."""
import pytest

from backend.services.research.publisher_links import observed_publisher_articles
from backend.services.research.research_models import EvidenceItem


def feed_parent(summary, *, kind='FEED_ENTRY', scope='FEED_INDEX'):
    return EvidenceItem(id='synthetic-feed', canonical_url='https://publisher.example/feed.xml',
        title='Observed publisher feed', content='Captured feed document',
        metadata={'read_success': True, 'page_metadata': {'content_scope': scope,
            'observed_links': [{'url': 'https://publisher.example/press/agency-case',
                               'text': 'Agency files consumer protection case',
                               'kind': kind, 'summary': summary}]}})


def test_subject_in_captured_feed_summary_permits_read_without_promoting_body():
    parent = feed_parent('The agency alleges Cedar Assist misled customers. The allegations remain unproven.')
    audit = []
    child, = observed_publisher_articles(parent, 'brand', audit, 'Cedar Assist')
    assert child.canonical_url == 'https://publisher.example/press/agency-case'
    assert child.content == '' and child.content_depth == 'INDEX_SNIPPET'
    assert child.metadata['source_type'] == 'FEED_ENTRY'
    assert child.metadata['linked_article_retrieved'] is False
    assert child.metadata['captured_feed_summary_used_for_read_selection'] is True
    assert 'allegations remain unproven' in child.snippet
    assert audit[0]['discard_reason'] is None


@pytest.mark.parametrize('summary,kind,scope', [
    ('The agency alleges an unrelated company misled customers.', 'FEED_ENTRY', 'FEED_INDEX'),
    ('Cedar Assist appears only in arbitrary link metadata.', 'ARTICLE_LEAD', 'FEED_INDEX'),
    ('Cedar Assist appears only in HTML link metadata.', 'FEED_ENTRY', 'main'),
    ('x' * 2000 + ' Cedar Assist', 'FEED_ENTRY', 'FEED_INDEX'),
])
def test_unrelated_unscoped_or_overbound_summary_cannot_fill_reader(summary, kind, scope):
    audit = []
    assert observed_publisher_articles(feed_parent(summary, kind=kind, scope=scope),
                                       'brand', audit, 'Cedar Assist') == []
    assert audit[0]['discard_reason'] == 'OFF_SUBJECT_CONTINUATION'


def test_parsed_feed_scope_survives_reader_and_harvest_continuation(monkeypatch):
    from types import SimpleNamespace
    from backend.infrastructure.acquisition.adapters.web.discovery_document import discovery_document
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.source_registry import source_registry
    xml = '''<rss><channel><title>Agency releases</title><item>
      <title>Agency files consumer protection case</title>
      <link>https://publisher.example/press/agency-case</link>
      <description>The agency alleges Cedar Assist misled customers.</description>
      </item></channel></rss>'''
    page = discovery_document(xml, 'https://publisher.example/feed.xml')
    parent = EvidenceItem(id='parsed-feed', canonical_url='https://publisher.example/feed.xml',
        title='Agency releases', source_quality_score=0.7, relevance_score=0.8,
        metadata={'discovery_kind': 'FEED_INDEX'})
    monkeypatch.setattr(source_registry, 'body_decision', lambda *_: {'eligible': True, 'status': 'EXISTING_ROUTE_POLICY'})
    monkeypatch.setattr(source_registry, 'robots_decision', lambda *_: {'eligible': True, 'status': 'ALLOWED'})
    service = SimpleNamespace(read=lambda *a, **k: {'status': 'success', 'markdown': xml, 'page_metadata': page})
    captured, trace = DeepReader().deep_read([parent], max_reads=1, timeout_per_read=3, service=service)
    assert trace['successful'] == 1
    assert captured[0].metadata['page_metadata']['content_scope'] == 'FEED_INDEX'
    children = HarvestingEngine._observed_children(captured[0], 'Cedar Assist', 'brand', [])
    assert len(children) == 1
    assert children[0].content == '' and children[0].content_depth == 'INDEX_SNIPPET'
