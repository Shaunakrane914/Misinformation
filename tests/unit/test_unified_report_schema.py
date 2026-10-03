"""
Unit tests — Unified Report Schema & Report Builder (v3.8.0)
=============================================================
Covers:
  1.  QueryTelemetry — counts derived from execution log, not channel status
  2.  UnifiedEvidenceItem — lineage merging and URL normalisation
  3.  UnifiedQualityTensor — None values preserved (no synthetic defaults)
  4.  ReportBuilder — claim, trending, scout, brandshield, personal mappings
  5.  classify_evidence_items — bucket assignment (primary/independent/community)
  6.  Missing-data sentinel values (None, not fabricated)

Run with:
    pytest tests/unit/test_unified_report_schema.py -v
"""

import pytest
from unittest.mock import MagicMock
from backend.schemas.unified_report import (
    UnifiedReport,
    UnifiedQualityTensor,
    UnifiedEvidenceItem,
    UnifiedEvidenceSource,
    RetrievalLineageEntry,
    QueryTelemetry,
    TrustMetadata,
    TimelineEvent,
    classify_evidence_items,
    build_trust_metadata,
)
from backend.services.report_builder import ReportBuilder, _dict_to_quality_tensor


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

def _make_qer(status: str, channel: str = "news", backend_id: str = "bing-news") -> dict:
    """Build a minimal QueryExecutionRecord dict."""
    return {
        "query_id": f"Q-{status}",
        "query_text": f"test query [{status}]",
        "channel": channel,
        "status": status,
        "retrieval_mode": "web_search_index",
        "backend_id": backend_id,
        "started_at": "2026-10-03T10:00:00Z",
        "completed_at": "2026-10-03T10:00:01Z",
        "latency_ms": 800,
        "result_count_raw": 5,
        "result_count_normalized": 4,
        "error": None,
    }


@pytest.fixture
def mixed_execution_log() -> list:
    """3-query log: 2 SUCCESS, 1 FAILED."""
    return [
        _make_qer("SUCCESS", "news"),
        _make_qer("SUCCESS", "reddit"),
        _make_qer("FAILED",  "twitter"),
    ]


@pytest.fixture
def full_execution_log() -> list:
    """7-query log covering all terminal states."""
    return [
        _make_qer("SUCCESS"),
        _make_qer("SUCCESS"),
        _make_qer("FAILED"),
        _make_qer("TIMEOUT"),
        _make_qer("AUTH_REQUIRED"),
        _make_qer("SKIPPED"),
        _make_qer("SUCCESS"),
    ]


