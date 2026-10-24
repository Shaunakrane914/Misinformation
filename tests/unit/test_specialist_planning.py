"""Offline synthetic controls, not fresh acquisition or accuracy evaluation."""
import copy
import json

import pytest

from backend.services.agent_reach.source_planner import PlanningBudget, SourceAction, SourcePlan, SourcePlanningEngine
from backend.services.research.research_models import ResearchRequest
from backend.services.research.specialist_planning import build_specialist_harvest_plan


def action(identifier, channel, text, category="brand_abuse_reporting", operation="search", **kwargs):
    return SourceAction(identifier, 1, channel, operation, text, category, "SEARCH_INDEX_DISCOVERY",
                        1, "Synthetic validated control.", **kwargs)


def plan(actions, claim="Cedar Tools", budget=None, decisions=None):
    return SourcePlan("sp_control", "brandshield", "Cedar Tools", claim, "general_verification",
                      actions, [], budget or PlanningBudget(), runtime_decisions=decisions or [])


def request(target="Cedar Tools", domain="brand", claim=None):
    return ResearchRequest(target=target, domain=domain,
        agent_name="personal_watch" if domain == "personal" else "brandshield",
        extra_params={"claim_text": claim} if claim else {})


def test_core_specialist_searches_preserve_validated_fields_without_mutation():
    original = plan([action("a", "web", '"Cedar Tools" counterfeit'),
                     action("b", "news", '"Cedar Tools" phishing'),
                     action("c", "rss", '"Cedar Tools" consumer complaint')])
    before = copy.deepcopy(original.to_dict())
    req = request()
    req_before = copy.deepcopy(req)
    rows, diagnostic = build_specialist_harvest_plan(req, original)
    assert len(rows) == 3
    for row in rows:
        source = next(item for item in original.actions if item.action_id == row["query_id"])
        assert (row["query_id"], row["query_class"], row["query_text"], row["operation"]) == (
            source.action_id, source.source_category, source.query, source.operation)
        assert row["basis"] == "VALIDATED_SPECIALIST_SOURCE_PLAN"
        assert row["source_plan_action_id"] == source.action_id
    assert diagnostic["network_calls"] == 0
    assert diagnostic["selected_core_count"] == 3
    assert original.to_dict() == before
    assert req == req_before


def test_entity_only_personal_retains_both_statement_and_identity_lanes():
    original = plan([action("abuse", "web", '"Elena Torres" impersonation scam', "personal_watch"),
                     action("media", "web", '"Elena Torres" deepfake', "synthetic_media_reporting"),
                     action("speech", "web", '"Elena Torres" statement interview', "public_statement_discovery"),
                     action("news", "news", '"Elena Torres" impersonation', "identity_abuse_reporting")],
                    claim="Elena Torres")
    rows, diagnostic = build_specialist_harvest_plan(request("Elena Torres", "personal"), original)
    assert diagnostic["requested_tasks"] == ["PUBLIC_STATEMENT", "IDENTITY_THREAT"]
    assert {row["acquisition_objective"] for row in rows[:2]} == {"PUBLIC_STATEMENT", "IDENTITY_THREAT"}
    assert {row["acquisition_objective"] for row in rows} <= {"PUBLIC_STATEMENT", "IDENTITY_THREAT"}
    assert all(row["requested_specialist_tasks"] == diagnostic["requested_tasks"] for row in rows)


@pytest.mark.parametrize("phrase, expected", [
    ("counterfeit products", "COUNTERFEIT"), ("phishing incident", "PHISHING"),
    ("consumer complaint", "COMPLAINT"), ("product recall", "PRODUCT_SAFETY"),
    ("impersonation allegation", "IMPERSONATION"), ("deepfake video", "DEEPFAKE"),
    ("false quotation", "FALSE_QUOTE"),
])
def test_explicit_task_does_not_spend_rows_on_unrelated_defaults(phrase, expected):
    claim = "Cedar Tools " + phrase
    original = plan([action("broad", "web", "Cedar Tools latest independent reporting", "independent_reporting"),
                     action("match", "news", claim, "primary_discovery"),
                     action("other", "rss", "Cedar Tools interview transcript", "public_statement_discovery")], claim)
    rows, diagnostic = build_specialist_harvest_plan(request(claim=claim), original)
    assert diagnostic["requested_tasks"] == [expected]
    assert [row["query_id"] for row in rows] == ["match"]
    assert rows[0]["specialist_task"] == expected
    assert any(row["reason"] == "UNRELATED_TO_EXPLICIT_SPECIALIST_TASK" for row in diagnostic["skipped"])


