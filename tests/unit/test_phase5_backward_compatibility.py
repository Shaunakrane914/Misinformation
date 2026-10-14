"""
Aegis Protocol — Phase 5 Backward Compatibility & Legacy Surface Verification
=============================================================================
Validates:
1. Exact class identity (`is`) between historical import paths and new canonical packages.
2. Singleton instance equivalence across all 4 domain agents and 4 domain extractors.
3. Historical public method signatures and return contracts.
4. Legacy unittesting patch targets (`backend.services.agent_reach.scout.engine.agent_reach_service.execute`).
5. Module-level helper functions and async/sync task runners.
6. Invariant verification: ScoutSourceEngine does not invoke ScoutTransport in production.
"""

import inspect
from unittest.mock import patch, MagicMock
import pytest

# 1. Historical Agent Imports
from backend.agents.brandshield_agent import (
    BrandShieldAgent as BSA_Hist,
    brandshield_agent as bsa_inst_Hist,
    THREAT_TAXONOMY as TT_Hist,
    KNOWN_BRAND_CATALOG as KBC_Hist,
)
from backend.agents.trending_agent import (
    TrendingAgent as TA_Hist,
    trending_agent as ta_inst_Hist,
    Trend as Trend_Hist,
    TrendEvidence as TrendEvidence_Hist,
    fetch_news as fn_Hist,
    fetch_targeted_news as ftn_Hist,
    fetch_paparazzi as fp_Hist,
    fetch_box_office as fbo_Hist,
)
from backend.agents.personal_agent import (
    PersonalWatchAgent as PA_Hist,
    personal_agent as pa_inst_Hist,
    process_personal_watch as ppw_Hist,
    THREAT_TAXONOMY as PTT_Hist,
    KNOWN_PUBLIC_PROFILES as KPP_Hist,
)
from backend.agents.scout_agent import (
    ScoutAgent as SA_Hist,
    scout_agent as sa_inst_Hist,
    process_scout_task as pst_Hist,
)

# Canonical New Package Imports
from backend.agents.brandshield import (
    BrandShieldAgent as BSA_Canon,
    brandshield_agent as bsa_inst_Canon,
    THREAT_TAXONOMY as TT_Canon,
    KNOWN_BRAND_CATALOG as KBC_Canon,
)
from backend.agents.trending import (
    TrendingAgent as TA_Canon,
    trending_agent as ta_inst_Canon,
    Trend as Trend_Canon,
    TrendEvidence as TrendEvidence_Canon,
    fetch_news as fn_Canon,
    fetch_targeted_news as ftn_Canon,
    fetch_paparazzi as fp_Canon,
    fetch_box_office as fbo_Canon,
)
from backend.agents.personal_watch import (
    PersonalWatchAgent as PA_Canon,
    personal_watch_agent as pa_inst_Canon,
    process_personal_watch as ppw_Canon,
    THREAT_TAXONOMY as PTT_Canon,
    KNOWN_PUBLIC_PROFILES as KPP_Canon,
)
from backend.agents.scout import (
    ScoutAgent as SA_Canon,
    scout_agent as sa_inst_Canon,
    process_scout_task as pst_Canon,
)

# Extraction imports
from backend.services.agent_reach.extraction.brandshield_extraction import (
    BrandShieldExtractionEngine as BSEE_Hist,
    brandshield_extractor as be_Hist,
)
from backend.agents.brandshield.extraction import (
    BrandShieldExtractionEngine as BSEE_Canon,
    brandshield_extractor as be_Canon,
)
from backend.services.agent_reach.extraction.trending_extraction import (
    TrendingExtractionEngine as TEE_Hist,
    trending_extractor as te_Hist,
)
from backend.agents.trending.extraction import (
    TrendingExtractionEngine as TEE_Canon,
    trending_extractor as te_Canon,
)
from backend.services.agent_reach.extraction.personal_extraction import (
    PersonalWatchExtractionEngine as PEE_Hist,
    personal_watch_extractor as pe_Hist,
)
from backend.agents.personal_watch.extraction import (
    PersonalWatchExtractionEngine as PEE_Canon,
    personal_watch_extractor as pe_Canon,
)
from backend.services.agent_reach.extraction.scout_extraction import (
    ScoutExtractionEngine as SEE_Hist,
    scout_extractor as se_Hist,
)
from backend.agents.scout.extraction import (
    ScoutExtractionEngine as SEE_Canon,
    scout_extractor as se_Canon,
)

# Scout Source Engine imports
from backend.services.agent_reach.scout.engine import (
    ScoutSourceEngine as SSE_Hist,
    scout_source_engine as sse_Hist,
)
from backend.agents.scout.sources.engine import (
    ScoutSourceEngine as SSE_Canon,
    scout_source_engine as sse_Canon,
)


def test_agent_class_identity_parity():
    """Verify historical imports resolve to identical canonical classes."""
    assert BSA_Hist is BSA_Canon
    assert TA_Hist is TA_Canon
    assert PA_Hist is PA_Canon
    assert SA_Hist is SA_Canon


def test_agent_singleton_identity_parity():
    """Verify historical singleton instances resolve to identical canonical singletons."""
    assert bsa_inst_Hist is bsa_inst_Canon
    assert ta_inst_Hist is ta_inst_Canon
    assert pa_inst_Hist is pa_inst_Canon
    assert sa_inst_Hist is sa_inst_Canon


