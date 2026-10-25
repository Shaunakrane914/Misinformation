"""Optional one-query advice after weak deterministic discovery; never evidence."""
import os
import time
from urllib.parse import urlsplit


def expand_with_advice(request, candidates, service, timeout, *, capture_feedback=None):
    trace = {"status": "DISABLED", "reason": "INSUFFICIENT_DIRECT_ARTICLE_CANDIDATES", "advisory_only": True}
    if os.getenv("AEGIS_SEARCH_ADVISOR_ENABLED", "false").lower() not in {"1", "true"} or timeout < 2:
        return None, trace
    from backend.services.research.publisher_links import is_publisher_hub
    from backend.services.research.content_roles import matches_objective, document_role, NON_EVENT_ROLES
    direct = [item for item in candidates if item.channel in {"web", "news", "rss"} and not is_publisher_hub(item.canonical_url)
              and document_role(item) not in NON_EVENT_ROLES and matches_objective(item.title, request.domain)
              and not (urlsplit(item.canonical_url).hostname or "").endswith(("google.com", "wikipedia.org", "x.com"))]
    if capture_feedback is not None:
        usable = [row for row in capture_feedback if row.get("usable_passage") and not row.get("duplicate_body_observation")]
        trace["trigger"] = "CAPTURED_PASSAGE_FEEDBACK"
        trace["usable_capture_observations"] = len(usable)
        if len(usable) >= 2:
            trace["status"] = "SKIPPED_ADEQUATE_CAPTURED_PASSAGES"
            return None, trace
    elif len(direct) >= 2:
        trace["status"] = "SKIPPED_ADEQUATE_DIRECT_LEADS"
        return None, trace
    from backend.services.research.evidence_advisor import private_or_secret_text
    if private_or_secret_text(request.target):
        trace["status"] = "SKIPPED_SENSITIVE_INPUT"
        return None, trace
    started = time.monotonic()
    try:
        from backend.infrastructure.llm.advisory_policy import require_advisory
        require_advisory("search_suggestion")
        from backend.services.agent_reach.source_planner import source_planning_engine
        context = request.target[:200]
        if capture_feedback is not None:
            # Bounded reason categories only, never source bodies, credentials,
            # allegations or a generated claim/verdict.
            categories = sorted({str(row.get("reason") or "UNKNOWN").split(":", 1)[0].split("(", 1)[0][:60]
                                 for row in capture_feedback if not row.get("usable_passage")})[:4]
            context += "; acquired-source gaps: " + ", ".join(categories)
        advice = source_planning_engine._get_llm_suggestions(
            context, request.target[:200], request.domain, request.agent_name)
        actions, rejected = source_planning_engine._validate_llm_actions(advice.actions[:1], request.target, {"news", "web"})
        trace.update(status="SUGGESTED", rejected=rejected, query_count=len(actions))
        if not actions or timeout - (time.monotonic() - started) <= 0:
            return None, trace
        action = actions[0]
        result = service.retrieve_many({action.channel: [{"query_id": "ai_search_1", "query_class": "advisory_discovery",
            "query_text": action.query}]}, perform_reads=False, target_name=request.target, domain=request.domain,
            timeout=min(6.0, timeout - (time.monotonic() - started)),
            budget={"max_queries_per_channel": 1, "max_results_per_query": 3, "max_total_evidence": 3})
        return result, trace
    except Exception as error:
        trace.update(status="UNAVAILABLE", error_type=type(error).__name__)
        return None, trace
    finally:
        trace["latency_ms"] = round((time.monotonic() - started) * 1000, 2)
