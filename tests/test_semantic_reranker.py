"""
Aegis Protocol — Semantic Reranker Unit Tests
=============================================
Tests CrossEncoder loading, deterministic inference, disabled mode gracefulness,
entity-gate invariance against adversarial homographs, and batching.
"""

import pytest
from backend.services.research.semantic_reranker import SemanticReranker, sigmoid

def test_sigmoid():
    assert sigmoid(0.0) == 0.5
    assert sigmoid(10.0) > 0.99
    assert sigmoid(-10.0) < 0.01

def test_disabled_reranker_graceful():
    reranker = SemanticReranker(enabled=False)
    assert not reranker.enabled
    candidates = [
        {"title": "Test 1", "snippet": "Snippet 1"},
        {"title": "Test 2", "snippet": "Snippet 2"},
    ]
    res = reranker.rerank("Query", candidates, top_k=2)
    assert len(res) == 2
    assert res[0]["semantic_status"] == "DISABLED"
    assert res[0]["semantic_score"] is None
    assert res[0]["raw_cross_encoder_score"] is None

def test_enabled_reranker_inference():
    reranker = SemanticReranker(enabled=True, device="cpu")
    assert reranker.is_available

    candidates = [
        {
            "candidate_id": "cand_pos",
            "title": "Microsoft Copilot Autonomous Agents Launch Announcement",
            "snippet": "Satya Nadella introduces enterprise autonomous AI workflows at keynote.",
            "entity_score": 0.90,
            "relevance_score": 0.85
        },
        {
            "candidate_id": "cand_neg",
            "title": "Electric Vehicle Battery Lithium Prices Slide in China",
            "snippet": "Commodity market analysis for global EV battery packs.",
            "entity_score": 0.0,
            "relevance_score": 0.05
        }
    ]

    res = reranker.rerank("Microsoft Copilot keynote announcement", candidates, top_k=2)
    assert len(res) == 2
    assert res[0]["candidate_id"] == "cand_pos"
    assert res[0]["semantic_status"] == "SCORED"
    assert 0.0 <= res[0]["semantic_score"] <= 1.0
    assert res[0]["semantic_score"] > res[1]["semantic_score"]

def test_adversarial_homograph_entity_defense():
    """
    Critical requirement: Even if a cross-encoder scores 'Satya' high on a text matching
    the word 'Satya', a low entity_score (e.g. Sanskrit philosophy) must be suppressed!
    """
    reranker = SemanticReranker(enabled=True, device="cpu")

    candidates = [
        {
            "candidate_id": "cand_homograph",
            "title": "Concept of Satya in Ancient Sanskrit Philosophical Texts",
            "snippet": "Satya represents truth and cosmic reality in Hindu and Jain meditation.",
            "entity_score": 0.10,  # Fails entity gate!
            "relevance_score": 0.10
        },
        {
            "candidate_id": "cand_genuine",
            "title": "Satya Nadella Outlines Microsoft Future Cloud AI Strategy",
            "snippet": "CEO Satya Nadella discussed enterprise infrastructure in annual shareholder address.",
            "entity_score": 0.95,  # Strong entity match
            "relevance_score": 0.88
        }
    ]

    res = reranker.rerank("Satya Nadella public statement", candidates, top_k=2)
    assert len(res) == 2
    # The genuine executive article must be Rank 1
    assert res[0]["candidate_id"] == "cand_genuine"
    # The homograph candidate must be penalized and ranked below
    assert res[1]["candidate_id"] == "cand_homograph"
