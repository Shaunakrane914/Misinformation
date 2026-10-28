"""Role separation, entity ambiguity, admission and exact reference text."""
import time
from types import SimpleNamespace
from unittest.mock import Mock

from backend.services.agent_reach.channels import CandidateSource, EvidenceFragment, FetchedDocument
from backend.services.research.reference_fallback import acquire_reference_background, select_entity
from backend.services.research.platform_selection import select_platform_queries
from backend.services.research.research_models import ResearchRequest


def request(domain='personal', target='Mary Barra'):
    return ResearchRequest(target=target, domain=domain)


def test_namesakes_are_not_resolved_by_first_search_hit():
    exact = CandidateSource(url='https://en.wikipedia.org/wiki/Mary_Barra', metadata={'wiki_title': 'Mary Barra'})
    other = CandidateSource(url='https://en.wikipedia.org/wiki/Mary', metadata={'wiki_title': 'Mary'})
    assert select_entity([other, exact], 'Mary Barra') is exact
    assert select_entity([exact, exact], 'Mary Barra') is None
    assert select_entity([other], 'Mary Barra') is None


def test_reference_never_becomes_article_evidence_and_keeps_exact_text():
    candidate = CandidateSource(url='https://en.wikipedia.org/wiki/Mary_Barra', metadata={'wiki_title': 'Mary Barra'})
    text = 'Mary Barra is described in this saved encyclopedic source.'
    adapter = Mock()
    adapter.discover.return_value = [candidate]
    adapter.acquire.return_value = FetchedDocument(url=candidate.url, status='SUCCESS', raw_content=text)
    adapter.normalize.return_value = [EvidenceFragment(platform="wikipedia", url=candidate.url, content=text, content_depth='REFERENCE_TEXT',
        raw_metadata={'content_role': 'BACKGROUND_REFERENCE', 'source_permission': {
            'author': 'Wikipedia contributors', 'licence_url': 'https://creativecommons.org/licenses/by-sa/4.0/'}})]
    captures, background = acquire_reference_background(request(), deadline=time.monotonic()+2,
        remaining_reads=1, adapters={'wikipedia': adapter})
    assert background['sources'][0]['passage'] == text
    assert background['sources'][0]['published_at'] is None
    assert captures[0].metadata['layer2_eligible'] is False
    assert background['read_attempts'] == 1
    assert adapter.acquire.call_count == 1


def test_reference_has_no_network_allowance_after_deadline_or_read_cap():
    adapter = Mock()
    for remaining, deadline in [(0, time.monotonic()+2), (2, time.monotonic()-1)]:
        _, result = acquire_reference_background(request(), deadline=deadline, remaining_reads=remaining,
            adapters={'wikipedia': adapter})
        assert result['status'] == 'BUDGET_EXHAUSTED'
    adapter.discover.assert_not_called()


def test_restricted_channels_do_not_trigger_reference_discovery():
    r = request()
    r.extra_params['allowed_channels'] = ['web']
    adapter = Mock()
    _, result = acquire_reference_background(r, deadline=time.monotonic()+2, remaining_reads=1, adapters={'wikipedia': adapter})
    assert result['status'] == 'CHANNEL_RESTRICTED'
    adapter.discover.assert_not_called()


def test_mirrors_and_scraped_transcripts_are_not_social_restoration():
    rows = [{'channel': platform, 'operation': 'search', 'query_text': 'Mary Barra'} for platform in ('reddit','twitter','youtube')]
    chosen, decisions = select_platform_queries(request(), rows)
    assert chosen == []
    assert len(decisions) == 3
    assert all('REQUIRED' in row['status'] for row in decisions)


def test_technical_community_selection_is_topic_specific():
    capability = SimpleNamespace(assess=lambda *_: {'decision': 'ELIGIBLE_UNVERIFIED'})
    chosen, _ = select_platform_queries(request('trending', 'semiconductor manufacturing'), [], capabilities=capability)
    assert [row['channel'] for row in chosen] == ['hackernews']
    assert select_platform_queries(request('trending', 'Shah Rukh Khan'), [], capabilities=capability)[0] == []


def test_reference_denial_does_not_activate_another_reader(monkeypatch):
    from backend.infrastructure.acquisition.adapters.expansion_safety import _FETCH_OBSERVATIONS
    wiki, data = Mock(), Mock()
    def denied(*args, **kwargs):
        _FETCH_OBSERVATIONS.get().append({'http_status': 403})
        return []
    wiki.discover.side_effect = denied
    captures, result = acquire_reference_background(request(), deadline=time.monotonic()+1,
        remaining_reads=2, adapters={'wikipedia': wiki, 'wikidata_exec': data})
    assert captures == []
    assert result['attempts'][0]['status'] == 'ACCESS_DENIED'
    data.discover.assert_not_called()


