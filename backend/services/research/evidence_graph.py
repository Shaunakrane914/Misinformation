"""
Aegis Protocol — Evidence Graph Builder
=======================================
Constructs directed evidentiary relationships linking findings to supporting/contradicting
evidence items, extracted passages, and canonical primary sources.
"""

from typing import Any, Dict, List, Set

from backend.services.research.research_models import EvidenceItem, Finding


class EvidenceGraphBuilder:
    """Builds a queryable evidentiary relationship graph."""

    def __init__(self):
        pass

    def build_graph(
        self,
        findings: List[Finding],
        evidence: List[EvidenceItem]
    ) -> Dict[str, Any]:
        """
        Generates nodes and edges connecting findings to underlying evidence items and sources.
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_nodes: Set[str] = set()

        ev_map = {e.id: e for e in evidence}

        # 1. Add Finding Nodes
        for f in findings:
            f_node_id = f"node_{f.finding_id}"
            if f_node_id not in seen_nodes:
                seen_nodes.add(f_node_id)
                nodes.append({
                    "id": f_node_id,
                    "type": "FINDING",
                    "label": f.title,
                    "statement": f.statement,
                    "finding_type": f.type,
                    "confidence": f.confidence,
                    "importance": f.importance
                })

            # Connect to Supporting Evidence
            for ev_id in f.supporting_evidence_ids:
                if ev_id in ev_map:
                    ev = ev_map[ev_id]
                    ev_node_id = f"node_{ev.id}"
                    if ev_node_id not in seen_nodes:
                        seen_nodes.add(ev_node_id)
                        nodes.append({
                            "id": ev_node_id,
                            "type": "EVIDENCE",
                            "label": ev.source_name or ev.title[:30],
                            "canonical_url": ev.canonical_url,
                            "content_depth": ev.content_depth,
                            "source_role": ev.source_role,
                            "relevant_excerpt": ev.relevant_excerpt,
                            "independence_group": ev.independence_group
                        })

                    edges.append({
                        "id": f"edge_{f.finding_id}_{ev.id}_sup",
                        "source": f_node_id,
                        "target": ev_node_id,
                        "relation": "SUPPORTS",
                        "weight": round(ev.source_quality_score, 2)
                    })

            # Connect to Contradicting Evidence
            for ev_id in f.contradicting_evidence_ids:
                if ev_id in ev_map:
                    ev = ev_map[ev_id]
                    ev_node_id = f"node_{ev.id}"
                    if ev_node_id not in seen_nodes:
                        seen_nodes.add(ev_node_id)
                        nodes.append({
                            "id": ev_node_id,
                            "type": "EVIDENCE",
                            "label": ev.source_name or ev.title[:30],
                            "canonical_url": ev.canonical_url,
                            "content_depth": ev.content_depth,
                            "source_role": ev.source_role,
                            "relevant_excerpt": ev.relevant_excerpt
                        })

                    edges.append({
                        "id": f"edge_{f.finding_id}_{ev.id}_cont",
                        "source": f_node_id,
                        "target": ev_node_id,
                        "relation": "CONTRADICTS",
                        "weight": 1.0
                    })

        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }


evidence_graph_builder = EvidenceGraphBuilder()
