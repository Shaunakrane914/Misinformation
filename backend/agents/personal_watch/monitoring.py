"""
Aegis Protocol — Personal Watch Monitoring & Retrieval
======================================================
Multi-channel retrieval execution, item normalization, URL deduplication,
and cross-platform spread/velocity analysis.
"""

from __future__ import annotations

import hashlib
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.agent_reach.planner import RetrievalPlanner
from backend.services.research import ResearchRequest, research_engine

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_domain(url: str) -> str:
    """Extract domain from URL safely."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc or ""
        return netloc.replace("www.", "").split(":")[0]
    except Exception:
        return ""


def normalize_item(
    item: Dict[str, Any],
    default_platform: str,
    source_role: str,
    subject: str,
) -> Dict[str, Any]:
    """Normalize raw item into structured PersonalEvidence model."""
    url = item.get("url", "").strip()
    title = item.get("title", "").strip() or "Untitled Mention"
    content = item.get("content", "").strip() or item.get("snippet", "").strip() or title
    snippet = item.get("snippet", "").strip() or content[:200]
    platform = item.get("platform") or default_platform
    source = item.get("source") or extract_domain(url) or platform
    author = item.get("author") or item.get("channel") or "@user"

    raw_id_seed = f"{url}:{title}:{author}"
    evidence_id = f"ev_{hashlib.md5(raw_id_seed.encode()).hexdigest()[:10]}"

    source_lower = source.lower()
    if any(d in source_lower for d in ["reuters", "bloomberg", "apnews", "bbc", "nytimes", "wsj", "thehindu", "indianexpress"]):
        source_tier = "TIER_1_MAINSTREAM_NEWS"
    elif platform in ("Twitter/X", "Reddit"):
        source_tier = "TIER_3_SOCIAL_FORUM"
    elif platform == "YouTube":
        source_tier = "TIER_2_VIDEO_STREAM"
    else:
        source_tier = "TIER_2_COMMUNITY_WEB"

    published_at = item.get("published_at") or item.get("published") or item.get("date") or "Recent"

    return {
        "evidence_id": evidence_id,
        "discovered_candidate_id": item.get("discovered_candidate_id"),
        "ranked_candidate_id": item.get("ranked_candidate_id"),
        "accepted_candidate_id": item.get("accepted_candidate_id"),
        "acquisition_attempt_id": item.get("acquisition_attempt_id"),
        "acquired_candidate_id": item.get("acquired_candidate_id"),
        "selection_decision": item.get("selection_decision"),
        "selection_reason": item.get("selection_reason"),
        "subject": subject,
        "platform": platform,
        "source": source,
        "title": title,
        "content": content,
        "snippet": snippet,
        "url": url,
        "canonical_url": url,
        "author": author,
        "published_at": published_at,
        "retrieved_at": utcnow_iso(),
        "source_role": source_role,
        "source_tier": source_tier,
        "retrieval_method": "Agent Reach Omni-Retrieval",
        "metadata": {
            "likes": item.get("likes", 0),
            "retweets": item.get("retweets", 0),
            "score": item.get("score", 0),
            "is_official": item.get("is_official", False)
        }
    }


def deduplicate_and_group_evidence(
    items: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Deduplicate by URL and normalized title.
    Assigns 'source_group_id' so syndicated news copies aren't counted as independent corroboration.
    """
    seen_urls: Set[str] = set()
    seen_titles: Set[str] = set()
    unique_items: List[Dict[str, Any]] = []
    syndicated_count = 0

    title_to_group: Dict[str, str] = {}

    for item in items:
        url = item.get("url", "")
        title = item.get("title", "")
        clean_title = re.sub(r"[^\w\s]", "", title.lower()).strip()
        title_key = " ".join(clean_title.split()[:8])

        if url and url in seen_urls:
            syndicated_count += 1
            continue
        if url:
            seen_urls.add(url)

        if title_key and title_key in seen_titles:
            syndicated_count += 1
            group_id = title_to_group.get(title_key, f"grp_{hashlib.md5(title_key.encode()).hexdigest()[:8]}")
            item["source_group_id"] = group_id
            item["is_syndicated"] = True
            unique_items.append(item)
            continue

        if title_key:
            seen_titles.add(title_key)
            group_id = f"grp_{hashlib.md5(title_key.encode()).hexdigest()[:8]}"
            title_to_group[title_key] = group_id
            item["source_group_id"] = group_id
            item["is_syndicated"] = False

        unique_items.append(item)

    return unique_items, syndicated_count


