"""Offline controls for focused discovery and preservation of all candidates."""
from types import SimpleNamespace
from unittest.mock import Mock
import time

from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.source_planner import SourcePlanningEngine


def test_personal_news_slots_are_abuse_specific_not_generic():
    plan = SourcePlanningEngine().plan("Public Person", entity="Public Person", domain="personal", agent="personal_watch", use_llm=False)
    news = plan.to_channel_queries()["news"]
    assert len(news) <= 3
    assert news[0]["query_text"] == '"Public Person" deepfake'
    assert news[1]["query_text"] == '"Public Person" impersonation'


def test_quoted_name_mismatch_uses_existing_secondary_search(monkeypatch):
    from backend.infrastructure.acquisition.routing import router as module
    response = SimpleNamespace(endpoint="https://www.bing.com/search", status_code=200, headers={}, body=b"html")
    monkeypatch.setattr(module, "fetch_public_http", Mock(return_value=response))
    monkeypatch.setattr(module, "decode_bounded_http_body", lambda response: b'<li class="b_algo"><h2><a href="https://sam.gov">SAM government portal</a></h2></li>')
    router = module.NativeRouter.__new__(module.NativeRouter)
    found = EvidenceFragment(platform="Web", title="Sam Altman deepfake report", url="https://publisher.example/report", content="", snippet="Sam Altman was discussed.")
    router._execute_yahoo_search = Mock(return_value=[found])
    assert router._execute_web_search('"Sam Altman" deepfake') == [found]
    router._execute_yahoo_search.assert_called_once()


def test_specialist_read_priority_does_not_erase_background(monkeypatch):
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_models import ResearchRequest, EvidenceItem
    from backend.services.research.research_budget import ResearchBudget
    background = EvidenceItem(id="bg", canonical_url="https://example.org/news", title="Person speaks about products")
    report = EvidenceItem(id="report", canonical_url="https://publisher.example/report", title="Public Person deepfake report")
    ranked = RankedEvidence([background, report], [background, report], {}, [])
    reader = Mock(return_value=([], {"attempted": 1}))
    from backend.application.research import reading
    monkeypatch.setattr(reading.deep_reader, "deep_read", reader)
    DeepReadingStage().run(ResearchRequest("Public Person", domain="personal"), ResearchBudget(), ranked, time.time(), 20)
    assert reader.call_args.args[0] == [report, background]
    assert ranked.ranked == [background, report]
