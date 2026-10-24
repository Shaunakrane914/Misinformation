"""Page observations are bounded context, not publisher-independent proof."""

from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.page_extraction import (
    extract_observed_page_details,
)


def test_article_observations_are_bounded_and_explicitly_unverified():
    html = """<html><head><script type="application/ld+json">
    {"@type":"NewsArticle","headline":"Publisher says it happened",
     "datePublished":"2026-10-10","author":{"name":"Editorial"}}
    </script></head><body><nav><a href="https://nav.example/not-evidence">Nav</a></nav>
    <article><a href="https://official.example/statement#section">Official statement</a>
    <a href="javascript:alert(1)">Bad link</a>
    <a href="https://user:password@bad.example/">Credential link</a>
    <a href="/related">Related page</a>
    <table><tr><th>Year</th><th>Amount</th></tr><tr><td>2026</td><td>7</td></tr></table>
    <blockquote>Quoted source passage</blockquote><figure><figcaption>Observed caption</figcaption></figure>
    <p>Correction: an earlier number was inaccurate.</p></article></body></html>"""
    details = extract_observed_page_details(
        BeautifulSoup(html, "html.parser"), "https://publisher.example/story"
    )
    assert details["content_scope"] == "article"
    assert details["observed_links"] == [
        {"url": "https://official.example/statement", "text": "Official statement",
         "external_domain": True, "verification": "UNVERIFIED_PAGE_LINK"},
        {"url": "https://publisher.example/related", "text": "Related page",
         "external_domain": False, "verification": "UNVERIFIED_PAGE_LINK"},
    ]
    assert details["tables"] == [[ ["Year", "Amount"], ["2026", "7"] ]]
    assert details["quotations"] == ["Quoted source passage"]
    assert details["media_captions"] == ["Observed caption"]
    assert details["potential_corrections"] == ["Correction: an earlier number was inaccurate."]
    assert details["declared_structured_data"] == [{
        "@type": "NewsArticle", "headline": "Publisher says it happened",
        "datePublished": "2026-10-10", "author_name": "Editorial",
        "declaration_basis": "PUBLISHER_JSONLD_UNVERIFIED",
    }]


def test_page_observation_limits_and_malformed_json_ld():
    html = "<html><head><script type='application/ld+json'>{invalid}</script></head><body><main>"
    html += "".join(f"<a href='https://example.org/{i}'>{i}</a>" for i in range(160))
    html += "<table>" + "".join("<tr><td>Cell</td></tr>" for _ in range(15)) + "</table>"
    html += "</main><nav>" + "".join(f"<a href='/archive/{i}'>News archive {i}</a>" for i in range(24)) + "</nav></body></html>"
    details = extract_observed_page_details(
        BeautifulSoup(html, "html.parser"), "https://example.com/page"
    )
    assert details["content_scope"] == "main"
    assert len(details["observed_links"]) == 120
    assert len(details["discovery_links"]) == 16
    assert len(details["tables"][0]) == 10
    assert details["declared_structured_data"] == []
