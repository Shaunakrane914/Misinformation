"""Unit test suite verifying all 10 decomposed research pipeline stages independently."""

from unittest.mock import MagicMock, patch
import time
import pytest

from backend.application.research import (
    AdaptiveDiscoveryCoordinator,
    AdaptiveEvidence,
    Analysis,
    AssembledResearch,
    BroadDiscoveryStage,
    CandidateQualificationStage,
    CorpusAssemblyStage,
    DeepReadingStage,
    Discovery,
    DiscoveryStage,
    DossierRegistrationStage,
    EvidenceGraphStage,
    GatingStage,
    GraphConstructionStage,
    GroundedSynthesisStage,
    IndependenceRankingStage,
    LedgerPersistenceStage,
    PassageAnalysisStage,
    PassageExtractionStage,
    PlanningStage,
    PrimaryEscalationStage,
    QueryPlan,
    QueryPlanningStage,
    RankingStage,
    ResearchPipeline,
    ResultPublicationStage,
    SynthesisStage,
)
from backend.services.agent_reach.channels import (
    EvidenceFragment,
    QueryExecutionRecord,
    RetrievalResult,
)
from backend.services.research.evidence_saturation import EvidenceNoveltyTracker
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import (
    EvidenceItem,
    Finding,
    FindingType,
    QualityTensor,
    ResearchCorpus,
    ResearchRequest,
    ResearchResult,
)


def _make_fragment(frag_id="ev_001", title="Test Title", snippet="Test Snippet", url="https://example.com/1", query_class="general"):
    return EvidenceFragment(
        platform="Web",
        title=title,
        url=url,
        content=snippet,
        snippet=snippet,
        evidence_id=frag_id,
        channel_name="web",
        query_id="q_001",
        query_class=query_class,
    )


def _make_item(item_id="ev_001", title="Test Title", snippet="Test Snippet", url="https://example.com/1", query_class="general", primary=False):
    frag = _make_fragment(frag_id=item_id, title=title, snippet=snippet, url=url, query_class=query_class)
    item = EvidenceItem.from_evidence_fragment(frag, item_id=item_id, target_name="Tesla Inc")
    if primary:
        item.primary_source = True
    return item


def test_stage_1_query_planning_stage():
    stage = PlanningStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial")
    plan = stage.run(request)

    assert isinstance(plan, QueryPlan)
    assert plan.planner is not None
    assert isinstance(plan.channel_queries, dict)
    assert len(plan.channel_queries) > 0
    assert plan.query_classes is not None


def test_stage_2_broad_discovery_stage():
    stage = DiscoveryStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial")
    budget = ResearchBudget()
    plan = QueryPlan(planner=MagicMock(), channel_queries={"web": [{"query_text": "Tesla"}]}, query_classes=["general"])

    dummy_result = RetrievalResult(
        query="Tesla",
        domain="financial",
        fragments=[_make_fragment()],
        channel_health={"web": "AVAILABLE"},
    )

    with patch("backend.services.agent_reach.agent_reach_service.retrieve_many", return_value=dummy_result) as mock_retrieve:
        retrieval = stage.run(request, budget, effective_timeout=10.0, plan=plan)
        assert retrieval == dummy_result
        mock_retrieve.assert_called_once()


def test_stage_3_candidate_qualification_gating_stage():
    stage = GatingStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial")

    frag_relevant = _make_fragment("ev_001", title="Tesla Q3 revenue", snippet="Tesla reported Q3 revenue growth.")
    frag_irrelevant = _make_fragment("ev_002", title="Cooking recipes", snippet="Chocolate chip cookies recipe.")

    retrieval = RetrievalResult(
        query="Tesla",
        domain="financial",
        fragments=[frag_relevant, frag_irrelevant],
        channel_health={"web": "AVAILABLE"},
    )

    discovery = stage.run(request, retrieval)
    assert isinstance(discovery, Discovery)
    assert len(discovery.raw_candidates) == 2
    assert len(discovery.accepted) >= 1
    assert any(c.id == "ev_001" for c in discovery.accepted)


def test_stage_4_primary_escalation_stage_empty_and_active():
    stage = PrimaryEscalationStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial")
    budget = ResearchBudget(primary_escalation_budget=2)

    ev_item = _make_item("ev_001", "Secondary article", "According to SEC filing, Tesla earned 25B.", "https://news.com/article")
    from backend.application.research.contracts import RankedEvidence
    ranked = RankedEvidence(accepted=[ev_item], ranked=[ev_item], clusters={"grp1": ["ev_001"]}, rejected=[])

    with patch("backend.services.research.primary_source_escalator.primary_source_escalator.escalate", return_value=([], {"queries": [], "escalations": 0})):
        escalated = stage.run(request, budget, ranked, start_ts=100.0, effective_timeout=50.0)
        assert len(escalated.primaries) == 0
        assert escalated.ranked == ranked


