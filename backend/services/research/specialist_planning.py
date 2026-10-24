"""Carry validated specialist searches into harvesting without a second planner.

This adapter only selects existing actions.  Task labels route acquisition and
do not establish that an allegation, quotation or threat has been verified.
It neither probes capabilities nor invents searches, locators or evidence.
"""
from __future__ import annotations

import re
from collections import Counter

from backend.services.agent_reach.native.operation_capabilities import EXECUTABLE_CAPABILITIES


_CORE = frozenset({"web", "news", "rss"})
_BASIS = "VALIDATED_SPECIALIST_SOURCE_PLAN"
_PATTERNS = (
    ("FALSE_QUOTE", r"\b(?:(?:false|fake|fabricated|misattributed)\s+(?:quote|quotation|statement)|"
                    r"(?:quote|quotation)\s+(?:is\s+)?(?:false|fake|fabricated)|did\s+not\s+say)\b"),
    ("COUNTERFEIT", r"\b(?:counterfeit(?:s|ing)?|knockoffs?|fake\s+products?)\b"),
    ("PHISHING", r"\b(?:phishing|credential\s+(?:theft|harvesting))\b"),
    ("IMPERSONATION", r"\b(?:impersonat(?:ion|ions|e|es|ed|ing|or|ors)|fake\s+accounts?)\b"),
    ("DEEPFAKE", r"\b(?:deepfakes?|synthetic\s+(?:media|video|audio)|voice\s+clon(?:e|ing))\b"),
    ("PRODUCT_SAFETY", r"\b(?:recall(?:s|ed)?|product\s+safety|safety\s+(?:notice|warning)|"
                       r"fire\s+hazard|defective\s+products?)\b"),
    ("COMPLAINT", r"\b(?:complaints?|consumer\s+grievances?|customer\s+disputes?)\b"),
    ("PUBLIC_STATEMENT", r"\b(?:statements?|interviews?|speeches?|speech|transcripts?|said|says)\b"),
)


def _tasks(text, personal):
    found = [task for task, pattern in _PATTERNS if re.search(pattern, text, re.I)]
    if found:
        # A disputed statement is not a separate request for ordinary statements.
        if "FALSE_QUOTE" in found and "PUBLIC_STATEMENT" in found:
            found.remove("PUBLIC_STATEMENT")
        return found
    if re.search(r"\b(?:scams?|fraud|brand\s+abuse|identity\s+(?:abuse|threat|misuse))\b", text, re.I):
        return ["IDENTITY_THREAT" if personal else "BRAND_ABUSE"]
    return []


def _subjectless(text, target):
    """Names such as 'Recall Labs' must not themselves select a safety task."""
    return re.sub(r"(?<!\w)" + re.escape(target) + r"(?!\w)", " ", text, flags=re.I) if target else text


def _explicit_tasks(claim, target, personal):
    if not claim.strip() or claim.strip().casefold() == target.strip().casefold():
        return []
    tasks = _tasks(_subjectless(claim, target), personal)
    # Exact public quotations need the quotation lookup even without a verb
    # such as 'said'. The literal quotation remains untouched in the action.
    if not tasks and personal and re.search(r'"[^"\n]{5,}"', claim):
        return ["PUBLIC_STATEMENT"]
    return tasks


def specialist_claim_intent(claim, domain, entity=""):
    """Keep a specialist's task ahead of incidental financial/product nouns."""
    if str(domain).casefold() in {"personal", "personal_watch"}:
        return "identity_attribution"
    if str(domain).casefold() == "brand":
        tasks = _explicit_tasks(str(claim), str(entity), False)
        if any(task in tasks for task in ("COUNTERFEIT", "PHISHING", "COMPLAINT", "PRODUCT_SAFETY",
                                          "IMPERSONATION", "BRAND_ABUSE")):
            return "general_verification"
    return None


