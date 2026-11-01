"""Allegation vs. Evidence Assessment Engine.

Synthesizes atomic claims, passage-level stance evidence, and source independence
into the user-facing Allegation vs. Evidence Matrix (Deliverable 1), detecting
deceptive framing patterns and generating calibrated epistemic verdicts across
the 6 standard states:
- SUPPORTED
- REFUTED
- MISLEADING_CONTEXT
- MIXED
- UNVERIFIED
- INSUFFICIENT_EVIDENCE

Strictly adheres to Aegis Protocol Invariants:
1. Corporate Denial Invariant: A corporate statement denying an allegation is
   recorded as evidence of a denial, NOT automatic proof that the allegation is false.
2. Temporal & Scope Invariant: Historical events (e.g. 2021 recall) do not substantiate
   allegations asserting new/current events (e.g. today's nationwide recall).
3. Corroboration Illusion Invariant: Reprints and syndication chains cannot inflate
   epistemic certainty.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.services.claim_intelligence.models import (
    AllegationMatrixItem,
    AtomicClaim,
    CorroborationSummary,
    DeceptiveFramingType,
    EpistemicOutcome,
    EvidenceLink,
    MisinformationDossier,
    NarrativeVersion,
    SourceRelationship,
    StanceType,
)

logger = logging.getLogger(__name__)


class AllegationAssessmentEngine:
    """Evaluates atomic claims against evidence links and source independence."""

    def assess_claim(
        self,
        claim: AtomicClaim,
        evidence_links: List[EvidenceLink],
        corroboration_summary: Optional[CorroborationSummary] = None,
        registries_checked: Optional[List[str]] = None,
    ) -> AllegationMatrixItem:
        """Construct a side-by-side Allegation vs. Evidence Matrix item."""
        checked_regs = registries_checked or [
            "Official Corporate Press Registry",
            "Regulatory Filings (SEC / EDGAR / FDA / FTC)",
            "Authoritative News Wires (Reuters, AP, Bloomberg)",
        ]

        # 1. Categorize Evidence Links
        supporting: List[EvidenceLink] = []
        contradicting: List[EvidenceLink] = []
        mentions: List[EvidenceLink] = []
        corporate_denials: List[EvidenceLink] = []
        temporal_mismatches: List[EvidenceLink] = []

        for link in evidence_links:
            if link.is_corporate_denial:
                corporate_denials.append(link)
            elif link.stance == StanceType.SUPPORTS:
                supporting.append(link)
            elif link.stance == StanceType.CONTRADICTS:
                contradicting.append(link)
            elif link.stance == StanceType.MENTIONS:
                mentions.append(link)

            if not link.temporal_match:
                temporal_mismatches.append(link)

        # 2. Detect Deceptive Framing Patterns
        deceptive_flags: List[DeceptiveFramingType] = []

        # (a) Out of context media / historical event passed off as current
        if temporal_mismatches and (claim.temporal_scope in {"today", "yesterday", "this week", "this month"} or not supporting):
            deceptive_flags.append(DeceptiveFramingType.OUT_OF_CONTEXT_MEDIA)

        # (b) Corroboration illusion (echo-chamber syndication)
        if corroboration_summary and corroboration_summary.corroboration_illusion_detected:
            deceptive_flags.append(DeceptiveFramingType.CORROBORATION_ILLUSION)

        # (c) Unsubstantiated escalation (rumor/question converted into definitive assertion)
        if any(q in {"alleged", "allegedly", "rumor", "unconfirmed", "supposedly"} for q in claim.extracted_qualifiers):
            if not supporting and (mentions or corporate_denials):
                deceptive_flags.append(DeceptiveFramingType.UNSUBSTANTIATED_ESCALATION)

        # 3. Determine Epistemic Verdict (6-State Calibrated Model)
        verdict, confidence, unverified_gaps = self._evaluate_verdict(
            claim=claim,
            supporting=supporting,
            contradicting=contradicting,
            corporate_denials=corporate_denials,
            mentions=mentions,
            temporal_mismatches=temporal_mismatches,
            corroboration_summary=corroboration_summary,
        )

        # 4. Synthesize Narratives
        allegation_summary = self._synthesize_allegation_summary(claim)
        record_summary = self._synthesize_verified_record_summary(
            claim=claim,
            verdict=verdict,
            supporting=supporting,
            contradicting=contradicting,
            corporate_denials=corporate_denials,
            temporal_mismatches=temporal_mismatches,
            checked_regs=checked_regs,
        )
        action_advisory = self._synthesize_action_advisory(
            claim=claim,
            verdict=verdict,
            corporate_denials=corporate_denials,
            unverified_gaps=unverified_gaps,
            deceptive_flags=deceptive_flags,
        )

        return AllegationMatrixItem(
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            allegation_summary=allegation_summary,
            verified_record_summary=record_summary,
            supporting_links=supporting,
            contradicting_links=contradicting,
            mention_links=mentions,
            corporate_denials=corporate_denials,
            deceptive_framing_flags=deceptive_flags,
            registries_checked=checked_regs,
            unresolved_uncertainty=unverified_gaps,
            action_advisory=action_advisory,
        )

    def _evaluate_verdict(
        self,
        claim: AtomicClaim,
        supporting: List[EvidenceLink],
        contradicting: List[EvidenceLink],
        corporate_denials: List[EvidenceLink],
        mentions: List[EvidenceLink],
        temporal_mismatches: List[EvidenceLink],
        corroboration_summary: Optional[CorroborationSummary],
    ) -> Tuple[EpistemicOutcome, float, List[str]]:
        """Calibrate verdict and compute uncertainty limitations."""
        total_evidence = len(supporting) + len(contradicting) + len(corporate_denials) + len(mentions)
        unverified_gaps: List[str] = []

        # Case 1: Insufficient Evidence (Zero topical links or strictly empty search corpus)
        if total_evidence == 0:
            unverified_gaps.append(
                f"No authoritative or public records found referencing '{claim.normalized_proposition}'."
            )
            return EpistemicOutcome.INSUFFICIENT_EVIDENCE, 0.15, unverified_gaps

        # Case 2: Temporal Framing Mismatch (Historical event presented as current event)
        if temporal_mismatches and not supporting:
            unverified_gaps.append(
                f"Identified historical events matching '{claim.predicate or 'action'}', but zero primary "
                f"records confirm the asserted time window ('{claim.temporal_scope or 'current'}')."
            )
            confidence = 0.82
            if corroboration_summary and corroboration_summary.corroboration_illusion_detected:
                confidence = max(0.65, confidence * 0.85)
            return EpistemicOutcome.MISLEADING_CONTEXT, round(confidence, 2), unverified_gaps

        # Case 3: Objective Refutation (Official debunking, registry confirmation of non-occurrence)
        if contradicting and not supporting:
            confidence = 0.88 if len(contradicting) >= 2 else 0.78
            if corporate_denials:
                unverified_gaps.append(
                    "Subject entity published a formal denial. Note that corporate denial alone is "
                    "evidence of a denial; refutation is based on objective external records."
                )
            return EpistemicOutcome.REFUTED, round(confidence, 2), unverified_gaps

        # Case 4: Objective Verification / Substantiated Claim
        if supporting and not contradicting:
            base_conf = 0.90 if len(supporting) >= 2 else 0.80
            # If echo chamber was detected, penalize confidence to avoid false certainty
            if corroboration_summary and corroboration_summary.corroboration_illusion_detected:
                base_conf = round(base_conf * 0.75, 2)
                unverified_gaps.append(
                    "Observed reporting relies heavily on a single syndicated origin; independent chain count is low."
                )
            if corporate_denials:
                # Entity denies, but primary records substantiate the event (e.g. official regulatory fine or recall notice)
                unverified_gaps.append(
                    "Entity issued a formal denial, but official public documentation confirms the underlying proposition."
                )
                return EpistemicOutcome.MIXED, round(base_conf, 2), unverified_gaps
            return EpistemicOutcome.SUPPORTED, round(base_conf, 2), unverified_gaps

        # Case 5: Contested / Mixed Evidence
        if supporting and contradicting:
            unverified_gaps.append(
                "Directly conflicting documentation exists between authoritative publishers or regulatory sources."
            )
            return EpistemicOutcome.MIXED, 0.70, unverified_gaps

        # Case 6: Corporate Denial Only (No primary proof, but entity has formally responded)
        if corporate_denials and not supporting and not contradicting:
            unverified_gaps.append(
                "Subject entity issued a public denial. In accordance with Aegis Protocol, a corporate denial alone "
                "is recorded as evidence of denial, not self-sufficient proof of falsity."
            )
            unverified_gaps.append("Independent verification from external regulatory bodies has not been published.")
            return EpistemicOutcome.UNVERIFIED, 0.65, unverified_gaps

        # Case 7: Unverified Rumor / Commentary Only
        unverified_gaps.append(
            f"Subject matter is circulating in public discourse, but no official confirmation or formal registry "
            f"record verifies the proposition for {claim.target_entity}."
        )
        return EpistemicOutcome.UNVERIFIED, 0.50, unverified_gaps

    def _synthesize_allegation_summary(self, claim: AtomicClaim) -> str:
        """Human-readable breakdown of the circulating allegation."""
        parts = [f"Allegation asserts that {claim.target_entity}"]
        if claim.predicate:
            parts.append(f"{claim.predicate}")
        else:
            parts.append(f"is involved in '{claim.normalized_proposition}'")

        if claim.subject_scope != "unspecified":
            parts.append(f"with scope '{claim.subject_scope}'")
        if claim.temporal_scope:
            parts.append(f"asserted as occurring '{claim.temporal_scope}'")

        if claim.extracted_qualifiers:
            parts.append(f"(qualifiers noted: {', '.join(claim.extracted_qualifiers)})")

        return " ".join(parts) + "."

    def _synthesize_verified_record_summary(
        self,
        claim: AtomicClaim,
        verdict: EpistemicOutcome,
        supporting: List[EvidenceLink],
        contradicting: List[EvidenceLink],
        corporate_denials: List[EvidenceLink],
        temporal_mismatches: List[EvidenceLink],
        checked_regs: List[str],
    ) -> str:
        """Synthesize what the checked public record actually demonstrates."""
        regs_str = ", ".join(checked_regs[:3])

        if verdict == EpistemicOutcome.SUPPORTED:
            pubs = ", ".join(list({l.publisher for l in supporting})[:2])
            return (
                f"Official public documentation confirmed by {pubs}. Primary filings substantiate the core "
                f"proposition regarding {claim.target_entity}."
            )
        elif verdict == EpistemicOutcome.REFUTED:
            pubs = ", ".join(list({l.publisher for l in contradicting})[:2])
            return (
                f"Authoritative investigations and public records ({pubs}) directly refute the circulating allegation. "
                f"Checked registries ({regs_str}) show no affirmative filings."
            )
        elif verdict == EpistemicOutcome.MISLEADING_CONTEXT:
            if temporal_mismatches:
                old_pubs = ", ".join(list({l.publisher for l in temporal_mismatches})[:2])
                return (
                    f"A historical event was located ({old_pubs}), but it does not substantiate the claim "
                    f"asserted for '{claim.temporal_scope or 'current'}'. Recycled or recontextualized narrative."
                )
            return (
                f"Checked sources show factual elements exist, but the overarching framing misrepresents scope, "
                f"timing, or attribution."
            )
        elif verdict == EpistemicOutcome.MIXED:
            return (
                f"Checked registries ({regs_str}) present conflicting evidence. While certain sub-claims find support, "
                f"key aspects are contested by independent sources."
            )
        elif verdict == EpistemicOutcome.UNVERIFIED:
            if corporate_denials:
                pubs = ", ".join(list({l.publisher for l in corporate_denials})[:2])
                return (
                    f"Checked registries ({regs_str}) contain zero affirmative verification. A formal denial was "
                    f"issued by {pubs}, but independent regulatory verification remains absent."
                )
            return (
                f"Checked registries ({regs_str}) show zero affirmative documentation verifying this claim. "
                "Circulating narrative lacks primary source corroboration."
            )
        else:
            return f"Checked registries ({regs_str}) yielded insufficient accessible evidence to substantiate or refute."

    def _synthesize_action_advisory(
        self,
        claim: AtomicClaim,
        verdict: EpistemicOutcome,
        corporate_denials: List[EvidenceLink],
        unverified_gaps: List[str],
        deceptive_flags: List[DeceptiveFramingType],
    ) -> str:
        """Action-oriented advisory: what to establish before sharing or amplifying."""
        lines = []

        if verdict == EpistemicOutcome.SUPPORTED:
            lines.append("CLAIM SUBSTANTIATED: Verified against official public documentation.")
        elif verdict == EpistemicOutcome.REFUTED:
            lines.append("DO NOT AMPLIFY: The allegation has been demonstrably refuted by primary documentation.")
        elif verdict == EpistemicOutcome.MISLEADING_CONTEXT:
            lines.append(
                "CONTEXT WARNING: Do not share without clarifying that past events are being presented out of context."
            )
        elif verdict == EpistemicOutcome.UNVERIFIED:
            lines.append("UNVERIFIED CLAIM: No primary or regulatory records corroborate this assertion.")
        elif verdict == EpistemicOutcome.MIXED:
            lines.append("PROCEED WITH CAUTION: Reporting contains conflicting documentation.")
        else:
            lines.append("INSUFFICIENT EVIDENCE: Evidence corpus is too sparse to evaluate reliability.")

        if DeceptiveFramingType.CORROBORATION_ILLUSION in deceptive_flags:
            lines.append(
                "Corroboration Illusion Alert: High search volume is driven by syndicated reprints from a single origin, not independent confirmation."
            )

        if corporate_denials:
            lines.append("Entity has issued a formal denial; monitor for official regulatory filings.")

        return " ".join(lines)

    def build_dossier(
        self,
        investigation_id: str,
        query: str,
        entity: str,
        agent: str,
        matrix_items: List[AllegationMatrixItem],
        corroboration_summary: CorroborationSummary,
        provenance_edges: Optional[List[SourceRelationship]] = None,
        narrative_mutations: Optional[List[NarrativeVersion]] = None,
        limitations: Optional[List[str]] = None,
    ) -> MisinformationDossier:
        """Build exportable Misinformation Dossier with Schema.org ClaimReview JSON-LD."""
        # 1. Determine overall investigation outcome
        if not matrix_items:
            overall_verdict = EpistemicOutcome.INSUFFICIENT_EVIDENCE
        else:
            verdicts = [item.verdict for item in matrix_items]
            if EpistemicOutcome.REFUTED in verdicts:
                overall_verdict = EpistemicOutcome.REFUTED
            elif EpistemicOutcome.MISLEADING_CONTEXT in verdicts:
                overall_verdict = EpistemicOutcome.MISLEADING_CONTEXT
            elif EpistemicOutcome.MIXED in verdicts:
                overall_verdict = EpistemicOutcome.MIXED
            elif EpistemicOutcome.SUPPORTED in verdicts:
                overall_verdict = EpistemicOutcome.SUPPORTED
            elif EpistemicOutcome.UNVERIFIED in verdicts:
                overall_verdict = EpistemicOutcome.UNVERIFIED
            else:
                overall_verdict = EpistemicOutcome.INSUFFICIENT_EVIDENCE

        # 2. Actionability advisory mapping
        actionability = {
            "verdict": overall_verdict.value,
            "corroboration_illusion": corroboration_summary.corroboration_illusion_detected,
            "independent_chains": corroboration_summary.independent_evidence_chains,
            "unique_publishers": corroboration_summary.unique_publishers,
            "recommendation": matrix_items[0].action_advisory if matrix_items else "Awaiting evidence.",
            "checkpoints": [
                "Verify primary regulatory filing or official agency bulletin.",
                "Inspect whether multiple outlets cite the exact same single initial report.",
                "Confirm that cited dates align with the current asserted event.",
            ],
        }

        # 3. Schema.org ClaimReview interoperability
        rating_map = {
            EpistemicOutcome.SUPPORTED: ("True", 5),
            EpistemicOutcome.REFUTED: ("False", 1),
            EpistemicOutcome.MISLEADING_CONTEXT: ("Misleading Context", 2),
            EpistemicOutcome.MIXED: ("Mixture", 3),
            EpistemicOutcome.UNVERIFIED: ("Unverified", 2),
            EpistemicOutcome.INSUFFICIENT_EVIDENCE: ("Insufficient Evidence", 2),
        }
        rat_label, rat_val = rating_map.get(overall_verdict, ("Unverified", 2))

        claim_review = {
            "@context": "https://schema.org",
            "@type": "ClaimReview",
            "url": f"https://aegis-protocol.local/dossier/{investigation_id}",
            "claimReviewed": query,
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rat_val,
                "bestRating": 5,
                "worstRating": 1,
                "alternateName": rat_label,
            },
            "itemReviewed": {
                "@type": "Claim",
                "author": {
                    "@type": "Organization",
                    "name": "Public Discourse / Web",
                },
                "appearance": [
                    {"@type": "CreativeWork", "url": grp.primary_origin_url}
                    for grp in corroboration_summary.groups
                    if grp.primary_origin_url
                ],
            },
            "author": {
                "@type": "Organization",
                "name": "Aegis Protocol Claim Intelligence Core",
                "url": "https://github.com/Shaunakrane914/Misinformation",
            },
        }

        all_limitations = list(limitations or [])
        if corroboration_summary.corroboration_illusion_detected:
            all_limitations.append(
                f"Observed search results exhibited syndication concentration: "
                f"{corroboration_summary.unique_publishers} publishers share only "
                f"{corroboration_summary.independent_evidence_chains} primary origin."
            )

        return MisinformationDossier(
            investigation_id=investigation_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            target_entity=entity,
            raw_query=query,
            agent=agent,
            overall_verdict=overall_verdict,
            actionability_advisory=actionability,
            allegation_matrix=matrix_items,
            corroboration_summary=corroboration_summary,
            provenance_edges=provenance_edges or [],
            narrative_mutations=narrative_mutations or [],
            limitations=all_limitations,
            claim_review_schema=claim_review,
        )


assessment_engine = AllegationAssessmentEngine()