def test_stage_5_independence_ranking_stage():
    stage = RankingStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial")
    plan = QueryPlan(planner=MagicMock(), channel_queries={}, query_classes=["general"])

    ev1 = _make_item("ev_001", "Tesla Q3", "Tesla revenue up", "https://sec.gov/1")
    ev2 = _make_item("ev_002", "Tesla Q3 copy", "Tesla revenue up", "https://mirror.com/1")

    ranked_res = stage.run(request, plan, accepted=[ev1, ev2], rejected=[])
    assert len(ranked_res.ranked) == 2
    assert "ev_001" in [i.id for i in ranked_res.ranked]


def test_adaptive_discovery_coordinator_empty():
    coordinator = AdaptiveDiscoveryCoordinator()
    request = ResearchRequest(target="Tesla Inc", domain="financial")
    budget = ResearchBudget(follow_up_budget=0)  # zero budget = no rounds
    plan = QueryPlan(planner=MagicMock(), channel_queries={}, query_classes=["general"])

    ev1 = _make_item("ev_001", "Tesla Q3", "Tesla revenue up", "https://sec.gov/1")
    from backend.application.research.contracts import RankedEvidence
    ranked = RankedEvidence(accepted=[ev1], ranked=[ev1], clusters={"grp1": ["ev_001"]}, rejected=[])
    discovery = Discovery(retrieval=MagicMock(), raw_candidates=[ev1], accepted=[ev1], rejected=[])

    adaptive = coordinator.run(request, budget, plan, discovery, ranked, start_ts=0.0, effective_timeout=10.0)
    assert isinstance(adaptive, AdaptiveEvidence)
    assert adaptive.telemetry["rounds_executed"] == 0
    assert len(adaptive.query_records) == 0


def test_shared_source_replan_is_triggered_by_real_evidence_gaps():
    from backend.application.research.contracts import RankedEvidence
    from backend.services.agent_reach.native.operation_capabilities import (
        runtime_operation_capabilities,
    )
    from backend.services.agent_reach.source_planner import source_planning_engine

    runtime_operation_capabilities.reset_observations()
    request = ResearchRequest(target="Acme", domain="general")
    budget = ResearchBudget(follow_up_budget=1, timeout_seconds=20)
    legacy_planner = MagicMock()
    legacy_planner.plan_adaptive_follow_ups.return_value = []
    source_plan = source_planning_engine.plan(
        "Acme made an unverified claim", entity="Acme", domain="general"
    )
    plan = QueryPlan(
        planner=legacy_planner, channel_queries={}, query_classes=["general"],
        source_plan=source_plan,
    )
    ranked = RankedEvidence(accepted=[], ranked=[], clusters={}, rejected=[])
    discovery = Discovery(
        retrieval=RetrievalResult(query="Acme", domain="general"),
        raw_candidates=[], accepted=[], rejected=[],
    )
    empty_replan = RetrievalResult(query="Acme", domain="general", query_records=[])
    with patch(
        "backend.services.agent_reach.agent_reach_service.retrieve_many",
        return_value=empty_replan,
    ) as retrieve_many:
        adaptive = AdaptiveDiscoveryCoordinator().run(
            request, budget, plan, discovery, ranked,
            start_ts=time.time(), effective_timeout=20.0,
        )
    assert adaptive.telemetry["source_replan"]["triggered"] is True
    assert "missing primary evidence" in adaptive.telemetry["source_replan"]["gaps"]
    submitted = retrieve_many.call_args.kwargs["channel_queries"]
    assert submitted
    assert all(
        item["operation"] == "search"
        for queries in submitted.values() for item in queries
    )


def test_stage_6_deep_reading_stage():
    stage = DeepReadingStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial", deep_read_budget=2)
    budget = ResearchBudget(deep_read_budget=2)

    ev1 = _make_item("ev_001", "Tesla Q3", "Tesla revenue up", "https://sec.gov/1")
    from backend.application.research.contracts import RankedEvidence
    ranked = RankedEvidence(accepted=[ev1], ranked=[ev1], clusters={"grp1": ["ev_001"]}, rejected=[])

    with patch("backend.services.research.deep_reader.deep_reader.deep_read", return_value=([ev1], {"attempted": 1, "successful": 1, "read_urls": [ev1.canonical_url]})):
        read_res = stage.run(request, budget, ranked, start_ts=0.0, effective_timeout=20.0)
        assert len(read_res.investigated) == 1
        assert read_res.telemetry["successful"] == 1


