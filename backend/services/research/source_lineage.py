"""
Aegis Protocol — Source Lineage DAG & Echo Detection Engine
============================================================
Distinguishes genuinely independent observations from syndicated echo chambers.
Constructs a Directed Acyclic Graph (DAG) mapping primary wire dispatches,
first-tier investigative reporting, and downstream republishing chains.
"""

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import EvidenceItem, SourceRole, SourceTier

logger = logging.getLogger(__name__)

# Explicit citation attribution phrases
CITATION_PATTERNS = [
    (r'(?:according to|cites|cited by|reported by|quoted by)\s+([A-Za-z0-9\s]{3,25})', 'cites'),
    (r'(?:republished from|syndicated from|first published by)\s+([A-Za-z0-9\s]{3,25})', 'syndicated_copy'),
    (r'(?:in a statement to|spokesperson told|confirmed to)\s+([A-Za-z0-9\s]{3,25})', 'official_disclosure'),
    (r'(?:per|via)\s+(reuters|bloomberg|ap|associated press|afp|pti|ani)', 'cites'),
]

KNOWN_WIRE_ORIGINS = {
    "reuters": "Reuters Financial Wire",
    "bloomberg": "Bloomberg News Desk",
    "associated press": "Associated Press Wire",
    "ap news": "Associated Press Wire",
    "press trust of india": "PTI Newswire",
    "pti": "PTI Newswire",
    "ani news": "ANI Newswire",
    "pr newswire": "PR Newswire Distribution",
    "business wire": "Business Wire Distribution",
    "globe newswire": "GlobeNewswire Distribution",
}


@dataclass
class LineageNode:
    """Node in the source provenance DAG."""
    id: str
    source_name: str
    domain: str
    url: str
    tier: str
    role: str
    is_origin: bool
    citation_depth: int  # 0 = primary/origin, 1 = direct report, 2+ = syndicated echo
    parent_origin_id: Optional[str] = None
    citation_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_name": self.source_name,
            "domain": self.domain,
            "url": self.url,
            "tier": self.tier,
            "role": self.role,
            "is_origin": self.is_origin,
            "citation_depth": self.citation_depth,
            "parent_origin_id": self.parent_origin_id,
            "citation_text": self.citation_text,
        }


@dataclass
class LineageEdge:
    """Directed edge representing citation or syndication transmission."""
    source_id: str
    target_id: str
    relation: str  # 'cites' | 'syndicated_copy' | 'amplifies' | 'official_disclosure'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.source_id,
            "to": self.target_id,
            "relation": self.relation,
        }


class SourceLineageEngine:
    """
    Constructs an evidence lineage DAG.
    Differentiates 40 distinct reports from 1 wire report echoed 40 times.
    """

    def __init__(self):
        pass

    def _extract_citation_mentions(self, text: str) -> List[Tuple[str, str]]:
        """Identify cited origins and relationship types from body text."""
        mentions = []
        lower = text.lower()
        for pat, rel in CITATION_PATTERNS:
            for match in re.finditer(pat, lower):
                cited_entity = match.group(1).strip()
                # Clean up entity name
                cited_entity = re.sub(r'[^a-z0-9\s]', '', cited_entity).strip()
                if len(cited_entity) >= 3 and cited_entity not in ("the", "sources", "reports", "officials"):
                    mentions.append((cited_entity, rel))
        return mentions

    def build_lineage_graph(self, items: List[EvidenceItem]) -> Dict[str, Any]:
        """
        Analyze a candidate set and compile an inspectable DAG.
        """
        nodes: Dict[str, LineageNode] = {}
        edges: List[LineageEdge] = []
        origin_nodes: Set[str] = set()
        echo_nodes: Set[str] = set()

        # Step 1: Initialize all items as potential nodes
        for it in items:
            combined_text = f"{it.title} {it.snippet} {it.content[:1000]}".lower()
            
            # Check if this item is inherently a wire or primary origin
            detected_wire = None
            for w_key, w_name in KNOWN_WIRE_ORIGINS.items():
                if w_key in it.source_domain.lower() or w_key in it.source_name.lower():
                    detected_wire = w_name
                    break

            is_origin = bool(detected_wire or it.primary_source or it.source_role == SourceRole.PRIMARY.value)
            
            nodes[it.id] = LineageNode(
                id=it.id,
                source_name=detected_wire or it.source_name or "Unknown Source",
                domain=it.source_domain or "web",
                url=it.canonical_url,
                tier=it.source_tier,
                role=it.source_role,
                is_origin=is_origin,
                citation_depth=0 if is_origin else 1,
            )
            if is_origin:
                origin_nodes.add(it.id)

        # Step 2: Extract citation relationships and build edges
        for it in items:
            node = nodes[it.id]
            combined_text = f"{it.title} {it.snippet} {it.content[:2000]}".lower()
            citations = self._extract_citation_mentions(combined_text)

            # Check if it cites another item in our set or a recognized wire
            for cited_name, rel in citations:
                # Match against known origins or existing nodes
                matched_parent_id = None
                for other_id, other_node in nodes.items():
                    if other_id == it.id:
                        continue
                    if cited_name in other_node.source_name.lower() or cited_name in other_node.domain:
                        matched_parent_id = other_id
                        break

                if matched_parent_id:
                    edges.append(LineageEdge(source_id=matched_parent_id, target_id=it.id, relation=rel))
                    node.parent_origin_id = matched_parent_id
                    node.citation_depth = nodes[matched_parent_id].citation_depth + 1
                    node.citation_text = f"Cites {nodes[matched_parent_id].source_name} ({rel})"
                    echo_nodes.add(it.id)
                    break
                else:
                    # Check if citing a known external wire not in the direct pool
                    for w_key, w_name in KNOWN_WIRE_ORIGINS.items():
                        if w_key in cited_name:
                            node.citation_depth = 2
                            node.citation_text = f"Syndicated wire copy from {w_name}"
                            node.parent_origin_id = f"origin_{w_key}"
                            echo_nodes.add(it.id)
                            break

        # Step 3: Compute Lineage Metrics
        total_items = len(items)
        unique_origins = len(origin_nodes)
        downstream_echoes = len(echo_nodes)
        independent_sources = max(1, total_items - downstream_echoes)

        logger.debug(f"[SourceLineage] Built DAG: {total_items} nodes, {len(edges)} edges, {unique_origins} origins, {downstream_echoes} echoes")

        return {
            "nodes": [n.to_dict() for n in nodes.values()],
            "edges": [e.to_dict() for e in edges],
            "metrics": {
                "total_nodes": total_items,
                "edges_count": len(edges),
                "origin_count": unique_origins,
                "echo_count": downstream_echoes,
                "true_independent_count": independent_sources,
                "syndication_compression_ratio": round(downstream_echoes / max(1, total_items), 3),
            }
        }


# Global singleton
source_lineage_engine = SourceLineageEngine()
