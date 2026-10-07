"""
Aegis Protocol — Scout Deduplication & Wire Syndication Clustering
===================================================================
Identifies duplicate articles and syndicated wire reprints (AP, Reuters, PR Newswire)
so that 20 reprints are never counted as 20 independent confirmations.
"""

import hashlib
import re
from typing import Dict, List, Set, Tuple
from backend.services.agent_reach.scout.models import ScoutEvidence, StoryCluster, EpistemicStatus

# Known news wire syndication signatures
WIRE_SIGNATURES = [
    "reuters", "associated press", "ap news", "bloomberg",
    "pr newswire", "business wire", "globe newswire", "afp", "dow jones"
]


class ScoutDeduplicator:
    """
    Groups identical or syndicated articles into unified StoryClusters.
    """

    def cluster_evidence(self, items: List[ScoutEvidence]) -> Tuple[List[ScoutEvidence], List[StoryCluster]]:
        """
        Processes evidence items, detects duplicate and syndicated reports,
        and builds StoryClusters.

        Returns:
            (deduplicated_or_tagged_evidence, story_clusters)
        """
        clusters: List[StoryCluster] = []
        if not items:
            return [], []

        # 1. Group by content hash / title similarity
        seen_hashes: Dict[str, str] = {}  # hash -> cluster_id
        cluster_map: Dict[str, List[ScoutEvidence]] = {}

        for item in items:
            wire_origin = self._detect_wire_syndication(item.title, item.body)
            if wire_origin:
                item.syndicated_from = wire_origin

            c_hash = self._compute_content_signature(item.title, item.body)
            # Find existing cluster matching signature
            matched_cluster_id = None
            for existing_hash, cid in seen_hashes.items():
                if self._are_signatures_similar(c_hash, existing_hash):
                    matched_cluster_id = cid
                    break

            if not matched_cluster_id:
                matched_cluster_id = f"cluster_{len(clusters) + 1:03d}"
                seen_hashes[c_hash] = matched_cluster_id
                cluster_map[matched_cluster_id] = []

            item.cluster_id = matched_cluster_id
            cluster_map[matched_cluster_id].append(item)

        # 2. Build StoryCluster instances
        for cid, cluster_items in cluster_map.items():
            primary_item = cluster_items[0]
            # If any item is Tier 1 Primary, promote it as cluster lead
            for ci in cluster_items:
                if ci.is_primary or ci.source_tier == "TIER_1_PRIMARY":
                    primary_item = ci
                    break

            syndicated_urls = [ci.url for ci in cluster_items[1:] if ci.syndicated_from]
            independent_sources = list({ci.author for ci in cluster_items if not ci.syndicated_from})

            has_primary = any(ci.is_primary for ci in cluster_items)
            epistemic = (
                EpistemicStatus.OFFICIAL if has_primary
                else (EpistemicStatus.CONFIRMED if len(independent_sources) >= 2
                else (EpistemicStatus.REPORTED if len(cluster_items) >= 1
                else EpistemicStatus.UNCONFIRMED_RUMOR))
            )

            clusters.append(StoryCluster(
                cluster_id=cid,
                headline=primary_item.title,
                primary_source_url=primary_item.url,
                syndicated_urls=syndicated_urls,
                independent_sources=independent_sources,
                first_seen_at=primary_item.published_at,
                last_updated_at=max((ci.published_at for ci in cluster_items), default=primary_item.published_at),
                primary_source_present=has_primary,
                epistemic_status=epistemic,
                confidence=0.90 if has_primary else (0.80 if len(independent_sources) >= 2 else 0.65)
            ))

        return items, clusters

    def _detect_wire_syndication(self, title: str, body: str) -> str:
        text = f"{title} {body[:500]}".lower()
        for wire in WIRE_SIGNATURES:
            if wire in text:
                return wire
        return ""

    def _compute_content_signature(self, title: str, body: str) -> str:
        # Normalized alphanumeric bag-of-words hash
        words = re.findall(r"\b[a-zA-Z0-9]{4,}\b", f"{title} {body[:400]}".lower())
        top_words = sorted(set(words))[:20]
        return " ".join(top_words)

    def _are_signatures_similar(self, sig1: str, sig2: str) -> bool:
        if not sig1 or not sig2:
            return False
        w1 = set(sig1.split())
        w2 = set(sig2.split())
        if not w1 or not w2:
            return False
        overlap = len(w1 & w2) / max(len(w1 | w2), 1)
        return overlap >= 0.60


scout_deduplicator = ScoutDeduplicator()
