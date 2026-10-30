"""Four offline controls for bounded link depth and already-acquired context."""
from copy import deepcopy

from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.page_extraction import (
    MAX_OBSERVED_LINKS, extract_observed_page_details, extract_reader_markdown, observe_text_structure, recovered_span_allowed,
)
from backend.services.research.evidence_workbench import _adjacent_brand_paragraphs
from backend.services.research.passage_extractor import has_usable_passage
from backend.services.research.publisher_links import observed_publisher_articles
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem


def test_late_subject_link_survives_bounded_pool_without_more_read_slots():
    links = ''.join(f'<a href="/story-{i}">Unrelated story {i}</a>' for i in range(350))
    links += '<a href="/acme-counterfeit-seizure">Acme counterfeit seizure report</a>'
    links += ''.join(f'<a href="/more-{i}">Other headline {i}</a>' for i in range(400))
    links += '<a href="https://user:secret@example.org/hidden">Acme counterfeit</a>'
    page = extract_observed_page_details(BeautifulSoup('<main>'+links+'</main>', 'html.parser'), 'https://example.org/search')
    assert len(page['observed_links']) == MAX_OBSERVED_LINKS
    parent = EvidenceItem(id='index', canonical_url='https://example.org/search', metadata={
        'read_success': True, 'page_metadata': page})
    children = observed_publisher_articles(parent, 'brand', [], 'Acme', max_children=1)
    assert len(children) == 1
    assert children[0].canonical_url == 'https://example.org/acme-counterfeit-seizure'
    assert not children[0].content and not children[0].acquired_id
    assert all('secret' not in row['url'] for row in page['observed_links'])


def test_observed_search_result_endpoint_is_discovery_and_keeps_publisher_scope():
    page = extract_reader_markdown('Title: Search\nMarkdown Content:\n'
        '[](https://example.org/dt-custom/search-results?query=Mary+Barra)\n'
        '[](https://other.example/search-results?q=Mary+Barra)')['page_metadata']
    parent = EvidenceItem(id='search', canonical_url='https://example.org/search?query=Mary+Barra',
        metadata={'read_success': True, 'page_metadata': page})
    children = observed_publisher_articles(parent, 'personal', [], 'Mary Barra')
    assert [row.canonical_url for row in children] == ['https://example.org/dt-custom/search-results?query=Mary+Barra']
    assert children[0].metadata['discovery_kind'] == 'FEED_INDEX'
    assert not children[0].acquired_id


def incident():
    winner = 'The enforcement agency (EA) seized counterfeit Acme products after identifying an illicit warehouse operation.'
    followups = ['EA officers executed a search warrant and recovered counterfeit devices from the warehouse during the operation.',
                 'According to a report from EA, no arrests were made and the investigation remains open.']
    body = '\n\n'.join([winner, 'Related Stories', 'Industry News', 'Other industry report', *followups])
    page = {'body_quality': {'body_kind': 'ARTICLE_BODY'}, 'headings': ['Related Stories'],
        **observe_text_structure(body, ['Related Stories']), 'observed_links': [
            {'text': text, 'url': 'https://example.org/related'} for text in ['Industry News', 'Other industry report']]}
    return EvidenceItem(id='source', canonical_url='https://example.org/acme-incident', title='Acme counterfeit seizure',
        content=body, content_depth='PARTIAL_CONTENT', metadata={'read_success': True, 'page_metadata': page}), winner, followups


def test_incident_qualification_survives_pool_but_cannot_jump_unobserved_prose():
    item, winner, followups = incident()
    pool = RawAcquisitionPool('offline-control')
    pool.add_capture(item)
    restored = RawAcquisitionPool.from_export(pool.export(include_text=True)).to_evidence_items()[0]
    for row in restored.metadata['page_metadata']['text_blocks']:
        if row['role'] == 'RELATED_LINK':
            assert not recovered_span_allowed(restored.content, restored.metadata['page_metadata'], row['start'], row['end'])
    assert [text for _, text in _adjacent_brand_paragraphs(restored, 'Acme', winner)] == followups
    assert restored.content == item.content
    for rejected in ['unobserved_widget', 'different_case', 'temporal', 'layer2']:
        bad = deepcopy(restored)
        if rejected == 'unobserved_widget':
            bad.metadata['page_metadata']['text_blocks'] = []
        elif rejected == 'different_case':
            bad.content = bad.content.replace('EA officers executed', 'EA officers in a separate case executed')
        elif rejected == 'temporal':
            bad.metadata.update(temporal_required=True, temporal_eligible=False)
        else:
            bad.metadata['layer2_eligible'] = False
        assert not _adjacent_brand_paragraphs(bad, 'Acme', winner)


def test_short_safety_prose_is_not_a_label_or_generic_product_evidence():
    sentence = 'The notice lists serious electrical hazards affecting the recalled units.'
    assert has_usable_passage({'content': sentence, 'content_depth': 'PARTIAL_CONTENT'})
    for label in ['Safety warning: Acme products', 'Published October 29, 2026', 'Share this article on Facebook']:
        assert not has_usable_passage({'content': label, 'content_depth': 'PARTIAL_CONTENT'})
    item = EvidenceItem(id='recall', canonical_url='https://example.org/recall', title='Acme recall',
        content='A recall has been issued for counterfeit Acme units after a safety investigation.\n\n'+sentence,
        content_depth='PARTIAL_CONTENT', metadata={'read_success': True, 'page_metadata': {'body_quality': {'body_kind': 'ARTICLE_BODY'}}})
    assert [text for _, text in _adjacent_brand_paragraphs(item, 'Acme')] == [sentence]
    item.content = item.content.replace('A recall has been issued for counterfeit', 'A new catalogue has been issued for')
    assert not _adjacent_brand_paragraphs(item, 'Acme')