def test_govuk_saved_search_guidance_paths_and_identity_gate(monkeypatch):
    import json
    from backend.infrastructure.acquisition.adapters.authoritative import govuk_public
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    from backend.services.agent_reach.channels import RetrievalRequest
    adapter = govuk_public.GovukPublicAdapter()
    payload = {'results': [{'title': 'AI guidance', 'link': '/guidance/ai', 'description': 'Guidance'}]}
    monkeypatch.setattr(govuk_public, 'safe_fetch', lambda *_a, **_k: BoundedHTTPResponse(
        json.dumps(payload).encode(), 'https://www.gov.uk/api/search.json', 200, 'application/json', {}, 1, 1))
    candidate = adapter.discover('AI')[0]
    assert candidate.url == 'https://www.gov.uk/guidance/ai'
    payload = {'base_path': '/guidance/ai', 'title': 'AI guidance', 'details': {'body': '<p>Agency text</p>'}}
    doc = adapter.acquire(candidate, RetrievalRequest(task_type='READ'))
    assert doc.raw_content == 'Agency text'
    assert adapter.normalize(doc, candidate, RetrievalRequest(task_type='READ'))[0].content_depth == 'OFFICIAL_STATEMENT'
    payload['base_path'] = '/other'
    assert adapter.acquire(candidate, RetrievalRequest(task_type='READ')).status == 'IDENTITY_MISMATCH'
    assert not adapter.can_handle(CandidateSource(url='https://www.gov.uk/guidance/%2e%2e/private'))
    assert not adapter.can_handle(CandidateSource(url='https://www.gov.uk.evil.test/guidance/ai'))


def test_govuk_rights_exception_is_terminal(monkeypatch):
    import json
    from backend.infrastructure.acquisition.adapters.authoritative import govuk_public
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    from backend.services.agent_reach.channels import RetrievalRequest
    body = json.dumps({'base_path': '/government/news/ai', 'details': {'body': '<p>All rights reserved</p>'}}).encode()
    monkeypatch.setattr(govuk_public, 'safe_fetch', lambda *_a, **_k: BoundedHTTPResponse(
        body, 'https://www.gov.uk/api/content/government/news/ai', 200, 'application/json', {}, 1, 1))
    assert govuk_public.GovukPublicAdapter().acquire(CandidateSource(url='https://www.gov.uk/government/news/ai'),
        RetrievalRequest(task_type='READ')).status == 'RIGHTS_EXCEPTION_REVIEW_REQUIRED'


def test_genuine_reference_pool_roundtrip_keeps_credit_without_new_acquisition():
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.research_models import EvidenceItem
    item = EvidenceItem(id='reference_fixture', canonical_url='https://en.wikipedia.org/wiki/Mary_Barra',
        content='Synthetic reference fixture: Mary Barra biography.', content_depth='REFERENCE_TEXT',
        metadata={'read_success': True, 'source_permission': {'author': 'Wikipedia contributors',
            'licence_url': 'https://creativecommons.org/licenses/by-sa/4.0/'}})
    pool = RawAcquisitionPool('synthetic-roundtrip')
    pool.add_capture(item)
    restored = pool.to_evidence_items()
    adapter = Mock()
    captures, result = acquire_reference_background(request(), deadline=time.monotonic()+1, remaining_reads=0,
        adapters={'wikipedia': adapter}, cached_captures=restored)
    assert captures == []
    assert result['published_words'] == len(item.content.split())
    assert result['acquisition_origin'] == 'REUSED_CAPTURE_NO_NEW_REQUEST'
    assert result['sources'][0]['evidence_id'] == item.id
    adapter.discover.assert_not_called()


def test_body_inclusive_community_api_is_retained_without_web_reader():
    from dataclasses import replace
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    from tests.unit.test_expanded_harvesting import SavedService
    fragment = EvidenceFragment(platform='Stack Overflow', channel_name='stackexchange',
        url='https://stackoverflow.com/questions/12345', title='Python programming question',
        content='Python programming question: how does this function work?', content_depth='PARTIAL_CONTENT',
        native_backend_id='stackexchange-api', raw_metadata={'transport': {'http_status': 200}})
    service = SavedService(leads=[fragment])
    result = HarvestingEngine(service).run(target='Python', domain='trending', intent='programming',
        profile=replace(QUICK, max_queries=1, host_spacing_seconds=0))
    assert len(result.captures) == 1
    assert result.captures[0].content == fragment.content
    assert result.captures[0].content_depth == 'SOCIAL_POST'
    assert result.captures[0].metadata['virality_measured'] is False
    assert service.reads == []


def test_reference_excerpt_excludes_family_and_keeps_exact_professional_offset():
    from backend.services.research.reference_fallback import background_span
    text = '# Profile\nBorn in a town. Her parents lived there.\nHer career includes leadership of the company and industry research.\n'
    passage, start, end = background_span(text)
    assert passage == 'Her career includes leadership of the company and industry research.'
    assert text[start:end] == passage
    assert background_span('Her parents and spouse live at this address.')[0] == ''