def test_extractor_class_and_singleton_parity():
    """Verify all 4 domain extractors maintain class and instance identity."""
    assert BSEE_Hist is BSEE_Canon
    assert be_Hist is be_Canon

    assert TEE_Hist is TEE_Canon
    assert te_Hist is te_Canon

    assert PEE_Hist is PEE_Canon
    assert pe_Hist is pe_Canon

    assert SEE_Hist is SEE_Canon
    assert se_Hist is se_Canon


def test_scout_source_engine_class_and_singleton_parity():
    """Verify ScoutSourceEngine maintains identity across historical and canonical paths."""
    assert SSE_Hist is SSE_Canon
    assert sse_Hist is sse_Canon


def test_public_model_and_taxonomy_parity():
    """Verify domain models and taxonomies are identical."""
    assert TT_Hist is TT_Canon
    assert KBC_Hist is KBC_Canon

    assert Trend_Hist is Trend_Canon
    assert TrendEvidence_Hist is TrendEvidence_Canon

    assert PTT_Hist is PTT_Canon
    assert KPP_Hist is KPP_Canon


def test_public_helper_functions_parity():
    """Verify module-level helper functions match."""
    assert ppw_Hist is ppw_Canon
    assert pst_Hist is pst_Canon

    assert fn_Hist is fn_Canon
    assert ftn_Hist is ftn_Canon
    assert fp_Hist is fp_Canon
    assert fbo_Hist is fbo_Canon


def test_brandshield_agent_method_signatures():
    """Verify BrandShieldAgent public method signatures remain backward-compatible."""
    sig_scan = inspect.signature(BSA_Canon.scan)
    assert "brand_name" in sig_scan.parameters
    assert "query" in sig_scan.parameters

    sig_resolve = inspect.signature(BSA_Canon.resolve_brand_entity)
    assert "raw_input" in sig_resolve.parameters

    sig_search = inspect.signature(BSA_Canon.search_brand_evidence)
    assert "brand_info" in sig_search.parameters


def test_trending_agent_method_signatures():
    """Verify TrendingAgent public method signatures remain backward-compatible."""
    sig_scan = inspect.signature(TA_Canon.scan)
    assert "asset_name" in sig_scan.parameters
    assert "identifiers" in sig_scan.parameters
    assert "category" in sig_scan.parameters
    assert "mode" in sig_scan.parameters

    sig_resolve = inspect.signature(TA_Canon.resolve_entity)
    assert "input_text" in sig_resolve.parameters


def test_personal_watch_agent_method_signatures():
    """Verify PersonalWatchAgent public method signatures remain backward-compatible."""
    sig_scan = inspect.signature(PA_Canon.scan)
    assert "vip_profile" in sig_scan.parameters

    sig_resolve = inspect.signature(PA_Canon.resolve_personal_entity)
    assert "profile_or_name" in sig_resolve.parameters


def test_scout_agent_method_signatures():
    """Verify ScoutAgent public method signatures remain backward-compatible."""
    sig_fetch = inspect.signature(SA_Canon.fetch_stock_data)
    assert "ticker" in sig_fetch.parameters

    sig_vol = inspect.signature(SA_Canon.analyze_volatility)
    assert "prices" in sig_vol.parameters

    sig_acq = inspect.signature(SA_Canon.acquire_market_intelligence)
    assert "ticker" in sig_acq.parameters

    sig_intel = inspect.signature(SA_Canon.generate_scout_intelligence)
    assert "subject" in sig_intel.parameters


def test_legacy_scout_patch_target_interception():
    """
    CRITICAL: Verify unittest monkeypatch target
    patch('backend.services.agent_reach.scout.engine.agent_reach_service.execute', ...)
    successfully intercepts calls made to scout_source_engine.execute.
    """
    from backend.services.agent_reach.channels import EvidenceFragment
    from backend.services.agent_reach.scout.models import ScoutSourceRequest

    mock_frag = EvidenceFragment(
        evidence_id="ev_patch_test",
        platform="web",
        url="https://sec.gov/filing/test",
        title="Test SEC Filing",
        content="Revenue of $10B reported.",
        snippet="Revenue of $10B.",
        author="SEC",
        published="2026-10-10T00:00:00Z"
    )

    with patch("backend.services.agent_reach.scout.engine.agent_reach_service.execute", return_value=[mock_frag]) as mock_exec:
        req = ScoutSourceRequest(query="test", target_entity="TestCorp")
        result = sse_Canon.execute(req)
        assert mock_exec.called
        assert len(result.evidence_items) == 1
        assert result.evidence_items[0].evidence_id == "ev_patch_test"


def test_scout_source_engine_does_not_call_scout_transport():
    """
    Architectural Invariant & Task 3 Audit:
    Prove that ScoutSourceEngine.execute() delegates to AgentReachService
    and never calls ScoutTransport.get() directly.
    """
    from backend.agents.scout.sources.transport import scout_transport
    from backend.services.agent_reach.channels import EvidenceFragment
    from backend.services.agent_reach.scout.models import ScoutSourceRequest

    mock_frag = EvidenceFragment(
        evidence_id="ev_transport_guard",
        platform="web",
        url="https://example.com/press",
        title="Press Release",
        content="Quarterly revenue $5B.",
        snippet="Quarterly revenue $5B.",
        author="Press",
        published="2026-10-10T00:00:00Z"
    )

    with patch.object(scout_transport, "get", side_effect=RuntimeError("ScoutTransport.get was unexpectedly called!")):
        with patch("backend.services.agent_reach.scout.engine.agent_reach_service.execute", return_value=[mock_frag]):
            req = ScoutSourceRequest(query="test", target_entity="TestCorp")
            result = sse_Canon.execute(req)
            assert len(result.evidence_items) == 1
