"""Development controls for role-aware selection and advisory-only AI."""
from types import SimpleNamespace

import pytest

from backend.services.research.research_models import EvidenceItem, ResearchRequest


@pytest.fixture(autouse=True)
def synthetic_advisory_source_permission(monkeypatch):
    """Explicit offline-double grant; no real publisher model rights implied."""
    from datetime import datetime, timezone
    import backend.services.research.source_registry as module
    synthetic = {
        'id': 'synthetic_advisory_example', 'hosts': ['example.org'],
        'permission_status': 'UNVERIFIED', 'agents': [], 'topics': ['synthetic'],
        'discovery': {'channel': 'web', 'operation': 'search'},
        'body': {'channel': 'web', 'operation': 'read'},
    }
    grant = {
        'decision': 'APPROVED', 'reviewed_at': '2026-10-26',
        'expires_at': '2027-01-01T00:00:00Z',
        'basis_url': 'https://example.org/synthetic-offline-test-policy',
        'scopes': ['discovery', 'body', 'excerpt', 'model_processing'],
    }
    value = module.SourceRegistry(sources=[*module.definitions(), synthetic],
        reviews={synthetic['id']: grant}, clock=lambda: datetime(2026, 10, 26, tzinfo=timezone.utc))
    monkeypatch.setattr(module, 'source_registry', value)


def evidence(text, **kwargs):
    return EvidenceItem(id="ev_sample", content=text, content_depth="PARTIAL_CONTENT",
                        canonical_url="https://example.org/article", **kwargs)


def test_author_bio_is_not_an_ev_event_and_raw_is_preserved():
    from backend.services.research.passage_extractor import PassageExtractor
    bio = "Jameson has been driving electric cars since 2009, and covering EVs, sustainability and policy for Electrek since 2016."
    item = evidence(bio)
    PassageExtractor().extract_passages([item], "electric vehicles", domain="trending")
    assert item.content == bio and not item.relevant_excerpt
    assert item.extraction_status == "NO_RELEVANT_PASSAGE"


def test_article_passage_survives_bio_filter_with_exact_offsets():
    from backend.services.research.passage_extractor import PassageExtractor
    body = ("This electric vehicles charging project has 120 chargers, but 48 additional chargers are not yet operational.\n\n"
            "Jameson has been driving electric cars since 2009, and covering EVs and policy for Electrek since 2016.")
    item = evidence(body)
    PassageExtractor().extract_passages([item], "electric vehicles", domain="trending")
    assert "not yet operational" in item.relevant_excerpt
    assert item.relevant_excerpt == body[item.excerpt_start:item.excerpt_end]
    assert item.content == body


@pytest.mark.parametrize("domain,text", [
    ("brand", "Apple has announced a new product with faster chips and advanced graphics for professional users."),
    ("personal", "Sam Altman has worked in technology for several years and is a company executive."),
    ("financial", "Apple has introduced new colors for its popular consumer devices and accessories."),
])
def test_generic_company_text_is_not_specialist_evidence(domain, text):
    from backend.services.research.passage_extractor import PassageExtractor
    item = evidence(text)
    PassageExtractor().extract_passages([item], "Sam Altman" if domain == "personal" else "Apple", domain=domain)
    assert not item.relevant_excerpt


@pytest.mark.parametrize("domain,text", [
    ("brand", "Apple customers reported a fake support account that requested payment through an unauthorized link."),
    ("personal", "Sam Altman denied appearing in the fabricated deepfake video promoting an investment scheme."),
    ("financial", "Apple reported quarterly revenue of $90 billion, but the prior period figure was not comparable."),
])
def test_relevant_specialist_passages_remain_observations(domain, text):
    from backend.services.research.passage_extractor import PassageExtractor
    item = evidence(text)
    PassageExtractor().extract_passages([item], "Sam Altman" if domain == "personal" else "Apple", domain=domain)
    assert item.relevant_excerpt == text


