"""
Aegis Protocol — Unit Tests for Hybrid Entity Resolution & Adaptive Discovery
=============================================================================
Verifies:
1. Failure Mode 1 (Target Unknown):
   - Layer 1 (Catalog hit) resolves deterministically without LLM.
   - Layer 2 (Registry hit) resolves dynamically from SEC index without LLM.
   - Layer 3 (Heuristic Fallback): Proposes candidate entity.
   - Verification Gate: Validates candidate against official registry; rejects hallucinations.
   - Invariant: Model suggestions NEVER mutate static catalogs.
2. Failure Mode 2 (Source Denied / Empty Observation):
   - Known entity has primary source denied (HTTP 403) or empty.
   - AI proposes alternative search paths for the SAME entity (never changes target).
   - Verification Gate verifies operations, channels, and safe URLs.
   - Telemetry honestly logs primary denial alongside fallback.
3. Agent-specific policies for Scout, BrandShield, Trending, and Personal Watch.
"""
import copy
from unittest.mock import MagicMock, patch
import pytest

from backend.infrastructure.llm.advisory_policy import MODEL, advisory_run, investigation_scope
from backend.infrastructure.llm.protocol import LLMProvider, LLMResponse, LLMUsage
from backend.infrastructure.llm.gateway import DefaultLLMGateway
from backend.services.agent_reach.source_planner import (
    PlanningBudget,
    SourceAction,
    SourcePlan,
    SourcePlanningEngine,
)
from backend.services.research.hybrid_discovery import (
    AdaptiveSourceProposal,
    CandidateEntityProposal,
    EntityProposalBatch,
    HybridDiscoveryCoordinator,
    VerificationGate,
)
from backend.services.research.issuer_identity import IssuerIdentityResolver


@pytest.fixture(autouse=True)
def offline_auth(tmp_path):
    with advisory_run(verified_models=[MODEL], database=tmp_path / "hybrid_adv.db"), investigation_scope("hybrid_test"):
        yield


@pytest.fixture
def sample_sec_resolver():
    """Resolver preloaded with a minimal authoritative SEC index double."""
    resolver = IssuerIdentityResolver()
    # Ingest synthetic official SEC index
    index_data = {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [
            [1067491, "Infosys Limited", "INFY", "NYSE"],
            [1065837, "Skechers U.S.A., Inc.", "SKX", "NYSE"],
            [320193, "Apple Inc.", "AAPL", "Nasdaq"],
            [103379, "V F CORP", "VFC", "NYSE"],  # Parent of Timberland
        ],
    }
    resolver.observe_ticker_index(
        index_data,
        "https://www.sec.gov/files/company_tickers_exchange.json",
        "0" * 64,
    )
    return resolver


# ===========================================================================
# 1. Failure Mode 1 Tests: Entity Resolution & Verification Gate
# ===========================================================================

def test_failure_mode_1_layer_1_and_2_resolve_without_llm(sample_sec_resolver):
    """When an entity is in Layer 1 or 2, it resolves directly without invoking LLM."""
    mock_gateway = MagicMock(spec=DefaultLLMGateway)
    coordinator = HybridDiscoveryCoordinator(gateway=mock_gateway)

    # Patch issuer_identity_resolver in hybrid_discovery to use sample_sec_resolver
    with patch("backend.services.research.issuer_identity.issuer_identity_resolver", sample_sec_resolver):
        res = coordinator.resolve_entity("INFY", agent="scout")
        assert res["status"] == "RESOLVED_WITH_PROVENANCE"
        assert res["cik"] == "0001067491"
        assert res["legal_name"] == "Infosys Limited"
        # Zero LLM calls made
        assert mock_gateway.generate_structured.call_count == 0


