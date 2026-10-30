"""A real publisher read failed on mixed naive/aware publication declarations."""
from bs4 import BeautifulSoup
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details, extract_readable_page


def test_mixed_timezone_declarations_keep_conflict_and_readable_article():
    html = ('<meta property="article:published_time" content="2018-12-03T12:00:00-05:00">'
            '<script type="application/ld+json">{"@type":"NewsArticle",'
            '"datePublished":"2018-12-03T12:00:00"}</script>'
            '<article><p>The chief executive discussed the announced factory changes in a reported interview.</p>'
            '<p>The published report preserves the statement and its surrounding business context for readers.</p></article>')
    soup = BeautifulSoup(html, 'html.parser')
    page = extract_observed_page_details(soup, 'https://publisher.example/story')
    assert page['publication_metadata_conflict'] is True
    assert 'published' not in page
    assert len(page['publication_observations']) == 2
    assert extract_readable_page(soup)['body_quality']['body_kind'] == 'ARTICLE_BODY'


def test_equivalent_aware_declarations_still_resolve_to_observed_value():
    html = ('<meta property="article:published_time" content="2018-12-03T12:00:00-05:00">'
            '<meta name="datePublished" content="2018-12-03T17:00:00Z">')
    page = extract_observed_page_details(BeautifulSoup(html, 'html.parser'), 'https://publisher.example/story')
    assert page['published'] == '2018-12-03T12:00:00-05:00'
    assert not page.get('publication_metadata_conflict')