def test_nested_issuer_index_is_not_primary_statement():
    from backend.services.research.source_quality import SourceQualityEngine
    item = evidence("Results for the First Quarter ended June 30, 2026.\n\nFinancial statements\n\nPress release",
                    title="First quarter results", metadata={"page_metadata": {"observed_links": [
                        {"url": "https://www.infosys.com/results.pdf", "text": "Financial statements"},
                        {"url": "https://www.infosys.com/release.pdf", "text": "Press release"}]}})
    item.canonical_url = "https://www.infosys.com/investors/reports-filings/quarterly-results/2026/q1/ind-as.html"
    SourceQualityEngine().classify_and_score(item, "Infosys")
    assert item.official_source and not item.primary_source
    assert item.metadata["content_role"] == "DOCUMENT_INDEX"


def test_real_statement_not_demoted_just_because_it_links_pdfs():
    from backend.services.research.source_quality import SourceQualityEngine
    item = evidence("Infosys reported revenue of INR 40,000 crore for the quarter ended June 30, 2026. "
                    "Operating profit was INR 8,000 crore and diluted earnings per share was INR 20.")
    item.canonical_url = "https://www.infosys.com/results/q1.html"
    SourceQualityEngine().classify_and_score(item, "Infosys")
    assert item.primary_source


def test_advisor_preserves_ids_and_never_rewrites_or_promotes_evidence():
    from backend.services.research.evidence_advisor import EvidenceAdvisor, PassageAdvice
    item = evidence("Acme reported quarterly revenue of $10 million, but did not confirm the rumored acquisition.")
    gateway = SimpleNamespace(generate_structured=lambda *a, **k: PassageAdvice(
        selections=[{"evidence_id": item.id, "start": 0, "end": len(item.content)}]))
    original = item.to_dict()
    outcome = EvidenceAdvisor(gateway).advise(ResearchRequest("Acme", domain="financial"), [item], timeout=1)
    assert outcome["status"] == "VALIDATED"
    assert item.id == original["id"] and item.content == original["content"]
    assert item.relevant_excerpt == item.content
    assert not item.primary_source
    assert outcome["entailment_verified"] is False


@pytest.mark.parametrize("selection", [
    {"evidence_id": "invented", "start": 0, "end": 80},
    {"evidence_id": "ev_sample", "start": -1, "end": 80},
    {"evidence_id": "ev_sample", "start": 0, "end": 9999},
])
def test_advisor_rejects_invalid_ids_and_offsets(selection):
    from backend.services.research.evidence_advisor import EvidenceAdvisor, PassageAdvice
    item = evidence("Acme reported quarterly revenue of $10 million and did not announce any acquisition.")
    gateway = SimpleNamespace(generate_structured=lambda *a, **k: PassageAdvice(selections=[selection]))
    outcome = EvidenceAdvisor(gateway).advise(ResearchRequest("Acme", domain="financial"), [item], timeout=1)
    assert not item.relevant_excerpt and outcome["accepted"] == 0


def test_advisor_cannot_select_a_bio_even_if_model_suggests_it():
    from backend.services.research.evidence_advisor import EvidenceAdvisor, PassageAdvice
    body = "Jameson has been driving electric cars since 2009, and covering EVs and policy for Electrek since 2016."
    item = evidence(body)
    gateway = SimpleNamespace(generate_structured=lambda *a, **k: PassageAdvice(selections=[
        {"evidence_id": item.id, "start": 0, "end": len(body)}]))
    outcome = EvidenceAdvisor(gateway).advise(ResearchRequest("electric vehicles", domain="trending"), [item], timeout=1)
    assert outcome["accepted"] == 0 and not item.relevant_excerpt


