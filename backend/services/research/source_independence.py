"""
Aegis Protocol — Source Independence & Syndication Clustering Engine
===================================================================
Identifies wire services, syndication chains, and republished wire copy (Reuters,
AP, Bloomberg, PTI, PR Newswire) to prevent false independent corroboration.
"""

import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import EvidenceItem

# Markers denoting wire service copy or press release distributors
WIRE_SERVICE_MARKERS: Dict[str, List[str]] = {
    "Reuters": ["reuters", "thomson reuters", "(reuters) -", "reporting by reuters"],
    "Associated Press": ["associated press", "(ap) -", "ap news", "by the associated press"],
    "Bloomberg": ["bloomberg news", "(bloomberg) -", "bloomberg l.p."],
    "Press Trust of India": ["press trust of india", "(pti) -", "pti news"],
    "PR Newswire": ["pr newswire", "prnewswire.com", "pr newswire association"],
    "Business Wire": ["business wire", "businesswire.com"],
    "GlobeNewswire": ["globenewswire", "globe newswire"],
    "Asian News International": ["ani news", "asian news international", "(ani) -"],
    "Indo-Asian News Service": ["ians news", "indo-asian news service"],
}


class SourceIndependenceEngine:
    """Clusters syndicated stories and calculates true independence scores."""

    def __init__(self):
        pass

    def _detect_wire_source(self, item: EvidenceItem) -> Optional[str]:
        """Detect if an article originates from a wire service or press distributor."""
        text = f"{item.title} {item.snippet} {item.content[:500]} {item.source_name}".lower()
        for wire_name, markers in WIRE_SERVICE_MARKERS.items():
            for m in markers:
                if m in text:
                    return wire_name
        return None

    def _normalize_title_slug(self, title: str) -> str:
        """Create a stripped alphanumeric fingerprint of a title."""
        slug = re.sub(r'[^a-z0-9]', '', (title or "").lower())
        return slug[:40]

    def cluster_independence(self, items: List[EvidenceItem]) -> Tuple[List[EvidenceItem], Dict[str, List[str]]]:
        """
        Group items into source families and assign independence scores.

        Returns:
            Tuple of (updated_items, independence_clusters_map)
        """
        # Map of wire_family -> list of item IDs
        wire_clusters: Dict[str, List[EvidenceItem]] = {}
        # Map of title_slug -> list of item IDs (for detecting identical headlines on different domains)
        title_clusters: Dict[str, List[EvidenceItem]] = {}
        
        clusters_map: Dict[str, List[str]] = {}

        for item in items:
            wire_origin = self._detect_wire_source(item)
            slug = self._normalize_title_slug(item.title)

            if wire_origin:
                item.syndicated_from = wire_origin
                family_key = f"wire_{wire_origin.lower().replace(' ', '_')}_{slug[:20]}"
                wire_clusters.setdefault(family_key, []).append(item)
            elif slug and len(slug) >= 15:
                title_clusters.setdefault(slug, []).append(item)
            else:
                # Independent source
                item.source_family_id = f"indep_{item.id}"
                item.independence_group = f"domain_{item.source_domain or item.channel}"
                item.independence_score = 1.0 if item.primary_source else 0.85
                clusters_map.setdefault(item.independence_group, []).append(item.id)

        # Process wire clusters
        for family_key, group_items in wire_clusters.items():
            clusters_map[family_key] = [it.id for it in group_items]
            # The first item (or primary/origin) gets highest weight; subsequent syndicated copies get low score
            for idx, it in enumerate(group_items):
                it.source_family_id = family_key
                it.independence_group = family_key
                if idx == 0:
                    it.independence_score = 0.65  # Origin wire reporting
                else:
                    it.independence_score = 0.15  # Syndicated republication (cannot confirm itself)

        # Process duplicate title clusters across domains
        for slug, group_items in title_clusters.items():
            if len(group_items) > 1:
                family_key = f"synd_title_{slug[:20]}"
                clusters_map[family_key] = [it.id for it in group_items]
                for idx, it in enumerate(group_items):
                    it.source_family_id = family_key
                    it.independence_group = family_key
                    it.independence_score = 0.70 if idx == 0 else 0.20
            else:
                it = group_items[0]
                it.source_family_id = f"indep_{it.id}"
                it.independence_group = f"domain_{it.source_domain or it.channel}"
                it.independence_score = 1.0 if it.primary_source else 0.85
                clusters_map.setdefault(it.independence_group, []).append(it.id)

        return items, clusters_map


source_independence_engine = SourceIndependenceEngine()
