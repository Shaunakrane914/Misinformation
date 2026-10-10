"""
Aegis Protocol — BrandShield Evidence Scanning & Acquisition
=============================================================
Orchestrates multi-channel retrieval via the shared AgentReach/ResearchEngine fabric
and extracts normalized evidence items with platform and provenance attributes.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def search_brand_evidence(
    brand_info: Dict[str, Any],
    max_results: int = 20,
    timeout: float = 12.0
) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any], int, Any]:
    """
    Execute domain-specific retrieval using the central AgentReachService.
    Returns:
        (evidence_items, channel_health_map, retrieval_plan, syndicated_count, research_res)
    """
    target_name = brand_info.get("resolved_entity", brand_info.get("brand", ""))
    brand_name = brand_info.get("brand", target_name)
    product_name = brand_info.get("product")

    try:
        try:
            from backend.services.agent_reach.planner import RetrievalPlanner
        except (ImportError, ModuleNotFoundError):
            from services.agent_reach.planner import RetrievalPlanner

        logger.info(f"[BrandShield 2.0] Launching multi-query Agent Reach retrieval for '{target_name}' (domain=brand)")

        from backend.services.research import research_engine, ResearchRequest
        planner = RetrievalPlanner()
        multi_queries, query_classes = planner.build_multi_channel_queries(target_name, domain="brand")

        research_req = ResearchRequest(
            target=target_name,
            domain="brand",
            agent_name="brandshield",
            intent=f"investigate brand reputation, counterfeits, impersonations, phishing, and online threats for {target_name}",
            query_classes=list(query_classes.keys()) if isinstance(query_classes, dict) else query_classes,
            deep_read_budget=15,
            corroboration_budget=4,
        )
        research_res = research_engine.investigate(research_req)
        fragments = research_res.evidence
        retrieval_trace = research_res.telemetry
        channel_health = retrieval_trace.get("channel_health", {})
        plan = {
            "query_classes": query_classes,
            "trace": retrieval_trace
        }
    except Exception as e:
        logger.warning(f"[BrandShield 2.0] ResearchEngine retrieval exception: {e}")
        fragments = []
        channel_health = {}
        plan = {}
        research_res = None

    evidence_items: List[Dict[str, Any]] = []
    syndicated_count = 0

    # Primary source domain markers
    brand_clean = re.sub(r'[^a-zA-Z0-9]', '', brand_name.lower())
    primary_markers = [
        f"{brand_clean}.com", f"investor.{brand_clean}", f"support.{brand_clean}",
        "cpsc.gov", "ftc.gov", "fda.gov", "sec.gov", "bbb.org", "consumeraffairs.com"
    ]

    for idx, f in enumerate(fragments):
        if hasattr(f, "canonical_url"):
            url = f.canonical_url or ""
            title = f.title or f"{target_name} Signal"
            content = f.content or f.snippet
            snippet = f.relevant_excerpt or f.snippet or content[:240]
            source = f.source_name or f.channel
            platform = f.channel
            author = f.source_name or f.channel
            published_at = f.published_at or "Recent"
            retrieved_at = f.discovered_at
            role = f.source_role
            tier = f.source_tier
            group = f.independence_group
            content_depth = f.content_depth
            query_id = f.query_id
            query_class = f.query_class
            query_text = f.query_text
            is_primary = f.primary_source or role in ("PRIMARY", "PRIMARY_OFFICIAL", "PRIMARY_REGULATORY")
            disc_id = getattr(f, "discovered_id", getattr(f, "id", None))
            rank_id = getattr(f, "ranked_id", None)
            acc_id = getattr(f, "accepted_id", None)
            att_id = getattr(f, "acquisition_attempt_id", None)
            acq_id = getattr(f, "acquired_id", None)
            sel_dec = getattr(f, "selection_decision", "ACCEPTED")
            sel_rea = getattr(f, "selection_reason", "ACQUIRED_EVIDENCE")
        else:
            url = f.url or ""
            title = f.title or f"{target_name} Signal"
            content = f.content or f.snippet
            snippet = f.snippet or content[:240]
            source = f.platform or getattr(f, "channel_name", "web")
            platform = getattr(f, "channel_name", None) or f.platform
            author = f.author or (f.channel_name.title() if getattr(f, "channel_name", None) else "Web")
            published_at = getattr(f, "published", "Recent")
            retrieved_at = getattr(f, "retrieved_at", "")
            role = f.raw_metadata.get("source_role", "DISCOVERY") if hasattr(f, "raw_metadata") else "DISCOVERY"
            tier = f.raw_metadata.get("source_tier", "TIER_3_AGGREGATE") if hasattr(f, "raw_metadata") else "TIER_3_AGGREGATE"
            group = f.raw_metadata.get("source_independence_group", "independent") if hasattr(f, "raw_metadata") else "independent"
            content_depth = getattr(f, "content_depth", "SNIPPET")
            query_id = getattr(f, "query_id", "")
            query_class = getattr(f, "query_class", "general")
            query_text = getattr(f, "query_text", "")
            is_primary = role == "PRIMARY"
            disc_id = getattr(f, "id", None)
            rank_id = None
            acc_id = None
            att_id = None
            acq_id = None
            sel_dec = None
            sel_rea = None

        norm_url = url.lower()
        if any(m in norm_url for m in primary_markers):
            is_primary = True
            role = "PRIMARY"
            tier = "TIER_1_OFFICIAL_FILING"

        if group.startswith("syndicated_"):
            syndicated_count += 1

        evidence_items.append({
            "evidence_id": f"ev_{idx+1:03d}",
            "discovered_candidate_id": disc_id,
            "ranked_candidate_id": rank_id,
            "accepted_candidate_id": acc_id,
            "acquisition_attempt_id": att_id,
            "acquired_candidate_id": acq_id,
            "selection_decision": sel_dec,
            "selection_reason": sel_rea,
            "title": title,
            "content": content,
            "snippet": snippet,
            "url": url,
            "has_url": bool(url and url.startswith("http")),
            "source": source,
            "platform": platform,
            "author": author,
            "published_at": published_at,
            "retrieved_at": retrieved_at,
            "source_role": role,
            "source_tier": tier,
            "independence_group": group,
            "is_primary": is_primary,
            "content_depth": content_depth,
            "query_id": query_id,
            "query_class": query_class,
            "query_text": query_text,
        })

    evidence_items = evidence_items[:max_results]
    return evidence_items, channel_health, plan, syndicated_count, research_res
