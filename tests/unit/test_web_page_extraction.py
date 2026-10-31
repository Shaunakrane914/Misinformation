"""Page observations are bounded context, not publisher-independent proof."""

from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.page_extraction import (
    extract_observed_page_details,
)


def test_single_wordpress_document_uses_observed_entry_body():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    prose = '<p>The council announced new eligibility rules, but no election result has been verified.</p>'
    page = extract_readable_page(BeautifulSoup('<h1>Observed report</h1><main><div class="hentry">'
        '<div class="entry">' + prose * 3 + '</div></div><aside>Related stories</aside></main>', 'html.parser'))
    assert page['body_quality']['body_kind'] == 'ARTICLE_BODY'
    assert page['content_scope'] == 'publisher_article_container'
    assert 'no election result has been verified' in page['text'] and 'Related stories' not in page['text']


def test_wordpress_archive_does_not_select_one_story_as_whole_page():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    card = '<div class="hentry"><div class="entry"><p>First reported story.</p><p>Further context.</p></div></div>'
    page = extract_readable_page(BeautifulSoup('<h1>Archive</h1><main>' + card * 2 + '</main>', 'html.parser'))
    assert page['content_scope'] == 'main'
    assert page['body_quality']['body_kind'] != 'ARTICLE_BODY'


def test_generic_entry_class_without_document_marker_is_not_article_proof():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    page = extract_readable_page(BeautifulSoup('<h1>Index</h1><main><div class="entry">'
        '<p>First navigation group.</p><p>Second navigation group.</p></div></main>', 'html.parser'))
    assert page['content_scope'] == 'main'


def test_drupal_body_excludes_one_paragraph_boilerplate_and_nested_contact():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    prose = '<p>The agency filed a complaint alleging deceptive advertising; the allegations remain unproven.</p>'
    html = '<main><article><h1>Agency case</h1><div class="field--name-body">' + prose * 3 + '</div>'
    html += '<article>Press contact</article></article><div class="field--name-body"><p>Subscribe.</p></div></main>'
    page = extract_readable_page(BeautifulSoup(html, 'html.parser'))
    assert page['body_quality']['body_kind'] == 'ARTICLE_BODY'
    assert 'allegations remain unproven' in page['text']
    assert 'Press contact' not in page['text'] and 'Subscribe' not in page['text']


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
    from backend.infrastructure.acquisition.adapters.web.page_extraction import MAX_OBSERVED_LINKS
    assert len(details["observed_links"]) == min(160, MAX_OBSERVED_LINKS)
    assert len(details["discovery_links"]) == 16
    assert len(details["tables"][0]) == 10
    assert details["declared_structured_data"] == []
def test_image_link_does_not_erase_later_observed_headline():
    from bs4 import BeautifulSoup
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details
    soup = BeautifulSoup('<main><a href="/research-recycling-process-enters-production/"><img src="/photo.png"></a>'
        '<h2><a href="/research-recycling-process-enters-production/">Researchers report a new recycling process</a></h2>'
        '<a href="/research-recycling-process-enters-production/">Another observed label</a></main>', 'html.parser')
    details = extract_observed_page_details(soup, 'https://publisher.example/search?q=recycling')
    links = [r for r in details['observed_links'] if '/research-recycling-process-' in r['url']]
    assert len(links) == 1
    assert links[0]['text'] == 'Researchers report a new recycling process'
    assert links[0]['verification'] == 'UNVERIFIED_PAGE_LINK'


def test_footer_rights_notice_survives_as_permission_observation_after_body_cleanup():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
    prose = ('The agency reported a recall affecting the named product and described the specific hazard. '
             'Consumers should review the issuing source for model numbers and the remedy. '
             'This synthetic article body is retained exactly for an offline extraction control.')
    html = ('<html><body><article><h1>Observed recall statement</h1><p>' + prose + '</p></article>'
            '<footer><p>Third-party content: All rights reserved.</p></footer></body></html>')
    page = extract_readable_page(BeautifulSoup(html, 'html.parser'))
    assert prose in page['text']
    assert 'All rights reserved' not in page['text']
    assert 'All rights reserved' in page['raw_text']
    assert page['rights_exception_observed'] is True
