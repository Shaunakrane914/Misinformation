"""Deterministic permission/routing controls. No claim of live source recall."""
import copy
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import json

import pytest

from backend.services.research.source_registry import SourceRegistry, definitions, source_body_scope, SourcePermissionError
from backend.services.research.topic_context import infer_context
from backend.services.agent_reach.source_planner import SourcePlanningEngine, PlanningBudget


NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)


def grant(scopes=('discovery', 'body', 'excerpt')):
    # Synthetic operator record, never installed as a real publisher approval.
    return {'decision': 'APPROVED', 'scopes': list(scopes), 'reviewed_at': '2026-10-26',
            'expires_at': '2026-11-01T00:00:00Z', 'basis_url': 'https://publisher.example/review'}


def registry(reviews=None):
    from types import SimpleNamespace
    return SourceRegistry(reviews={} if reviews is None else reviews, clock=lambda: NOW,
        robots_fetcher=lambda *args, **kwargs: SimpleNamespace(status_code=200,body=b'User-agent: *\nAllow: /'))


@pytest.mark.parametrize('agent,domain,claim,target,topic,task', [
    ('trending','trending','Bollywood actor Kavya Rao film announcement','Kavya Rao','bollywood','TOPIC_DISCOVERY'),
    ('trending','trending','Tamil cinema actor Vela Raman interview','Vela Raman','regional_cinema','TOPIC_DISCOVERY'),
    ('personal_watch','personal','Cricketer Aarav Malik public statement','Aarav Malik','cricket','PUBLIC_STATEMENT'),
    ('trending','trending','Indian election parliament debate','election debate','elections','TOPIC_DISCOVERY'),
    ('trending','trending','semiconductor manufacturing capacity','semiconductor manufacturing','semiconductors','TOPIC_DISCOVERY'),
    ('scout','financial','Northstar Company quarterly revenue','Northstar Company','finance','FINANCIAL_VERIFICATION'),
    ('brandshield','brand','Oriole fake celebrity advertisement Bollywood','Oriole','bollywood','ENDORSEMENT_CLAIM'),
    ('personal_watch','personal','Politician Elena Iqbal false quote','Elena Iqbal','false_quotes','QUOTE_VERIFICATION'),
])
def test_eight_topic_role_tasks_are_not_one_generic_plan(agent,domain,claim,target,topic,task):
    context = infer_context(claim,target,agent=agent,domain=domain)
    assert topic in context.topics and task in context.tasks
    assert 0 < context.confidence < 1


def test_unknown_name_stays_unknown_and_observed_title_requires_subject_match():
    initial = infer_context('Asha Vale','Asha Vale',agent='trending')
    wrong = infer_context('Asha Vale','Asha Vale',agent='trending', observed_titles=['Other Person Bollywood actor interview'])
    refined = infer_context('Asha Vale','Asha Vale',agent='trending', observed_titles=['Asha Vale Bollywood actor interview'])
    assert not initial.topics and not wrong.topics
    assert 'bollywood' in refined.topics and refined.confidence == .55
    assert refined.basis == 'REQUEST_AND_OBSERVED_TITLE_CUES'


def test_partial_words_do_not_select_topics_or_incidents_from_entity_name():
    assert 'technology' not in infer_context('Kiran Sain','Kiran Sain').topics
    assert 'PRODUCT_SAFETY' not in infer_context('Recall Labs','Recall Labs',agent='brandshield').tasks
    assert 'product_safety' not in infer_context('Recall Labs','Recall Labs',agent='brandshield').topics


def test_original_language_is_explicit_or_script_uncertain_no_translation():
    value = infer_context('मीरा देसाई अभिनेत्री बयान','मीरा देसाई',agent='personal_watch')
    assert value.language == 'und-Deva'
    explicit = infer_context('मीरा देसाई अभिनेत्री बयान','मीरा देसाई',hints={'language':'mr','aliases':['Mira Desai']})
    assert explicit.language == 'mr' and explicit.aliases == ('Mira Desai',)


