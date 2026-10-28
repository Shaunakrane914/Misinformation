"""Background publication never upgrades old/missing/future text to current evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import pytest
from backend.services.research.research_models import EvidenceItem
from backend.services.research.trending_background import historical_background
from backend.services.research.relevance_gate import RelevanceGate
from backend.services.research.source_registry import source_registry

NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def capture(date='2026-05-27T10:00:00Z'):
    body = ('Aster expanded its ceramic battery recycling program across the region. The company reported that the new process recovers materials from used batteries.\n\n'
            'The battery recycling program includes collection sites for consumers. The announcement describes how workers will sort batteries before processing them.')
    return EvidenceItem(id='captured-source', title='Aster expands ceramic battery recycling',
        canonical_url='https://publisher.example/battery-recycling', content=body,
        published_at=date, content_depth='PARTIAL_CONTENT', source_quality_score=0.8,
        metadata={'read_success': True, 'layer2_eligible': False, 'temporal_required': True,
            'temporal_eligible': False, 'page_metadata': {'body_kind': 'ARTICLE_BODY',
                'published': date, 'publication_time_source': 'HTML_META:article:published_time'}})


def test_old_body_becomes_separate_background_without_mutating_original(monkeypatch):
    monkeypatch.setattr(source_registry, 'excerpt_decision', lambda *a: {'eligible': True})
    item = capture()
    item.extraction_status = 'TEMPORAL_INELIGIBLE'
    before = deepcopy(item)
    result = historical_background([item], 'battery recycling', reference_time=NOW)
    assert result['status'] == 'AVAILABLE' and result['published_words'] > 20
    row, = result['sources']
    assert row['freshness'] == 'OLDER_BACKGROUND'
    assert all(text in item.content for text in row['passage'].split('\n\n'))
    assert item == before
    assert not RelevanceGate(reference_time=NOW).evaluate_item(item, 'battery recycling', domain='trending').is_accepted


@pytest.mark.parametrize('date', ['', 'not a date', '2026-10-30T00:00:00Z', '2026-10-27T18:00:00Z'])
def test_unknown_future_and_fresh_are_not_historical_fallback(monkeypatch, date):
    monkeypatch.setattr(source_registry, 'excerpt_decision', lambda *a: {'eligible': True})
    assert historical_background([capture(date)], 'battery recycling', reference_time=NOW)['sources'] == []


def test_permissions_remain_mandatory(monkeypatch):
    monkeypatch.setattr(source_registry, 'excerpt_decision', lambda *a: {'eligible': False})
    assert historical_background([capture()], 'battery recycling', reference_time=NOW)['sources'] == []


def test_old_feed_date_without_article_publication_cannot_become_background(monkeypatch):
    monkeypatch.setattr(source_registry, 'excerpt_decision', lambda *a: {'eligible': True})
    item = capture()
    item.metadata['page_metadata'].pop('published')
    assert historical_background([item], 'battery recycling', reference_time=NOW)['sources'] == []


def test_shared_report_retains_background_without_current_findings():
    from backend.services.report_builder import ReportBuilder
    background = {'sources': [{'evidence_id': 'captured', 'published_at': '2020-01-01',
        'passage': 'An older source reported battery recycling information.'}], 'published_words': 8}
    report = ReportBuilder.from_trending_result(query='battery recycling',
        trend_data={'retrieval_trace': {'historical_background': background}})
    assert report.agent_intelligence['historical_background'] == background
    assert report.findings == []


@pytest.mark.parametrize('change', ['unread', 'index', 'unrelated'])
def test_discovery_indexes_and_unrelated_bodies_cannot_fill_background(monkeypatch, change):
    monkeypatch.setattr(source_registry, 'excerpt_decision', lambda *a: {'eligible': True})
    item = capture()
    if change == 'unread': item.metadata['read_success'] = False
    if change == 'index': item.metadata['page_metadata']['body_kind'] = 'SOURCE_INDEX'
    if change == 'unrelated':
        item.title = 'Tennis results'; item.content = 'The tennis team won the tournament in the city. ' * 10
        item.canonical_url = 'https://publisher.example/tennis'
    assert historical_background([item], 'battery recycling', reference_time=NOW)['sources'] == []