def test_false_quote_personal_primary_lookup_remains_false_quote_task_not_identity_proof():
    claim = "Elena Torres false quote about the merger"
    original = plan([action("quote", "web", '"Elena Torres" interview transcript', "quotation_verification"),
                     action("abuse", "news", '"Elena Torres" impersonation scam', "identity_abuse_reporting")], claim)
    rows, diagnostic = build_specialist_harvest_plan(request("Elena Torres", "personal", claim), original)
    assert diagnostic["requested_tasks"] == ["FALSE_QUOTE"]
    assert len(rows) == 1
    assert rows[0]["specialist_task"] == "FALSE_QUOTE"
    assert rows[0]["acquisition_objective"] == "IDENTITY_THREAT"


def test_core_read_is_skipped_not_converted_to_url_search():
    original = plan([action("feed", "rss", "https://publisher.example/feed", "public_statement_discovery", "read"),
                     action("search", "news", "Cedar Tools counterfeit")])
    rows, diagnostic = build_specialist_harvest_plan(request(), original)
    assert [row["query_id"] for row in rows] == ["search"]
    assert {row["reason"] for row in diagnostic["skipped"]} == {"UNSUPPORTED_CORE_READ_ROUTING"}


def test_optional_route_operation_is_preserved_and_blocked_action_stays_blocked():
    original = plan([action("profile", "twitter", "Elena Torres", "verified_profile", "profile"),
                     action("blocked", "reddit", "Elena Torres allegations", validation_status="EXCLUDE"),
                     action("runtime", "youtube", "Elena Torres interview", "technical_video"),
                     action("invalid", "rss", "Elena Torres", operation="profile")], claim="Elena Torres",
                    decisions=[{"action_id": "runtime", "decision": "DEFER_TEMPORARY"}])
    rows, diagnostic = build_specialist_harvest_plan(request("Elena Torres", "personal"), original)
    assert len(rows) == 1
    assert rows[0]["operation"] == "profile"
    assert rows[0]["channel"] == "twitter"
    assert "UNSUPPORTED_CHANNEL_OR_OPERATION" in {row["reason"] for row in diagnostic["skipped"]}
    assert sum(row["reason"] == "ACTION_NOT_VALIDATED_OR_RUNTIME_BLOCKED" for row in diagnostic["skipped"]) == 2


def test_adapter_respects_source_plan_channel_budget_without_resurrecting_actions():
    original = plan([action("first", "web", "Cedar Tools counterfeit"),
                     action("outside", "web", "Cedar Tools phishing"),
                     action("news", "news", "Cedar Tools complaint")],
                    budget=PlanningBudget(max_queries_per_channel=1))
    rows, diagnostic = build_specialist_harvest_plan(request(), original)
    assert {row["query_id"] for row in rows} == {"first", "news"}
    assert diagnostic["skipped"] == [{"source_plan_action_id": "outside", "reason": "OUTSIDE_SOURCE_PLAN_CHANNEL_BUDGET",
                                      "source_category": "brand_abuse_reporting"}]


def test_six_core_and_two_optional_ceiling_and_total_action_limit():
    actions = [action(f"{channel}{i}", channel, f"Cedar Tools counterfeit case {i}")
               for channel in ("web", "news", "rss", "youtube", "reddit", "twitter") for i in range(3)]
    original = plan(actions)
    rows, diagnostic = build_specialist_harvest_plan(request(), original)
    assert len(rows) == 8
    assert diagnostic["selected_core_count"] == 6
    assert diagnostic["selected_optional_count"] == 2
    assert len({row["channel"] for row in rows[:3]}) == 3
    assert "SPECIALIST_CORE_LIMIT" in {row["reason"] for row in diagnostic["skipped"]}
    original.budget = PlanningBudget(max_actions=2)
    rows, _ = build_specialist_harvest_plan(request(), original)
    assert len(rows) == 2


def test_no_action_and_non_specialist_domain_do_not_create_fallback_queries():
    rows, diagnostic = build_specialist_harvest_plan(request(), plan([]))
    assert rows == []
    assert diagnostic["status"] == "NO_ADMITTED_SPECIALIST_ACTIONS"
    req = ResearchRequest(target="Cedar Tools", domain="financial", agent_name="scout")
    rows, diagnostic = build_specialist_harvest_plan(req, plan([action("a", "news", "Cedar Tools counterfeit")]))
    assert rows == []
    assert diagnostic["status"] == "NOT_SPECIALIST_DOMAIN"