def test_catalog_presence_channel_health_or_request_hints_cannot_grant_permission():
    r = registry()
    health = Mock(); health.assess.return_value={'decision':'ELIGIBLE'}
    c = infer_context('Bollywood actor Kavya Rao','Kavya Rao',agent='trending',hints={'approved': True})
    selected, decisions = r.select(c, runtime_capabilities=health)
    assert decisions
    assert all(s['permission_status']=='EXISTING_ROUTE_POLICY' for s in selected)
    assert all(not d['eligible_for_bounded_probe'] for d in decisions
               if r.by_id[d['source_family']]['permission_status']!='EXISTING_ROUTE_POLICY')
    assert any(d['status']=='PERMISSION_REQUIRED' for d in decisions)
    # An existing native route can still be assessed; an unreviewed new
    # publisher cannot inherit permission from that route's health.


def test_discovery_grant_does_not_authorize_body_or_display():
    r = registry({'bollywood_hungama': grant(('discovery',))})
    assert r.assess('bollywood_hungama')['eligible_for_bounded_probe']
    assert not r.body_decision('https://www.bollywoodhungama.com/news/observed')['eligible']
    assert not r.excerpt_decision('https://www.bollywoodhungama.com/news/observed')['eligible']
    assert r.assess('bollywood_hungama')['runtime_availability']=='UNVERIFIED'


@pytest.mark.parametrize('mutation', [
    {'expires_at':'2026-01-01T00:00:00Z'}, {'expires_at':'2027-01-01'},
    {'basis_url':'http://publisher.example/'}, {'scopes':['all']}, {'decision':True},
    {'scopes':None}, {'basis_url':'https://user:password@publisher.example/'}])
def test_malformed_expired_or_overscoped_review_fails_closed(mutation):
    value=grant();value.update(mutation)
    assert not registry({'filmfare':value}).assess('filmfare')['eligible_for_bounded_probe']


def test_server_file_is_bounded_validated_and_invalid_does_not_restore_public_reviews(tmp_path,monkeypatch):
    p=tmp_path/'reviews.json';p.write_text('{broken')
    monkeypatch.setenv('AEGIS_SOURCE_REVIEWS_FILE',str(p))
    r=SourceRegistry(clock=lambda:NOW)
    assert not r.assess('govuk')['eligible_for_bounded_probe']
    p.write_text(json.dumps({'schema_version':1,'reviews':{'filmfare':grant()}}))
    assert r.assess('filmfare')['eligible_for_bounded_probe']
    assert not r.assess('govuk')['eligible_for_bounded_probe']


def test_auth_and_runtime_cooldown_are_separate_from_licence(monkeypatch):
    monkeypatch.delenv('GUARDIAN_API_KEY',raising=False)
    assert registry({'guardian':grant()}).assess('guardian')['status']=='AUTH_REQUIRED'
    health=Mock();health.assess.return_value={'decision':'DEFER_TEMPORARY'}
    assert registry({'filmfare':grant()}).assess('filmfare',runtime_capabilities=health)['status']=='BLOCKED'


def test_same_subject_different_agent_task_gets_different_eligible_families():
    r=registry({'bollywood_hungama':grant(),'ftc':grant(),'boom':grant()})
    entertainment=infer_context('Bollywood actor Kavya Rao film news','Kavya Rao',agent='trending')
    abuse=infer_context('Kavya Rao Bollywood fake celebrity advertisement','Kavya Rao',agent='brandshield')
    first,_=r.select(entertainment);second,_=r.select(abuse)
    assert 'bollywood_hungama' in {s['id'] for s in first}
    assert second and second[0]['id'] in {'ftc','boom'}


def test_scope_is_projected_through_existing_planner_without_new_channel_or_caps():
    r=registry({'bollywood_hungama':grant()})
    p=SourcePlanningEngine(source_registry=r,budget=PlanningBudget(max_actions=5,max_queries_per_channel=2))
    plan=p.plan('Kavya Rao Bollywood actor film news',entity='Kavya Rao',agent='trending',allowed_channels=['web','news'],use_llm=False)
    assert len(plan.actions)<=5
    rows=plan.to_channel_queries()
    assert len(rows['web'])<=2 and set(rows)<={'web','news'}
    assert any(row.get('source_family')=='bollywood_hungama' for row in rows['web'])
    assert plan.research_context['topics'] and plan.source_family_decisions
    assert not p.plan('Kavya Rao Bollywood news',entity='Kavya Rao',allowed_channels=[]).actions