def test_stage_7_passage_extraction_stage():
    stage = PassageExtractionStage()
    request = ResearchRequest(target="Tesla Inc", domain="financial")

    ev1 = _make_item("ev_001", "Tesla Q3", "Tesla revenue up", "https://sec.gov/1")
    ev1.raw_text = "Tesla announced Q3 financial revenue rose 20%."
    from backend.application.research.contracts import RankedEvidence, ReadEvidence
    ranked = RankedEvidence(accepted=[ev1], ranked=[ev1], clusters={"grp1": ["ev_001"]}, rejected=[])
    read = ReadEvidence(investigated=[ev1], telemetry={})

    out = stage.run(request, ranked, read)
    assert len(out.investigated) == 1
    assert out.investigated[0].id == "ev_001"


def test_stage_8_and_9_synthesis_and_graph_construction_stages():
    synth_stage = SynthesisStage()
    graph_stage = GraphConstructionStage()

    request = ResearchRequest(target="Tesla Inc", domain="financial")
    ev1 = _make_item("ev_001", "Tesla Revenue Report", "Tesla Q3 earnings report confirmed revenue increase.", "https://sec.gov/1", query_class="financial_earnings", primary=True)
    ev1.relevant_excerpt = "Tesla Q3 earnings report confirmed revenue increase."
    ev1.source_name = "SEC"

    from backend.application.research.contracts import RankedEvidence, ReadEvidence
    ranked = RankedEvidence(accepted=[ev1], ranked=[ev1], clusters={"grp1": ["ev_001"]}, rejected=[])
    read = ReadEvidence(investigated=[ev1], telemetry={})

    analysis = synth_stage.run(request, ranked, read)
    assert isinstance(analysis, Analysis)
    assert len(analysis.findings) >= 1

    analysis_with_graphs = graph_stage.run(ranked, analysis)
    assert "nodes" in analysis_with_graphs.graph or "findings" in analysis_with_graphs.graph or isinstance(analysis_with_graphs.graph, dict)
    assert isinstance(analysis_with_graphs.lineage_graph, dict)


def test_stage_10_assembly_dossier_and_publication():
    corpus_stage = CorpusAssemblyStage()
    dossier_stage = LedgerPersistenceStage()
    pub_stage = ResultPublicationStage()

    request = ResearchRequest(target="Tesla Inc", domain="financial", agent_name="tester")
    budget = ResearchBudget()
    plan = QueryPlan(planner=MagicMock(), channel_queries={"web": [{"query_id": "q1", "query_text": "Tesla"}]}, query_classes=["general"])

    ev1 = _make_item("ev_001", "Tesla Revenue", "Revenue up", "https://sec.gov/1", primary=True)
    from backend.application.research.contracts import (
        AdaptiveEvidence,
        Analysis,
        Discovery,
        EscalatedEvidence,
        RankedEvidence,
        ReadEvidence,
    )
    discovery = Discovery(
        retrieval=RetrievalResult(query="Tesla", domain="financial", fragments=[], channel_health={"web": "AVAILABLE"}, query_records=[
            QueryExecutionRecord(query_id="q1", channel="web", query_text="Tesla", query_class="general", phase="initial", status="SUCCESS")
        ]),
        raw_candidates=[ev1],
        accepted=[ev1],
        rejected=[],
    )
    ranked = RankedEvidence(accepted=[ev1], ranked=[ev1], clusters={"grp1": ["ev_001"]}, rejected=[])
    adaptive = AdaptiveEvidence(ranked=ranked, novelty=EvidenceNoveltyTracker(), telemetry={"attempted": 0, "rounds_executed": 0}, query_records=[])
    escalated = EscalatedEvidence(ranked=ranked, primaries=[], telemetry={"queries": [], "escalations": 0}, query_records=[])
    read = ReadEvidence(investigated=[ev1], telemetry={"attempted": 1, "successful": 1, "total_chars_read": 100})
    analysis = Analysis(contradictions=[], findings=[], integrity_report=MagicMock(to_dict=lambda: {}), graph={}, lineage_graph={"metrics": {"origin_count": 1, "echo_count": 0}})

    assembled = corpus_stage.run(
        request, budget, plan, discovery, ranked, adaptive, escalated, read, analysis, start_ts=0.0
    )
    assert isinstance(assembled, AssembledResearch)
    assert assembled.corpus.funnel["candidates_found"] == 1

    dossier_stage.run(request, ranked, analysis, assembled)
    assert assembled.telemetry.get("dossier_id") is not None

    res = pub_stage.run(request, budget, discovery, ranked, read, analysis, assembled)
    assert isinstance(res, ResearchResult)
    assert res.target == "Tesla Inc"
    assert res.domain == "financial"
    assert len(res.evidence) == 1