def test_advisor_failure_and_no_budget_do_not_block_or_fabricate():
    from backend.services.research.evidence_advisor import EvidenceAdvisor
    def fail(*args, **kwargs):
        raise RuntimeError("provider-secret-error")
    advisor = EvidenceAdvisor(SimpleNamespace(generate_structured=fail))
    item = evidence("Acme reported quarterly revenue of $10 million and did not announce any acquisition.")
    assert advisor.advise(ResearchRequest("Acme"), [item], timeout=0)["status"] == "SKIPPED_BUDGET"
    outcome = advisor.advise(ResearchRequest("Acme"), [item], timeout=1)
    assert outcome["status"] == "UNAVAILABLE" and "secret" not in str(outcome)
    assert not item.relevant_excerpt


def test_provider_respects_advisory_timeout_attempt_and_token_limits(monkeypatch, tmp_path):
    from backend.core.settings import Settings
    from backend.infrastructure.llm.providers.gemini import GeminiProvider
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status_code=429)
    monkeypatch.setattr("requests.post", unavailable)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    provider = GeminiProvider(Settings(gemini_api_keys=["fixture-key"], gemini_models=["one", "two"], llm_max_retries=3))
    from backend.infrastructure.llm.advisory_policy import advisory_run, investigation_scope, MODEL
    with advisory_run(verified_models=[MODEL], database=tmp_path / "policy.db"), investigation_scope(), pytest.raises(RuntimeError):
        provider.generate("advice", model=MODEL, purpose="passage_suggestion", timeout=0.5, total_timeout=0.5, max_attempts=1, max_output_tokens=160)
    assert len(calls) == 1
    assert 0 < calls[0]["timeout"] <= 0.5
    assert calls[0]["json"]["generationConfig"]["maxOutputTokens"] == 160


def test_advisor_does_not_send_sensitive_content(monkeypatch):
    from backend.services.research.evidence_advisor import EvidenceAdvisor
    def forbidden(*args, **kwargs):
        raise AssertionError("must not call provider")
    advisor = EvidenceAdvisor(SimpleNamespace(generate_structured=forbidden))
    item = evidence("Acme reported a quarterly loss. Contact private.person@example.org for personal account details.")
    assert advisor.advise(ResearchRequest("Acme"), [item])["status"] == "SKIPPED_NOT_NEEDED"
    assert advisor.advise(ResearchRequest("Public Figure", domain="personal"), [item])["status"] == "SKIPPED_PRIVACY"


def test_brand_searches_precede_generic_company_queries():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    plan = SourcePlanningEngine().plan("Apple", entity="Apple", domain="brand", agent="brandshield", use_llm=False)
    queries = plan.to_channel_queries()["web"]
    assert queries[0]["query_class"] in {"brand_risk", "brand_abuse_reporting"}
    assert not any(a.source_category == "publisher_announcements" for a in plan.actions)


def test_encyclopedic_brand_text_does_not_become_complaint():
    from backend.agents.brandshield.assessment import heuristic_threat_synthesis
    result = heuristic_threat_synthesis({"brand": "Adidas"}, [{"evidence_id": "ev_company", "platform": "web",
        "url": "https://en.wikipedia.org/wiki/Adidas", "title": "Adidas", "content":
        "Adidas has a history of sponsoring athletes and sporting events. The company was founded in Germany.",
        "content_depth": "PARTIAL_CONTENT"}])
    assert not result["threats"] and not result["claims"]


def test_late_advice_cannot_mutate_a_timed_out_investigation():
    import threading
    from backend.services.research.evidence_advisor import EvidenceAdvisor, PassageAdvice
    release = threading.Event()
    started = threading.Event()
    item = evidence("Acme reported quarterly revenue of $10 million, but did not announce the proposed acquisition.")
    def stall(*args, **kwargs):
        started.set()
        release.wait(1)
        return PassageAdvice(selections=[{"evidence_id": item.id, "start": 0, "end": len(item.content)}])
    try:
        outcome = EvidenceAdvisor(SimpleNamespace(generate_structured=stall)).advise(ResearchRequest("Acme"), [item], timeout=.01)
        assert started.is_set() and outcome["status"] == "UNAVAILABLE"
        assert not item.relevant_excerpt
    finally:
        release.set()
    assert not item.relevant_excerpt