def test_failure_mode_1_unknown_entity_heuristic_verified_by_gate(sample_sec_resolver):
    """When entity is unknown, LLM proposes candidate, and Verification Gate confirms in SEC index."""
    mock_gateway = MagicMock(spec=DefaultLLMGateway)
    # Simulate LLM proposing "V F CORP" for query "Timberland"
    mock_gateway.generate_structured.return_value = EntityProposalBatch(
        candidates=[
            CandidateEntityProposal(
                legal_name="V F CORP",
                ticker="VFC",
                cik="0000103379",
                parent_company="V F CORP",
                rationale="Timberland is a subsidiary of VF Corporation (NYSE: VFC)",
            )
        ]
    )

    coordinator = HybridDiscoveryCoordinator(gateway=mock_gateway)

    with patch("backend.services.research.issuer_identity.issuer_identity_resolver", sample_sec_resolver):
        res = coordinator.resolve_entity("Timberland Boots", agent="scout")
        assert res["status"] == "RESOLVED_WITH_PROVENANCE"
        assert res["cik"] == "0000103379"
        assert res["legal_name"] == "V F CORP"
        assert res["resolution_path"] == "AI_HEURISTIC_CONFIRMED_IN_REGISTRY"
        assert mock_gateway.generate_structured.call_count == 1


def test_failure_mode_1_hallucinated_candidate_rejected_by_gate(sample_sec_resolver):
    """When LLM proposes a non-existent or fabricated entity, Verification Gate discards it."""
    mock_gateway = MagicMock(spec=DefaultLLMGateway)
    # Propose fictional CIK and company
    mock_gateway.generate_structured.return_value = EntityProposalBatch(
        candidates=[
            CandidateEntityProposal(
                legal_name="Fictional Vaporware LLC",
                ticker="FAKE",
                cik="0009999999",
                rationale="Invented company",
            )
        ]
    )

    coordinator = HybridDiscoveryCoordinator(gateway=mock_gateway)

    with patch("backend.services.research.issuer_identity.issuer_identity_resolver", sample_sec_resolver):
        res = coordinator.resolve_entity("UnheardOf Startup 99", agent="scout")
        assert res["status"] == "UNRESOLVED"
        assert res["cik"] is None
        assert "Fictional Vaporware LLC" in res["candidate_proposals_rejected"]


def test_failure_mode_1_never_mutates_static_catalog():
    """Verify that heuristic resolutions are strictly in-memory and never written to catalog file."""
    from backend.services.research.issuer_identity import CATALOG_PATH
    import json
    
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        before_catalog = json.load(f)

    gate = VerificationGate()
    proposal = CandidateEntityProposal(
        legal_name="Transient Candidate Corp",
        ticker="TCC",
        cik="0001234567",
        rationale="Transient test proposal",
    )
    # Verification fails on mock
    gate.verify_candidate_entity("scout", proposal, IssuerIdentityResolver())

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        after_catalog = json.load(f)

    assert before_catalog == after_catalog


# ===========================================================================
# 2. Failure Mode 2 Tests: Adaptive Source Discovery on Primary Source Denial
# ===========================================================================

def test_failure_mode_2_primary_source_denied_proposes_alternative_channels():
    """When primary SEC EDGAR returns 403, coordinator proposes permitted news/web wires for SAME entity."""
    mock_gateway = MagicMock(spec=DefaultLLMGateway)
    mock_gateway.generate_structured.return_value = MagicMock(
        actions=[
            AdaptiveSourceProposal(
                channel="news",
                operation="search",
                query="Infosys financial results quarterly announcement press release",
                rationale="Official quarterly announcements wire backup",
            )
        ]
    )

    coordinator = HybridDiscoveryCoordinator(gateway=mock_gateway)
    plan = SourcePlan(
        plan_id="sp_test_infosys",
        agent="scout",
        entity="Infosys Limited",
        claim="Infosys quarterly revenue report",
        intent_class="financial_integrity",
        actions=[
            SourceAction(
                action_id="act_init_1",
                stage=1,
                channel="sec_edgar",
                operation="search",
                query="Infosys 10-Q filing",
                source_category="regulatory_filing",
                expected_depth="FULL_DOCUMENT",
                priority=1,
                rationale="Primary regulatory filings",
            )
        ],
        excluded=[],
        budget=PlanningBudget(),
    )

    adaptive_actions = coordinator.adapt_sources_on_failure(
        plan, failed_channel="sec_edgar", failure_code_or_status="HTTP 403 Forbidden"
    )

    assert len(adaptive_actions) == 1
    action = adaptive_actions[0]
    assert action.channel == "news"
    assert "quarterly announcement press release" in action.query
    assert action.metadata["adaptive_fallback"] is True
    assert action.metadata["primary_failed_channel"] == "sec_edgar"
    assert action.metadata["primary_failure_status"] == "HTTP 403 Forbidden"
    # Entity identity remains unchanged
    assert plan.entity == "Infosys Limited"


