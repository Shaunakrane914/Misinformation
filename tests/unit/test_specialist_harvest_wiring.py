"""Offline wiring controls: synthetic responses do not prove live recall."""
from dataclasses import replace
from collections import Counter
from unittest.mock import patch

import pytest

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
from backend.services.agent_reach.source_planner import SourceAction, SourcePlan, PlanningBudget
from backend.services.research.harvesting import HarvestingEngine, HarvestResult, _read_priority
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.research_profiles import QUICK


@pytest.mark.parametrize("domain,target,category", [
    ("brand", "Quartz Tools", "brand_abuse_reporting"),
    ("personal", "Elena Rivera", "public_statement_discovery"),
])
def test_specialist_validated_core_plan_reaches_real_harvest_boundary(domain, target, category):
    from backend.application.research.harvest_pipeline import run_harvest_pipeline
    action = SourceAction("validated-core", 1, "web", "search",
                          target + (" phishing report" if domain == "brand" else " statement interview"),
                          category, "SEARCH_INDEX_DISCOVERY", 0, "Synthetic validated query.")
    plan = SourcePlan("test-plan", "test-agent", target, target, domain, [action], [], PlanningBudget())
    empty = HarvestResult(metrics={}, read_telemetry={"attempted": 0, "successful": 0, "total_chars_read": 0})
    with patch("backend.services.agent_reach.source_planner.source_planning_engine.plan", return_value=plan), \
         patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=empty) as harvest, \
         patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        result = run_harvest_pipeline(ResearchRequest(target=target, domain=domain),
                                     ResearchBudget(timeout_seconds=20), "QUICK")
    rows = harvest.call_args.kwargs["query_plan"]
    assert any(row.get("source_plan_action_id") == "validated-core" for row in rows)
    assert result.telemetry["specialist_planning"]["selected_core_count"] == 1


class CapturingService:
    def retrieve_many(self, plan, **kwargs):
        fragments = []
        for channel, rows in plan.items():
            for row in rows:
                fragments.append(EvidenceFragment(
                    platform=channel, title="Elena Rivera interview transcript",
                    url="https://publisher.example/observed-interview", query_id=row["query_id"],
                    raw_metadata={"query_class": row["query_class"]}))
        return RetrievalResult(query="Elena Rivera", domain="personal", fragments=fragments)

    def read(self, url, max_chars):
        return {"status": "success", "content": 'Elena Rivera said, "We will publish the audited figures next month."',
                "page_metadata": {"title": "Elena Rivera interview", "content_scope": "article",
                                  "body_quality": {"body_kind": "ARTICLE_BODY"}}}


def test_deduplicated_candidate_keeps_all_specialist_objectives_and_action_lineage():
    rows = [
        {"channel": "web", "query_class": "public_statement_discovery", "query_text": "Elena Rivera interview",
         "source_plan_action_id": "statement-action", "specialist_task": "PUBLIC_STATEMENT",
         "acquisition_objective": "PUBLIC_STATEMENT"},
        {"channel": "news", "query_class": "identity_abuse_reporting", "query_text": "Elena Rivera impersonation",
         "source_plan_action_id": "identity-action", "specialist_task": "IMPERSONATION",
         "acquisition_objective": "IDENTITY_THREAT"},
    ]
    result = HarvestingEngine(CapturingService()).run(
        "Elena Rivera", "personal", profile=replace(QUICK, max_queries=2, host_spacing_seconds=0),
        query_plan=rows)
    assert len(result.captures) == 1
    meta = result.captures[0].metadata
    assert set(meta["specialist_tasks"]) == {"PUBLIC_STATEMENT", "IMPERSONATION"}
    assert set(meta["acquisition_objectives"]) == {"PUBLIC_STATEMENT", "IDENTITY_THREAT"}
    assert set(meta["source_plan_action_ids"]) == {"statement-action", "identity-action"}
    assert result.captures[0].content.startswith("Elena Rivera said,")


def test_targeted_read_priority_uses_observed_lead_not_query_or_task_label():
    def item(identity, title, query):
        return EvidenceItem(id=identity, canonical_url="https://publisher.example/" + identity,
                            title=title, query_text=query,
                            metadata={"requested_specialist_tasks": ["PHISHING"], "specialist_tasks": ["PHISHING"]})
    complaint = item("a", "Quartz Tools delivery complaint", "Quartz Tools phishing")
    phishing = item("b", "Quartz Tools credential phishing report", "Quartz Tools customer complaint")
    assert _read_priority(phishing, "Quartz Tools", "brand", Counter(), Counter()) < _read_priority(
        complaint, "Quartz Tools", "brand", Counter(), Counter())
    assert not phishing.relevant_excerpt and not complaint.relevant_excerpt


