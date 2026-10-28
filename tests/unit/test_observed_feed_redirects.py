"""Observed feed targets remain discovery leads and retain wrapper provenance."""
import pytest
from backend.services.agent_reach.native.normalizer import NativeNormalizer


@pytest.mark.parametrize('locator,target', [
    ('https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fpublisher.example%2Farticle', 'https://publisher.example/article'),
    ('https://r.search.yahoo.com/x/RU=https%3A%2F%2Fpublisher.example%2Farticle/RK=2/', 'https://publisher.example/article'),
    ('https://bing.com.attacker.example/news/apiclick.aspx?url=https%3A%2F%2Fpublisher.example%2Farticle', None),
    ('https://www.bing.com/news/apiclick.aspx?url=javascript%3Aalert%281%29', None),
])
def test_only_known_wrappers_unwrap_observed_http_targets(locator, target):
    item, = NativeNormalizer().normalize_rss_entries([{'link': locator, 'title': 'Article', 'summary': 'Observed lead'}])
    assert item.url == (target or locator)
    assert item.content_depth == 'FEED_ENTRY_SUMMARY'
    assert item.raw_metadata['linked_article_retrieved'] is False
    if target:
        assert item.raw_metadata['discovery_url'] == locator
