"""
Aegis Protocol — Scout Source Orchestration Engine
===================================================
Master coordinator for Agent 1 Scout's market intelligence extraction,
corroboration, and evidence production.

CRITICAL ARCHITECTURE INVARIANT:
Scout does NOT own an independent network retrieval stack. All network
discovery and content acquisition flows strictly through the authoritative
Shared Acquisition Fabric (AgentReachService / NativeRouter). Scout acts
purely as an orchestration and domain extraction layer.
"""

import logging
import time
from typing import List, Optional

from backend.services.agent_reach.adapter import agent_reach_service
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalRequest
from backend.agents.scout.sources.corroboration import scout_corroboration_engine
from backend.agents.scout.sources.deduplication import scout_deduplicator
from backend.agents.scout.sources.extraction import (
    corporate_event_extractor,
    financial_number_extractor,
    temporal_extractor,
)
from backend.agents.scout.sources.models import (
    CorporateEventType,
    EpistemicStatus,
    ScoutEvidence,
    ScoutResult,
    ScoutSourceRequest,
    SourceTier,
)
from backend.agents.scout.sources.telemetry import ScoutTelemetry

logger = logging.getLogger(__name__)


class ScoutSourceEngine:
    """
    Scout orchestration and financial domain extraction engine.
    Consumes EvidenceFragment objects from the Shared Acquisition Fabric
    and extracts structured corporate events, financial numbers, story clusters,
    and contradiction matrices.
    """

    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency

    def execute(self, request: ScoutSourceRequest) -> ScoutResult:
        """
        Execute Scout pipeline:
        1. Delegate network acquisition to Shared Acquisition Fabric (AgentReachService).
        2. Convert normalized EvidenceFragment objects to ScoutEvidence with domain extraction.
        3. Deduplication: Detect wire syndication and cluster identical stories.
        4. Corroboration: Cross-check claims, detect financial number contradictions.
        5. Epistemic Assessment: Assign OFFICIAL | CONFIRMED | REPORTED | UNCONFIRMED | CONTRADICTED.
        """
        telemetry = ScoutTelemetry()
        t0 = time.time()

        # 1. Delegate network acquisition to Shared Acquisition Fabric
        channels = ["web", "news"]
        if request.allow_social:
            channels.extend(["reddit", "twitter"])

        from backend.services.agent_reach.profile import SCOUT_PROFILE

        retrieval_request = RetrievalRequest(
            request_id=f"scout_{int(time.time()*1000)}",
            agent="scout",
            entity=request.target_entity or request.query,
            intent="market_intelligence",
            task_type="SEARCH",
            scope=request.requested_scope,
            allowed_channels=channels,
            candidate_budget=request.max_candidates or 5,
            query=request.query,
            profile=SCOUT_PROFILE,
            metadata={"tickers": request.tickers},
        )

        t_acq = time.time()
        fragments: List[EvidenceFragment] = agent_reach_service.execute(retrieval_request)
        telemetry.acquisition_latency_ms = int((time.time() - t_acq) * 1000)
        telemetry.candidates_discovered = len(fragments)
        telemetry.acquisitions_attempted = len(fragments)
        telemetry.acquisitions_successful = len(fragments)
        telemetry.network_requests_count = len(fragments)

        # 2. Convert to ScoutEvidence and apply domain extractors
        acquired_evidence: List[ScoutEvidence] = []
        for idx, frag in enumerate(fragments):
            tier = (
                SourceTier.TIER_2_PRESS
                if frag.platform in ("web", "news")
                else SourceTier.TIER_4_COMMUNITY
            )
            is_primary = (
                frag.platform in ("github", "sec_edgar")
                or "official" in frag.title.lower()
                or (request.target_entity and request.target_entity.lower() in frag.author.lower())
            )

            text_corpus = f"{frag.title}. {frag.content or frag.snippet}"
            scout_ev = ScoutEvidence(
                evidence_id=frag.evidence_id,
                url=frag.url,
                canonical_url=frag.url,
                platform=frag.platform,
                source_type="article" if frag.platform in ("web", "news") else "post",
                source_tier=tier.value if hasattr(tier, "value") else str(tier),
                external_id=frag.evidence_id,
                title=frag.title,
                author=frag.author,
                body=frag.content or frag.snippet,
                snippet=frag.snippet or frag.title,
                published_at=frag.published,
                event_at=None,
                retrieved_at=frag.retrieved_at,
                is_primary=is_primary,
            )

            # Extract financial numbers & corporate events
            scout_ev.financial_facts = financial_number_extractor.extract_from_text(
                text_corpus, source_url=frag.url
            )
            scout_ev.events = corporate_event_extractor.extract_from_text(
                text_corpus, source_url=frag.url
            )

            # Temporal disambiguation
            temp_res = temporal_extractor.extract(text_corpus, frag.published)
            scout_ev.event_at = temp_res["event_at"]

            acquired_evidence.append(scout_ev)
            telemetry.sources_by_tier[tier] = telemetry.sources_by_tier.get(tier, 0) + 1

        # 3. Deduplication & Story Clustering
        deduped_evidence, clusters = scout_deduplicator.cluster_evidence(acquired_evidence)

        # 4. Corroboration & Contradiction Detection
        contradictions = scout_corroboration_engine.analyze_corroboration(
            deduped_evidence, clusters
        )

        # 5. Aggregate facts & events
        all_facts = []
        all_events = []
        for ev in deduped_evidence:
            all_facts.extend(ev.financial_facts)
            all_events.extend(ev.events)

        primary_present = any(ev.is_primary for ev in deduped_evidence)
        independent_sources = list({ev.author for ev in deduped_evidence if not ev.syndicated_from})

        # Epistemic status evaluation
        epistemic = (
            EpistemicStatus.CONTRADICTED
            if contradictions
            else (
                EpistemicStatus.OFFICIAL
                if primary_present
                else (
                    EpistemicStatus.CONFIRMED
                    if len(independent_sources) >= 2
                    else (
                        EpistemicStatus.REPORTED
                        if len(deduped_evidence) >= 1
                        else EpistemicStatus.UNCONFIRMED_RUMOR
                    )
                )
            )
        )

        total_lat = int((time.time() - t0) * 1000)
        telemetry.total_latency_ms = total_lat

        return ScoutResult(
            query=request.query,
            entity=request.target_entity,
            evidence_items=deduped_evidence,
            clusters=clusters,
            financial_facts=all_facts,
            events=all_events,
            contradictions=contradictions,
            primary_source_present=primary_present,
            independent_source_count=len(independent_sources),
            epistemic_status=epistemic.value,
            telemetry=telemetry.to_dict(),
        )


# Global singleton engine instance
scout_source_engine = ScoutSourceEngine()

