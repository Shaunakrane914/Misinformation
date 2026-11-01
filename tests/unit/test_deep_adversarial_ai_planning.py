"""
Tests for Option B: Deep AI Layer Enhancement
Verifies adversarial misinformation probe generation, verification gate validation,
and misinformation claim grounding via Centralized LLM Gateway.
"""
import pytest
from backend.services.research.hybrid_discovery import (
    hybrid_discovery_coordinator,
    VerificationGate,
    AdversarialProbeProposal,
    AdversarialProbeBatch,
)
from backend.services.agent_reach.source_planner import SourcePlanningEngine
from backend.services.intelligence import analyze_misinformation_grounding


def test_adversarial_probe_batch_schema():
    """Verify AdversarialProbeProposal and AdversarialProbeBatch validation."""
    probe = AdversarialProbeProposal(
        channel="news",
        operation="search",
        query='"AcmeCorp" (accounting fraud OR whistleblower)',
        angle="REGULATORY_ALLEGATION",
        rationale="Probe for unverified accounting allegations."
    )
    assert probe.channel == "news"
    assert probe.operation == "search"
    batch = AdversarialProbeBatch(probes=[probe])
    assert len(batch.probes) == 1


def test_verification_gate_verify_adversarial_action():
    """Verify VerificationGate accepts valid probes and rejects unsafe or invalid actions."""
    gate = VerificationGate()
    allowed = {"news", "web", "reddit"}

    # 1. Valid probe
    valid_probe = AdversarialProbeProposal(
        channel="web",
        operation="search",
        query='"Tesla" (whistleblower OR safety defect OR recall)',
        angle="REGULATORY_ALLEGATION",
        rationale="Target safety defect allegations"
    )
    ok, action, reason = gate.verify_adversarial_action(valid_probe, "Tesla", allowed)
    assert ok is True
    assert action is not None
    assert action.channel == "web"
    assert action.source_category == "adversarial_misinformation_probe"

    # 2. Reject unpermitted channel
    bad_channel_probe = AdversarialProbeProposal(
        channel="darkweb",
        operation="search",
        query='"Tesla" leaks',
        rationale="invalid channel"
    )
    ok, action, reason = gate.verify_adversarial_action(bad_channel_probe, "Tesla", allowed)
    assert ok is False
    assert reason == "UNSUPPORTED_CHANNEL_OR_OPERATION"

    # 3. Reject non-search operation
    bad_op_probe = AdversarialProbeProposal(
        channel="web",
        operation="read",
        query='"Tesla" statements',
        rationale="invalid operation"
    )
    ok, action, reason = gate.verify_adversarial_action(bad_op_probe, "Tesla", allowed)
    assert ok is False
    assert reason == "AI_SEARCH_SUGGESTIONS_ONLY"

    # 4. Reject direct URL query
    url_probe = AdversarialProbeProposal(
        channel="web",
        operation="search",
        query='https://malicious-site.com/exploit',
        rationale="raw URL probe"
    )
    ok, action, reason = gate.verify_adversarial_action(url_probe, "Tesla", allowed)
    assert ok is False
    assert reason == "UNVALIDATED_SEARCH_QUERY"


def test_hybrid_discovery_coordinator_generates_adversarial_probes():
    """Verify coordinator generates verified adversarial probes across different agents."""
    coord = hybrid_discovery_coordinator
    allowed = {"news", "web", "reddit"}

    # Scout Agent
    scout_probes = coord.generate_adversarial_probes("Nvidia", "GPU shortage", "scout", allowed_channels=allowed)
    assert len(scout_probes) >= 1
    assert any("Nvidia" in a.query for a in scout_probes)
    assert all(a.source_category == "adversarial_misinformation_probe" for a in scout_probes)

    # BrandShield Agent
    brand_probes = coord.generate_adversarial_probes("Rolex", "Watch sales", "brandshield", allowed_channels=allowed)
    assert len(brand_probes) >= 1
    assert any("counterfeit" in a.query or "replica" in a.query or "boycott" in a.query for a in brand_probes)

    # Personal Watch Agent
    pw_probes = coord.generate_adversarial_probes("Sam Altman", "OpenAI speech", "personal_watch", allowed_channels=allowed)
    assert len(pw_probes) >= 1
    assert any("deepfake" in a.query or "voice clone" in a.query or "did not say" in a.query for a in pw_probes)


def test_source_planning_engine_includes_adversarial_probes():
    """Verify SourcePlanningEngine plan includes adversarial misinformation probes."""
    engine = SourcePlanningEngine()
    plan = engine.plan("Pfizer vaccine claims", entity="Pfizer", domain="brand", agent="brandshield")
    
    categories = [a.source_category for a in plan.actions]
    assert "adversarial_misinformation_probe" in categories or "contradiction_probe" in categories
    assert len(plan.actions) <= plan.budget.max_actions


def test_analyze_misinformation_grounding():
    """Verify analyze_misinformation_grounding handles evidence analysis gracefully."""
    evidence = [
        {
            "evidence_id": "ev1",
            "platform": "News",
            "source_role": "PRIMARY",
            "content": "Official regulatory filing states all products met compliance standards and no recall was issued.",
        },
        {
            "evidence_id": "ev2",
            "platform": "Reddit",
            "source_role": "COMMUNITY",
            "content": "Unverified forum post claimed massive secret recall was happening yesterday.",
        }
    ]
    result = analyze_misinformation_grounding(
        "Company secretly recalled products",
        evidence,
        target_entity="TechCorp"
    )
    assert isinstance(result, dict)
    assert "verdict" in result
    assert "confidence" in result
    assert "summary" in result