def test_observed_child_retains_task_route_without_inventing_attribution():
    class Service(CapturingService):
        def retrieve_many(self, plan, **kwargs):
            query = next(iter(plan.values()))[0]
            return RetrievalResult(query="Elena Rivera", domain="personal", fragments=[EvidenceFragment(platform="web",
                title="Elena Rivera interview archive", url="https://publisher.example/news",
                query_id=query["query_id"])])
        def read(self, url, max_chars):
            if url.endswith("/news"):
                return {"status": "success", "content": "Elena Rivera interviews archive.",
                    "page_metadata": {"content_scope": "NEWS_INDEX", "observed_links": [
                        {"url": "https://publisher.example/observed-interview", "text": "Elena Rivera interview transcript"}]}}
            return super().read(url, max_chars)
    rows = [{"channel": "web", "query_class": "public_statement_discovery", "query_text": "Elena Rivera interview",
             "source_plan_action_id": "speaker-action", "specialist_task": "PUBLIC_STATEMENT",
             "acquisition_objective": "PUBLIC_STATEMENT"}]
    result = HarvestingEngine(Service()).run("Elena Rivera", "personal",
        profile=replace(QUICK, max_queries=1, host_spacing_seconds=0), query_plan=rows)
    article = next(item for item in result.captures if item.canonical_url.endswith("/observed-interview"))
    assert article.metadata["specialist_tasks"] == ["PUBLIC_STATEMENT"]
    assert article.metadata["source_plan_action_ids"] == ["speaker-action"]
    assert not article.metadata.get("identity_authenticated")


def test_explicit_task_fallbacks_stay_on_task_without_larger_query_limits():
    from backend.services.research.harvesting import diversified_queries
    rows = diversified_queries("Elena Rivera", "personal", specialist_tasks=["FALSE_QUOTE"])
    assert len(rows) == 9
    assert all(row["specialist_task"] == "FALSE_QUOTE" for row in rows)
    assert all(row["acquisition_objective"] == "IDENTITY_THREAT" for row in rows)
    assert not any("deepfake" in row["query_text"] or "career" in row["query_text"] for row in rows)
    rows = diversified_queries("Quartz Tools", "brand", specialist_tasks=["PRODUCT_SAFETY"])
    assert all(row["specialist_task"] == "PRODUCT_SAFETY" for row in rows)
    assert not any("counterfeit" in row["query_text"] for row in rows)


def test_specialist_task_arguments_do_not_change_other_domains():
    from backend.services.research.harvesting import diversified_queries
    for domain in ("financial", "general", "trending"):
        expected = diversified_queries("Quartz Tools", domain)
        assert diversified_queries("Quartz Tools", domain, specialist_tasks=["FALSE_QUOTE"]) == expected


def test_specialist_route_roundtrips_raw_pool_without_promoting_evidence():
    from backend.services.research.raw_pool import RawAcquisitionPool
    row = EvidenceItem(id="native-route", canonical_url="https://publisher.example/story",
        content='Elena Rivera said, "We will publish the figures next month."',
        content_depth="PARTIAL_CONTENT", read_status="SUCCESS", acquired_id="native-capture",
        metadata={"read_success": True, "specialist_tasks": ["PUBLIC_STATEMENT"],
                  "source_plan_action_ids": ["original-action"],
                  "acquisition_objectives": ["PUBLIC_STATEMENT"],
                  "page_metadata": {"body_quality": {"body_kind": "ARTICLE_BODY"}}})
    pool = RawAcquisitionPool("routing-control")
    pool.add_capture(row)
    saved = pool.export(include_text=True)["sources"][0]
    assert saved["specialist_tasks"] == ["PUBLIC_STATEMENT"]
    assert saved["qualification_status"] == "PENDING"
    replayed = pool.to_evidence_items()[0]
    assert replayed.metadata["source_plan_action_ids"] == ["original-action"]
    assert replayed.content == row.content
    assert not replayed.relevant_excerpt


def test_disputed_claim_projection_remains_separate_from_target_speech():
    from backend.services.report_builder import ReportBuilder
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    body = 'Elena Rivera never said "The merger has been approved"; the publisher describes a fabricated quote.'
    source = {"evidence_id": "dispute-source", "url": "https://publisher.example/dispute",
              "title": "Elena Rivera quotation dispute", "content": body, "content_depth": "PARTIAL_CONTENT"}
    synthesis = synthesize_personal_threats({"name": "Elena Rivera"}, [source])
    report = ReportBuilder.from_personal_result(query="Elena Rivera", personal_data={
        **synthesis, "evidence": [source], "summary": "A publisher reports disputed attribution."})
    assert not report.agent_intelligence["public_statements"]
    dispute = report.agent_intelligence["disputed_claims"][0]
    assert dispute["text"] == body and dispute["claim_status"] == "UNVERIFIED"
    assert dispute["source_passages"][0]["evidence_id"] == "dispute-source"
    assert not synthesis["suspected_impersonations"]
