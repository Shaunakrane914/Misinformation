"""
Aegis Protocol — Trending Agent 2.0
===================================
Autonomous Trend Discovery & Multi-Source Trend Intelligence Engine.
Owns domain entity resolution, trend-specific query planning, clustering,
syndication detection, velocity tracking, and trend intelligence reporting.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.trending.assessment import (
    compute_cluster_sentiment,
    evaluate_misinformation_risk,
)
from backend.agents.trending.clustering import (
    cluster_trends,
    detect_syndication_group,
    extract_claims_from_cluster,
    extract_narratives_from_cluster,
)
from backend.agents.trending.discovery import (
    fetch_box_office,
    fetch_news,
    fetch_paparazzi,
    fetch_targeted_news,
    resolve_entity,
)
from backend.agents.trending.models import (
    KNOWN_ENTITY_CATALOG,
    WIRE_SIGNATURES,
    Trend,
    TrendClaim,
    TrendEvidence,
    TrendNarrative,
)
from backend.agents.trending.temporal import (
    calculate_velocity,
    parse_timestamp_epoch,
)
from backend.services.agent_reach import agent_reach_service
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalRequest
from backend.services.agent_reach.planner import RetrievalPlanner
from backend.services.research import ResearchRequest, research_engine
from backend.services.research.relevance_gate import relevance_gate

logger = logging.getLogger(__name__)

# Try importing ApifyClient safely
try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None


class TrendingAgent:
    """
    Trending Agent 2.0: Real-Time Trend Discovery & Trend Intelligence Engine.
    Operates in Entity Mode and Discovery Mode with zero synthetic hallucinations.
    """

    # In-memory snapshot persistence for real velocity and time-series charts
    _trend_history: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, client: Optional[Any] = None) -> None:
        token = os.getenv("APIFY_TOKEN")
        if client:
            self.client = client
        elif token and ApifyClient:
            try:
                self.client = ApifyClient(token)
            except Exception as e:
                logger.warning(f"Apify initialization failed: {e}")
                self.client = None
        else:
            self.client = None
            logger.info("APIFY_TOKEN missing — paparazzi direct scraping will be skipped.")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Mode Detection & Entity Resolution
    # ─────────────────────────────────────────────────────────────────────────

    def resolve_entity(self, input_text: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Normalize input and detect whether query is Entity Mode or Discovery Mode."""
        return resolve_entity(input_text, category=category)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Multi-Channel Ingestion (Agent Reach & Fallbacks)
    # ─────────────────────────────────────────────────────────────────────────

    def fetch_news(self, keyword: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Fetch news headlines via shared acquisition fabric with clean URL and source parsing."""
        return fetch_news(keyword, limit=limit)

    def fetch_targeted_news(self, query: str, window_mins: int = 1440) -> List[Dict[str, Any]]:
        """Fetch targeted news articles within time window for /api/trending-news."""
        return fetch_targeted_news(query, window_mins=window_mins, fetch_news_fn=self.fetch_news)

    def fetch_paparazzi(self, instagram_url: str, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
        """Scrape latest Instagram posts via Apify if available with bounded timeout."""
        return fetch_paparazzi(instagram_url, client=self.client, timeout_seconds=timeout_seconds)

    def fetch_box_office(self, movie_name: str) -> Dict[str, Any]:
        """Truthful Box Office telemetry handler."""
        return fetch_box_office(movie_name)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Evidence Normalization & Provenance
    # ─────────────────────────────────────────────────────────────────────────

    def _normalize_evidence(
        self,
        raw_items: List[Dict[str, Any]],
        platform_name: str,
        retrieval_method: str = "agent_reach"
    ) -> List[TrendEvidence]:
        """Convert raw channel results into normalized TrendEvidence objects."""
        normalized: List[TrendEvidence] = []

        for idx, item in enumerate(raw_items):
            ev_id = f"EV-{platform_name.upper()[:2]}-{idx + 1:03d}"
            title = item.get("title") or item.get("headline") or item.get("caption") or item.get("text") or "Trend signal"
            content = item.get("content") or item.get("snippet") or item.get("summary") or item.get("text") or title
            snippet = content[:200] + ("..." if len(content) > 200 else "")

            # URL validation: never allow '#' or empty URLs
            raw_url = str(item.get("url") or item.get("link") or "").strip()
            if not raw_url or raw_url == "#" or not raw_url.startswith("http"):
                url = "Source URL unavailable"
            else:
                url = raw_url

            # Determine source role and tier
            source = str(item.get("source") or item.get("channel") or item.get("author") or platform_name.title())
            author = str(item.get("author") or item.get("channel") or source)

            source_role = "SECONDARY"
            source_tier = "TIER_2"

            p_lower = platform_name.lower()
            if p_lower in ["reddit", "twitter", "x"]:
                source_role = "COMMUNITY"
                source_tier = "TIER_4"
            elif p_lower in ["youtube", "video"]:
                source_role = "COMMENTARY"
                source_tier = "TIER_3"
            elif p_lower in ["instagram", "paparazzi"]:
                source_role = "DIRECT_MEDIA"
                source_tier = "TIER_3"
            elif any(w in source.lower() for w in WIRE_SIGNATURES):
                source_role = "PRIMARY"
                source_tier = "TIER_1"

            # Check for wire syndication signature
            source_group_id = self._detect_syndication_group(title, source)

            pub_time = item.get("published") or item.get("published_at") or item.get("taken_at")
            if not pub_time:
                pub_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            normalized.append(TrendEvidence(
                evidence_id=ev_id,
                platform=platform_name,
                source=source,
                title=title[:220],
                content=content[:1000],
                snippet=snippet,
                url=url,
                canonical_url=url if url != "Source URL unavailable" else "",
                author=author,
                published_at=str(pub_time),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                source_role=source_role,
                source_tier=source_tier,
                source_group_id=source_group_id,
                retrieval_method=retrieval_method,
                metadata=item.get("metadata", {})
            ))

        return normalized

    def _detect_syndication_group(self, title: str, source: str) -> str:
        """Assign unified group ID to syndicated wire stories to detect duplication."""
        return detect_syndication_group(title, source)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Trend Clustering & Narrative Extraction
    # ─────────────────────────────────────────────────────────────────────────

    def _cluster_trends(
        self,
        evidence_list: List[TrendEvidence],
        entity_info: Dict[str, Any]
    ) -> List[Trend]:
        """Cluster evidence items into coherent trend stories."""
        return cluster_trends(
            evidence_list,
            entity_info,
            velocity_calc_fn=self._calculate_velocity,
        )

    _heuristic_trend_clustering = _cluster_trends

    def _extract_narratives_from_cluster(self, items: List[TrendEvidence]) -> List[Dict[str, Any]]:
        """Extract dominant narrative angles with evidence citations."""
        return extract_narratives_from_cluster(items)

    def _extract_claims_from_cluster(self, items: List[TrendEvidence]) -> List[Dict[str, Any]]:
        """Extract circulating factual claims and assign verification status."""
        return extract_claims_from_cluster(items)

    def _compute_cluster_sentiment(self, items: List[TrendEvidence]) -> Tuple[str, int]:
        """Calculate sentiment independently from misinformation."""
        return compute_cluster_sentiment(items)

    def _evaluate_misinformation_risk(
        self,
        items: List[TrendEvidence],
        claims: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """Evaluate misinformation risk."""
        return evaluate_misinformation_risk(items, claims)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Velocity, Momentum & Snapshot Persistence
    # ─────────────────────────────────────────────────────────────────────────

    def _calculate_velocity(
        self,
        topic: str,
        signal_count: int,
        source_count: int,
        platform_count: int,
        entity_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute real trend velocity and momentum from actual historical snapshots."""
        return calculate_velocity(
            topic=topic,
            signal_count=signal_count,
            source_count=source_count,
            platform_count=platform_count,
            entity_key=entity_key,
            history_store=self._trend_history,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Main Intelligence Scan Pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def scan(
        self,
        asset_name: str,
        identifiers: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute full Trend Discovery & Intelligence Pipeline."""
        start_time = time.time()
        identifiers = identifiers or {}
        instagram_url = identifiers.get("instagram_url") or identifiers.get("instagram")
        hashtag = identifiers.get("hashtag")
        check_box_office = identifiers.get("box_office", False)

        # 1. Entity Resolution & Mode Classification
        entity_res = self.resolve_entity(asset_name, category=category)
        if mode in ["entity", "discovery"]:
            entity_res["mode"] = mode

        target_query = entity_res.get("resolved_entity") or asset_name
        is_discovery = entity_res.get("mode") == "discovery"

        # 2. Query Planning via Agent Reach Planner
        planner = RetrievalPlanner()
        multi_queries, query_classes = planner.build_multi_channel_queries(
            target_query,
            domain="trending"
        )

        # 3. Multi-Channel Retrieval & Deep Research Investigation via Shared Research Engine
        all_raw_evidence: List[TrendEvidence] = []
        channel_health: Dict[str, Dict[str, Any]] = {}
        retrieval_trace: Dict[str, Any] = {}
        research_findings = []
        research_contradictions = []

        try:
            research_req = ResearchRequest(
                target=target_query,
                domain="trending",
                agent_name="trending",
                intent=f"discover emerging viral trends, public narratives, and cross-channel discourse for {target_query}",
                query_classes=list(query_classes.keys()) if isinstance(query_classes, dict) else query_classes,
                deep_read_budget=15,
                corroboration_budget=2,
            )
            research_res = research_engine.investigate(research_req)
            retrieval_trace = research_res.telemetry
            research_findings = research_res.findings
            research_contradictions = research_res.contradictions

            for item in research_res.evidence:
                ch = item.channel or "web"
                ev_id = f"EV-{ch.upper()[:2]}-{len(all_raw_evidence) + 1:03d}"
                role = item.source_role
                tier = item.source_tier
                group = item.independence_group
                url = item.canonical_url or "Source URL unavailable"

                all_raw_evidence.append(TrendEvidence(
                    evidence_id=ev_id,
                    platform=ch,
                    source=item.source_name or ch,
                    title=item.title[:220],
                    content=item.content[:1000] if item.content else item.snippet[:1000],
                    snippet=(item.relevant_excerpt or item.snippet)[:300],
                    url=url,
                    canonical_url=url if url != "Source URL unavailable" else "",
                    author=item.source_name or ch,
                    published_at=item.published_at or "",
                    retrieved_at=item.discovered_at or datetime.now(timezone.utc).isoformat(),
                    source_role=role,
                    source_tier=tier,
                    source_group_id=group,
                    retrieval_method="agent_reach",
                    discovered_candidate_id=getattr(item, "discovered_id", getattr(item, "id", None)),
                    ranked_candidate_id=getattr(item, "ranked_id", None),
                    accepted_candidate_id=getattr(item, "accepted_id", None),
                    acquisition_attempt_id=getattr(item, "acquisition_attempt_id", None),
                    acquired_candidate_id=getattr(item, "acquired_id", None),
                    selection_decision=getattr(item, "selection_decision", "ACCEPTED"),
                    selection_reason=getattr(item, "selection_reason", "ACQUIRED_EVIDENCE"),
                    metadata={
                        "content_depth": item.content_depth,
                        "query_id": item.query_id,
                        "query_class": item.query_class,
                        "query_text": item.query_text,
                        "relevant_excerpt": item.relevant_excerpt,
                        "independence_score": item.independence_score,
                    }
                ))

            for ch_name, status in retrieval_trace.get("channel_health", {}).items():
                channel_health[ch_name] = {
                    "status": status,
                    "retrieved_count": sum(1 for f in research_res.evidence if f.channel == ch_name),
                    "latency_ms": retrieval_trace.get("total_latency_ms", 500)
                }

        except Exception as reach_err:
            logger.warning(f"[TrendingAgent] ResearchEngine investigate encountered: {reach_err}")

        # Fallback to direct news retrieval if research_engine produced no evidence
        if not all_raw_evidence:
            news_raw = self.fetch_news(target_query, limit=8)
            if news_raw:
                news_norm = self._normalize_evidence(news_raw, "news", retrieval_method="news")
                all_raw_evidence.extend(news_norm)
                channel_health["news"] = {
                    "status": "LIMITED",
                    "retrieved_count": len(news_raw),
                    "latency_ms": None,
                    "content_class": "SYNDICATED_OR_INDEXED",
                    "limitation": "Fallback result count does not prove direct article acquisition",
                }

        accepted_ev, _ = relevance_gate.filter_candidates(
            all_raw_evidence,
            target_entity=target_query,
            domain="trending"
        )
        usable_evidence = accepted_ev

        # Deduplicate evidence by clean title/content
        seen_titles = set()
        deduped_evidence: List[TrendEvidence] = []
        for ev in usable_evidence:
            norm_k = re.sub(r'[^a-zA-Z0-9]', '', ev.title.lower()[:50])
            if norm_k not in seen_titles:
                seen_titles.add(norm_k)
                deduped_evidence.append(ev)

        # 6. Trend Clustering & Intelligence Extraction
        trends = self._cluster_trends(deduped_evidence, entity_res)

        # 7. Truthful Box Office
        box_office_data = {}
        if check_box_office or entity_res.get("category") == "cinema":
            box_office_data = self.fetch_box_office(target_query)

        # 8. Timeline Construction
        timeline = []
        for ev in sorted(deduped_evidence, key=lambda x: parse_timestamp_epoch(x.published_at))[:10]:
            timeline.append({
                "timestamp": ev.published_at,
                "platform": ev.platform,
                "source": ev.source,
                "event": ev.title,
                "url": ev.url
            })

        # 9. Aggregate Platform Breakdown
        platform_breakdown: Dict[str, int] = {}
        for ev in deduped_evidence:
            platform_breakdown[ev.platform] = platform_breakdown.get(ev.platform, 0) + 1

        # 10. Backward Compatibility Feed Items (threats array for legacy API)
        feed_items = []
        for ev in deduped_evidence:
            feed_items.append({
                "title": ev.title,
                "source": ev.source,
                "summary": ev.snippet,
                "url": ev.url,
                "is_threat": ev.source_role == "COMMUNITY" and any(w in ev.title.lower() for w in ["boycott", "scandal", "leak", "fake"]),
                "sentiment": -40 if any(w in ev.title.lower() for w in ["boycott", "scandal", "leak", "fake"]) else 25
            })

        threat_count = sum(1 for f in feed_items if f.get("is_threat"))
        safe_count = len(feed_items) - threat_count

        scan_duration = round(time.time() - start_time, 2)

        limitations = []
        if not deduped_evidence:
            limitations.append("No verified live trend evidence was retrieved for this query.")
        if channel_health.get("instagram", {}).get("status") == "unavailable":
            limitations.append("Instagram / Paparazzi node unavailable or rate-limited.")

        chart_history = []
        if trends:
            primary_trend = trends[0]
            chart_history = primary_trend.velocity.get("history", [])

        paparazzi_items = [e.to_dict() for e in deduped_evidence if e.platform in ["instagram", "paparazzi"]]

        return {
            # Legacy fields for backward compatibility
            "asset_name": asset_name,
            "identifiers": identifiers,
            "threats": feed_items,
            "threat_count": threat_count,
            "safe_count": safe_count,
            "sources": {
                "news": [e.to_dict() for e in deduped_evidence if e.platform == "news"],
                "paparazzi": paparazzi_items,
                "box_office": box_office_data,
                "fan_wars": [e.to_dict() for e in deduped_evidence if e.platform in ["twitter", "reddit", "youtube"]]
            },
            "counts": {
                "paparazzi": len(paparazzi_items),
                "news": len([e for e in deduped_evidence if e.platform == "news"]),
                "fan_wars": len([e for e in deduped_evidence if e.platform in ["twitter", "reddit", "youtube"]]),
                "total_threats": threat_count,
                "threat_count": threat_count,
                "safe_count": safe_count,
                "total_items": len(feed_items)
            },

            # Trending Agent 2.0 Schema
            "mode": entity_res.get("mode", "entity"),
            "entity_resolution": entity_res,
            "retrieval": {
                "plan": query_classes,
                "channels": channel_health,
                "scan_time_s": scan_duration,
                "deep_reads": retrieval_trace.get("deep_read_success", 0),
                "trace": retrieval_trace,
            },
            "retrieval_trace": retrieval_trace,
            "trends": [t.to_dict() for t in trends],
            "evidence": [e.to_dict() for e in deduped_evidence],
            "findings": [f.to_dict() if hasattr(f, "to_dict") else f for f in research_findings],
            "contradictions": [c.to_dict() if hasattr(c, "to_dict") else c for c in research_contradictions],
            "deep_research_trace": retrieval_trace,
            "timeline": timeline,
            "platform_breakdown": platform_breakdown,
            "chart_history": chart_history,
            "box_office": box_office_data,
            "telemetry": {
                "signals_retrieved": len(deduped_evidence),
                "unique_sources": len({e.source.lower() for e in deduped_evidence}),
                "independent_groups": len({e.source_group_id for e in deduped_evidence}),
                "platforms_active": len(platform_breakdown),
                "discovered_trends": len(trends),
                "deep_reads": retrieval_trace.get("deep_read_success", 0),
                "acquisition_attempts": retrieval_trace.get("acquisition_attempts", []),
                "scan_duration_s": scan_duration
            },
            "limitations": limitations
        }

    def generate_trending_intelligence(
        self,
        person: str,
        trend_window: str = "24h",
        check_paparazzi: bool = False,
        check_box_office: bool = False
    ) -> Dict[str, Any]:
        """Aegis Protocol Output Contract implementation for Trending Agent."""
        scan_res = self.scan_trends(
            asset_name=person,
            identifiers={"box_office": check_box_office, "paparazzi": check_paparazzi}
        )

        entity_res = scan_res.get("entity_resolution", {})
        canonical_name = entity_res.get("resolved_entity") or person
        confidence = float(entity_res.get("confidence", 0.85))

        evidence_items = scan_res.get("evidence", [])
        trends = scan_res.get("trends", [])
        narratives = []
        for t in trends:
            for narr in t.get("narratives", []):
                narratives.append(narr)

        # 1. Observed facts
        observed: List[str] = []
        for ev in evidence_items[:5]:
            observed.append(f"Direct publication ({ev.get('platform')}/{ev.get('source')}): {ev.get('title')}")
        box_office = scan_res.get("box_office", {})
        if box_office.get("reported_gross"):
            observed.append(f"Reported box office revenue: {box_office.get('reported_gross')}")

        # 2. Inferred interpretations
        inferred: List[str] = []
        for t in trends[:3]:
            vel = t.get("velocity", {}).get("label", "STABLE")
            inferred.append(f"Narrative '{t.get('topic')}' exhibits {vel} spread velocity across {t.get('platform_count', 1)} platforms.")
        if not inferred and evidence_items:
            inferred.append(f"Public attention is steady with {len(evidence_items)} recorded signals.")

        # 3. Uncertain / Unknown
        uncertain: List[str] = []
        for t in trends:
            if t.get("misinformation_risk") in ("HIGH", "MEDIUM"):
                uncertain.append(f"Potential unverified viral narrative: {t.get('topic')} ({t.get('misinformation_rationale')})")
        for contra in scan_res.get("contradictions", []):
            uncertain.append(f"Contradictory reporting detected: {contra}")
        if not evidence_items:
            uncertain.append(f"No verified public signals discovered in current monitoring window for {canonical_name}.")

        primary_sentiment = "neutral"
        sentiment_conf = 0.50
        sample_basis = f"Sampled {len(evidence_items)} public articles/posts"
        if trends:
            primary_sentiment = trends[0].get("sentiment", "NEUTRAL").lower()
            sentiment_conf = 0.75

        retrieval_trace = scan_res.get("retrieval_trace", {})
        fallback_used = retrieval_trace.get("fallback_rate", 0.0) > 0.0
        fallback_reason = "SEARCH_INDEX_FALLBACK" if fallback_used else None

        return {
            "agent": "trending",
            "person": canonical_name,
            "identity_confidence": round(confidence, 2),
            "trend_window": trend_window,
            "top_trends": trends,
            "narrative_clusters": narratives,
            "timeline": scan_res.get("timeline", []),
            "observed": observed,
            "inferred": inferred,
            "uncertain": uncertain,
            "sentiment": {
                "direction": primary_sentiment if primary_sentiment in ("positive", "negative", "mixed", "neutral", "unknown") else "neutral",
                "confidence": sentiment_conf,
                "sample_basis": sample_basis
            },
            "sources": evidence_items,
            "corroboration": scan_res.get("findings", []),
            "contradictions": scan_res.get("contradictions", []),
            "retrieval": {
                "direct": not fallback_used,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason
            }
        }

    # Backward-compatible aliases
    generate_intelligence = generate_trending_intelligence
    scan_trends = scan


trending_agent = TrendingAgent()

__all__ = [
    "TrendingAgent",
    "trending_agent",
]