def test_failure_mode_2_replan_integrates_adaptive_fallback():
    """Verify that SourcePlanningEngine.replan() activates adaptive discovery when primary is denied."""
    from backend.services.research.hybrid_discovery import hybrid_discovery_coordinator

    planner = SourcePlanningEngine()
    plan = SourcePlan(
        plan_id="sp_denied_test",
        agent="scout",
        entity="Apple Inc.",
        claim="Apple revenue report",
        intent_class="financial_integrity",
        actions=[],
        excluded=[],
        budget=PlanningBudget(max_replans=1),
    )

    mock_action = SourceAction(
        action_id="act_adaptive_sec_edgar_1",
        stage=2,
        channel="news",
        operation="search",
        query="Apple revenue announcement press release",
        source_category="adaptive_alternative_channel",
        expected_depth="CAPABILITY_DEPENDENT",
        priority=2,
        rationale="Fallback for blocked SEC filings",
    )

    with patch.object(hybrid_discovery_coordinator, "adapt_sources_on_failure", return_value=[mock_action]):
        replanned = planner.replan(
            plan,
            evidence_gaps=["sec_edgar HTTP 403 Forbidden: primary filing blocked"],
            primary_failure={"channel": "sec_edgar", "status": "HTTP 403 Forbidden"},
        )

    assert replanned.replan_count == 1
    # Check that warning documents the denial
    assert any("Adaptive source fallback: Primary channel 'sec_edgar'" in w for w in replanned.warnings)
    assert any(a.action_id == "act_adaptive_sec_edgar_1" for a in replanned.actions)


def test_failure_mode_2_rejects_unsafe_url_hints():
    """Verification Gate rejects SSRF or dangerous URL hints in proposals."""
    gate = VerificationGate()
    dangerous_proposal = AdaptiveSourceProposal(
        channel="web",
        operation="search",
        query="Safe query",
        source_hint="http://169.254.169.254/latest/meta-data/",  # Cloud metadata IP
        rationale="Dangerous probe",
    )
    valid, action, reason = gate.verify_adaptive_action(dangerous_proposal, "Apple", {"web", "news"})
    assert valid is False
    assert reason == "UNSAFE_URL_HINT"


# ===========================================================================
# 3. Agent-Specific Policies Tests
# ===========================================================================

def test_brandshield_policy_validates_brand_and_safe_domain():
    """BrandShield policy verifies domain safety."""
    gate = VerificationGate()
    prop_safe = CandidateEntityProposal(
        legal_name="Nike Inc.",
        official_domain="nike.com",
        rationale="Official brand domain",
    )
    valid, record, _ = gate.verify_candidate_entity("brandshield", prop_safe, None)
    assert valid is True
    assert record["official_domain"] == "nike.com"

    prop_unsafe = CandidateEntityProposal(
        legal_name="Nike Impersonator",
        official_domain="127.0.0.1",
        rationale="Private localhost probe",
    )
    valid, _, reason = gate.verify_candidate_entity("brandshield", prop_unsafe, None)
    assert valid is False
    assert reason == "UNSAFE_PROPOSED_DOMAIN"


def test_personal_watch_policy_rejects_sensitive_pii():
    """Personal Watch policy strictly rejects candidate proposals containing PII."""
    gate = VerificationGate()
    prop_pii = CandidateEntityProposal(
        legal_name="John Doe",
        rationale="Contact at john.doe@secretcorp.com with phone +15551234567",
    )
    valid, _, reason = gate.verify_candidate_entity("personal_watch", prop_pii, None)
    assert valid is False
    assert reason == "REJECTED_SENSITIVE_PII"