def search_personal_evidence(
    subject_info: Dict[str, Any],
    max_results: int = 24,
    timeout: float = 12.0
) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any], int, Optional[Any]]:
    """
    Execute domain-specific multi-channel retrieval using the Agent Reach backbone.
    Channels queried: News, Web, Reddit, Twitter/X, YouTube, RSS.
    """
    target_name = subject_info.get("canonical_name", subject_info.get("name", ""))

    evidence_items: List[Dict[str, Any]] = []
    channel_health: Dict[str, str] = {
        "news": "standby",
        "web": "standby",
        "reddit": "standby",
        "twitter": "standby",
        "youtube": "standby",
        "rss": "standby",
        "instagram": "unavailable"
    }
    retrieval_plan_info: Dict[str, Any] = {}
    last_research_res = None

    try:
        planner = RetrievalPlanner()
        multi_queries, query_classes = planner.build_multi_channel_queries(
            target_name,
            domain="personal"
        )
        retrieval_plan_info["query_classes"] = query_classes

        research_req = ResearchRequest(
            target=target_name,
            domain="personal",
            intent=f"monitor personal identity threat surface, impersonation profiles, synthetic deepfakes, scams, and false claims for {target_name}",
            query_classes=list(query_classes.keys()) if isinstance(query_classes, dict) else query_classes,
            deep_read_budget=15,
            corroboration_budget=4,
        )
        research_res = research_engine.investigate(research_req)
        last_research_res = research_res
        retrieval_plan_info["trace"] = research_res.telemetry
        retrieval_plan_info["plan"] = {
            "query_classes": query_classes,
            "trace": research_res.telemetry
        }

        for f in research_res.evidence:
            if hasattr(f, "canonical_url"):
                url = f.canonical_url or ""
                title = f.title
                snippet = f.relevant_excerpt or f.snippet
                content = f.content or f.snippet
                source = f.source_name or f.channel
                channel = f.channel
                platform = f.channel
                role = f.source_role
                tier = f.source_tier
                author = f.source_name or f.channel
                pub = f.published_at or "Recent"
                depth = f.content_depth
                q_id = f.query_id
                q_class = f.query_class
                q_text = f.query_text
                excerpt = f.relevant_excerpt
                indep_group = f.independence_group
                disc_id = getattr(f, "discovered_id", getattr(f, "id", None))
                rank_id = getattr(f, "ranked_id", None)
                acc_id = getattr(f, "accepted_id", None)
                att_id = getattr(f, "acquisition_attempt_id", None)
                acq_id = getattr(f, "acquired_id", None)
                sel_dec = getattr(f, "selection_decision", "ACCEPTED")
                sel_rea = getattr(f, "selection_reason", "ACQUIRED_EVIDENCE")
            else:
                url = getattr(f, "url", "")
                title = getattr(f, "title", "")
                snippet = getattr(f, "snippet", "")
                content = getattr(f, "content", "")
                source = getattr(f, "platform", "web")
                channel = getattr(f, "channel_name", "web")
                platform = getattr(f, "channel_name", "web")
                role = f.raw_metadata.get("source_role", "WEB_REFERENCE") if hasattr(f, "raw_metadata") else "WEB_REFERENCE"
                tier = f.raw_metadata.get("source_tier", "TIER_3_AGGREGATE") if hasattr(f, "raw_metadata") else "TIER_3_AGGREGATE"
                author = getattr(f, "author", "Web")
                pub = getattr(f, "published", "Recent")
                depth = getattr(f, "content_depth", "SNIPPET")
                q_id = getattr(f, "query_id", "")
                q_class = getattr(f, "query_class", "general")
                q_text = getattr(f, "query_text", "")
                excerpt = ""
                indep_group = "independent"
                disc_id = getattr(f, "id", None)
                rank_id = None
                acc_id = None
                att_id = None
                acq_id = None
                sel_dec = None
                sel_rea = None

            ch = (channel or platform or "Web").title()
            norm_dict = {
                "title": title,
                "url": url,
                "snippet": snippet,
                "content": content,
                "author": author,
                "published": pub,
                "published_at": pub,
                "source": source,
                "channel": channel,
                "platform": platform,
                "source_role": role,
                "source_tier": tier,
                "discovered_candidate_id": disc_id,
                "ranked_candidate_id": rank_id,
                "accepted_candidate_id": acc_id,
                "acquisition_attempt_id": att_id,
                "acquired_candidate_id": acq_id,
                "selection_decision": sel_dec,
                "selection_reason": sel_rea,
                "metadata": {
                    "content_depth": depth,
                    "query_id": q_id,
                    "query_class": q_class,
                    "query_text": q_text,
                    "relevant_excerpt": excerpt,
                    "independence_group": indep_group,
                }
            }
            evidence_items.append(normalize_item(norm_dict, default_platform=ch, source_role=role, subject=target_name))

        for ch_name, status in research_res.telemetry.get("channel_health", {}).items():
            count = sum(1 for f in research_res.evidence if f.channel == ch_name)
            channel_health[ch_name] = f"{status} ({count})"

    except Exception as reach_err:
        logger.error(f"[PersonalWatch 2.0] ResearchEngine investigate error: {reach_err}")
        last_research_res = None

    deduped, syndication_count = deduplicate_and_group_evidence(evidence_items)

    logger.info(f"[PersonalWatch 2.0] Retrieved {len(deduped)} normalized evidence items ({syndication_count} syndicated copies grouped)")
    return deduped[:max_results], channel_health, retrieval_plan_info, syndication_count, last_research_res


def analyze_spread_and_velocity(evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute real spread and velocity metrics across platforms.
    If timestamps are insufficient, truthfully states insufficient historical data.
    """
    if not evidence_list:
        return {
            "status": "no_data",
            "platforms_count": 0,
            "sources_count": 0,
            "signals_count": 0,
            "velocity_trend": "Nominal",
            "assessment": "No live evidence found."
        }

    platforms = set(e.get("platform", "Web") for e in evidence_list)
    sources = set(e.get("source", "Web") for e in evidence_list)
    signals_count = len(evidence_list)

    timestamps = [e.get("published_at", "") for e in evidence_list if e.get("published_at") and e.get("published_at") != "Recent"]

    if len(timestamps) >= 3:
        first_seen = min(timestamps)
        latest_seen = max(timestamps)
        velocity_trend = "Accelerating" if len(evidence_list) > 10 else "Steady"
        assessment = f"Activity spreading across {len(platforms)} platforms with {len(sources)} distinct sources."
    else:
        first_seen = "Recent"
        latest_seen = "Recent"
        velocity_trend = "Insufficient historical data"
        assessment = f"Current active cross-platform visibility across {len(platforms)} platform(s)."

    return {
        "status": "computed",
        "platforms_count": len(platforms),
        "sources_count": len(sources),
        "signals_count": signals_count,
        "first_observed": first_seen,
        "latest_observed": latest_seen,
        "velocity_trend": velocity_trend,
        "assessment": assessment
    }
