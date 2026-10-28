"""Genuine normalized drift replay plus synthetic source-access regressions.

No network/model calls. Synthetic positive controls do not prove live recall.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.infrastructure.acquisition.adapters.web.search_observations import capture_search, result_fit
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
from backend.services.research.research_models import EvidenceItem
from backend.services.research.source_registry import SourceRegistry, _BODY_REGISTRY, enforce_scoped_body_access
from backend.services.research.topic_context import infer_context


@pytest.mark.parametrize('query,url,reason', [
    ('Asha Vale site:publisher.example','https://publisher.example/interview',None),
    ('Asha Vale site:publisher.example','https://news.publisher.example/interview',None),
    ('Asha Vale site:publisher.example','https://publisher.example.evil.test/interview','SITE_SCOPE_MISMATCH'),
    ('Asha Vale site:publisher.example','https://other.example/publisher.example','SITE_SCOPE_MISMATCH'),
    ('Asha Vale (site:first.example OR site:second.example)','https://second.example/interview',None),
    ('Asha Vale -site:other.example','https://other.example/interview','SITE_SCOPE_MISMATCH'),
    ('Asha Vale -site:other.example','https://publisher.example/interview',None),
    ('Asha Vale site:publisher.example/news','https://publisher.example/newsroom','SITE_SCOPE_MISMATCH'),
    ('Asha Vale site:publisher.example/news','https://publisher.example/news/interview',None),
    ('Asha Vale site:publisher.example:bad','https://publisher.example/interview','INVALID_SITE_SCOPE'),
])
def test_search_scope_is_a_url_constraint_not_a_title_signal(query,url,reason):
    with capture_search('Asha Vale','personal'):
        assert result_fit(query,'Asha Vale public statement','',url)[1]==reason


def test_genuine_bumrah_offsite_rows_cannot_suppress_scoped_fallback():
    saved=json.loads(Path(__file__).with_name('fixtures').joinpath('oct26_topic_scope_drift.json').read_text(encoding='utf-8'))
    with capture_search(saved['target'],'personal'):
        decisions=[result_fit(saved['query'],row['title'],'',row['url'])[1] for row in saved['rows']]
    assert len(decisions)==10
    assert all(reason=='SITE_SCOPE_MISMATCH' for reason in decisions)


def test_nonempty_offsite_primary_activates_existing_secondary_provider():
    body=b'<li class="b_algo"><h2><a href="https://other.example/a">Asha Vale public statement</a></h2></li>'
    response=BoundedHTTPResponse(body=body,endpoint='https://www.bing.com/search',status_code=200,
        content_type='text/html',headers={'Content-Type':'text/html'},latency_ms=1,attempts=1)
    good=EvidenceFragment(platform='web',title='Asha Vale public statement',url='https://publisher.example/article')
    router=NativeRouter()
    with capture_search('Asha Vale','personal') as observations, \
         patch('backend.infrastructure.acquisition.routing.router.fetch_public_http',return_value=response), \
         patch.object(router,'_execute_yahoo_search',return_value=[good]) as secondary:
        rows=router._execute_web_search('Asha Vale site:publisher.example',limit=1)
    secondary.assert_called_once()
    assert rows[0].url==good.url
    assert observations[0]['status']=='IRRELEVANT_RESULTS'
    assert observations[0]['decisions'][0]['discard_reason']=='SITE_SCOPE_MISMATCH'


def test_existing_routes_can_be_selected_without_inventing_new_publisher_approval():
    r=SourceRegistry(reviews={})
    assert r.assess('microsoft_source')['eligible_for_bounded_probe']
    assert r.assess('microsoft_source')['status']=='EXISTING_ROUTE_POLICY'
    assert not r.assess('filmfare')['eligible_for_bounded_probe']
    health=Mock();health.assess.return_value={'decision':'EXCLUDE'}
    assert not r.assess('microsoft_source',runtime_capabilities=health)['eligible_for_bounded_probe']


def test_existing_native_auth_still_required(monkeypatch):
    r=SourceRegistry(reviews={})
    row=dict(r.by_id['microsoft_source'],auth_env='TEST_EXISTING_SOURCE_KEY')
    r=SourceRegistry(reviews={},sources=[row])
    monkeypatch.delenv('TEST_EXISTING_SOURCE_KEY',raising=False)
    assert r.assess(row['id'])['status']=='AUTH_REQUIRED'


def test_topic_match_cannot_send_unrelated_company_to_another_issuer():
    r=SourceRegistry(reviews={})
    selected,_=r.select(infer_context('Cedar Instruments technology public statement','Cedar Instruments',agent='personal_watch'))
    assert not {'apple_newsroom','microsoft_source'} & {row['id'] for row in selected}


def test_indian_official_sources_need_a_jurisdiction_routing_hint(monkeypatch):
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    r=SourceRegistry(clock=lambda:datetime(2026,10,26,tzinfo=timezone.utc))
    context=infer_context('Australian cricketer Asha Vale statement','Asha Vale',agent='personal_watch')
    assert context.jurisdiction=='AU'
    assert not {'pib','yas'} & {row['id'] for row in r.select(context)[0]}


def test_observed_country_hint_requires_subject_match_and_keeps_conflicts_ambiguous():
    first=infer_context('Asha Vale','Asha Vale',agent='personal_watch',observed_titles=['Other Person India cricket captain'])
    assert first.jurisdiction=='UNKNOWN'
    second=infer_context('Asha Vale','Asha Vale',agent='personal_watch',observed_titles=['Asha Vale India cricket captain'])
    assert second.jurisdiction=='IN' and second.basis=='REQUEST_AND_OBSERVED_TITLE_CUES'
    conflict=infer_context('Asha Vale','Asha Vale',agent='personal_watch',observed_titles=[
        'Asha Vale India cricket captain','Asha Vale Australia statement'])
    assert conflict.jurisdiction=='UNKNOWN'


@pytest.mark.parametrize('query,target,agent,expected',[
    ('Bollywood actor Asha Vale film award','Asha Vale','trending','pib'),
    ('Indian cricketer Asha Vale public statement','Asha Vale','personal_watch','yas'),
])
def test_reviewed_official_sources_are_eligible_for_relevant_subjects(monkeypatch,query,target,agent,expected):
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    r=SourceRegistry(clock=lambda:datetime(2026,10,26,tzinfo=timezone.utc))
    selected,_=r.select(infer_context(query,target,agent=agent),limit=3)
    assert expected in {row['id'] for row in selected}
    assert r.body_decision('https://'+r.by_id[expected]['hosts'][0]+'/article')['eligible']
    assert not r.excerpt_decision('https://'+r.by_id[expected]['hosts'][0]+'/article',
                                 {'rights_exception_observed':True})['eligible']


def test_wrapper_resolution_is_discovery_but_actual_body_keeps_source_scope(monkeypatch):
    import backend.services.research.source_registry as registry_module
    from backend.services.research.deep_reader import DeepReader
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    monkeypatch.setenv('AEGIS_SOURCE_ALLOWED_FAMILIES','pib')
    r=SourceRegistry(clock=lambda:datetime(2026,10,26,tzinfo=timezone.utc),
        robots_fetcher=lambda *a,**kw:SimpleNamespace(status_code=200,body=b'User-agent: *\nAllow: /'))
    monkeypatch.setattr(registry_module,'source_registry',r)
    title='Asha Vale addresses national cinema awards ceremony'
    observed_url='https://www.pib.gov.in/PressReleasePage.aspx?PRID=123456'

    class Service:
        def retrieve_many(self,*args,**kwargs):
            assert kwargs['perform_reads'] is False
            assert _BODY_REGISTRY.get() is None
            return RetrievalResult(query=title,domain='personal',fragments=[EvidenceFragment(
                platform='web',url=observed_url,title=title)])

        def read(self,url,max_chars):
            assert _BODY_REGISTRY.get() is r
            assert url==observed_url
            enforce_scoped_body_access(url)
            return {'status':'success','content':('Asha Vale said she would address the national cinema awards ceremony. '*20),
                    'page_metadata':{'body_quality':{'body_kind':'ARTICLE_BODY'},'content_scope':'article'}}

    item=EvidenceItem(id='synthetic_wrapper_1',canonical_url='https://news.google.com/rss/articles/opaque',
                      channel='web',title=title,metadata={'candidate_score':.9})
    captures,telemetry=DeepReader().deep_read([item],max_reads=1,timeout_per_read=3,service=Service())
    assert len(captures)==1 and telemetry['successful']==1
    assert captures[0].canonical_url==observed_url


@pytest.mark.parametrize('controller',['legacy','pipelined_v1'])
def test_reviewed_directory_can_find_native_article_when_search_is_empty(monkeypatch,controller):
    """Synthetic full chain: configured directory -> observed article -> real reader.

    The article URL is returned by the provider double's captured link metadata,
    never installed into the planner or supplied as the investigation input.
    """
    from dataclasses import replace
    import backend.services.research.source_registry as registry_module
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    from backend.services.research.research_models import ResearchRequest
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    monkeypatch.setenv('AEGIS_SOURCE_ALLOWED_FAMILIES','yas')
    monkeypatch.setenv('AEGIS_SEARCH_ADVISOR_ENABLED','false')
    r=SourceRegistry(clock=lambda:datetime(2026,10,26,tzinfo=timezone.utc),
        robots_fetcher=lambda *a,**kw:SimpleNamespace(status_code=200,body=b'User-agent: *\nAllow: /'))
    monkeypatch.setattr(registry_module,'source_registry',r)
    claim='Indian cricketer Asha Vale public statement'
    plan=SourcePlanningEngine(source_registry=r).plan(claim,entity='Asha Vale',agent='personal_watch',
        domain='personal',allowed_channels=['web'],use_llm=False)
    rows=[{'channel':c,**q,'source_plan_action_id':q['query_id']} for c,values in plan.to_channel_queries().items() for q in values]
    article='https://yas.gov.in/news/observed-asha-remarks'

    class Service:
        def __init__(self):self.urls=[]

        def retrieve_many(self,*a,**kw):
            return RetrievalResult(query='Asha Vale',domain='personal',fragments=[])

        def read(self,url,max_chars):
            self.urls.append(url)
            if url=='https://yas.gov.in/':
                return {'status':'success','content':'Sports ministry latest releases and official records. '*10,
                    'page_metadata':{'content_scope':'PUBLIC_DISCOVERY_INDEX','body_quality':{'body_kind':'NEWS_INDEX'},
                        'observed_links':[{'url':article,'text':'Asha Vale public statement'}]}}
            assert url==article
            return {'status':'success','content':'Asha Vale said she would publish the complete statement. '*20,
                    'page_metadata':{'content_scope':'article','body_quality':{'body_kind':'ARTICLE_BODY'}}}

    service=Service()
    result=HarvestingEngine(service).run('Asha Vale','personal',agent_name='personal_watch',source_plan=plan,
        query_plan=rows,controller=controller,request=ResearchRequest(target='Asha Vale',domain='personal',
            extra_params={'claim_text':claim,'allowed_channels':['web']}),
        profile=replace(QUICK,max_queries=2,max_reads=3,host_spacing_seconds=0))
    assert service.urls==['https://yas.gov.in/',article], {
        'families':[a.source_family for a in plan.actions if a.source_family],
        'directories':result.retrieval_trace.get('publisher_directories'),
        'rejected':result.rejected,'metrics':result.metrics}
    assert result.metrics['article_bodies']==1
    assert result.read_telemetry['attempted']==2
    assert any(row['source_family']=='yas' for row in result.retrieval_trace['publisher_directories'])
    assert not r.discovery_entrypoints('filmfare')


def paced_registry():
    tick=[0.0]
    sleeps=[]
    def sleep(seconds):
        sleeps.append(seconds)
        tick[0]+=seconds
    r=SourceRegistry(clock=lambda:datetime(2026,10,26,tzinfo=timezone.utc),monotonic=lambda:tick[0],sleeper=sleep,
        robots_fetcher=lambda *a,**kw:SimpleNamespace(status_code=200,
            body=b'User-agent: *\nCrawl-delay: 10\nAllow: /'))
    return r,tick,sleeps


def test_observed_crawl_delay_is_honored_before_every_transfer(monkeypatch):
    from backend.services.research.source_registry import source_body_scope
    from backend.infrastructure.acquisition.network.http import fetch_public_http
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    r,tick,sleeps=paced_registry()
    starts=[]
    def transfer(*a,**kwargs):
        starts.append(tick[0]);tick[0]+=1
        assert kwargs['max_attempts']==1 and kwargs['max_redirects']==0
        return SimpleNamespace(status_code=200)
    with source_body_scope(r),patch('backend.infrastructure.acquisition.network.http._fetch_public_http',side_effect=transfer):
        fetch_public_http('https://globalvoices.org/',timeout=5,max_attempts=2,max_redirects=4)
        fetch_public_http('https://globalvoices.org/observed-article/',timeout=5)
    assert starts==[10.0,21.0] and sleeps==[10.0,10.0]


def test_crawl_delay_cannot_extend_parent_deadline_or_start_http(monkeypatch):
    import time
    from backend.services.research.source_registry import source_body_scope,SourcePermissionError
    from backend.infrastructure.acquisition.network.budget import acquisition_deadline
    from backend.infrastructure.acquisition.network.http import fetch_public_http
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    r,_,sleeps=paced_registry()
    with source_body_scope(r),acquisition_deadline(time.monotonic()+2), \
         patch('backend.infrastructure.acquisition.network.http._fetch_public_http') as transfer:
        with pytest.raises(SourcePermissionError) as error:
            fetch_public_http('https://globalvoices.org/')
    assert error.value.failure_kind=='ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED'
    transfer.assert_not_called();assert not sleeps


def test_concurrent_same_origin_requests_share_one_pacing_lease(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from contextvars import copy_context
    from backend.services.research.source_registry import source_body_scope
    from backend.infrastructure.acquisition.network.http import fetch_public_http
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE','')
    r,tick,_=paced_registry();starts=[]
    def transfer(*a,**kw):
        starts.append(tick[0]);tick[0]+=1
        return SimpleNamespace(status_code=200)
    with source_body_scope(r),patch('backend.infrastructure.acquisition.network.http._fetch_public_http',side_effect=transfer):
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures=[workers.submit(copy_context().run,fetch_public_http,'https://globalvoices.org/') for _ in range(2)]
            for future in futures:future.result()
    assert starts==[10.0,21.0]


def test_native_policy_denial_cannot_be_reinterpreted_as_empty_html():
    from backend.services.agent_reach.native.executor import NativeExecutor
    from backend.services.research.source_registry import SourcePermissionError
    denial=SourcePermissionError({'status':'ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED'})
    with patch('backend.services.agent_reach.native.executor.is_safe_url',return_value=(True,'')), \
         patch('backend.services.agent_reach.native.executor.fetch_public_http',side_effect=denial) as fetch:
        with pytest.raises(SourcePermissionError):NativeExecutor().execute_web_read('https://globalvoices.org/')
    assert fetch.call_count==1


def test_modular_reader_cannot_fallback_after_native_policy_denial():
    from backend.infrastructure.acquisition.adapters.web.jina import execute_web_read
    from backend.services.research.source_registry import SourcePermissionError
    executor=Mock();executor.execute_web_read.side_effect=SourcePermissionError({'status':'PERMISSION_REQUIRED'})
    paid=Mock()
    with patch('backend.infrastructure.acquisition.adapters.web.jina.is_safe_url',return_value=(True,'')):
        with pytest.raises(SourcePermissionError):
            execute_web_read('https://globalvoices.org/',executor=executor,firecrawl_adapter=paid)
    paid.scrape_article.assert_not_called()
