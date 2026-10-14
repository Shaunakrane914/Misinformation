"""
Aegis Protocol — Trending Clustering & Narrative Extraction
============================================================
Clusters normalized TrendEvidence items into structured Trend and Narrative objects.
Assigns syndication groups and extracts verifiable claims.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from backend.agents.trending.assessment import compute_cluster_sentiment, evaluate_misinformation_risk
from backend.agents.trending.models import (
    Trend,
    TrendClaim,
    TrendEvidence,
    TrendNarrative,
    WIRE_SIGNATURES,
)
from backend.agents.trending.temporal import calculate_velocity, parse_timestamp_epoch
from backend.services.agent_reach.channels import EvidenceFragment

logger = logging.getLogger(__name__)


def detect_syndication_group(title: str, source: str) -> str:
    """Assign unified group ID to syndicated wire stories to detect duplication."""
    s_lower = source.lower()
    for wire in WIRE_SIGNATURES:
        if wire in s_lower:
            return f"G-WIRE-{wire.upper()[:3]}"

    norm_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower()[:40])
    if norm_title:
        return f"G-{hash(norm_title) % 1000:03d}"
    return "G-INDEP"


def extract_narratives_from_cluster(items: List[TrendEvidence]) -> List[Dict[str, Any]]:
    """Extract dominant narrative angles with evidence citations."""
    narratives = []
    media_items = [it for it in items if it.source_role in ["PRIMARY", "SECONDARY"]]
    community_items = [it for it in items if it.source_role in ["COMMUNITY", "COMMENTARY"]]

    if media_items:
        narratives.append({
            "narrative_id": f"N-MED-{len(narratives)+1}",
            "title": "Official & Press Media Coverage",
            "summary": f"Reported by {len(media_items)} news outlets including {media_items[0].source}.",
            "sentiment": "NEUTRAL",
            "evidence_ids": [it.evidence_id for it in media_items[:3]],
            "platforms": list({it.platform for it in media_items})
        })

    if community_items:
        narratives.append({
            "narrative_id": f"N-COM-{len(narratives)+1}",
            "title": "Public & Social Media Discourse",
            "summary": "Circulating across social communities with fan debate and reactions.",
            "sentiment": "MIXED",
            "evidence_ids": [it.evidence_id for it in community_items[:3]],
            "platforms": list({it.platform for it in community_items})
        })

    return narratives


def extract_claims_from_cluster(items: List[TrendEvidence]) -> List[Dict[str, Any]]:
    """Extract circulating factual claims and assign verification status."""
    claims = []
    for idx, it in enumerate(items[:4]):
        text = it.title.strip()
        is_unverified = any(w in text.lower() for w in ["rumor", "alleged", "claimed", "unconfirmed", "leaked", "speculation"])
        is_contradicted = any(w in text.lower() for w in ["debunked", "false", "refutes", "denies", "fake"])
        is_primary = it.source_role == "PRIMARY" or it.source_tier == "TIER_1"

        if is_contradicted:
            status = "CONTRADICTED"
        elif is_primary and not is_unverified:
            status = "VERIFIED"
        elif not is_unverified and it.source_role == "SECONDARY":
            status = "SUPPORTED"
        else:
            status = "UNVERIFIED"

        claims.append({
            "claim_id": f"C-{idx+1:02d}",
            "claim_text": text,
            "status": status,
            "supporting_sources": 1 if status in ["VERIFIED", "SUPPORTED"] else 0,
            "contradicting_sources": 1 if status == "CONTRADICTED" else 0,
            "evidence_ids": [it.evidence_id],
            "source_urls": [it.url] if it.url != "Source URL unavailable" else []
        })
    return claims


def cluster_trends(
    evidence_list: List[TrendEvidence],
    entity_info: Dict[str, Any],
    velocity_calc_fn: Optional[Callable[..., Dict[str, Any]]] = None,
) -> List[Trend]:
    """
    Cluster evidence items into coherent trend stories.
    Does not lump unrelated events together.
    """
    if not evidence_list:
        return []

    # Real execution stage: invoke TrendingExtractionEngine
    from backend.agents.trending.extraction import trending_extractor
    frags = [
        EvidenceFragment(
            platform=ev.platform,
            title=ev.title,
            content=ev.content,
            snippet=ev.content[:200] if ev.content else "",
            url=ev.url,
            author=ev.source,
            published=ev.published_at,
            evidence_id=ev.evidence_id,
        )
        for ev in evidence_list
    ]
    trending_extractor.extract_trending_intelligence(
        target_name=entity_info.get("resolved_entity", "Topic"),
        fragments=frags,
    )

    categories = {
        "announcement": ["announce", "project", "reveal", "trailer", "release", "launch", "cast", "signed"],
        "controversy": ["controversy", "boycott", "backlash", "criticism", "allegation", "feud", "dispute", "scandal"],
        "viral_moment": ["viral", "look", "spotted", "airport", "fashion", "clip", "meme", "dance", "moment"],
        "box_office": ["box office", "crore", "collection", "opening", "record", "gross", "hit", "flop"],
        "personal_event": ["wedding", "birthday", "vacation", "spotted", "family", "appearance", "interview"],
        "business_tech": ["acquisition", "ai", "model", "partnership", "shares", "stock", "patent", "funding"]
    }

    clusters: Dict[str, List[TrendEvidence]] = {}

    for ev in evidence_list:
        text = f"{ev.title} {ev.content}".lower()
        assigned_cat = "general_discourse"

        for cat_name, kw_list in categories.items():
            if any(kw in text for kw in kw_list):
                assigned_cat = cat_name
                break

        clusters.setdefault(assigned_cat, []).append(ev)

    trends: List[Trend] = []
    t_idx = 1

    for cat_key, items in clusters.items():
        if not items:
            continue

        sorted_items = sorted(items, key=lambda x: parse_timestamp_epoch(x.published_at))
        first_ev = sorted_items[0]
        latest_ev = sorted_items[-1]

        if parse_timestamp_epoch(first_ev.published_at) > parse_timestamp_epoch(latest_ev.published_at):
            first_ev, latest_ev = latest_ev, first_ev

        unique_sources = len({it.source.lower() for it in items})
        unique_platforms = len({it.platform.lower() for it in items})
        independent_groups = len({it.source_group_id for it in items})

        headline = first_ev.title
        if len(headline) > 80:
            headline = headline[:80] + "..."
        topic = f"{entity_info.get('resolved_entity', 'Topic')}: {headline}"

        narratives = extract_narratives_from_cluster(items)
        claims = extract_claims_from_cluster(items)
        sent_label, sent_score = compute_cluster_sentiment(items)
        misinfo_risk, misinfo_rationale = evaluate_misinformation_risk(items, claims)

        entity_key = f"{entity_info.get('resolved_entity', 'global')}_{cat_key}"
        if velocity_calc_fn:
            velocity = velocity_calc_fn(topic, len(items), unique_sources, unique_platforms, entity_key=entity_key)
        else:
            velocity = calculate_velocity(topic, len(items), unique_sources, unique_platforms, entity_key=entity_key)

        origin = {
            "first_observed_source": first_ev.source,
            "first_observed_platform": first_ev.platform,
            "first_observed_at": first_ev.published_at,
            "amplification_platforms": list({it.platform for it in items if it.platform != first_ev.platform})
        }

        v_status = velocity.get("velocity_status") or velocity.get("status", "INSUFFICIENT_HISTORY")
        if v_status == "INSUFFICIENT_HISTORY" or len(velocity.get("history", [])) <= 1:
            trend_nature = "NEWLY_OBSERVED"
        elif v_status == "ACCELERATING" and unique_platforms >= 3:
            trend_nature = "VIRAL"
        elif unique_platforms >= 2 and independent_groups >= 2:
            trend_nature = "TRENDING"
        elif cat_key in ["announcement", "box_office", "business_tech"] and any(it.source_role == "PRIMARY" for it in items):
            trend_nature = "NEWSWORTHY"
        elif len(velocity.get("history", [])) >= 3:
            trend_nature = "RECURRING"
        elif len(items) >= 5:
            trend_nature = "HIGH_VOLUME"
        else:
            trend_nature = "NEWLY_OBSERVED"

        if v_status == "INSUFFICIENT_HISTORY":
            why_trending = (
                f"Circulating across {unique_platforms} platform(s) with {independent_groups} independent source group(s) "
                f"and {len(items)} verified evidence signals (single observation baseline; rate of change requires second scan)."
            )
        else:
            why_trending = (
                f"Circulating across {unique_platforms} platform(s) with {independent_groups} independent source group(s) "
                f"and {len(items)} verified evidence signals ({v_status.lower()} velocity)."
            )

        emergence_window = f"{first_ev.published_at} to {latest_ev.published_at}"
        underlying_event = first_ev.title

        debunk_status = "NO_CONTRADICTION"
        if misinfo_risk == "HIGH":
            debunk_status = "DISPUTED"
        elif misinfo_risk == "MEDIUM":
            debunk_status = "UNVERIFIED"

        trends.append(Trend(
            trend_id=f"T-{t_idx:02d}",
            topic=topic,
            category=cat_key,
            first_seen_at=first_ev.published_at,
            latest_seen_at=latest_ev.published_at,
            signal_count=len(items),
            source_count=len(items),
            unique_source_count=unique_sources,
            independent_source_count=independent_groups,
            platform_count=unique_platforms,
            velocity=velocity,
            origin=origin,
            narratives=narratives,
            claims=claims,
            sentiment=sent_label,
            sentiment_score=sent_score,
            misinformation_risk=misinfo_risk,
            misinformation_rationale=misinfo_rationale,
            evidence_ids=[it.evidence_id for it in items],
            status="active" if velocity.get("status") in ["ACTIVE", "ACCELERATING"] else "stable",
            trend_nature=trend_nature,
            why_trending=why_trending,
            emergence_window=emergence_window,
            underlying_event=underlying_event,
            debunk_status=debunk_status,
            contradictions=[]
        ))
        t_idx += 1

    return trends
