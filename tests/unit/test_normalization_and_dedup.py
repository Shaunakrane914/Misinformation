"""
Aegis Protocol — Unit Tests: Claim Normalization & Deduplication
================================================================
Validates:
- Unicode NFC normalization
- Whitespace collapsing and markdown stripping
- Deterministic SHA-256 hash calculation
- Database-backed idempotency (re-submitting identical claim returns is_new=False)
- Length validation
"""

import pytest
from backend.agents.claim_ingestion_agent import get_claim_ingestion_agent


@pytest.mark.unit
def test_unicode_nfc_normalization():
    agent = get_claim_ingestion_agent()
    # "e\u0301" (decomposed e + acute) vs "\u00e9" (precomposed é)
    decomposed = "Cafe\u0301 cures diabetes"
    precomposed = "Café cures diabetes"
    
    norm1 = agent.normalize(decomposed)
    norm2 = agent.normalize(precomposed)
    assert norm1 == norm2
    assert agent.compute_hash(norm1) == agent.compute_hash(norm2)


@pytest.mark.unit
def test_whitespace_and_punctuation_collapsing():
    agent = get_claim_ingestion_agent()
    messy = "   BREAKING:   Drinking   lemon water   cures   cancer!!!   "
    clean = agent.normalize(messy)
    assert clean == "breaking: drinking lemon water cures cancer"
    assert "  " not in clean


@pytest.mark.unit
def test_deterministic_sha256_hash():
    agent = get_claim_ingestion_agent()
    claim = "5G cellular networks spread coronavirus pathogens"
    h1 = agent.compute_hash(agent.normalize(claim))
    h2 = agent.compute_hash(agent.normalize(claim))
    assert len(h1) == 64
    assert h1 == h2


@pytest.mark.unit
def test_claim_ingestion_idempotency():
    agent = get_claim_ingestion_agent()
    claim_text = "Scientists confirm the earth is completely spherical in orbit"
    
    # First ingestion
    res1 = agent.ingest(claim_text=claim_text)
    assert res1["is_new"] is True
    assert "claim_id" in res1
    first_id = res1["claim_id"]

    # Duplicate ingestion
    res2 = agent.ingest(claim_text=claim_text)
    assert res2["is_new"] is False
    assert res2["claim_id"] == first_id
    assert res2["claim_hash"] == res1["claim_hash"]


@pytest.mark.unit
def test_empty_and_whitespace_claim_rejection():
    agent = get_claim_ingestion_agent()
    with pytest.raises(ValueError, match="too short"):
        agent.ingest(claim_text="    ")