def test_ai_selection_survives_stage_and_public_report_contract(monkeypatch):
    # Explicit offline-double opt-in; ordinary requests must never call AI.
    monkeypatch.setenv("AEGIS_EVIDENCE_ADVISOR_ENABLED", "true")
    from backend.services.research import evidence_advisor
    from backend.application.research.synthesis import PassageAnalysisStage
    from backend.application.research.contracts import RankedEvidence, ReadEvidence
    from backend.services.report_builder import ReportBuilder
    first = "Acme reported quarterly revenue of $10 million, but comparative figures need review."
    second = "Acme denied the proposed acquisition and confirmed that no agreement had been signed."
    item = evidence(first + "\n\n" + second)
    start = item.content.index(second)
    gateway = SimpleNamespace(generate_structured=lambda *a, **k: evidence_advisor.PassageAdvice(selections=[
        {"evidence_id": item.id, "start": start, "end": start + len(second)}]))
    advisor = evidence_advisor.EvidenceAdvisor(gateway)
    monkeypatch.setattr(evidence_advisor, "EvidenceAdvisor", lambda: advisor)
    read = PassageAnalysisStage().run(ResearchRequest("Acme", domain="financial"),
        RankedEvidence([item], [item], {}, []), ReadEvidence([item], {}), advisor_timeout=1)
    assert item.relevant_excerpt == second and item.content == first + "\n\n" + second
    report = ReportBuilder.from_scout_result(query="Acme", scout_data={
        "sources": [item.to_dict()], "deep_research_trace": read.telemetry}).to_dict()
    assert report["processing_notes"]["ai_passage_advice"]["accepted"] == 1
    assert report["processing_notes"]["ai_passage_advice"]["entailment_verified"] is False


def test_validated_ai_query_fits_existing_search_budget_and_cannot_add_reads():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine, LLMSuggestedPlan
    gateway = SimpleNamespace(generate_structured=lambda *a, **k: LLMSuggestedPlan(actions=[{
        "channel": "web", "operation": "search", "query": "Acme recall regulator notice", "rationale": "Inspect original recall notice"},
        {"channel": "web", "operation": "read", "query": "http://127.0.0.1/private", "rationale": "Untrusted URL suggestion"}]))
    plan = SourcePlanningEngine(llm_gateway=gateway).plan("Acme", entity="Acme", use_llm=True, discovery_failed=True)
    queries = plan.to_channel_queries()["web"]
    assert len(queries) <= plan.budget.max_queries_per_channel
    assert any(q["query_text"] == "Acme recall regulator notice" for q in queries)
    assert any(x["reason"] == "AI_SEARCH_SUGGESTIONS_ONLY" for x in plan.excluded)


def test_cyclone_product_name_is_not_a_counterfeit_clone():
    from backend.agents.brandshield.assessment import heuristic_threat_synthesis
    result = heuristic_threat_synthesis({"brand": "Nike"}, [{"evidence_id": "ev_catalog", "platform": "web",
        "url": "https://unverified-retailer.example/shoes", "title": "Nike shoes", "content":
        "Nike Air Cyclone 360 cushioning is available in several sizes for running and walking.",
        "content_depth": "PARTIAL_CONTENT"}])
    assert not result["threats"] and not result["counterfeits"]


def test_native_brand_extractor_does_not_confuse_cyclone_and_clone():
    from backend.agents.brandshield.extraction import brandshield_extractor
    from backend.services.agent_reach.channels import EvidenceFragment
    result = brandshield_extractor.extract([EvidenceFragment(platform="web", title="Nike Cyclone shoes",
        content="Nike Air Cyclone 360 is available in multiple sizes.", evidence_id="ev_product")], "Nike")
    assert not result.counterfeits and not result.threats
