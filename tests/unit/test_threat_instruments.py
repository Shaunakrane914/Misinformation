"""
Aegis Protocol — Unit Tests: Threat Intelligence Lab Instruments
=================================================================
Validates:
- Mandelbrot Power-Law rank fit and synthetic text detection
- Hawkes self-exciting point process simulation
- Byzantine / Ensemble consensus arbitrament and statistical outlier pruning
"""

import pytest
from backend.services.threat_instruments import (
    compute_mandelbrot_fit,
    simulate_hawkes_contagion,
    arbitrate_ensemble_consensus
)


@pytest.mark.unit
def test_mandelbrot_insufficient_sample():
    res = compute_mandelbrot_fit("Too short")
    assert res["verdict"] == "INSUFFICIENT_DATA"
    assert res["status"] in ("error", "warning")


@pytest.mark.unit
def test_mandelbrot_valid_text():
    sample = (
        "The quick brown fox jumps over the lazy dog repeatedly while the researchers "
        "measure token rank frequency distribution to determine whether an autoregressive "
        "large language model composed the paragraph."
    )
    res = compute_mandelbrot_fit(sample)
    assert res["status"] == "success"
    assert "r_squared" in res
    assert "entropy" in res
    assert "ttr" in res
    assert res["verdict"] in ("SYNTHETIC", "HUMAN")
    assert len(res["curve_data"]) > 0


@pytest.mark.unit
def test_hawkes_point_process_simulation():
    res = simulate_hawkes_contagion(
        topic="Biometric ID Conspiracy",
        claim="Microchips secretly embedded into common flu vaccines",
        horizon_hours=24
    )
    assert res["status"] == "success"
    assert res["is_simulation"] is True
    assert "reproduction_number_R0" in res
    assert res["reproduction_number_R0"] > 0
    assert len(res["hourly_distribution"]) == 24
    assert res["threat_level"] in ("CRITICAL CONTAGION", "ELEVATED", "NOMINAL")
    assert res["trajectory"] != ""


@pytest.mark.unit
def test_hawkes_empty_input_validation():
    with pytest.raises(ValueError):
        simulate_hawkes_contagion(topic="", claim="")


@pytest.mark.unit
def test_ensemble_consensus_majority_and_outlier():
    nodes = [
        {"id": "node-1", "name": "Skeptic", "verdict": "FALSE", "confidence": 92.0},
        {"id": "node-2", "name": "Empirical", "verdict": "FALSE", "confidence": 95.0},
        {"id": "node-3", "name": "Adversary", "verdict": "TRUE", "confidence": 40.0}
    ]
    res = arbitrate_ensemble_consensus(nodes)
    assert res["status"] == "success"
    assert res["consensus_verdict"] == "FALSE"
    assert res["consensus_reached"] is True
    assert res["quorum_ratio"] >= 0.66
    
    # Check that node-3 was tagged as outlier
    outlier = next(n for n in res["nodes"] if n["id"] == "node-3")
    assert outlier["is_outlier"] is True
