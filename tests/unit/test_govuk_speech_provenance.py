"""GOV.UK structural metadata contracts; synthetic controls, no live proof."""
import json

import pytest

from backend.infrastructure.acquisition.adapters.authoritative import govuk_public
from backend.infrastructure.acquisition.adapters import expanded_catalog
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest
from backend.services.research.research_models import EvidenceItem
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.passage_records import public_statement_attribution
from backend.services.research.passage_extractor import PassageExtractor
from backend.agents.personal_watch.monitoring import attribution_metadata


URL = 'https://www.gov.uk/government/speeches/synthetic-leadership-address'


def payload():
    return {'base_path':'/government/speeches/synthetic-leadership-address', 'document_type':'speech',
        'title':'Leadership address', 'first_published_at':'2024-02-02T10:30:00Z',
        'links':{'speaker':[{'title':'The Rt Hon Alex Rivera MP', 'base_path':'/government/people/alex-rivera'}],
                 'organisations':[{'title':'Department for Example Policy'}]},
        'details':{'delivered_on':'2024-01-31T00:00:00Z', 'body':
            '<h2>Public service</h2><p>Listen to understand the people around you. Protect your integrity and own your mistakes as you build your career.</p>'
            '<p>We work together to improve public services and support our communities. We will listen to those who use these services.</p>'}}


def mocked_api(monkeypatch, data):
    def fetch(url, **kwargs):
        return BoundedHTTPResponse(json.dumps(data).encode(),url,200,'application/json',{},0,1)
    monkeypatch.setattr(govuk_public,'safe_fetch',fetch)


def read(monkeypatch, data):
    mocked_api(monkeypatch,data)
    return expanded_catalog.read_expanded_url(URL)


def item_from_result(result):
    return EvidenceItem(id='speech-control',canonical_url=URL,title=result['title'],
        content=result['content'],content_depth=result['content_depth'],published_at=result['page_metadata']['published'],
        acquired_id='native-capture',query_class='public_statement_discovery',metadata={
            'read_success':True,'page_metadata':result['page_metadata'],'acquisition_objective':'PUBLIC_STATEMENT'})


def test_content_api_speaker_publisher_organisation_and_dates_stay_distinct(monkeypatch):
    result=read(monkeypatch,payload());page=result['page_metadata'];address=page['published_address']
    assert result['status']=='success'
    assert page['publisher']=='GOV.UK'
    assert address['speaker']=='The Rt Hon Alex Rivera MP'
    assert address['issuing_organisations']==['Department for Example Policy']
    assert address['speaker_basis']=='links.speaker'
    assert address['delivered_on']=='2024-01-31T00:00:00Z'
    assert page['published']==address['first_published_at']=='2024-02-02T10:30:00Z'
    assert not address['identity_authenticated']


def test_speech_scope_survives_pool_personal_metadata_and_exact_passages(monkeypatch):
    item=item_from_result(read(monkeypatch,payload()));pool=RawAcquisitionPool('govuk-offline-control')
    pool.add_candidate(item);pool.add_capture(item);restored=pool.to_evidence_items()[0]
    normal={'content':restored.content,'content_depth':restored.content_depth,'metadata':attribution_metadata(restored)}
    paragraph=restored.content.split('\n\n')[1]
    assert public_statement_attribution(normal,paragraph,'Alex Rivera')=='OBSERVED_PUBLISHER_ADDRESS_SECTION'
    assert public_statement_attribution(normal,paragraph,'Department for Example Policy') is None
    assert public_statement_attribution(normal,paragraph,'Jordan Rivera') is None
    PassageExtractor().extract_passages([restored],'Alex Rivera',domain='personal')
    rows=restored.metadata['evidence_passages']
    assert rows and all(restored.content[row['start']:row['end']]==row['text'] for row in rows)
    assert all(row['context_labels']['delivery_date']=='Delivered: 2024-01-31T00:00:00Z' for row in rows)
    from backend.schemas.evidence_inspection import inspect_evidence
    public_rows=inspect_evidence(restored)['evidence_passages']
    assert all(row['context_labels']['delivery_date']=='Delivered: 2024-01-31T00:00:00Z' for row in public_rows)
    assert all(row['context_labels']['issuing_organisation']=='Issued by: Department for Example Policy' for row in public_rows)


def test_named_speaker_without_profile_is_observed_without_inventing_profile(monkeypatch):
    data=payload();data['links']['speaker']=None;data['details']['speaker_without_profile']='Jordan Rivera'
    page=read(monkeypatch,data)['page_metadata'];address=page['published_address']
    assert address['speaker']=='Jordan Rivera' and not address['speaker_profile_url']
    assert address['speaker_basis']=='details.speaker_without_profile'


@pytest.mark.parametrize('condition',['missing','conflict','not_speech','null_details'])
def test_missing_or_conflicting_speaker_never_defaults_to_issuing_department(monkeypatch,condition):
    data=payload()
    if condition=='missing':data['links']['speaker']=None
    elif condition=='conflict':data['details']['speaker_without_profile']='Jordan Rivera'
    elif condition=='not_speech':data['document_type']='guidance'
    else:data['details']=None
    mocked_api(monkeypatch,data);adapter=govuk_public.GovukPublicAdapter()
    doc=adapter.acquire(CandidateSource(url=URL),RetrievalRequest(task_type='READ'))
    if doc.status=='SUCCESS':
        assert 'published_address' not in doc.raw_metadata['page_metadata']
        assert adapter.normalize(doc,CandidateSource(url=URL),RetrievalRequest(task_type='READ'))[0].author!='Department for Example Policy'