def test_explicit_site_or_direct_url_is_not_replaced_by_registry_selector():
    p=SourcePlanningEngine(source_registry=registry({'bollywood_hungama':grant()}))
    plan=p.plan('Kavya Rao Bollywood site:publisher.example',entity='Kavya Rao',use_llm=False)
    assert not any(a.source_family for a in plan.actions)


def test_host_matching_is_exact_or_real_subdomain_not_suffix_spoofing():
    r=registry()
    assert r.match_url('https://www.bollywoodhungama.com/news')['id']=='bollywood_hungama'
    assert r.match_url('https://bollywoodhungama.com.evil.example/') is None
    assert r.match_url('https://evilbollywoodhungama.com/') is None
    assert r.match_url('https://user:pass@bollywoodhungama.com/') is None


def test_redirect_to_unapproved_source_is_blocked_before_next_request():
    from backend.infrastructure.acquisition.network.http import _ValidatingRedirectHandler
    from urllib.request import Request
    with source_body_scope(registry()), patch('backend.infrastructure.acquisition.network.http.is_safe_url') as safe:
        with pytest.raises(SourcePermissionError):
            _ValidatingRedirectHandler(4).redirect_request(Request('https://publisher.example/story'),None,302,'Found',{},
                                                        'https://www.bollywoodhungama.com/news/observed')
    safe.assert_not_called()


def test_topic_diversification_does_not_add_science_to_entertainment_or_unknown_name():
    from backend.services.research.source_diversity import diversify_search_plan
    rows=[{'channel':'web','query_id':str(i),'query_text':f'Kavya Rao film news {i}'} for i in range(8)]
    for target in ('Bollywood actor Kavya Rao','Kavya Rao'):
        result=diversify_search_plan(rows,target,'trending',8)
        assert len(result)<=8
        assert not any(r.get('source_family') in {'science_reporting','technology_reporting'} for r in result)


def test_registry_records_explicit_capability_depth_cost_and_unknown_availability():
    r=registry()
    assert len(definitions())==60
    data=r.describe('bollywood_hungama')
    assert data['capabilities']['DISCOVERY_ONLY']['status']=='UNVERIFIED'
    assert data['capabilities']['STRUCTURED_EVIDENCE']['runtime_availability']=='UNVERIFIED'
    assert data['request_cost']['monetary']=='UNKNOWN'
    assert data['local_runtime']=='UNVERIFIED'


@pytest.mark.parametrize('status,body,allowed',[(200,b'User-agent: *\nDisallow: /private',True),
    (403,b'',False),(404,b'',True),(200,b'User-agent: *\nDisallow: /',False)])
def test_robots_checks_are_bounded_cached_and_separate_from_permission(status,body,allowed):
    from types import SimpleNamespace
    fetch=Mock(return_value=SimpleNamespace(status_code=status,body=body))
    r=SourceRegistry(reviews={'global_voices':grant()},clock=lambda:NOW,robots_fetcher=fetch)
    url='https://globalvoices.org/2026/10/26/article/'
    assert r.assess('global_voices')['network_calls']==0
    fetch.assert_not_called()
    assert r.robots_decision(url)['eligible'] is allowed
    assert r.robots_decision(url)['eligible'] is allowed
    assert fetch.call_count==1
    assert fetch.call_args.kwargs['max_attempts']==1 and fetch.call_args.kwargs['max_bytes']==128_000
    if status==200 and b'/private' in body:
        assert not r.robots_decision('https://globalvoices.org/private/record')['eligible']


def test_observed_topic_refinement_replaces_only_pending_same_channel_action():
    p=SourcePlanningEngine(source_registry=registry({'bollywood_hungama':grant()}))
    plan=p.plan('Asha Vale',entity='Asha Vale',agent='trending',allowed_channels=['web','news'],use_llm=False)
    before=len(plan.actions)
    pending=[a.action_id for a in plan.actions if a.channel=='web']
    updates=p.refine_topics(plan,observed_titles=['Asha Vale Bollywood actor interview'],pending_action_ids=pending,domain='trending')
    assert updates and all(old.action_id in pending and old.channel==new.channel for old,new in updates)
    assert len(plan.actions)==before and plan.replan_count==1
    assert 'bollywood' in plan.research_context['topics']
    assert not p.refine_topics(plan,observed_titles=['Asha Vale cricket player'],pending_action_ids=pending)


