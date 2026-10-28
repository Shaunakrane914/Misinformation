"""No network: ported cache behavior preserves denial, DNS and quota boundaries."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.infrastructure.acquisition.adapters.social import reddit
from backend.infrastructure.acquisition.network import http
from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget, reserve_public_request
from backend.infrastructure.acquisition.security import url_validator
from backend.infrastructure.acquisition.routing.social_handlers import SocialChannelHandlers


@pytest.fixture
def cache(monkeypatch):
    monkeypatch.setenv('AEGIS_REDDIT_RSS_ENABLED', 'true')
    data = {}
    return data, {'cache_get':data.get, 'cache_set':data.__setitem__}


def response(body=b'<rss version="2.0"><channel></channel></rss>'):
    return http.BoundedHTTPResponse(body=body, endpoint='https://www.reddit.com/r/testing/.rss',
        status_code=200, content_type='application/xml', headers={}, latency_ms=1, attempts=1)


def test_successful_empty_rss_cache_consumes_no_second_http_admission(monkeypatch, cache):
    calls=[]
    def fetch(url, **kwargs):
        reserve_public_request(url)
        calls.append(kwargs)
        return response()
    monkeypatch.setattr(reddit, 'fetch_public_http', fetch)
    budget=PublicRequestBudget(total=1)
    with public_request_budget(budget):
        assert reddit.fetch_reddit_subreddit_rss('testing', **cache[1]) == []
        assert reddit.fetch_reddit_subreddit_rss('testing', **cache[1]) == []
    assert len(calls)==1 and budget.snapshot()['native_http_admissions']==1
    assert calls[0]['max_bytes']==1_000_000 and calls[0]['max_attempts']==1
    assert calls[0]['max_redirects']==0
    assert 0 < calls[0]['timeout'] <= 5


@pytest.mark.parametrize('status',[401,403,429])
def test_denied_rss_remains_a_typed_failure_in_cache_without_retry(monkeypatch, cache, status):
    fetch=Mock(side_effect=http.ProviderHTTPError('Denied', endpoint='',status_code=status,
                                                 retry_after_seconds=60,network_observed=True))
    monkeypatch.setattr(reddit, 'fetch_public_http', fetch)
    for index in range(2):
        with pytest.raises(http.ProviderHTTPError) as observed:
            reddit.fetch_reddit_subreddit_rss('testing', **cache[1])
        assert observed.value.status_code==status
        assert observed.value.network_observed is (index==0)
    assert fetch.call_count==1


def test_200_denial_page_is_not_cached_as_empty_success(monkeypatch, cache):
    monkeypatch.setattr(reddit,'fetch_public_http',lambda *a,**k:response(b'<html><h1>Access denied</h1></html>'))
    with pytest.raises(http.ProviderHTTPError) as observed:
        reddit.fetch_reddit_subreddit_rss('testing', **cache[1])
    assert observed.value.status_code==403


def test_rss_denial_does_not_activate_another_social_reader():
    router=SimpleNamespace(_fetch_reddit_subreddit_rss=Mock(side_effect=http.ProviderHTTPError(
        'Denied',endpoint='',status_code=403)),use_arctic_shift=True,
        _fetch_arctic_shift_search=Mock())
    source=SimpleNamespace(source_type='subreddit',subreddit='testing')
    with pytest.raises(http.ProviderHTTPError):
        SocialChannelHandlers(router)._fetch_direct_reddit(source,2,'id','general','r/testing')
    router._fetch_arctic_shift_search.assert_not_called()


def test_invalid_subreddit_is_rejected_before_network(monkeypatch, cache):
    fetch=Mock();monkeypatch.setattr(reddit,'fetch_public_http',fetch)
    assert reddit.fetch_reddit_subreddit_rss('../../private', **cache[1])==[]
    fetch.assert_not_called()


def test_dns_capacity_denial_cannot_open_a_socket(monkeypatch):
    monkeypatch.setattr(url_validator,'_DNS_SLOTS',threading.BoundedSemaphore(0))
    sock=Mock();monkeypatch.setattr('socket.socket',sock)
    with pytest.raises(url_validator.DNSResolutionError) as observed:
        http._connect_public_socket(('public.example',443),timeout=.02)
    assert observed.value.failure_kind=='DNS_CAPACITY'
    sock.assert_not_called()


@pytest.mark.parametrize('status',[401,403,429])
def test_reader_denial_does_not_activate_firecrawl_or_jina(monkeypatch,status):
    from backend.infrastructure.acquisition.adapters.web import jina
    monkeypatch.setattr(jina,'is_safe_url',lambda url:(True,''))
    alternative=Mock();monkeypatch.setattr(jina,'read_article_via_jina',alternative)
    native=SimpleNamespace(execute_web_read=Mock(side_effect=http.ProviderHTTPError(
        'Denied',endpoint='',status_code=status,network_observed=True)))
    paid=Mock();paid.is_configured.return_value=True
    result=jina.execute_web_read('https://publisher.example/story',executor=native,firecrawl_adapter=paid)
    assert result['transport']['http_status']==status and result['status']=='failed'
    alternative.assert_not_called();paid.scrape_article.assert_not_called()