def test_govuk_speech_byte_or_subject_mismatch_cannot_inherit_attribution(monkeypatch):
    item=item_from_result(read(monkeypatch,payload()));paragraph=item.content.split('\n\n')[1]
    item.content+=' Modified bytes.'
    assert public_statement_attribution(item,paragraph,'Alex Rivera') is None
    normalized={'content':item.content,'content_depth':item.content_depth,'author':'Alex Rivera',
                'query_class':'public_statement_discovery','metadata':attribution_metadata(item)}
    assert public_statement_attribution(normalized,paragraph,'Alex Rivera') is None


def test_explicit_speech_discovery_filter_keeps_observed_url_only(monkeypatch):
    seen=[]
    def fetch(url,**kwargs):
        seen.append(url)
        return BoundedHTTPResponse(json.dumps({'results':[{'title':'An address',
            'link':'/government/speeches/observed-address','format':'speech'}]}).encode(),url,200,'application/json',{},0,1)
    monkeypatch.setattr(govuk_public,'safe_fetch',fetch)
    result=govuk_public.GovukPublicAdapter().discover('leadership',limit=2,speeches_only=True)
    assert 'filter_format=speech' in seen[0]
    assert result[0].url=='https://www.gov.uk/government/speeches/observed-address'


def test_other_speakers_quote_cannot_fall_back_to_document_author(monkeypatch):
    data=payload();data['details']['body']+='<p>He said: "We will provide the strongest possible support for local communities."</p>'
    item=item_from_result(read(monkeypatch,data));paragraph=item.content.split('\n\n')[-1]
    record={'content':item.content,'content_depth':item.content_depth,'author':'Alex Rivera',
            'query_class':'public_statement_discovery','metadata':attribution_metadata(item)}
    assert public_statement_attribution(record,paragraph,'Alex Rivera') is None
    PassageExtractor().extract_passages([item],'Alex Rivera',domain='personal')
    assert not any(row['text']==paragraph for row in item.metadata['evidence_passages'])


def test_adjacent_short_speech_fragments_stay_exact_and_do_not_consume_one_slot_each(monkeypatch):
    data=payload();data['details']['body']=''.join('<p>We need to work together.</p><p>To improve outcomes for our communities.</p><p>And ensure public services remain accessible.</p><p>-</p>' for _ in range(20))
    item=item_from_result(read(monkeypatch,data))
    from backend.services.research.passage_records import address_paragraph_candidates
    groups=address_paragraph_candidates(item,'Alex Rivera')
    assert len(groups)==20
    assert all(group in item.content for group in groups)
    assert all('\n\n' in group and '\n\n-\n\n' not in group for group in groups)


def test_issuer_and_dates_survive_absent_speaker_without_granting_attribution(monkeypatch):
    data=payload();data['links']['speaker']=None;item=item_from_result(read(monkeypatch,data))
    pool=RawAcquisitionPool('missing-speaker-context');pool.add_candidate(item);pool.add_capture(item)
    restored=pool.to_evidence_items()[0];statement=attribution_metadata(restored)['page_metadata']['official_statement']
    assert statement['issuing_organisations']==['Department for Example Policy']
    assert statement['delivered_on']=='2024-01-31T00:00:00Z'
    assert not statement['speaker']


def test_separately_introduced_other_voice_never_becomes_the_official_speakers_statement(monkeypatch):
    data=payload();data['details']['body']+='<p>My colleague is a journalist and he wrote:</p><p>“We are preparing for weather events unlike any we have experienced before.”</p>'
    item=item_from_result(read(monkeypatch,data));quote=item.content.split('\n\n')[-1]
    assert public_statement_attribution(item,quote,'Alex Rivera') is None
    PassageExtractor().extract_passages([item],'Alex Rivera',domain='personal')
    assert not any(quote in row['text'] for row in item.metadata['evidence_passages'])


def test_original_speech_list_items_without_final_punctuation_are_retained(monkeypatch):
    data=payload();data['details']['body']+='<p>The review identified two important areas for our future work, including:</p><ul><li>improving education in every region and supporting teachers through meaningful professional development</li><li>listening to parents and communities before we make decisions about local public services</li></ul>'
    item=item_from_result(read(monkeypatch,data));PassageExtractor().extract_passages([item],'Alex Rivera',domain='personal')
    assert any('improving education in every region' in row['text'] for row in item.metadata['evidence_passages'])
    assert any('listening to parents and communities' in row['text'] for row in item.metadata['evidence_passages'])


def test_missing_original_dates_never_take_the_update_or_retrieval_timestamp(monkeypatch):
    data=payload();data.pop('first_published_at');data['details'].pop('delivered_on');data['public_updated_at']='2026-10-30T10:00:00Z'
    page=read(monkeypatch,data)['page_metadata'];address=page['published_address']
    assert not page['published'] and not address['first_published_at'] and not address['delivered_on']


@pytest.mark.parametrize('status',[401,403,429])
def test_real_govuk_transport_denial_keeps_terminal_status_without_another_reader(monkeypatch,status):
    from backend.infrastructure.acquisition.adapters import expansion_safety
    from backend.infrastructure.acquisition.network.http import ProviderHTTPError
    calls=[]
    def denied(url,**kwargs):
        calls.append((url,kwargs))
        raise ProviderHTTPError('denied',endpoint=url,status_code=status,network_observed=True,attempts=1)
    monkeypatch.setattr(expansion_safety,'validate_url_safe',lambda url:(True,''))
    monkeypatch.setattr(expansion_safety,'_fetch',denied)
    with pytest.raises(ProviderHTTPError) as failure:
        expanded_catalog.read_expanded_url(URL)
    assert failure.value.status_code==status
    assert len(calls)==1 and calls[0][0]=='https://www.gov.uk/api/content/government/speeches/synthetic-leadership-address'
    assert calls[0][1]['max_attempts']==1 and calls[0][1]['max_redirects']==0