@pytest.fixture
def mock_evidence_item():
    """Mock research_models.EvidenceItem with all fields."""
    m = MagicMock()
    m.id = "ev-001"
    m.canonical_url = "https://example.com/article"
    m.title = "Test Article"
    m.source_name = "Example News"
    m.source_domain = "example.com"
    m.channel = "news"
    m.query_id = "Q-001"
    m.retrieval_mode = "web_search_index"
    m.native_backend_id = "bing-news"
    m.fallback_reason = None
    m.is_authenticated = False
    m.published_at = "2026-10-01T12:00:00Z"
    m.discovered_at = "2026-10-01T13:00:00Z"
    m.snippet = "An interesting excerpt."
    m.relevant_excerpt = ""
    m.source_role = "SECONDARY"
    m.source_tier = "TIER_2_FINANCIAL_PRESS"
    m.primary_source = False
    m.official_source = False
    m.retrieval_lineage = []
    qt = MagicMock()
    qt.relevance = 0.87
    qt.source_quality = 0.75
    qt.independence = 1.0
    qt.primary_weight = 0.5
    qt.freshness = 0.9
    qt.contradiction_level = 0.05
    m.quality_tensor = qt
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 1. QUERY TELEMETRY — execution-log-based counts
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryTelemetry:
    def test_counts_from_mixed_log(self, mixed_execution_log):
        tel = QueryTelemetry.from_execution_log(
            log=mixed_execution_log, queries_planned=3
        )
        assert tel.queries_planned == 3
        assert tel.queries_submitted == 3   # all 3 are non-PLANNED
        assert tel.queries_started == 3     # SUCCESS + SUCCESS + FAILED
        assert tel.queries_succeeded == 2
        assert tel.queries_failed == 1
        assert tel.queries_timed_out == 0
        assert tel.queries_auth_required == 0
        assert tel.queries_skipped == 0

    def test_full_state_coverage(self, full_execution_log):
        tel = QueryTelemetry.from_execution_log(
            log=full_execution_log, queries_planned=7
        )
        assert tel.queries_succeeded == 3
        assert tel.queries_failed == 1
        assert tel.queries_timed_out == 1
        assert tel.queries_auth_required == 1
        assert tel.queries_skipped == 1
        # skipped is NOT counted in started
        assert tel.queries_started == 6   # SUCCESS*3 + FAILED + TIMEOUT + AUTH_REQUIRED

    def test_empty_log_is_zero_counts(self):
        tel = QueryTelemetry.from_execution_log(log=[], queries_planned=0)
        assert tel.queries_succeeded == 0
        assert tel.queries_failed == 0
        assert tel.execution_log == []

    def test_execution_log_serialized(self, mixed_execution_log):
        tel = QueryTelemetry.from_execution_log(mixed_execution_log, queries_planned=3)
        assert len(tel.execution_log) == 3
        statuses = [r["status"] for r in tel.execution_log]
        assert "SUCCESS" in statuses
        assert "FAILED" in statuses

    def test_to_dict_has_all_keys(self, mixed_execution_log):
        tel = QueryTelemetry.from_execution_log(mixed_execution_log, queries_planned=3)
        d = tel.to_dict()
        required_keys = {
            "queries_planned", "queries_submitted", "queries_started",
            "queries_succeeded", "queries_failed", "queries_timed_out",
            "queries_auth_required", "queries_skipped", "execution_log",
        }
        assert required_keys.issubset(d.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 2. UNIFIED QUALITY TENSOR — no synthetic defaults
# ─────────────────────────────────────────────────────────────────────────────

class TestUnifiedQualityTensor:
    def test_default_is_all_none(self):
        qt = UnifiedQualityTensor()
        d = qt.to_dict()
        for key in ("relevance", "source_quality", "independence",
                    "primary_weight", "freshness", "contradiction"):
            assert d[key] is None, f"Expected None for {key}, got {d[key]}"

    def test_from_research_model_preserves_values(self, mock_evidence_item):
        qt = UnifiedQualityTensor.from_research_model(mock_evidence_item.quality_tensor)
        assert qt.relevance == pytest.approx(0.87)
        assert qt.contradiction == pytest.approx(0.05)

    def test_from_none_returns_empty(self):
        qt = UnifiedQualityTensor.from_research_model(None)
        assert qt.relevance is None
        assert qt.contradiction is None

    def test_dict_to_quality_tensor_roundtrip(self):
        d = {"relevance": 0.8, "source_quality": 0.7, "independence": 0.9,
             "primary_weight": 0.6, "freshness": 0.85, "contradiction": 0.1}
        qt = _dict_to_quality_tensor(d)
        assert qt.relevance == 0.8
        assert qt.contradiction == 0.1

    def test_dict_to_quality_tensor_missing_keys_are_none(self):
        qt = _dict_to_quality_tensor({"relevance": 0.9})
        assert qt.relevance == 0.9
        assert qt.source_quality is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. EVIDENCE ITEM — lineage and URL handling
# ─────────────────────────────────────────────────────────────────────────────

class TestUnifiedEvidenceItem:
    def test_from_evidence_item_maps_fields(self, mock_evidence_item):
        item = UnifiedEvidenceItem.from_evidence_item(mock_evidence_item)
        assert item.title == "Test Article"
        assert item.url == "https://example.com/article"
        assert item.snippet == "An interesting excerpt."
        assert item.source.name == "Example News"
        assert item.source.domain == "example.com"

    def test_empty_url_normalised_to_none(self, mock_evidence_item):
        mock_evidence_item.canonical_url = ""
        item = UnifiedEvidenceItem.from_evidence_item(mock_evidence_item)
        assert item.url is None, "Empty URL must be normalised to None"

    def test_lineage_built_from_item_fields(self, mock_evidence_item):
        """When retrieval_lineage is empty, a lineage entry is created from item attributes."""
        item = UnifiedEvidenceItem.from_evidence_item(mock_evidence_item)
        assert len(item.retrieval_lineage) == 1
        entry = item.retrieval_lineage[0]
        assert entry.query_id == "Q-001"
        assert entry.channel == "news"
        assert entry.backend_id == "bing-news"

    def test_existing_lineage_preserved(self, mock_evidence_item):
        mock_evidence_item.retrieval_lineage = [
            {"query_id": "Q-A", "channel": "reddit", "backend_id": "pushshift",
             "retrieval_mode": "web_search_index", "is_authenticated": False,
             "fallback_reason": None, "retrieved_at": "2026-10-01T12:00:00Z"},
            {"query_id": "Q-B", "channel": "news",   "backend_id": "bing-news",
             "retrieval_mode": "web_search_index", "is_authenticated": False,
             "fallback_reason": None, "retrieved_at": "2026-10-01T12:01:00Z"},
        ]
        item = UnifiedEvidenceItem.from_evidence_item(mock_evidence_item)
        assert len(item.retrieval_lineage) == 2, "Both lineage entries must be preserved"
        assert item.retrieval_lineage[0].channel == "reddit"
        assert item.retrieval_lineage[1].channel == "news"

    def test_to_dict_structure(self, mock_evidence_item):
        item = UnifiedEvidenceItem.from_evidence_item(mock_evidence_item)
        d = item.to_dict()
        for key in ("title", "snippet", "url", "timestamp", "source",
                    "quality_tensor", "retrieval_lineage"):
            assert key in d

    def test_quality_tensor_is_not_synthetic(self, mock_evidence_item):
        """quality_tensor values must come from the model, not from hardcoded defaults."""
        item = UnifiedEvidenceItem.from_evidence_item(mock_evidence_item)
        qt_dict = item.quality_tensor.to_dict()
        # Should NOT be the old default 0.5 placeholder
        assert qt_dict["relevance"] != 0.5
        assert qt_dict["relevance"] == pytest.approx(0.87)


# ─────────────────────────────────────────────────────────────────────────────
# 4. CLASSIFY EVIDENCE ITEMS — bucket assignment
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyEvidenceItems:
    def _make_item(self, primary_source=False, channel="news", role="SECONDARY"):
        m = MagicMock()
        m.primary_source = primary_source
        m.channel = channel
        m.source_role = role
        m.canonical_url = "https://example.com"
        m.title = "Test"
        m.source_name = "Outlet"
        m.source_domain = "example.com"
        m.snippet = "snippet"
        m.relevant_excerpt = ""
        m.published_at = ""
        m.query_id = "Q-X"
        m.retrieval_mode = "web_search_index"
        m.native_backend_id = None
        m.fallback_reason = None
        m.is_authenticated = False
        m.discovered_at = ""
        m.source_tier = "TIER_2_INVESTIGATIVE"
        m.retrieval_lineage = []
        m.quality_tensor = None
        return m

    def test_primary_source_flag_routes_to_primary(self):
        item = self._make_item(primary_source=True, channel="news")
        evset = classify_evidence_items([item])
        assert len(evset.primary) == 1
        assert len(evset.independent) == 0
        assert len(evset.community) == 0

    def test_social_channel_routes_to_community(self):
        for ch in ("reddit", "twitter", "x", "instagram", "youtube"):
            item = self._make_item(primary_source=False, channel=ch, role="SECONDARY")
            evset = classify_evidence_items([item])
            assert len(evset.community) == 1, f"Expected community for channel={ch}"

    def test_news_channel_routes_to_independent(self):
        item = self._make_item(primary_source=False, channel="news", role="SECONDARY")
        evset = classify_evidence_items([item])
        assert len(evset.independent) == 1

    def test_mixed_items_distributed_correctly(self):
        items = [
            self._make_item(primary_source=True,  channel="news"),
            self._make_item(primary_source=False, channel="reddit"),
            self._make_item(primary_source=False, channel="news"),
            self._make_item(primary_source=False, channel="web"),
        ]
        evset = classify_evidence_items(items)
        assert len(evset.primary) == 1
        assert len(evset.community) == 1
        assert len(evset.independent) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 5. REPORT BUILDER — claim verifier
# ─────────────────────────────────────────────────────────────────────────────

class TestReportBuilderClaim:
    @pytest.fixture
    def verdict_false(self):
        return {
            "verdict": "False",
            "confidence": 0.88,
            "reasoning": "No clinical trials support this claim. Health ministry denies any link. Multiple sources contradict it.",
            "severity": "High",
        }

    def test_summary_contains_verdict(self, verdict_false):
        report = ReportBuilder.from_claim_result(
            claim_text="Claim X", verdict=verdict_false
        )
        assert report.summary is not None
        assert "False" in report.summary

    def test_findings_extracted_from_reasoning(self, verdict_false):
        report = ReportBuilder.from_claim_result(
            claim_text="Claim X", verdict=verdict_false
        )
        assert len(report.findings) > 0
        # None of the findings should be hardcoded
        for f in report.findings:
            assert isinstance(f, str)
            assert f.strip() != ""

    def test_null_corpus_yields_null_quality_tensor(self):
        report = ReportBuilder.from_claim_result(
            claim_text="Test", verdict={"verdict": "Unverified"}, corpus=None
        )
        # CRITICAL: must NOT fabricate quality scores
        assert report.trust.quality_tensor is None

    def test_null_corpus_yields_null_ind_count(self):
        report = ReportBuilder.from_claim_result(
            claim_text="Test", verdict=None, corpus=None
        )
        assert report.trust.independent_source_count is None

    def test_empty_verdict_yields_null_summary(self):
        report = ReportBuilder.from_claim_result(claim_text="X", verdict=None)
        assert report.summary is None

    def test_to_dict_has_all_required_keys(self, verdict_false):
        report = ReportBuilder.from_claim_result(
            claim_text="Test", verdict=verdict_false
        )
        d = report.to_dict()
        required = {"summary", "findings", "evidence", "disagreements",
                    "changes", "timeline", "trust", "next_steps"}
        assert required.issubset(d.keys())

    def test_evidence_buckets_always_present(self, verdict_false):
        report = ReportBuilder.from_claim_result(
            claim_text="X", verdict=verdict_false
        )
        d = report.to_dict()
        assert "primary" in d["evidence"]
        assert "independent" in d["evidence"]
        assert "community" in d["evidence"]

    def test_trust_query_telemetry_present(self, verdict_false, mixed_execution_log):
        report = ReportBuilder.from_claim_result(
            claim_text="X",
            verdict=verdict_false,
            execution_log=mixed_execution_log,
            queries_planned=3,
        )
        tel = report.to_dict()["trust"]["query_telemetry"]
        assert tel["queries_planned"] == 3
        assert tel["queries_succeeded"] == 2
        assert tel["queries_failed"] == 1

    def test_agent_field_is_claim_verifier(self, verdict_false):
        report = ReportBuilder.from_claim_result(
            claim_text="Test", verdict=verdict_false
        )
        assert report.agent == "claim_verifier"


# ─────────────────────────────────────────────────────────────────────────────
# 6. REPORT BUILDER — trending, scout, brand, personal mappings
# ─────────────────────────────────────────────────────────────────────────────

class TestReportBuilderOtherAgents:
    def test_trending_uses_narratives_as_findings(self):
        trend_data = {
            "trend_summary": "Story X is trending due to controversy.",
            "narratives": [
                {"summary": "Users claim Event A occurred."},
                {"summary": "Counter-narrative: Event A is disputed."},
            ],
        }
        report = ReportBuilder.from_trending_result(query="Story X", trend_data=trend_data)
        assert report.summary == "Story X is trending due to controversy."
        assert len(report.findings) == 2
        assert report.agent == "trending"

    def test_scout_uses_catalysts_as_findings(self):
        scout_data = {
            "market_summary": "NVDA stock rose 8% after earnings beat.",
            "catalysts": ["EPS beat by 40%", "Revenue guidance raised"],
        }
        report = ReportBuilder.from_scout_result(query="NVDA", scout_data=scout_data)
        assert "NVDA" in report.summary
        assert len(report.findings) == 2
        assert report.agent == "scout"

    def test_brandshield_uses_threats_as_findings(self):
        brand_data = {
            "status": "Brand health compromised: 2 threats.",
            "threats": [
                {"description": "Counterfeit listing on Amazon."},
                {"description": "Fake social account detected."},
            ],
        }
        report = ReportBuilder.from_brandshield_result(query="AcmeCo", brand_data=brand_data)
        assert len(report.findings) == 2
        assert report.agent == "brandshield"

    def test_personal_uses_alerts_as_findings(self):
        personal_data = {
            "status": "Impersonation detected.",
            "threats": [{"description": "Twitter account mimicking verified identity."}],
        }
        report = ReportBuilder.from_personal_result(query="Jane Doe", personal_data=personal_data)
        assert len(report.findings) == 1
        assert report.agent == "personal_watch"

    def test_all_agents_produce_nonempty_next_steps(self):
        """Default next_steps must be provided even when no data contains them."""
        for name, fn, kw in [
            ("trending", ReportBuilder.from_trending_result,
             {"query": "Q", "trend_data": {}}),
            ("scout",    ReportBuilder.from_scout_result,
             {"query": "Q", "scout_data": {}}),
            ("brand",    ReportBuilder.from_brandshield_result,
             {"query": "Q", "brand_data": {}}),
            ("personal", ReportBuilder.from_personal_result,
             {"query": "Q", "personal_data": {}}),
        ]:
            report = fn(**kw)
            assert len(report.next_steps) > 0, f"{name} must have default next_steps"


# ─────────────────────────────────────────────────────────────────────────────
# 7. BUILD TRUST METADATA — corpus-aware
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildTrustMetadata:
    def test_null_corpus_all_null(self):
        trust = build_trust_metadata(corpus=None)
        assert trust.quality_tensor is None
        assert trust.independent_source_count is None

    def test_corpus_without_qt_leaves_qt_null(self):
        corpus = MagicMock()
        corpus.quality_tensor = None
        corpus.independent_source_groups = None
        trust = build_trust_metadata(corpus=corpus)
        assert trust.quality_tensor is None

    def test_corpus_with_ind_groups_counted(self):
        corpus = MagicMock()
        corpus.quality_tensor = None
        corpus.independent_source_groups = ["GroupA", "GroupB", "GroupC"]
        trust = build_trust_metadata(corpus=corpus)
        assert trust.independent_source_count == 3

    def test_telemetry_aggregated_from_log(self, mixed_execution_log):
        trust = build_trust_metadata(
            corpus=None,
            execution_log=mixed_execution_log,
            queries_planned=3,
        )
        assert trust.query_telemetry.queries_succeeded == 2
        assert trust.query_telemetry.queries_failed == 1