def test_refinement_cannot_replace_submitted_actions_or_create_read_permission():
    p=SourcePlanningEngine(source_registry=registry({'bollywood_hungama':grant(('discovery',))}))
    plan=p.plan('Asha Vale',entity='Asha Vale',agent='trending',use_llm=False)
    assert not p.refine_topics(plan,observed_titles=['Asha Vale Bollywood actor interview'],pending_action_ids=[])
    assert not p.source_registry.body_decision('https://www.bollywoodhungama.com/news/article')['eligible']


def test_captured_language_licence_and_author_required_for_reusable_article():
    from bs4 import BeautifulSoup
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.research_models import EvidenceItem
    html='<html lang="mr"><head></head><body><article><h1>Article</h1><p>मूळ मराठी मजकूर.</p></article><footer><a rel="license" href="https://creativecommons.org/licenses/by/3.0/">Licence</a></footer></body></html>'
    page=extract_readable_page(BeautifulSoup(html,'html.parser'))
    assert page['language']=='mr' and page['licence_urls']==['https://creativecommons.org/licenses/by/3.0/']
    r=registry({'global_voices':grant()});url='https://globalvoices.org/2026/10/26/observed/'
    assert not r.excerpt_decision(url,page)['eligible']
    page['author']='Observed author'
    assert r.excerpt_decision(url,page)['eligible']
    item=EvidenceItem(id='captured',canonical_url=url,content=page.pop('text'),content_depth='PARTIAL_CONTENT',
                      metadata={'page_metadata':page,'read_success':True})
    pool=RawAcquisitionPool('language-control');pool.add_capture(item)
    saved=pool.export(include_text=True)['sources'][0]
    assert saved['page_metadata']['language']=='mr'
    assert saved['page_metadata']['licence_urls']==page['licence_urls']
    assert 'मूळ मराठी' in saved['readable_text']
    page['rights_exception_observed']=True
    assert not r.excerpt_decision(url,page)['eligible']


def test_pilot_allowlist_restricts_bodies_without_creating_a_permission_grant(monkeypatch):
    monkeypatch.setenv('AEGIS_SOURCE_ALLOWED_FAMILIES','bollywood_hungama')
    r=registry()
    assert not r.body_decision('https://publisher.example/article')['eligible']
    assert not r.body_decision('https://www.bollywoodhungama.com/news/article')['eligible']
    assert r.body_decision('https://news.google.com/rss/articles/observed')['status']=='DISCOVERY_ONLY'


@pytest.mark.parametrize('controller',['legacy','pipelined_v1'])
def test_unknown_name_is_refined_in_real_harvest_wiring_without_new_budget(monkeypatch,controller):
    """Synthetic routing replay, not fresh discovery or a real-person result.

    Repeated generic results describe one article, leaving a bounded opportunity
    for the refined source. Refinement does not promise an additional read after
    independent read-attempt caps are exhausted.
    """
    from dataclasses import replace
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    from backend.services.research.research_models import ResearchRequest
    from backend.services.agent_reach.channels import EvidenceFragment,RetrievalResult
    import backend.services.research.source_registry as registry_module
    import backend.services.agent_reach.source_planner as planner_module
    r=registry({'bollywood_hungama':grant()});p=SourcePlanningEngine(source_registry=r)
    monkeypatch.setattr(registry_module,'source_registry',r)
    monkeypatch.setattr(planner_module,'source_planning_engine',p)
    class ReplayService:
        def __init__(self):self.queries=[]
        def retrieve_many(self,channel_queries,**kwargs):
            fragments=[]
            for channel,rows in channel_queries.items():
                for row in rows:
                    self.queries.append(row['query_text'])
                    scoped='site:bollywoodhungama.com' in row['query_text']
                    # The same replay title/snippet is one observed article,
                    # rather than a new read attempt invented for each query.
                    url=('https://www.bollywoodhungama.com/news/observed-interview' if scoped else
                         'https://publisher.example/observed-interview-lead')
                    fragments.append(EvidenceFragment(platform=channel,url=url,title='Asha Vale Bollywood actor interview',
                        snippet='Reported interview lead',query_id=row['query_id'],raw_metadata={'query_class':row['query_class']}))
            return RetrievalResult(query='Asha Vale',domain='personal',fragments=fragments)
        def read(self,url,max_chars=12000):
            if 'bollywoodhungama.com' not in url:return {'status':'failed','failure_kind':'HTTP_FAILURE'}
            return {'status':'success','content':('Asha Vale said, "We will publish the complete interview tomorrow." '*12),
                'page_metadata':{'title':'Asha Vale interview','author':'Observed reporter',
                    'body_quality':{'body_kind':'ARTICLE_BODY'},'content_scope':'article'}}
    service=ReplayService();plan=p.plan('Asha Vale',entity='Asha Vale',agent='personal_watch',domain='personal',use_llm=False,
                                     allowed_channels=['web','news'])
    rows=[{'channel':c,**row,'source_plan_action_id':row['query_id']} for c,values in plan.to_channel_queries().items() for row in values]
    profile=replace(QUICK,max_queries=8,max_reads=3,host_spacing_seconds=0)
    result=HarvestingEngine(service).run('Asha Vale','personal',agent_name='personal_watch',profile=profile,controller=controller,
        query_plan=rows,source_plan=plan,request=ResearchRequest(target='Asha Vale',domain='personal'))
    assert any('site:bollywoodhungama.com' in q for q in service.queries)
    assert result.retrieval_trace['topic_refinement']
    assert len(service.queries)<=8 and result.read_telemetry['attempted']<=3
    assert any(item.content.startswith('Asha Vale said') for item in result.captures)


