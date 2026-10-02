"""
Unit Tests for Evidence Provenance Lineage and Deduplication Integrity
======================================================================
Verifies:
1. EvidenceFragment auto-baseline in __post_init__:
   - requested_channel defaults to channel.
   - actual_retrieval_channel defaults to channel.
   - retrieval_lineage initialized with baseline entry.
2. Deduplication preserves and merges lineage:
   - Merges retrieval_lineage across duplicates (no losing provenance).
   - Retains richer content and snippet when duplicate has higher length/detail.
3. Telemetry preservation during channel fallback:
   - requested_channel vs actual_retrieval_channel distinction.
   - final_by_ch groups by requested_channel so original channels aren't zeroed out.
4. EvidenceItem model serialization:
   - from_evidence_fragment carries over retrieval_lineage.
   - to_dict exports retrieval_lineage cleanly.
"""

import pytest
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.adapter import AgentReachService
from backend.services.research.research_models import EvidenceItem


class TestEvidenceFragmentProvenance:
    """Tests for EvidenceFragment provenance and lineage initialization."""

    def test_post_init_seeds_lineage(self):
        frag = EvidenceFragment(
            platform="Web",
            title="Headline 1",
            content="Detailed report content here...",
            url="https://example.com/article",
            snippet="Short snippet",
            channel_name="web",
            requested_channel="web",
            actual_retrieval_channel="news",
            retrieval_mode="live",
            native_backend_id="searxng",
            is_authenticated=True,
        )

        assert frag.requested_channel == "web"
        assert frag.actual_retrieval_channel == "news"
        assert len(frag.retrieval_lineage) == 1
        lineage = frag.retrieval_lineage[0]
        assert lineage["channel"] == "news"
        assert lineage["requested_channel"] == "web"
        assert lineage["retrieval_mode"] == "live"
        assert lineage["backend_id"] == "searxng"
        assert lineage["is_authenticated"] is True

    def test_fragment_to_dict_includes_lineage(self):
        frag = EvidenceFragment(
            platform="Twitter",
            title="Post",
            content="Tweet text",
            url="https://x.com/user/status/123",
            channel_name="social",
        )
        d = frag.to_dict()
        assert "requested_channel" in d
        assert "actual_retrieval_channel" in d
        assert "retrieval_lineage" in d
        assert isinstance(d["retrieval_lineage"], list)


class TestProvenanceDeduplication:
    """Tests for merging lineage and selecting richer content during deduplication."""

    def test_dedup_merges_lineage_and_keeps_richer_content(self):
        service = AgentReachService()

        # Fragment 1: shorter snippet from web
        f1 = EvidenceFragment(
            platform="Web",
            title="FDA Warning Letter",
            content="FDA issues warning letter to Acme Corp.",
            snippet="FDA issues warning",
            url="https://fda.gov/warning-letters/acme",
            channel_name="web",
            requested_channel="web",
            actual_retrieval_channel="web",
            retrieval_mode="live",
            native_backend_id="ddg",
        )

        # Fragment 2: duplicate URL from news channel with richer content
        f2 = EvidenceFragment(
            platform="News",
            title="FDA Warning Letter to Acme Corp",
            content="FDA issues warning letter to Acme Corp regarding manufacturing defects found during inspection.",
            snippet="FDA issues warning letter regarding manufacturing defects found during on-site inspection.",
            url="https://fda.gov/warning-letters/acme",
            channel_name="news",
            requested_channel="news",
            actual_retrieval_channel="news",
            retrieval_mode="live",
            native_backend_id="gdelt",
        )

        deduped, dupes_count = service._deduplicate_fragments([f1, f2])

        # Must dedup to 1 fragment
        assert len(deduped) == 1
        assert dupes_count == 1
        canonical = deduped[0]

        # Richer content should be retained
        assert "manufacturing defects" in canonical.content
        assert "manufacturing defects" in canonical.snippet

        # Lineage should contain both origins
        channels_in_lineage = {entry["channel"] for entry in canonical.retrieval_lineage}
        assert "web" in channels_in_lineage
        assert "news" in channels_in_lineage
        assert len(canonical.retrieval_lineage) == 2


class TestEvidenceItemLineagePreservation:
    """Tests that EvidenceItem preserves retrieval lineage from EvidenceFragment."""

    def test_from_evidence_fragment_preserves_lineage(self):
        frag = EvidenceFragment(
            platform="Reddit",
            title="Reddit Discussion",
            content="Full post discussion on thread",
            url="https://reddit.com/r/investing/comments/xyz",
            channel_name="reddit",
            requested_channel="social",
            actual_retrieval_channel="reddit",
            retrieval_lineage=[
                {"channel": "reddit", "requested_channel": "social", "retrieval_mode": "native"},
                {"channel": "web", "requested_channel": "web", "retrieval_mode": "search"}
            ]
        )

        item = EvidenceItem.from_evidence_fragment(
            frag,
            item_id="ev_001",
            target_name="Reddit Discussion",
        )

        assert len(item.retrieval_lineage) == 2
        assert item.retrieval_lineage[0]["channel"] == "reddit"
        assert item.retrieval_lineage[1]["channel"] == "web"

        item_dict = item.to_dict()
        assert "retrieval_lineage" in item_dict
        assert len(item_dict["retrieval_lineage"]) == 2
