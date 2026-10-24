"""Offline generated extraction controls, not live acquisition or truth labels."""
import hashlib
import json

import pytest
from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.discovery_document import discovery_document
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details, extract_readable_page
from backend.services.research.body_context import reconcile_captured_context
from backend.services.research.publisher_links import observed_publisher_articles
from backend.services.research.research_models import EvidenceItem


def test_article_body_container_keeps_negation_and_table_context_not_navigation():
    body = ('<nav><a href="/shop">Shop all</a> Privacy policy</nav><main><div class="article-body">'
            '<h1>Cedar Materials quarterly results</h1><p>Cedar Materials did <strong>not</strong> report an annual loss. '
            'The unaudited quarterly statement instead reported lower operating profit in local currency.</p>'
            '<p>Management said the comparison excludes the discontinued division and is not a forecast for the coming year.</p>'
            '<table><tr><th>Period</th><th>USD million</th></tr><tr><td>Q2</td><td>120</td></tr></table></div></main>')
    result = extract_readable_page(BeautifulSoup(body, "html.parser"))
    assert result["content_scope"] == "publisher_article_container"
    assert "did not report" in result["text"] and "not a forecast" in result["text"]
    assert "USD million" in result["text"] and "Shop all" not in result["text"]
    assert result["body_quality"]["body_kind"] == "ARTICLE_BODY"
    assert result["body_quality"]["evidence_qualified"] is False
    assert result["readable_text_sha256"] == hashlib.sha256(result["text"].encode()).hexdigest()


def test_jsonld_explicit_body_is_observed_not_description_and_preserves_inline_context():
    actual = ('Cedar Materials did <strong>not</strong> announce a recall. The company reported that its public investigation '
              'is ongoing and that the allegation has not been established. ' * 5)
    source = {"@graph": [{"@type": "WebPage", "name": "Public reporting"},
                          {"@type": ["NewsArticle", "Article"], "headline": "Cedar Materials statement",
                           "datePublished": "2026-10-19T10:00:00Z", "articleBody": actual,
                           "publisher": {"name": "Example Publisher"}}]}
    soup = BeautifulSoup('<script type="application/ld+json">' + json.dumps(source) + '</script><main>Loading report</main>', "html.parser")
    result = extract_readable_page(soup)
    assert result["selection_method"] == "PUBLISHER_JSONLD_ARTICLE_BODY"
    assert "did not announce" in result["text"]
    page = extract_observed_page_details(soup, "https://publisher.example/story")
    assert page["published"] == "2026-10-19T10:00:00Z"
    assert page["publication_time_source"] == "JSONLD:datePublished"
    assert page["title"] == "Cedar Materials statement"
    description = BeautifulSoup('<script type="application/ld+json">' + json.dumps({"@type": "NewsArticle", "description": actual}) + '</script><main>Loading</main>', "html.parser")
    assert extract_readable_page(description)["text"] == "Loading"


def test_multiple_article_cards_are_not_misclassified_as_one_acquired_article():
    soup = BeautifulSoup('<main><article><a href="/a">Cedar revenue report</a></article>'
                         '<article><a href="/b">A different report</a></article></main>', "html.parser")
    result = extract_readable_page(soup)
    assert result["content_scope"] == "main"
    assert result["body_quality"]["body_kind"] == "UNCLASSIFIED_PAGE"


def test_conflicting_article_dates_do_not_become_verified_freshness():
    soup = BeautifulSoup('<meta property="article:published_time" content="2026-10-19">'
                         '<time itemprop="datePublished" datetime="2026-10-18"></time><article>Captured report</article>', "html.parser")
    page = extract_observed_page_details(soup, "https://publisher.example/story")
    assert page["publication_metadata_conflict"]
    item = EvidenceItem(id="capture", content="Captured report text", published_at="2026-10-19",
                        metadata={"read_success": True, "page_metadata": page})
    reconcile_captured_context(item)
    assert item.published_at == ""
    assert item.metadata["discovery_published_at"] == "2026-10-19"
    assert item.metadata["publication_time_basis"] == "CONFLICTING_CAPTURED_DECLARATIONS"


