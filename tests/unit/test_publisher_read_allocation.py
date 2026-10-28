"""Synthetic allocation controls; no live provider, generated source or quota usage."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.services.research.publisher_read_policy import PublisherReadPolicy, discovery_kind
from backend.services.research.candidate_selection import SelectionContext, score_candidate
from backend.services.research.harvesting import HarvestingEngine
from backend.services.research.research_models import EvidenceItem
from tests.unit.test_pipelined_acquisition import FakeWorld


def lead(path, title="", **metadata):
    return EvidenceItem(id="fixture_" + path.replace('/', '_'), canonical_url="https://publisher.example" + path,
                        title=title, metadata=metadata)


@pytest.mark.parametrize("cap,articles,initial,adaptive", [(8, 4, 2, 2), (5, 2, 2, 1), (3, 1, 2, 0)])
def test_reservations_stay_within_original_host_cap(cap, articles, initial, adaptive):
    p = PublisherReadPolicy(cap).snapshot()
    assert (p['article_reserve'], p['initial_discovery'], p['adaptive_reservation']) == (articles, initial, adaptive)
    assert articles + p['maximum_discovery'] == cap


def test_comments_do_not_replace_main_feed_or_erase_real_comments_article():
    assert discovery_kind(lead('/comments/feed/', 'Comments for Publisher'), True) == 'COMMENT_FEED'
    assert discovery_kind(lead('/feed/', 'Publisher feed'), True) == 'MAIN_FEED'
    assert discovery_kind(lead('/opinion/executive-comments-on-energy-storage/', 'Comments on energy storage')) == 'ARTICLE'
    assert PublisherReadPolicy(8).reason('publisher.example', 'COMMENT_FEED', False) == 'DEFERRED_COMMENT_FEED_FOR_ARTICLE_TASK'


def test_adaptive_discovery_follows_actual_article_feedback_only():
    p = PublisherReadPolicy(8)
    for _ in range(2):p.submit('publisher.example', 'HUB')
    assert p.reason('publisher.example', 'MAIN_FEED', True)
    p.observe('publisher.example', {'source_type':'SOURCE_INDEX','reason':'TEMPORAL_MISSING_TIMESTAMP'})
    assert p.unusable_articles['publisher.example'] == 0
    for _ in range(2):p.observe('publisher.example', {'source_type':'ARTICLE_BODY','reason':'TEMPORAL_STALE'})
    assert p.reason('publisher.example', 'MAIN_FEED', True) is None
    assert p.priority('publisher.example','MAIN_FEED',1) < p.priority('publisher.example','ARTICLE',1)
    p.submit('publisher.example','MAIN_FEED');p.submit('publisher.example','SEARCH')
    assert p.reason('publisher.example','SITEMAP',False) == 'DISCOVERY_SHARE_RESERVED_FOR_ARTICLES'
    assert p.reason('publisher.example','ARTICLE',True) is None


def test_no_article_supply_can_release_adaptive_discovery_without_inventing_yield():
    p = PublisherReadPolicy(8)
    p.submit('p','HUB');p.submit('p','MAIN_FEED')
    assert p.reason('p','SEARCH',False) is None
    assert p.reason('p','SEARCH',False,host_busy=True)
    assert p.unusable_articles['p'] == 0


def test_off_subject_actual_articles_release_discovery_without_counting_indexes():
    p=PublisherReadPolicy(8)
    p.submit('p','HUB');p.submit('p','MAIN_FEED')
    for _ in range(2):p.observe('p',{'source_type':'ARTICLE_BODY','reason':'Insufficient entity match confidence'})
    assert p.reason('p','SEARCH',True) is None
    p.observe('p',{'source_type':'ARTICLE_BODY','usable_passage':True})
    assert p.unusable_articles['p']==0


def test_topic_order_does_not_outvote_complete_subject_coverage():
    ctx = SelectionContext('orbital energy storage','trending')
    a = lead('/orbital-energy-storage-research-results/', 'Orbital energy storage research results')
    b = lead('/orbital-storage-energy-research-results/', 'Storage of orbital energy: research results')
    for item in (a,b):item.metadata['harvest_temporal_priority']=1
    scores=[score_candidate(item,ctx,is_wrapper=False,is_index=False)[0] for item in (a,b)]
    assert scores[0] == scores[1]


class PublisherWorld(FakeWorld):
    def __init__(self, block_feed=False, missing_body_date=False):
        super().__init__([], {})
        self.block_feed, self.missing_body_date = block_feed, missing_body_date
        self.fresh=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        self.old=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
        self.visited=[]

    def read(self,url,max_chars=12000):
        self.visited.append(url)
        base='https://publisher.example'
        def link(path,title,kind='ARTICLE_LEAD',date=''):
            return {'url':base+path,'text':title,'kind':kind,'published':date}
        if url==base+'/':
            page={'body_kind':'UNCLASSIFIED_PAGE','discovery_links':[
                link('/comments/feed/','Comments for Publisher','FEED_INDEX'),
                link('/feed/','Publisher main feed','FEED_INDEX')],
                'observed_links':[link('/search?q=orbital','Orbital energy storage search','FEED_INDEX')]}
        elif url==base+'/feed/':
            if self.block_feed:return {'status':'failed','error':'HTTP 403','failure_kind':'ACCESS_DENIED'}
            page={'content_scope':'FEED_INDEX','observed_links':[
                link('/orbital-energy-storage-old-research-a/','Orbital energy storage old research A',date=self.old),
                link('/orbital-energy-storage-old-research-b/','Orbital energy storage old research B',date=self.old)]}
        elif url.startswith(base+'/search?'):
            page={'content_scope':'PUBLIC_DISCOVERY_INDEX','observed_links':[
                link('/search/feed/?q=orbital','Orbital energy storage results feed','FEED_INDEX')]}
        elif url.startswith(base+'/search/feed/'):
            page={'content_scope':'FEED_INDEX','observed_links':[
                link('/storage-of-orbital-energy-new-research/','Storage of orbital energy: new research',date=self.fresh)]}
        else:
            published=self.fresh if url.endswith('-new-research/') else self.old
            page={'body_kind':'ARTICLE_BODY','title':'Orbital energy storage research'}
            if not self.missing_body_date:page['declared_structured_data']=[{'@type':'NewsArticle','datePublished':published}]
        text=('Researchers reported that orbital energy storage reduced energy losses by 12 percent. '
              'The study describes orbital energy storage performance using measured laboratory data. ')*3
        return {'status':'success','markdown':text,'page_metadata':page,
                'transport':{'endpoint':url,'redirect_chain':[url],'http_status':200}}


@pytest.mark.parametrize('blocked',[False,True])
def test_feed_article_chain_survives_inside_eight_host_reads(blocked):
    world=PublisherWorld(block_feed=blocked)
    result=HarvestingEngine(world).run(target='orbital energy storage',domain='trending',profile='DEEP',
        controller='pipelined_v1',initial_candidates=[lead('/', 'Publisher', publisher_basis='OBSERVED_PUBLIC_LINK')])
    assert len(world.visited) <= 8
    assert not any('/comments/' in url for url in world.visited)
    assert any('/storage-of-orbital-energy-new-research/' in c.canonical_url for c in result.captures)
    assert any(r['usable_passage'] for r in result.metrics['acquisition_controller']['capture_feedback'])
    assert len(result.metrics['acquisition_controller']['publisher_yield_memory']) == 1


def test_feed_publication_hint_does_not_qualify_an_undated_captured_body():
    world=PublisherWorld(missing_body_date=True)
    result=HarvestingEngine(world).run(target='orbital energy storage',domain='trending',profile='DEEP',
        controller='pipelined_v1',initial_candidates=[lead('/', 'Publisher',publisher_basis='OBSERVED_PUBLIC_LINK')])
    feedback=result.metrics['acquisition_controller']['capture_feedback']
    assert feedback and not any(r['usable_passage'] for r in feedback)
    assert any(str(r['reason']).startswith('TEMPORAL_MISSING_TIMESTAMP') for r in feedback if r['source_type']=='ARTICLE_BODY')


@pytest.mark.parametrize('missing_date',[False,True])
def test_later_feed_alias_updates_routing_but_captured_date_still_decides(missing_date):
    class AliasWorld(PublisherWorld):
        def read(self,url,max_chars=12000):
            result=super().read(url,max_chars=max_chars)
            article='https://publisher.example/storage-of-orbital-energy-new-research/'
            if url=='https://publisher.example/':
                result['page_metadata']['observed_links'].append({'url':article,
                    'text':'Orbital energy storage research','published':self.old})
            elif url=='https://publisher.example/feed/':
                result['page_metadata']['observed_links']=[{'url':article,
                    'text':'Storage of orbital energy: research','published':self.fresh}]
            return result
    world=AliasWorld(missing_body_date=missing_date)
    result=HarvestingEngine(world).run(target='orbital energy storage',domain='trending',profile='DEEP',
        controller='pipelined_v1',initial_candidates=[lead('/', 'Publisher',publisher_basis='OBSERVED_PUBLIC_LINK')])
    captured=next(c for c in result.captures if c.canonical_url.endswith('-new-research/'))
    assert captured.metadata['temporal_routing_basis']=='BEST_OBSERVED_DISCOVERY_ALIAS_NOT_BODY_VERIFICATION'
    feedback=next(r for r in result.metrics['acquisition_controller']['capture_feedback'] if r['source_id']==captured.id)
    assert feedback['usable_passage'] is (not missing_date)
