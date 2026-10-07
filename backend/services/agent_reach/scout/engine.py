"""
Aegis Protocol — Scout Source Acquisition Engine
=================================================
Master coordinator for Agent 1 Scout's proprietary source acquisition,
extraction, corroboration, and evidence production.
"""

import concurrent.futures
import logging
import time
from typing import List, Optional

from backend.services.agent_reach.scout.adapters import ALL_SCOUT_ADAPTERS, ScoutSourceAdapter
from backend.services.agent_reach.scout.cache import scout_cache
from backend.services.agent_reach.scout.corroboration import scout_corroboration_engine
from backend.services.agent_reach.scout.deduplication import scout_deduplicator
from backend.services.agent_reach.scout.discovery import scout_discovery
from backend.services.agent_reach.scout.models import (
    CandidateSource,
    EpistemicStatus,
    RawSource,
    ScoutEvidence,
    ScoutResult,
    ScoutSourceRequest,
)
from backend.services.agent_reach.scout.ranking import scout_ranking_engine
from backend.services.agent_reach.scout.telemetry import ScoutTelemetry

logger = logging.getLogger(__name__)


class ScoutSourceEngine:
    """
    Proprietary source discovery, acquisition, extraction, and validation engine
    powering Scout (Agent 1).
    """

    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.adapters: List[ScoutSourceAdapter] = ALL_SCOUT_ADAPTERS

    def execute(self, request: ScoutSourceRequest) -> ScoutResult:
        """
        Execute the end-to-end Scout source acquisition pipeline:
        1. Discovery: Generate multi-engine candidate pools.
        2. Candidate Gate: Apply hard rejection rules & rank Top-5 candidates.
        3. Acquisition Cascade: Concurrently fetch content via specialist adapters.
        4. Structured Extraction: Extract metadata, financial numbers, events.
        5. Deduplication: Detect wire syndication and cluster identical stories.
        6. Corroboration: Cross-check claims, flag contradictions.
        7. Evidence Normalization: Emit ScoutResult with full telemetry.
        """
        telemetry = ScoutTelemetry()
        t0 = time.time()

        # 1. Discovery Phase
        t_disc = time.time()
        discovered_candidates = scout_discovery.discover_candidates(request)
        telemetry.discovery_latency_ms = int((time.time() - t_disc) * 1000)
        telemetry.candidates_discovered = len(discovered_candidates)

        # 2. Hard Gates & Ranking Phase
        ranked_candidates = scout_ranking_engine.rank_candidates(discovered_candidates, request)
        telemetry.candidates_accepted_gates = len(ranked_candidates)
        telemetry.candidates_rejected_gates = len(discovered_candidates) - len(ranked_candidates)

        # 3. Acquisition Cascade (Bounded Concurrency)
        t_acq = time.time()
        acquired_evidence: List[ScoutEvidence] = []

        def _process_candidate(cand: CandidateSource) -> Optional[ScoutEvidence]:
            # Cache check
            cache_key = f"scout_source:{cand.canonical_url}"
            if not request.force_refresh:
                cached_ev = scout_cache.get(cache_key)
                if cached_ev:
                    telemetry.cache_hits += 1
                    return cached_ev

            telemetry.cache_misses += 1
            # Select matching adapter
            adapter = None
            for a in self.adapters:
                if a.can_handle(cand):
                    adapter = a
                    break

            if not adapter:
                return None

            try:
                telemetry.acquisitions_attempted += 1
                telemetry.network_requests_count += 1
                raw = adapter.acquire(cand, request)
                telemetry.bytes_retrieved += raw.bytes_retrieved

                if raw.status_code == 200 and raw.content_raw:
                    telemetry.acquisitions_successful += 1
                    evidence = adapter.extract(raw, request)
                    if evidence:
                        scout_cache.set(cache_key, evidence, ttl_sec=600.0)
                        return evidence
                else:
                    telemetry.acquisitions_failed += 1
            except Exception as e:
                logger.debug(f"[ScoutSourceEngine] Acquisition exception for {cand.canonical_url}: {e}")
                telemetry.acquisitions_failed += 1

            return None

        # Execute parallel bounded acquisitions
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            future_to_cand = {executor.submit(_process_candidate, c): c for c in ranked_candidates}
            for future in concurrent.futures.as_completed(future_to_cand):
                res = future.result()
                if res:
                    acquired_evidence.append(res)
                    tier = res.source_tier
                    telemetry.sources_by_tier[tier] = telemetry.sources_by_tier.get(tier, 0) + 1

        telemetry.acquisition_latency_ms = int((time.time() - t_acq) * 1000)

        # 4. Deduplication & Story Clustering
        deduped_evidence, clusters = scout_deduplicator.cluster_evidence(acquired_evidence)

        # 5. Corroboration & Contradiction Detection
        contradictions = scout_corroboration_engine.analyze_corroboration(deduped_evidence, clusters)

        # Aggregate facts & events
        all_facts = []
        all_events = []
        for ev in deduped_evidence:
            all_facts.extend(ev.financial_facts)
            all_events.extend(ev.events)

        primary_present = any(ev.is_primary for ev in deduped_evidence)
        independent_sources = list({ev.author for ev in deduped_evidence if not ev.syndicated_from})

        # Epistemic status
        epistemic = (
            EpistemicStatus.CONTRADICTED if contradictions
            else (EpistemicStatus.OFFICIAL if primary_present
            else (EpistemicStatus.CONFIRMED if len(independent_sources) >= 2
            else (EpistemicStatus.REPORTED if len(deduped_evidence) >= 1
            else EpistemicStatus.UNCONFIRMED_RUMOR)))
        )

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
