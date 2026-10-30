"""Narrow failures observed in the authorized WXYZ/Duke probe; no network."""
import json

import pytest

from backend.infrastructure.acquisition.adapters.web.discovery_document import drupal_search_document
from backend.services.research.passage_extractor import PassageExtractor
from backend.services.research.passage_records import reported_person_context, public_statement_attribution
from backend.services.research.research_models import EvidenceItem


def envelope(fragment, *, command='insert', method='replaceWith', selector='.js-view-dom-id-search__search'):
    return '<textarea>' + json.dumps([{'command': command, 'method': method, 'selector': selector, 'data': fragment}]) + '</textarea>'


def test_ajax_search_links_are_observed_without_executing_commands_or_becoming_bodies():
    fragment = ('<article class="story-card"><a href="/2022/05/person-statement">'
                '<h3>Mary Barra: Five Lessons from the Kitchen Table</h3></a></article>'
                '<script>fetch("https://example.org/secret")</script>')
    page = drupal_search_document(envelope(fragment), 'https://today.duke.edu/dt-custom/search-results?query=Mary+Barra')
    assert page['content_scope'] == 'PUBLIC_DISCOVERY_INDEX'
    assert page['source_type'] == 'SOURCE_INDEX'
    assert page['body_quality']['body_kind'] != 'ARTICLE_BODY'
    assert page['observed_links'] == [{'url': 'https://today.duke.edu/2022/05/person-statement',
        'text': 'Mary Barra: Five Lessons from the Kitchen Table', 'kind': 'ARTICLE_LEAD',
        'verification': 'OBSERVED_AJAX_SEARCH_LINK_UNVERIFIED'}]


@pytest.mark.parametrize('href', ['https://other.example/article', 'http://today.duke.edu/article',
                                  'https://user:secret@today.duke.edu/article', 'javascript:alert(1)'])
def test_ajax_search_does_not_follow_external_or_credential_or_script_links(href):
    raw = envelope(f'<article class="story-card"><a href="{href}"><h3>Mary Barra statement</h3></a></article>')
    assert drupal_search_document(raw, 'https://today.duke.edu/search') is None


def test_non_search_commands_and_unwrapped_or_malformed_json_are_not_interpreted():
    fragment = '<article class="story-card"><a href="/story"><h3>Mary Barra statement</h3></a></article>'
    for raw in [envelope(fragment, command='add_js'), envelope(fragment, selector='body'),
                envelope(fragment, method='prepend'), '<textarea>not-json</textarea>',
                '<textarea>[]</textarea><script>anything</script>', json.dumps([{'data': fragment}])]:
        assert drupal_search_document(raw, 'https://today.duke.edu/search') is None


def person_item():
    return EvidenceItem(id='new-person-body', canonical_url='https://example.org/story', title='Mary Barra interview',
        content='GM CEO Mary Barra discussed plans in an interview.\n\n'
                'Barra also told shareholders the company suspended dividends and sold bonds during the shutdown.\n\n'
                'She says the company will invest further resources in manufacturing.',
        content_depth='PARTIAL_CONTENT', acquired_id='actual-capture', metadata={
            'read_success': True, 'layer2_eligible': True,
            'page_metadata': {'body_quality': {'body_kind': 'ARTICLE_BODY'}}})


def test_observed_surname_paraphrase_survives_as_context_not_authenticated_quotation():
    item = person_item()
    paragraph = item.content.split('\n\n')[1]
    assert reported_person_context(item, paragraph, 'Mary Barra')
    assert not public_statement_attribution(item, paragraph, 'Mary Barra')
    PassageExtractor().extract_passages([item], 'Mary Barra', domain='personal')
    rows = item.metadata['evidence_passages']
    row = next(row for row in rows if row['text'] == paragraph)
    assert row['content_role'] == 'SOURCE_REPORTED_CONTEXT'
    assert row['attribution'] == 'SOURCE_ASSERTION'
    assert item.content[row['start']:row['end']] == paragraph
    assert not any(row['text'].startswith('She says') for row in rows)


@pytest.mark.parametrize('condition', ['namesake', 'snippet', 'failed', 'temporal', 'rejected', 'fabricated'])
def test_surname_context_retains_ambiguity_acquisition_and_temporal_boundaries(condition):
    item = person_item()
    if condition == 'namesake':
        item.content += '\n\nJessica Barra also attended the meeting.'
    elif condition == 'snippet':
        item.content_depth = 'INDEX_SNIPPET'
    elif condition == 'failed':
        item.acquired_id = ''; item.metadata['read_success'] = False
    elif condition == 'temporal':
        item.metadata.update(temporal_required=True, temporal_eligible=False)
    elif condition == 'rejected':
        item.metadata['layer2_eligible'] = False
    elif condition == 'fabricated':
        item.content = item.content.replace('Barra also told', 'Barra said the fake quote claimed she told')
    assert not reported_person_context(item, item.content.split('\n\n')[1], 'Mary Barra')