def specialist_action_priority(action, *, agent="", entity="", claim=""):
    """Task-aware prefix used *before* the planner's existing hard caps.

    Zero for entity-only/non-specialist plans preserves their original stable
    ordering. This is selection priority, never acquisition authorization or a
    change to an action's priority, text, identity or validation status.
    """
    agent = str(agent).casefold()
    personal = agent in {"personal", "personal_watch", "personal_watch_agent"}
    brand = agent in {"brandshield", "brandshield_agent"}
    if not (personal or brand):
        return 0
    requested = _explicit_tasks(str(claim), str(entity), personal)
    if not requested:
        return 0
    row = {"query_text": action.query, "query_class": action.source_category}
    _, matches = _task_for(row, requested, personal, str(entity))
    if personal and action.source_category == "quotation_verification" and any(
            task in requested for task in ("PUBLIC_STATEMENT", "FALSE_QUOTE")):
        return 0
    if personal and "FALSE_QUOTE" in requested and action.source_category == "contradiction_probe":
        return 1
    return 2 if matches else 3


def _task_for(row, requested, personal, target):
    tasks = _tasks(_subjectless(row["query_text"], target), personal)
    category = row["query_class"]
    if category == "quotation_verification":
        tasks = (["FALSE_QUOTE"] if "FALSE_QUOTE" in requested else ["PUBLIC_STATEMENT"]) + tasks
    elif category == "public_statement_discovery":
        tasks = ["PUBLIC_STATEMENT"] + tasks
    elif category in {"identity_primary", "verified_profile"} and not tasks:
        tasks = ["IDENTITY_THREAT"]
    if not tasks:
        tasks = ["IDENTITY_THREAT" if personal else "BRAND_ABUSE"]
    for task in requested:
        if task in tasks:
            return task, True
        if task == "IDENTITY_THREAT" and any(value in tasks for value in ("IMPERSONATION", "DEEPFAKE", "FALSE_QUOTE")):
            return tasks[0], True
        if task == "BRAND_ABUSE" and any(value in tasks for value in ("IMPERSONATION", "PHISHING", "COUNTERFEIT")):
            return tasks[0], True
    return tasks[0], False


def _balanced(rows, limit):
    """Use existing priority order within tasks, with channel/task diversity."""
    pending = list(rows)
    result, objective_counts, task_counts, channel_counts = [], Counter(), Counter(), Counter()
    while pending and len(result) < limit:
        index = min(range(len(pending)), key=lambda i: (
            objective_counts[pending[i]["acquisition_objective"]],
            task_counts[pending[i]["specialist_task"]],
            channel_counts[pending[i]["channel"]], i,
        ))
        row = pending.pop(index)
        result.append(row)
        objective_counts[row["acquisition_objective"]] += 1
        task_counts[row["specialist_task"]] += 1
        channel_counts[row["channel"]] += 1
    return result


