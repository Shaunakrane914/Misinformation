"""
Aegis Protocol — Threat Intelligence Lab Instruments
=====================================================
Educational statistical profiles and deterministic illustrations:
1. Zipf-Mandelbrot token-frequency curve fit (not authorship detection)
2. Illustrative diffusion curve with Hawkes-style intensity (not observed reach)
3. Multi-Node Fault-Tolerant Consensus Arbitrament (Outlier Trimming & Ensemble Quorum)
"""

import hashlib
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 1. ZIPF-MANDELBROT TOKEN-RANK POWER-LAW REGRESSION
# ─────────────────────────────────────────────────────────────────────────────

def compute_mandelbrot_fit(
    text: str,
    beta: float = 1.8,
    gamma: float = 1.12,
    max_ranks: int = 25
) -> Dict[str, Any]:
    """
    Evaluate Zipf-Mandelbrot token-rank power-law regression:
    P(r) = P_0 * (r + beta)^(-gamma)
    
    Returns:
        Dict containing R^2 goodness of fit, Shannon entropy, Type-Token Ratio (TTR),
        per-token curve data; authorship remains undetermined.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return {
            "status": "error",
            "message": "Empty text provided.",
            "verdict": "INSUFFICIENT_DATA",
            "r_squared": 0.0,
            "entropy": 0.0,
            "ttr": 0.0,
            "curve_data": []
        }

    tokens = re.findall(r"\b[a-zA-Z]{2,}\b", clean_text.lower())
    if len(tokens) < 10:
        return {
            "status": "warning",
            "message": "Sample too small for statistically valid regression (minimum 10 words required).",
            "verdict": "INSUFFICIENT_DATA",
            "confidence": None,
            "r_squared": 0.0,
            "entropy": 0.0,
            "ttr": 0.0,
            "total_tokens": len(tokens),
            "unique_tokens": len(set(tokens)),
            "curve_data": [],
            "analysis": "Provide a longer sample (at least 20-30 words) for full token rank regression."
        }

    total_tokens = len(tokens)
    counts = Counter(tokens)
    unique_tokens = len(counts)
    sorted_items = counts.most_common()

    ranks = min(unique_tokens, max_ranks)
    top_p = [cnt / total_tokens for _, cnt in sorted_items[:ranks]]

    zipf_denom = sum(1.0 / r for r in range(1, ranks + 1))
    mandel_denom = sum(1.0 / ((r + beta) ** gamma) for r in range(1, ranks + 1))

    curve_data: List[Dict[str, Any]] = []
    actual_vals: List[float] = []
    mandel_vals: List[float] = []

    for idx in range(ranks):
        r = idx + 1
        word, count = sorted_items[idx]
        p_act = count / total_tokens
        p_zipf = (1.0 / r) / zipf_denom * sum(top_p)
        p_mandel = (1.0 / ((r + beta) ** gamma)) / mandel_denom * sum(top_p)

        actual_vals.append(p_act)
        mandel_vals.append(p_mandel)

        curve_data.append({
            "rank": r,
            "token": word,
            "count": count,
            "p_actual": round(p_act, 4),
            "p_mandelbrot": round(p_mandel, 4),
            "p_zipf": round(p_zipf, 4),
            "delta": round(abs(p_act - p_mandel), 4)
        })

    # Calculate Coefficient of Determination (R^2)
    mean_act = sum(actual_vals) / len(actual_vals) if actual_vals else 1e-6
    ss_tot = sum((y - mean_act) ** 2 for y in actual_vals)
    ss_res = sum((y - f) ** 2 for y, f in zip(actual_vals, mandel_vals))

    if ss_tot > 1e-9:
        r_squared = max(0.0, min(0.999, 1.0 - (ss_res / ss_tot)))
    else:
        r_squared = 0.0

    ttr = round(unique_tokens / total_tokens, 4)
    entropy = round(-sum((c / total_tokens) * math.log2(c / total_tokens) for c in counts.values()), 3)

    confidence = None
    verdict = "AUTHORSHIP_UNDETERMINED"

    analysis = (
        f"Mandelbrot rank-frequency regression yielded R² = {r_squared:.3f} (entropy: {entropy} bits, TTR: {ttr:.2f}). "
        + "This describes a token-frequency fit. It does not determine authorship or provide a calibrated probability of AI generation."
    )

    return {
        "status": "success",
        "verdict": verdict,
        "confidence": confidence,
        "r_squared": round(r_squared, 4),
        "entropy": entropy,
        "ttr": ttr,
        "total_tokens": total_tokens,
        "unique_tokens": unique_tokens,
        "curve_data": curve_data,
        "analysis": analysis,
        "methodology": "Zipf-Mandelbrot Power-Law Rank Fit"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. HAWKES POINT-PROCESS CONTAGION SIMULATOR
# ─────────────────────────────────────────────────────────────────────────────

def simulate_hawkes_contagion(
    topic: str = "",
    claim: str = "",
    horizon_hours: int = 24
) -> Dict[str, Any]:
    """
    Simulate narrative contagion velocity using a self-exciting Hawkes process:
    lambda(t) = mu + sum_{t_i < t} alpha * exp(-beta * (t - t_i))
    
    Branching ratio: R_0 = alpha / beta
    - R_0 < 1.0: Subcritical attenuation (narrative decays naturally)
    - R_0 >= 1.0: Supercritical cascade (viral contagion)
    """
    text = f"{topic} {claim}".strip()
    if not text:
        raise ValueError("Either topic or claim must be provided for Hawkes contagion analysis.")

    # Deterministic example parameters; these are not fitted observations.
    seed_val = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)

    # Base background intensity (spontaneous submissions)
    mu = round(0.5 + ((seed_val % 40) / 100.0), 2)

    # Infectivity / excitation rate
    alpha = round(0.7 + (((seed_val >> 4) % 80) / 100.0), 2)

    # Temporal memory decay rate
    beta = round(0.5 + (((seed_val >> 8) % 45) / 100.0), 2)

    # Basic reproduction number (branching ratio)
    r0 = round(alpha / beta, 2)

    if r0 >= 1.5:
        threat_level = "CRITICAL CONTAGION"
        threat_color = "red"
        trajectory = "Supercritical exponential cascade"
    elif r0 >= 1.0:
        threat_level = "ELEVATED"
        threat_color = "yellow"
        trajectory = "Supercritical propagation" if r0 > 1.0 else "Critical sustained propagation"
    else:
        threat_level = "NOMINAL"
        threat_color = "green"
        trajectory = "Sub-critical attenuation"

    hourly_distribution: List[Dict[str, Any]] = []
    current_cum = 0
    base_spread = int(100 * (r0 ** 2.0))

    for h in range(1, horizon_hours + 1):
        decay = math.exp(-beta * (h / 6.0))
        h_intensity = round(mu + alpha * decay * (1.0 + 0.25 * math.sin(h / 3.0)), 2)
        growth_factor = (h ** 1.25) * math.exp(-0.08 * h) * (r0 ** 1.7)
        new_nodes = max(10, int(base_spread * growth_factor * (0.85 + 0.3 * ((seed_val + h * 31) % 100) / 100.0)))
        current_cum += new_nodes

        hourly_distribution.append({
            "hour": h,
            "hour_label": f"+{h}h",
            "new_nodes": new_nodes,
            "cumulative_nodes": current_cum,
            "intensity": h_intensity
        })

    return {
        "status": "success",
        "topic": topic,
        "claim": claim,
        "threat_level": threat_level,
        "threat_color": threat_color,
        "reproduction_number_R0": r0,
        "reproduction_number_r0": r0,
        "base_intensity_mu": mu,
        "excitation_alpha": alpha,
        "decay_rate_beta": beta,
        "total_projected_reach_24h": current_cum,
        "projected_reach_24h": current_cum,
        "trajectory": trajectory,
        "hourly_distribution": hourly_distribution,
        "critical_window_hours": 4.5 if r0 >= 1.2 else 8.0,
        "containment_recommendation": (
            "Illustrative supercritical model (R0 > 1); no observed reach or intervention recommendation."
            if r0 > 1.0 else
            "Illustrative critical model (R0 = 1); no observed reach." if r0 == 1.0 else
            "Illustrative subcritical model (R0 < 1); no observed reach."
        ),
        "is_simulation": True,
        "methodology": "Illustrative diffusion curve with Hawkes-style exponential intensity; not a fitted point process"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. MULTI-NODE FAULT-TOLERANT ENSEMBLE CONSENSUS
# ─────────────────────────────────────────────────────────────────────────────

def arbitrate_ensemble_consensus(
    node_evaluations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Arbitrate consensus across multiple independent evaluators with outlier detection.
    
    Fault Model:
    - Tolerates up to f < n/2 faulty or outlier nodes in an n-node ensemble.
    - An evaluator is considered an outlier if its verdict contradicts the majority
      or its confidence score deviates by > 2.0 standard deviations from the ensemble mean.
    """
    if not node_evaluations or len(node_evaluations) < 2:
        return {
            "status": "error",
            "message": "At least 2 node evaluations required for consensus.",
            "consensus_reached": False
        }

    verdict_votes: Counter = Counter()
    confidences: List[float] = []

    for node in node_evaluations:
        v = str(node.get("verdict", "UNVERIFIED")).upper()
        verdict_votes[v] += 1
        confidences.append(float(node.get("confidence", 50.0)))

    # Majority vote
    top_verdict, top_count = verdict_votes.most_common(1)[0]
    total_nodes = len(node_evaluations)
    quorum_ratio = round(top_count / total_nodes, 2)
    consensus_reached = quorum_ratio >= 0.60

    mean_conf = sum(confidences) / len(confidences)
    variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
    std_dev = math.sqrt(variance) if variance > 0 else 0.0

    # Flag outlier nodes
    annotated_nodes: List[Dict[str, Any]] = []
    for node in node_evaluations:
        n_copy = dict(node)
        n_verdict = str(n_copy.get("verdict", "UNVERIFIED")).upper()
        n_conf = float(n_copy.get("confidence", 50.0))

        is_verdict_outlier = (n_verdict != top_verdict) if top_count > 1 else False
        is_conf_outlier = (abs(n_conf - mean_conf) > 2.0 * std_dev) if std_dev > 5.0 else False

        n_copy["is_outlier"] = is_verdict_outlier or is_conf_outlier
        annotated_nodes.append(n_copy)

    return {
        "status": "success",
        "consensus_verdict": top_verdict,
        "consensus_reached": consensus_reached,
        "quorum_ratio": quorum_ratio,
        "total_nodes": total_nodes,
        "agreement_count": top_count,
        "mean_confidence": round(mean_conf, 1),
        "nodes": annotated_nodes,
        "fault_tolerance_model": "Ensemble Majority with Statistical Outlier Pruning"
    }