def test_diagnostics_do_not_export_query_or_claim_text():
    secret_like = "token-value-must-not-appear"
    claim = "Cedar Tools phishing " + secret_like
    rows, diagnostic = build_specialist_harvest_plan(request(claim=claim),
        plan([action("a", "news", claim)], claim))
    assert rows[0]["query_text"] == claim
    assert secret_like not in json.dumps(diagnostic)
    assert "query_text" not in json.dumps(diagnostic)


def test_entity_name_is_not_a_task_keyword():
    original = plan([action("a", "news", "Recall Labs counterfeit")], claim="Recall Labs")
    rows, diagnostic = build_specialist_harvest_plan(request("Recall Labs"), original)
    assert diagnostic["explicit_task"] is False
    assert rows[0]["specialist_task"] == "COUNTERFEIT"


def test_removing_entity_does_not_strip_parts_of_task_words():
    claim = "Deep deepfake video"
    original = plan([action("a", "news", claim)], claim=claim)
    rows, diagnostic = build_specialist_harvest_plan(request("Deep", claim=claim), original)
    assert diagnostic["requested_tasks"] == ["DEEPFAKE"]
    assert rows[0]["specialist_task"] == "DEEPFAKE"


def test_custom_projection_cannot_modify_validated_operation_or_query(monkeypatch):
    original = plan([action("a", "web", "Cedar Tools counterfeit")])
    monkeypatch.setattr(original, "to_channel_queries", lambda: {"web": [{"query_id": "a", "operation": "search",
        "query_class": "brand_abuse_reporting", "query_text": "https://unexpected.example/"}]})
    rows, diagnostic = build_specialist_harvest_plan(request(), original)
    assert rows == []
    assert diagnostic["skipped"][0]["reason"] == "VALIDATED_ACTION_PROJECTION_MISMATCH"


class OfflineCapabilities:
    """No environment lookup or provider/health probe is needed by these tests."""

    def __init__(self, blocked=()):
        self.blocked = set(blocked)

    def assess(self, channel, operation, **kwargs):
        return {"decision": "EXCLUDE" if (channel, operation) in self.blocked else "ELIGIBLE",
                "reason": "OFFLINE_CAPABILITY_CONTROL", "channel": channel, "operation": operation}


def actual_plan(claim, *, agent="personal_watch", target="Elena Torres", budget=None, blocked=()):
    engine = SourcePlanningEngine(budget=budget, runtime_capabilities=OfflineCapabilities(blocked))
    return engine.plan(claim, agent=agent, entity=target,
                       domain="personal" if agent == "personal_watch" else "brand", use_llm=False)


def test_actual_planner_false_quote_survives_both_hard_caps_before_adapter_selection():
    claim = "Elena Torres false quote about the merger"
    original = actual_plan(claim)
    before = copy.deepcopy(original.to_dict())
    projected = original.to_channel_queries()
    assert projected["web"][0]["query_class"] == "quotation_verification"
    assert projected["web"][1]["query_class"] == "contradiction_probe"
    rows, diagnostic = build_specialist_harvest_plan(request("Elena Torres", "personal", claim), original)
    classes = {row["query_class"] for row in rows}
    assert {"quotation_verification", "contradiction_probe", "identity_corroboration"} <= classes
    assert {row["specialist_task"] for row in rows} == {"FALSE_QUOTE"}
    assert original.to_dict() == before
    assert len(original.actions) <= original.budget.max_actions
    assert all(len(values) <= original.budget.max_queries_per_channel for values in projected.values())
    assert diagnostic["explicit_task"] is True


@pytest.mark.parametrize("claim", [
    'Elena Torres said "The merger will preserve every research role"',
    'Elena Torres "The merger will preserve every research role"',
    'Elena Torres false quote "The merger will preserve every research role"',
])
def test_actual_planner_preserves_literal_quoted_lookup_without_generic_displacement(claim):
    original = actual_plan(claim)
    rows, _ = build_specialist_harvest_plan(request("Elena Torres", "personal", claim), original)
    quoted = [row for row in rows if row["query_class"] == "quotation_verification"]
    assert len(quoted) == 1
    assert quoted[0]["query_text"] == '"The merger will preserve every research role" Elena Torres'
    assert rows[0]["query_id"] == quoted[0]["query_id"]


