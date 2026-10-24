"""Synthetic controls for observed search drift; never live provider fixtures."""
from unittest.mock import patch

from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.research.entity_resolver import EntityResolver, TargetEntity


def response(html):
    return BoundedHTTPResponse(body=html.encode(), endpoint="https://www.bing.com/search",
        status_code=200, content_type="text/html", headers={"Content-Type": "text/html"}, latency_ms=1, attempts=1)


def test_resolution_search_tries_secondary_when_nonempty_primary_is_unrelated():
    html = '<li class="b_algo"><h2><a href="https://shop.example/">ExampleCo counterfeit products advice</a></h2></li>'
    matching = EvidenceFragment(platform="web", title="ExampleCo counterfeit kits seized by customs",
                                url="https://publisher.example/seizure")
    router = NativeRouter()
    with patch("backend.infrastructure.acquisition.routing.router.fetch_public_http", return_value=response(html)), \
         patch.object(router, "_execute_yahoo_search", return_value=[matching]) as secondary:
        rows = router._execute_web_search("ExampleCo counterfeit kits seized by customs", limit=3,
                                          query_class="publisher_url_resolution")
    secondary.assert_called_once()
    assert rows[0].url == matching.url


def test_search_title_and_snippet_keep_inline_word_boundaries():
    html = '<li class="b_algo"><h2><a href="https://publisher.example/a"><b>ExampleCo</b> counterfeit kits seized</a></h2><div class="b_caption"><p><b>Customs</b> seized kits.</p></div></li>'
    router = NativeRouter()
    with patch("backend.infrastructure.acquisition.routing.router.fetch_public_http", return_value=response(html)):
        rows = router._execute_web_search("ExampleCo counterfeit kits seized", query_class="publisher_url_resolution")
    assert rows[0].title == "ExampleCo counterfeit kits seized"
    assert rows[0].snippet == "Customs seized kits."


def test_matching_primary_does_not_add_secondary_call():
    html = '<li class="b_algo"><h2><a href="https://publisher.example/a">ExampleCo counterfeit kits seized</a></h2></li>'
    router = NativeRouter()
    with patch("backend.infrastructure.acquisition.routing.router.fetch_public_http", return_value=response(html)), \
         patch.object(router, "_execute_yahoo_search") as secondary:
        assert router._execute_web_search("ExampleCo counterfeit kits seized", query_class="publisher_url_resolution")
    secondary.assert_not_called()


def test_topic_variants_are_not_given_name_surname_matches():
    target = EntityResolver.resolve_entity("quantum computing", domain="trending")
    score, signals, rejection = EntityResolver.evaluate_entity_match("New quantum computers tested in laboratory", target)
    assert score >= 0.35 and rejection is None
    assert not any("name" in signal or "surname" in signal for signal in signals)
    score, _, rejection = EntityResolver.evaluate_entity_match("Quantum data storage company opens office", target)
    assert score < 0.35 and rejection


def test_person_given_name_alone_stays_rejected():
    target = TargetEntity(canonical_name="Ada Example", entity_type="person")
    score, _, rejection = EntityResolver.evaluate_entity_match("Ada publishes travel photos", target)
    assert score < 0.35 and rejection


def test_scam_education_is_a_report_not_a_counterfeit_listing():
    from backend.agents.brandshield.assessment import synthesize_brand_threats
    source = {"evidence_id": "advice", "url": "https://publisher.example/advice", "platform": "Web",
        "title": "How ExampleCo scams target families online", "content_depth": "PARTIAL_CONTENT",
        "content": "Fake webstores may offer counterfeit ExampleCo sets at very low prices. Families should inspect seller details before buying.",
        "snippet": ""}
    original = source["content"]
    result = synthesize_brand_threats({"brand": "ExampleCo"}, [source])
    assert result["threats"] and len(result["threats"]) == 1
    report = result["threats"][0]
    assert report["type"] == "SAFETY_ADVISORY" and report["is_threat"] is False
    assert report["actor_url"] is None and report["confidence"] is None
    assert report["description"] == report["summary"]
    assert result["counterfeits"] == []
    assert report["evidence_ids"] == ["advice"] and source["content"] == original
    from backend.services.report_builder import ReportBuilder
    unified = ReportBuilder.from_brandshield_result(query="ExampleCo", brand_data={**result, "evidence": [source]})
    assert "specific suspected listing" in " ".join(unified.next_steps)


def test_advice_context_does_not_erase_an_enforcement_report():
    from backend.agents.brandshield.assessment import synthesize_brand_threats
    source = {"evidence_id": "incident", "url": "https://publisher.example/advice", "platform": "Web",
        "title": "How to avoid ExampleCo counterfeit scams", "content_depth": "PARTIAL_CONTENT",
        "content": "Customs officers seized counterfeit ExampleCo shoes, according to the enforcement report.", "snippet": ""}
    result = synthesize_brand_threats({"brand": "ExampleCo"}, [source])
    assert result["threats"] and all(t["source_relation"] == "REPORTS_ENFORCEMENT" for t in result["threats"])