@pytest.mark.parametrize('controller', ['legacy', 'pipelined_v1'])
def test_policy_denied_leads_do_not_exhaust_reader_or_suppress_next_query(monkeypatch, controller):
    """Synthetic regression for the live pilot's pre-access read-slot loss."""
    from dataclasses import replace
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
    import backend.services.research.source_registry as registry_module
    r = registry({'govuk': grant()})
    monkeypatch.setattr(registry_module, 'source_registry', r)
    monkeypatch.setenv('AEGIS_SOURCE_ALLOWED_FAMILIES', 'govuk')
    monkeypatch.setenv('AEGIS_SEARCH_ADVISOR_ENABLED', 'false')

    class ReplayService:
        def __init__(self):
            self.reads, self.queries = [], []

        def retrieve_many(self, channel_queries, **kwargs):
            fragments = []
            for rows in channel_queries.values():
                for row in rows:
                    self.queries.append(row['query_text'])
                    urls = (['https://restricted.example/news/asha-'+str(i) for i in range(6)]
                            if row['query_text'] == 'Asha Vale statement' else
                            ['https://www.gov.uk/government/speeches/observed-asha-statement'])
                    fragments.extend(EvidenceFragment(platform='web', url=url, title='Asha Vale public statement',
                        snippet='Asha Vale said she would publish the statement.', query_id=row['query_id']) for url in urls)
            return RetrievalResult(query='Asha Vale', domain='personal', fragments=fragments)

        def read(self, url, max_chars=12000):
            self.reads.append(url)
            return {'status': 'success', 'content': 'Asha Vale said she would publish the full statement. '*20,
                    'page_metadata': {'body_quality': {'body_kind': 'ARTICLE_BODY'}, 'content_scope': 'article'}}

    service = ReplayService()
    rows = [{'channel': 'web', 'query_id': 'policy_q_'+str(i), 'query_text': query, 'query_class': 'general'}
            for i, query in enumerate(['Asha Vale statement', 'Asha Vale statement site:gov.uk'])]
    result = HarvestingEngine(service).run('Asha Vale', 'personal', agent_name='personal_watch',
        profile=replace(QUICK, max_queries=2, max_reads=1, concurrency=1, host_spacing_seconds=0),
        query_plan=rows, controller=controller)
    assert len(service.queries) == 2
    assert result.read_telemetry['attempted'] == 1
    assert len(service.reads) == 1 and 'gov.uk' in service.reads[0]
    assert len(result.captures) == 1
    assert result.metrics['unread_by_reason']['SOURCE_OUTSIDE_SERVER_ALLOWLIST'] == 6
    denied = [r for r in result.read_telemetry['candidate_selection_audit']
              if r.get('rejection_reason') == 'SOURCE_OUTSIDE_SERVER_ALLOWLIST']
    assert len(denied) == 6 and all(not r['eligible_for_read'] for r in denied)
