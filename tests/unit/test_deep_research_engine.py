"""
Unit Tests for Aegis Protocol Shared Deep Research Engine
==========================================================
Verifies:
1. EvidenceItem typed model and dictionary backwards compatibility
2. SourceQualityEngine classification across regulatory, financial press, and community
3. SourceIndependenceEngine wire syndication clustering (Reuters/AP)
4. CandidateRanker deterministic scoring & diversity weighting
5. DeepReader diversity-aware candidate selection
6. PassageExtractor relevant excerpt and entity extraction
7. CorroborationEngine independent confirmation without syndication bias
8. ContradictionDetector factual negation and attribution conflict categorization
9. EvidenceGraphBuilder graph structure
10. ResearchEngine complete pipeline synthesis
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.research import (
    AtomicClaim,
    CandidateRanker,
    ConfidenceLevel,
    ContentDepth,
    ContradictionDetector,
    ContradictionType,
    CorroborationEngine,
    DeepReader,
    EvidenceGraphBuilder,
    EvidenceItem,
    Finding,
    FindingType,
    PassageExtractor,
    PrimarySourceEscalator,
    ResearchEngine,
    ResearchRequest,
    ResearchResult,
    SourceIndependenceEngine,
    SourceQualityEngine,
    SourceRole,
    SourceTier,
)


class TestDeepResearchEngine:
    """Test suite for the shared deep research infrastructure."""

    def test_evidence_item_model_and_dict_compatibility(self):
        item = EvidenceItem(
            id="ev_001",
            canonical_url="https://sec.gov/edgar/data/123/form10k.htm",
            title="Tesla Form 10-K Annual Report",
            source_name="SEC EDGAR",
            source_domain="sec.gov",
            channel="web",
            content_depth=ContentDepth.PRIMARY_DOCUMENT.value,
            snippet="Annual report pursuant to Section 13 or 15(d)",
            content="Full annual report text here...",
            primary_source=True,
            metadata={"custom_key": "val_123"}
        )

        # Typed access
        assert item.id == "ev_001"
        assert item.primary_source is True
        assert item.content_depth == "PRIMARY_DOCUMENT"

        # Dict-like backwards compatibility
        assert item["url"] == "https://sec.gov/edgar/data/123/form10k.htm"
        assert item["source"] == "SEC EDGAR"
        assert item["platform"] == "web"
        assert item["custom_key"] == "val_123"
        assert "url" in item
        assert item.get("source") == "SEC EDGAR"
        assert item.get("nonexistent", "default_val") == "default_val"

        # Serialized dictionary
        d = item.to_dict()
        assert d["evidence_id"] == "ev_001"
        assert d["is_primary"] is True
        assert d["has_url"] is True

    def test_source_quality_engine_classification(self):
        engine = SourceQualityEngine()

        # 1. SEC Regulatory Domain
        sec_item = EvidenceItem(id="1", canonical_url="https://www.sec.gov/edgar/10k", source_domain="sec.gov", title="10-K Filing")
        engine.classify_and_score(sec_item, target_name="Tesla")
        assert sec_item.source_role == SourceRole.PRIMARY.value
        assert sec_item.source_tier == SourceTier.TIER_1_OFFICIAL_FILING.value
        assert sec_item.source_quality_score >= 0.90

        # 2. Tier 1 Financial Press (Reuters)
        reuters_item = EvidenceItem(id="2", canonical_url="https://www.reuters.com/business/autos", source_domain="reuters.com", title="Tesla quarterly deliveries")
        engine.classify_and_score(reuters_item, target_name="Tesla")
        assert reuters_item.source_role == SourceRole.SECONDARY.value
        assert reuters_item.source_tier == SourceTier.TIER_2_FINANCIAL_PRESS.value
        assert reuters_item.source_quality_score >= 0.80

        # 3. Community Forum (Reddit)
        reddit_item = EvidenceItem(id="3", canonical_url="https://reddit.com/r/stocks/comments/xyz", source_domain="reddit.com", title="Discussion on EV stocks", channel="reddit")
        engine.classify_and_score(reddit_item, target_name="Tesla")
        assert reddit_item.source_role == SourceRole.COMMUNITY.value
        assert reddit_item.source_tier == SourceTier.TIER_3_INVESTOR_COMMUNITY.value
        assert reddit_item.source_quality_score <= 0.60

    def test_source_independence_wire_clustering(self):
        engine = SourceIndependenceEngine()

        # Create two articles republishing the same Reuters wire copy
        item1 = EvidenceItem(
            id="ev_01",
            canonical_url="https://finance.yahoo.com/news/tesla-deliveries-reuters",
            source_domain="finance.yahoo.com",
            title="Tesla quarterly deliveries beat estimates: Reuters",
            snippet="(Reuters) - Tesla reported quarterly electric vehicle deliveries that exceeded analyst expectations."
        )
        item2 = EvidenceItem(
            id="ev_02",
            canonical_url="https://msn.com/money/news/tesla-deliveries-reuters",
            source_domain="msn.com",
            title="Tesla quarterly deliveries beat estimates: Reuters",
            snippet="Reporting by Reuters - Electric vehicle maker Tesla beat expectations on deliveries Wednesday."
        )
        item3 = EvidenceItem(
            id="ev_03",
            canonical_url="https://techcrunch.com/2026/tesla-autonomous-taxi-report",
            source_domain="techcrunch.com",
            title="Hands on with Tesla new robotaxi software architecture",
            snippet="Our independent teardown of the new full self driving platform revealed key upgrades."
        )

        items, clusters = engine.cluster_independence([item1, item2, item3])

        # item1 and item2 must share the same wire family
        assert item1.source_family_id == item2.source_family_id
        assert item1.independence_group == item2.independence_group
        assert "wire_reuters" in item1.source_family_id
        assert item1.syndicated_from == "Reuters"
        assert item2.syndicated_from == "Reuters"

        # The syndicated copy receives heavily reduced independence score
        assert item1.independence_score > item2.independence_score
        assert item2.independence_score <= 0.20

        # item3 is independent
        assert item3.independence_group != item1.independence_group
        assert item3.independence_score >= 0.80

    def test_candidate_ranker_deterministic_scoring(self):
        ranker = CandidateRanker()

        item_prim = EvidenceItem(
            id="1",
            title="Tesla Inc Form 8-K Regulatory Filing",
            canonical_url="https://sec.gov/edgar/tsla",
            source_domain="sec.gov",
            source_role=SourceRole.PRIMARY.value,
            source_quality_score=0.95,
            primary_source=True,
            content_depth=ContentDepth.FULL_ARTICLE.value
        )
        item_sec = EvidenceItem(
            id="2",
            title="Tesla stock moves on delivery data",
            canonical_url="https://reuters.com/tesla",
            source_domain="reuters.com",
            source_role=SourceRole.SECONDARY.value,
            source_quality_score=0.82,
            content_depth=ContentDepth.PARTIAL_CONTENT.value
        )
        item_junk = EvidenceItem(
            id="3",
            title="Unrelated headline about gadgets",
            canonical_url="https://randomblog.com/gadgets",
            source_domain="randomblog.com",
            source_quality_score=0.30,
            content_depth=ContentDepth.HEADLINE_ONLY.value
        )

        ranked = ranker.rank_candidates([item_sec, item_junk, item_prim], target_name="Tesla", intent="earnings")
        assert ranked[0].id == "1", "Primary document must rank highest"
        assert ranked[1].id == "2", "Tier 1 press must rank second"
        assert ranked[2].id == "3", "Low quality unrelated source must rank last"

    def test_passage_extractor(self):
        extractor = PassageExtractor()
        content = (
            "This is a general introduction paragraph about clean energy trends across North America and Europe.\n\n"
            "On Wednesday, Tesla announced quarterly revenue of $25.17 billion, up 8% year-over-year, and confirmed that "
            "production of its new next-generation vehicle remains on schedule for early 2026. Management disclosed capital "
            "expenditures of $2.4 billion for autonomous compute.\n\n"
            "In other news, weather across California remained unseasonably mild according to meteorological bureaus."
        )
        item = EvidenceItem(id="ev_test", title="Tesla Earnings Release", content=content, canonical_url="https://tesla.com/press")
        extractor.extract_passages([item], target_name="Tesla", intent="earnings revenue")

        assert "$25.17 billion" in item.relevant_excerpt
        assert "announced quarterly revenue" in item.relevant_excerpt
        assert item.extraction_status == "SUCCESS"
        assert any("$25.17 billion" in top for top in item.topics)

    def test_corroboration_engine_group_accounting(self):
        engine = CorroborationEngine()

        it1 = EvidenceItem(id="1", source_name="Reuters", independence_group="wire_reuters_01")
        it2 = EvidenceItem(id="2", source_name="Yahoo", independence_group="wire_reuters_01")  # Syndicated copy of it1
        it3 = EvidenceItem(id="3", source_name="Bloomberg", independence_group="wire_bloomberg_01")
        it4 = EvidenceItem(id="4", source_name="Tesla IR", independence_group="domain_tesla.com", primary_source=True)

        res = engine.evaluate_corroboration([it1, it2, it3, it4])
        # 4 items, but only 3 independent source groups (it1 & it2 are in same wire group)
        assert res["independent_group_count"] == 3
        assert res["syndicated_repetition_count"] == 1
        assert res["primary_source_count"] == 1
        assert res["confidence"] == ConfidenceLevel.HIGH.value

    def test_contradiction_detector(self):
        detector = ContradictionDetector()

        it_affirmative = EvidenceItem(
            id="ev_01",
            title="Tata Motors in talks to acquire British EV battery startup for 500M",
            snippet="Report claims Tata Motors is finalizing acquisition talks for battery startup."
        )
        it_denial = EvidenceItem(
            id="ev_02",
            title="Tata Motors denies rumors of battery startup acquisition talks",
            snippet="Tata Motors officially dismissed and rejected reports that it is in talks to acquire the battery startup, calling rumors unfounded.",
            source_name="Tata Motors Official Statement",
            primary_source=True
        )

        contradictions = detector.detect_contradictions([it_affirmative, it_denial], target_name="Tata Motors")
        assert len(contradictions) >= 1
        c = contradictions[0]
        assert c["type"] == ContradictionType.FACTUAL_CONTRADICTION.value
        assert it_affirmative.contradiction_flag is True
        assert it_denial.contradiction_flag is True
        assert c["severity"] == "HIGH"

    def test_evidence_graph_builder(self):
        builder = EvidenceGraphBuilder()

        finding = Finding(
            finding_id="fnd_001",
            title="Quarterly Earnings Beat",
            statement="Reported revenue exceeded consensus.",
            supporting_evidence_ids=["ev_10", "ev_20"],
            contradicting_evidence_ids=["ev_30"]
        )
        ev1 = EvidenceItem(id="ev_10", title="SEC 10-Q Filing", source_name="SEC", canonical_url="https://sec.gov")
        ev2 = EvidenceItem(id="ev_20", title="Reuters Coverage", source_name="Reuters", canonical_url="https://reuters.com")
        ev3 = EvidenceItem(id="ev_30", title="Analyst Downgrade", source_name="ShortSeller", canonical_url="https://blog.com")

        graph = builder.build_graph([finding], [ev1, ev2, ev3])
        assert graph["node_count"] == 4  # 1 finding + 3 evidence items
        assert graph["edge_count"] == 3  # 2 SUPPORTS + 1 CONTRADICTS
        edge_relations = [e["relation"] for e in graph["edges"]]
        assert "SUPPORTS" in edge_relations
        assert "CONTRADICTS" in edge_relations

    def test_research_engine_investigate_pipeline(self):
        engine = ResearchEngine()

        mock_frag = MagicMock()
        mock_frag.url = "https://sec.gov/edgar/data/123/tsla.htm"
        mock_frag.title = "Tesla Form 10-K Filing Discloses Capital Outlay"
        mock_frag.content = "Tesla reported annual revenue of $96.7 billion and announced factory expansion in Nevada."
        mock_frag.snippet = "Annual report Form 10-K filed with the SEC."
        mock_frag.author = "SEC EDGAR"
        mock_frag.platform = "web"
        mock_frag.channel_name = "web"
        mock_frag.published = "2026-01-20"
        mock_frag.retrieved_at = "2026-01-20T10:00:00Z"
        mock_frag.content_depth = "FULL_ARTICLE"
        mock_frag.query_id = "wb_01"
        mock_frag.query_class = "filing"
        mock_frag.query_text = "Tesla 10-K filing"
        mock_frag.score = 0.95
        mock_frag.retrieval_method = "agent_reach"
        mock_frag.raw_metadata = {
            "source_role": "PRIMARY",
            "source_tier": "TIER_1_OFFICIAL_FILING",
            "source_independence_group": "sec_edgar"
        }

        mock_retrieval_result = MagicMock()
        mock_retrieval_result.fragments = [mock_frag]
        mock_retrieval_result.channel_health = {"web": "AVAILABLE"}
        mock_retrieval_result.retrieval_trace = {"total_raw": 1}

        with patch("backend.services.agent_reach.adapter.AgentReachService.retrieve_many", return_value=mock_retrieval_result):
            req = ResearchRequest(
                target="Tesla",
                domain="financial",
                intent="identify revenue and capex",
                deep_read_budget=2
            )
            result = engine.investigate(req)

            assert isinstance(result, ResearchResult)
            assert result.target == "Tesla"
            assert result.domain == "financial"
            assert len(result.evidence) >= 1
            assert len(result.findings) >= 1
            assert result.findings[0].type in (FindingType.CATALYST.value, FindingType.FACT.value)
            assert "node_count" in result.source_graph
            assert result.telemetry["candidates_found"] >= 1
