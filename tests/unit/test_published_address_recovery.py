"""Acquired speech container, date and attribution regressions; no live I/O."""
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page, extract_observed_page_details
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem
from backend.services.research.passage_records import public_statement_attribution, usable_published_address_paragraph
from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage
from backend.agents.personal_watch.monitoring import attribution_metadata


def speech_html():
    paragraphs = [
        'Our manufacturing team works hard to build vehicles safely. We learn from our colleagues and keep improving.',
        'Listen to understand the people around you. Protect your integrity and own your mistakes as you build your career.',
        'My first role was inspecting components on the assembly line. The talented people there taught me empathy and leadership.',
        'We restored the policy because I had failed to listen. People needed flexibility to manage their work and family lives.',
        'There is always room for another person at our table. We should make inclusion part of the way we lead.',
        'Your purpose can guide difficult decisions at work. Be honest with yourself and stay open to feedback from other people.',
    ]
    return ('<html><main><article class="story"><div class="row"><header class="story-header">'
            '<small class="story-published-info">PUBLISHED <time datetime="2022-05-08 12:00">May 8, 2022</time></small>'
            '<h1>Alex Rivera: Leadership lessons</h1></header></div><div class="story-author-name">Alex Rivera</div>'
            '<div class="story-main-content"><aside class="editors-note"><strong>Editor\'s Note:</strong>'
            '<p>Alex Rivera is the company CEO. They delivered the following address at the 2022 commencement ceremonies.</p>'
            '</aside>' + ''.join('<p>'+p+'</p>' for p in paragraphs) + '</div>'
            '<footer><h2>Recent Stories</h2><article class="story-card"><p>Unrelated new report.</p>'
            '<time datetime="2026-10-30">October 30, 2026</time></article></footer></article></main></html>')


def acquired_item(html=None):
    soup = BeautifulSoup(html or speech_html(), 'html.parser')
    page = extract_observed_page_details(soup, 'https://example.org/speech')
    extracted = extract_readable_page(soup)
    page.update({k:v for k,v in extracted.items() if k not in {'text', 'raw_text'}})
    return EvidenceItem(id='native-speech', canonical_url='https://example.org/speech',
        title='Alex Rivera: Leadership lessons', content=extracted['text'],
        published_at=page.get('published', ''), content_depth='PARTIAL_CONTENT', acquired_id='capture-id',
        metadata={'read_success':True, 'acquisition_objective':'PUBLIC_STATEMENT', 'page_metadata':page})


def test_nested_recommendation_cards_do_not_hide_original_body_or_advance_publication():
    item = acquired_item()
    page = item.metadata['page_metadata']
    assert page['body_quality']['body_kind'] == 'ARTICLE_BODY'
    assert 'Recent Stories' not in item.content and 'Unrelated' not in item.content
    assert page['published'] == item.published_at == '2022-05-08'
    assert page['publication_time_source'] == 'HTML_PUBLISHED_HEADER:calendar_date'
    assert page['published_address']['speaker'] == 'Alex Rivera'
    assert not page['published_address']['identity_authenticated']


def test_address_scope_survives_pool_and_personal_normalization_without_claiming_authentication():
    item = acquired_item()
    pool = RawAcquisitionPool('address-offline'); pool.add_candidate(item); pool.add_capture(item)
    restored = pool.to_evidence_items()[0]
    assert restored.metadata['page_metadata']['published_address'] == item.metadata['page_metadata']['published_address']
    normalized = {'content':restored.content, 'content_depth':restored.content_depth,
                  'metadata':attribution_metadata(restored)}
    paragraph = restored.content.split('\n\n')[2]
    assert public_statement_attribution(normalized, paragraph, 'Alex Rivera') == 'OBSERVED_PUBLISHER_ADDRESS_SECTION'
    assert public_statement_attribution(normalized, paragraph, 'Another Rivera') is None


def test_actual_address_instructions_survive_declarative_only_filter_with_exact_citations():
    item = acquired_item()
    paragraph = next(p for p in item.content.split('\n\n') if p.startswith('Listen to understand'))
    assert not has_usable_passage({'content':paragraph, 'content_depth':'PARTIAL_CONTENT'})
    assert usable_published_address_paragraph(item, paragraph, 'Alex Rivera')
    PassageExtractor().extract_passages([item], 'Alex Rivera', domain='personal')
    row = next(row for row in item.metadata['evidence_passages'] if row['text'] == paragraph)
    assert item.content[row['start']:row['end']] == paragraph
    assert row['attribution'] == 'OBSERVED_PUBLISHER_ADDRESS_SECTION'
    assert row['published_at'] == '2022-05-08'


@pytest.mark.parametrize('change', ['author', 'intro', 'multiple_authors', 'second_speaker'])
def test_title_name_alone_or_ambiguous_speech_does_not_create_attribution(change):
    html = speech_html()
    if change == 'author':
        html = html.replace('class="story-author-name"', 'class="not-an-author"')
    elif change == 'intro':
        html = html.replace('delivered the following address', 'attended the following event')
    elif change == 'multiple_authors':
        html = html.replace('<div class="story-main-content">', '<span class="story-author-name">Jordan Rivera</span><div class="story-main-content">')
    else:
        html = html.replace('<p>Our manufacturing', '<p>Jordan Rivera: This is another speaker.</p><p>Our manufacturing')
    assert 'published_address' not in acquired_item(html).metadata['page_metadata']


@pytest.mark.parametrize('change', ['hash', 'failed', 'snippet', 'temporal', 'rejected'])
def test_speech_scope_cannot_survive_changed_bytes_or_bypass_existing_gates(change):
    item = deepcopy(acquired_item())
    paragraph = item.content.split('\n\n')[2]
    if change == 'hash': item.content += ' Changed capture.'
    elif change == 'failed': item.acquired_id=''; item.metadata['read_success']=False
    elif change == 'snippet': item.content_depth='INDEX_SNIPPET'
    elif change == 'temporal': item.metadata.update(temporal_required=True, temporal_eligible=False)
    elif change == 'rejected': item.metadata['layer2_eligible']=False
    assert not usable_published_address_paragraph(item, paragraph, 'Alex Rivera')


def test_update_label_and_sidebar_clock_do_not_become_original_publication():
    item = acquired_item(speech_html().replace('>PUBLISHED ', '>UPDATED '))
    assert not item.metadata['page_metadata'].get('published')
