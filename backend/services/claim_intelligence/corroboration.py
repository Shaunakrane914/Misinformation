"""Source Independence Graph & Corroboration Illusion Detector.

Identifies whether 12 websites represent 12 independent investigations
or 1 single origin syndicated across 11 aggregators (Echo-Chamber Illusion).
Uses n-gram shingle similarity, explicit attribution matching, and quotation tracing.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.claim_intelligence.models import (
    CorroborationGroup,
    CorroborationSummary,
    SourceCapture,
    SourceRelationship,
    SourceRelationType,
)

logger = logging.getLogger(__name__)

ATTRIBUTION_PATTERNS = [
    r"(?:originally\s+reported\s+by|reported\s+first\s+by|first\s+reported\s+by)\s+([A-Za-z0-9.\- ]{2,30})",
    r"(?:according\s+to|as\s+reported\s+in|citing)\s+([A-Za-z0-9.\- ]{2,30})",
    r"(?:via|courtesy\s+of|credit:)\s+([A-Za-z0-9.\- ]{2,30})",
    r"(?:reprinted\s+with\s+permission\s+from|syndicated\s+from)\s+([A-Za-z0-9.\- ]{2,30})",
]


class CorroborationDetector:
    """Detects source independence and identifies corroboration illusions."""

    def __init__(self, similarity_threshold: float = 0.65):
        self.similarity_threshold = similarity_threshold

    def analyze_sources(
        self,
        sources: List[Dict[str, Any]],
    ) -> Tuple[CorroborationSummary, List[SourceRelationship]]:
        """Analyze a collection of acquired sources to build the independence graph."""
        if not sources:
            return CorroborationSummary(
                total_sources_scanned=0,
                unique_publishers=0,
                independent_evidence_chains=0,
                syndicated_reprints_count=0,
                corroboration_illusion_detected=False,
                corroboration_ratio=1.0,
                groups=[],
            ), []

        # 1. Normalize source records
        normalized_sources = []
        for s in sources:
            sid = s.get("source_id") or s.get("id") or s.get("evidence_id") or "src_" + hashlib.sha256(str(s.get("url", "")).encode()).hexdigest()[:8]
            url = s.get("canonical_url") or s.get("url") or s.get("source_url") or ""
            pub = s.get("publisher_host") or s.get("publisher") or s.get("source_domain") or "Unknown"
            body = s.get("content") or s.get("body") or s.get("snippet") or s.get("text") or ""
            pub_date = s.get("published_at")
            shingles = self._compute_shingles(body)

            normalized_sources.append({
                "source_id": sid,
                "url": url,
                "publisher": pub,
                "published_at": pub_date,
                "body": body,
                "shingles": shingles,
            })

        # 2. Build pairwise relationships
        relationships: List[SourceRelationship] = []
        groups_map: Dict[str, Set[str]] = {}  # origin_publisher -> set(source_ids)
        reprint_publishers: Dict[str, Set[str]] = {}

        n = len(normalized_sources)
        for i in range(n):
            src_a = normalized_sources[i]
            for j in range(i + 1, n):
                src_b = normalized_sources[j]
                rel = self._evaluate_relationship(src_a, src_b)
                if rel:
                    relationships.append(rel)

        # 3. Cluster into Corroboration Groups
        # Union-Find or adjacency connected components for syndication clusters
        visited = set()
        groups: List[CorroborationGroup] = []

        for i, src in enumerate(normalized_sources):
            sid = src["source_id"]
            if sid in visited:
                continue

            cluster_ids = {sid}
            cluster_pubs = {src["publisher"]}
            reprints = []

            for rel in relationships:
                if rel.relation_type in {
                    SourceRelationType.EXPLICIT_REPRINT,
                    SourceRelationType.QUOTES,
                    SourceRelationType.HIGH_TEXT_SIMILARITY,
                }:
                    if rel.source_a_id in cluster_ids and rel.source_b_id not in cluster_ids:
                        target = next((s for s in normalized_sources if s["source_id"] == rel.source_b_id), None)
                        if target:
                            cluster_ids.add(target["source_id"])
                            cluster_pubs.add(target["publisher"])
                            reprints.append(target["publisher"])
                    elif rel.source_b_id in cluster_ids and rel.source_a_id not in cluster_ids:
                        target = next((s for s in normalized_sources if s["source_id"] == rel.source_a_id), None)
                        if target:
                            cluster_ids.add(target["source_id"])
                            cluster_pubs.add(target["publisher"])
                            reprints.append(target["publisher"])

            visited.update(cluster_ids)
            is_indep = len(cluster_ids) == 1 or len(cluster_pubs) == 1
            synd_ratio = len(reprints) / max(len(cluster_ids), 1)

            groups.append(CorroborationGroup(
                group_id=f"grp_{len(groups) + 1}",
                primary_origin_publisher=src["publisher"],
                primary_origin_url=src["url"],
                reprint_publishers=sorted(list(set(reprints))),
                all_source_ids=sorted(list(cluster_ids)),
                is_independent=is_indep,
                syndication_ratio=round(synd_ratio, 2),
            ))

        # 4. Generate Summary & Corroboration Illusion Alert
        total_scanned = len(normalized_sources)
        known_publishers = {s["publisher"] for s in normalized_sources if s["publisher"] != "Unknown"}
        unique_publishers = len(known_publishers) if known_publishers else total_scanned
        independent_chains = len(groups)
        syndicated_reprints = max(0, total_scanned - independent_chains)

        corroboration_ratio = min(1.0, independent_chains / max(total_scanned, 1))
        # Corroboration illusion occurs when multiple publishers parrot the same underlying origin
        illusion_detected = (
            unique_publishers >= 3
            and independent_chains == 1
            and syndicated_reprints >= 2
        ) or (
            total_scanned >= 4 and corroboration_ratio <= 0.40
        )

        warning_msg = None
        if illusion_detected:
            warning_msg = (
                f"CORROBORATION ILLUSION DETECTED: {unique_publishers} distinct publishers returned matching text, "
                f"but source analysis reveals only {independent_chains} independent reporting origin. "
                "Echo-chamber syndication detected."
            )

        summary = CorroborationSummary(
            total_sources_scanned=total_scanned,
            unique_publishers=unique_publishers,
            independent_evidence_chains=independent_chains,
            syndicated_reprints_count=max(syndicated_reprints, 0),
            corroboration_illusion_detected=illusion_detected,
            corroboration_ratio=round(corroboration_ratio, 2),
            warning_message=warning_msg,
            groups=groups,
        )

        return summary, relationships

    def _evaluate_relationship(
        self,
        src_a: Dict[str, Any],
        src_b: Dict[str, Any],
    ) -> Optional[SourceRelationship]:
        """Compute relationship edge between two sources."""
        # 1. Check Explicit Attribution (A cites B, or B cites A)
        pub_a = src_a["publisher"].lower()
        pub_b = src_b["publisher"].lower()
        body_a = src_a["body"].lower()
        body_b = src_b["body"].lower()

        a_cites_b = bool(re.search(rf"\b(?:according\s+to|citing|via|reported\s+by)\s+{re.escape(pub_b)}\b", body_a))
        b_cites_a = bool(re.search(rf"\b(?:according\s+to|citing|via|reported\s+by)\s+{re.escape(pub_a)}\b", body_b))

        edge_id = f"edge_{src_a['source_id'][:6]}_{src_b['source_id'][:6]}"

        if a_cites_b:
            return SourceRelationship(
                edge_id=edge_id,
                source_a_id=src_a["source_id"],
                source_b_id=src_b["source_id"],
                relation_type=SourceRelationType.QUOTES,
                similarity_score=0.5,
                rationale=f"{src_a['publisher']} explicitly cites {src_b['publisher']}.",
            )
        if b_cites_a:
            return SourceRelationship(
                edge_id=edge_id,
                source_a_id=src_b["source_id"],
                source_b_id=src_a["source_id"],
                relation_type=SourceRelationType.QUOTES,
                similarity_score=0.5,
                rationale=f"{src_b['publisher']} explicitly cites {src_a['publisher']}.",
            )

        # 2. Check Text Shingle Jaccard Similarity (Syndication / Reprint Detection)
        jaccard = self._jaccard_similarity(src_a["shingles"], src_b["shingles"])
        if jaccard >= 0.85:
            # Wire reprint or word-for-word copy
            return SourceRelationship(
                edge_id=edge_id,
                source_a_id=src_a["source_id"],
                source_b_id=src_b["source_id"],
                relation_type=SourceRelationType.EXPLICIT_REPRINT,
                similarity_score=round(jaccard, 3),
                rationale=f"Word-for-word syndication match (similarity {round(jaccard, 2)}).",
            )
        elif jaccard >= self.similarity_threshold:
            return SourceRelationship(
                edge_id=edge_id,
                source_a_id=src_a["source_id"],
                source_b_id=src_b["source_id"],
                relation_type=SourceRelationType.HIGH_TEXT_SIMILARITY,
                similarity_score=round(jaccard, 3),
                rationale=f"Substantial overlapping prose without formal attribution (similarity {round(jaccard, 2)}).",
            )

        return None

    def _compute_shingles(self, text: str, k: int = 3) -> Set[str]:
        """Compute word k-shingles for Jaccard similarity."""
        words = re.findall(r"\b[a-z0-9]+\b", (text or "").lower())
        if len(words) < k:
            return set(words)
        return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}

    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        """Compute Jaccard similarity between two shingle sets."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0


corroboration_detector = CorroborationDetector()