def build_specialist_harvest_plan(request, source_plan):
    """Return bounded harvest rows and query-free selection diagnostics.

    Only the existing ``to_channel_queries`` admitted subset is considered;
    channel limits and capability decisions are not recalculated or enlarged.
    The caller retains the original profile/global query and HTTP ceilings.
    Core READ actions are intentionally not repackaged as SEARCH actions: a
    separate observed-URL read path is required to support them in harvesting.
    """
    domain = str(getattr(request, "domain", "")).casefold()
    agent = str(getattr(request, "agent_name", "")).casefold()
    personal = domain in {"personal", "personal_watch"} or agent in {"personal", "personal_watch", "personal_watch_agent"}
    brand = domain == "brand" or agent in {"brandshield", "brandshield_agent"}
    diagnostics = {"basis": _BASIS, "requested_tasks": [], "selected": [], "skipped": [],
                   "core_limit": 6, "optional_limit": 2, "selected_core_count": 0,
                   "selected_optional_count": 0, "network_calls": 0}
    if not (personal or brand):
        diagnostics["status"] = "NOT_SPECIALIST_DOMAIN"
        return [], diagnostics

    target = str(getattr(request, "target", ""))
    params = getattr(request, "extra_params", {}) or {}
    claim = str(params.get("claim_text") or getattr(source_plan, "claim", "") or "")
    requested = _explicit_tasks(claim, target, personal)
    explicit_tasks = bool(requested)
    if not requested:
        requested = (["PUBLIC_STATEMENT", "IDENTITY_THREAT"] if personal else
                     ["COUNTERFEIT", "PHISHING", "COMPLAINT", "BRAND_ABUSE", "PRODUCT_SAFETY"])
    diagnostics.update(requested_tasks=list(requested), explicit_task=explicit_tasks, status="SELECTED")

    actions = {action.action_id: action for action in source_plan.actions}
    blocked = {row.get("action_id") for row in getattr(source_plan, "runtime_decisions", [])
               if row.get("decision") in {"EXCLUDE", "DEFER_TEMPORARY"}}
    admitted = source_plan.to_channel_queries()
    core, optional, seen, admitted_ids = [], [], set(), set()

    def skip(action_id, reason, category=None):
        entry = {"source_plan_action_id": action_id, "reason": reason}
        if category:
            entry["source_category"] = category
        diagnostics["skipped"].append(entry)

    for channel, rows in admitted.items():
        for original in rows:
            action_id = original.get("query_id")
            admitted_ids.add(action_id)
            action = actions.get(action_id)
            if not action or action.validation_status != "VALID" or action_id in blocked:
                skip(action_id, "ACTION_NOT_VALIDATED_OR_RUNTIME_BLOCKED")
                continue
            operation = original.get("operation")
            if operation not in EXECUTABLE_CAPABILITIES.get(channel, set()):
                skip(action_id, "UNSUPPORTED_CHANNEL_OR_OPERATION", action.source_category)
                continue
            # Do not trust a stale/custom projection to change the validated action.
            if (channel, operation, original.get("query_text"), original.get("query_class")) != (
                    action.channel, action.operation, action.query, action.source_category):
                skip(action_id, "VALIDATED_ACTION_PROJECTION_MISMATCH", action.source_category)
                continue
            if channel in _CORE and operation != "search":
                skip(action_id, "UNSUPPORTED_CORE_READ_ROUTING", action.source_category)
                continue
            key = (channel, operation, original.get("query_text"))
            if key in seen:
                skip(action_id, "DUPLICATE_VALIDATED_ACTION", action.source_category)
                continue
            seen.add(key)
            row = {**original, "channel": channel}
            task, matches_requested = _task_for(row, requested, personal, target)
            if explicit_tasks and not matches_requested:
                skip(action_id, "UNRELATED_TO_EXPLICIT_SPECIALIST_TASK", action.source_category)
                continue
            row.update(source_plan_action_id=action_id, specialist_task=task,
                       requested_specialist_tasks=list(requested), basis=_BASIS,
                       acquisition_objective=("PUBLIC_STATEMENT" if task == "PUBLIC_STATEMENT" else "IDENTITY_THREAT")
                       if personal else task)
            (core if channel in _CORE else optional).append(row)

    for action in source_plan.actions:
        if action.action_id not in admitted_ids:
            skip(action.action_id, "OUTSIDE_SOURCE_PLAN_CHANNEL_BUDGET", action.source_category)
    total_limit = max(0, source_plan.budget.max_actions)
    chosen_core = _balanced(core, min(6, total_limit))
    chosen_optional = _balanced(optional, min(2, max(0, total_limit - len(chosen_core))))
    selected = chosen_core + chosen_optional
    chosen_ids = {row["source_plan_action_id"] for row in selected}
    for row in core + optional:
        if row["source_plan_action_id"] not in chosen_ids:
            skip(row["source_plan_action_id"], "SPECIALIST_CORE_LIMIT" if row["channel"] in _CORE else
                 "SPECIALIST_OPTIONAL_LIMIT", row["query_class"])
    diagnostics.update(selected_core_count=len(chosen_core), selected_optional_count=len(chosen_optional))
    diagnostics["selected"] = [{"source_plan_action_id": row["source_plan_action_id"],
        "channel": row["channel"], "operation": row["operation"], "source_category": row["query_class"],
        "specialist_task": row["specialist_task"], "acquisition_objective": row["acquisition_objective"]}
        for row in selected]
    if not selected:
        diagnostics["status"] = "NO_ADMITTED_SPECIALIST_ACTIONS"
    return selected, diagnostics