@pytest.mark.parametrize("phrase, task", [("phishing incident", "PHISHING"), ("product recall", "PRODUCT_SAFETY")])
def test_actual_brand_planner_prefers_claim_actions_not_generic_brand_risk(phrase, task):
    claim = "Cedar Tools " + phrase
    original = actual_plan(claim, agent="brandshield", target="Cedar Tools")
    rows, diagnostic = build_specialist_harvest_plan(request(claim=claim), original)
    assert rows
    assert original.actions[0].source_category == "primary_discovery"
    assert {row["specialist_task"] for row in rows} == {task}
    assert all(row["query_class"] != "brand_risk" for row in rows)
    assert diagnostic["requested_tasks"] == [task]


def test_actual_planner_small_global_and_channel_caps_are_not_enlarged():
    claim = 'Elena Torres false quote "The proposed merger is cancelled"'
    original = actual_plan(claim, budget=PlanningBudget(max_actions=2, max_queries_per_channel=1))
    assert len(original.actions) == 2
    assert [item.source_category for item in original.actions] == ["quotation_verification", "contradiction_probe"]
    rows, _ = build_specialist_harvest_plan(request("Elena Torres", "personal", claim), original)
    assert len(rows) == 1
    assert rows[0]["query_class"] == "quotation_verification"


def test_actual_planner_task_priority_does_not_reenable_blocked_web_search():
    claim = "Elena Torres false quote about the merger"
    original = actual_plan(claim, blocked={("web", "search")})
    assert not any(item.channel == "web" for item in original.actions)
    rows, _ = build_specialist_harvest_plan(request("Elena Torres", "personal", claim), original)
    assert rows and all(row["channel"] != "web" for row in rows)
    assert any(row["channel"] == "web" and row["reason"] == "OFFLINE_CAPABILITY_CONTROL"
               for row in original.excluded)


@pytest.mark.parametrize("claim", [
    "Elena Torres false quote about quarterly revenue",
    'Elena Torres said "Our semiconductor revenue doubled this quarter"',
])
def test_actual_personal_planner_retains_quote_action_on_financial_or_hardware_subject(claim):
    original = actual_plan(claim)
    assert original.intent_class == "identity_attribution"
    rows, _ = build_specialist_harvest_plan(request("Elena Torres", "personal", claim), original)
    assert rows[0]["query_class"] == "quotation_verification"
    if "false quote" in claim:
        assert "contradiction_probe" in {row["query_class"] for row in rows}
    else:
        assert rows[0]["query_text"] == '"Our semiconductor revenue doubled this quarter" Elena Torres'


@pytest.mark.parametrize("task_phrase", ["phishing financial report", "product recall revenue impact"])
def test_actual_brand_task_precedes_incidental_financial_words(task_phrase):
    claim = "Cedar Tools " + task_phrase
    original = actual_plan(claim, agent="brandshield", target="Cedar Tools")
    assert original.intent_class == "general_verification"
    assert any(item.source_category == "primary_discovery" and claim in item.query for item in original.actions)


def test_pure_security_and_scout_trending_intent_classification_is_unchanged():
    assert SourcePlanningEngine._classify_intent("Cedar Tools GPU vulnerability CVE-2026-12345", "brand") == "technical_product"
    assert SourcePlanningEngine._classify_intent("Cedar Tools quarterly revenue", "financial") == "financial_integrity"
    assert SourcePlanningEngine._classify_intent("semiconductor revenue", "trending") == "financial_integrity"


@pytest.mark.parametrize("agent, entity, claim", [
    ("personal_watch", "Elena Torres", "Elena Torres"),
    ("brandshield", "Cedar Tools", "Cedar Tools"),
    ("trending", "battery chemistry", "battery chemistry false quote"),
])
def test_entity_only_and_non_specialists_keep_original_stage_priority_order(agent, entity, claim):
    engine = SourcePlanningEngine(runtime_capabilities=OfflineCapabilities())
    domain = "personal" if agent == "personal_watch" else "brand" if agent == "brandshield" else "trending"
    original = engine.plan(claim, agent=agent, entity=entity, domain=domain, use_llm=False)
    assert original.actions == sorted(original.actions, key=lambda item: (item.stage, item.priority))
    expected = {}
    for item in sorted(original.actions, key=lambda item: (item.stage, item.priority)):
        rows = expected.setdefault(item.channel, [])
        if len(rows) < original.budget.max_queries_per_channel:
            rows.append(item.action_id)
    assert {channel: [row["query_id"] for row in rows] for channel, rows in original.to_channel_queries().items()} == expected