def test_news_sitemap_date_and_publisher_are_separate_from_lastmod():
    xml = '''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
      xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"><url><loc>https://publisher.example/cedar-results</loc>
      <lastmod>2026-10-20</lastmod><news:news><news:publication><news:name>Example News</news:name></news:publication>
      <news:publication_date>2026-10-19</news:publication_date><news:title>Cedar Materials results</news:title></news:news></url></urlset>'''
    page = discovery_document(xml, "https://publisher.example/news.xml")
    row = page["observed_links"][0]
    assert row["text"] == "Cedar Materials results" and row["publisher"] == "Example News"
    assert row["published"] == "2026-10-19" and row["publication_time_source"] == "NEWS_SITEMAP:publication_date"
    assert row["modified"] == "2026-10-20" and row["source_type"] == "DISCOVERY_LEAD"


def test_sitemap_indexes_continue_as_indexes_not_articles():
    page = discovery_document('<sitemapindex><sitemap><loc>/news-sitemap.xml</loc><lastmod>2026-10-20</lastmod></sitemap></sitemapindex>', "https://publisher.example/sitemap.xml")
    row = page["observed_links"][0]
    assert row["url"] == "https://publisher.example/news-sitemap.xml"
    assert row["kind"] == "FEED_INDEX" and row["published"] == ""
    parent = EvidenceItem(id="index", canonical_url="https://publisher.example/sitemap.xml",
                          metadata={"read_success": True, "page_metadata": page})
    children = observed_publisher_articles(parent, "financial", [], "Cedar Materials", max_children=12, max_hops=3)
    assert children[0].metadata["source_type"] == "SOURCE_INDEX" and not children[0].content


def test_atom_summary_publication_and_explicit_base_survive_without_becoming_body():
    xml = '''<feed xmlns="http://www.w3.org/2005/Atom" xml:base="https://publisher.example/news/"><title>Publisher newsroom</title>
      <entry><title>Cedar Materials</title><link rel="self" href="/api/entry"/><link rel="alternate" href="cedar"/>
      <published>2026-10-18</published><updated>2026-10-20</updated><summary>&lt;p&gt;Actual feed summary, not an article body.&lt;/p&gt;</summary></entry></feed>'''
    page = discovery_document(xml, "https://publisher.example/feed")
    row = page["observed_links"][0]
    assert row["url"] == "https://publisher.example/news/cedar"
    assert row["published"] == "2026-10-18" and row["modified"] == "2026-10-20"
    assert row["summary"] == "Actual feed summary, not an article body."
    assert row["source_type"] == "FEED_ENTRY" and row["feed_identity"] == "Publisher newsroom"


@pytest.mark.parametrize("value", ["javascript:alert(1)", "https://user:password@publisher.example/report", ""])
def test_xml_rejects_non_public_locator_shapes_and_missing_urls(value):
    page = discovery_document('<rss><channel><item><title>Report</title><link>' + value + '</link></item></channel></rss>', "https://publisher.example/feed")
    assert page["observed_links"] == []


def test_archive_harvesting_increases_observed_capacity_but_never_guesses_slugs():
    links = ''.join('<a href="/reports/cedar-' + str(n) + '">Cedar Materials public update ' + str(n) + '</a>' for n in range(24))
    soup = BeautifulSoup('<nav><a href="/archive">News archive</a></nav><link rel="sitemap" href="/actual-sitemap.xml"><main>' + links + '</main>', "html.parser")
    page = extract_observed_page_details(soup, "https://publisher.example/archive/2026")
    assert len(page["observed_links"]) == 24
    parent = EvidenceItem(id="archive", canonical_url="https://publisher.example/archive/2026",
                          query_id="query-1", metadata={"read_success": True, "page_metadata": page})
    children = observed_publisher_articles(parent, "brand", [], "Cedar Materials", max_children=12, max_hops=3)
    assert len(children) == 12 and all('/reports/cedar-' in row.canonical_url for row in children)
    assert all(not row.content and row.query_id == "query-1" for row in children)
    assert all(row.metadata["source_type"] == "DISCOVERY_LEAD" for row in children)
