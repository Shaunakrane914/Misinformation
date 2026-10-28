"""Offline pipeline-exception reporting controls; no provider or model calls."""
import logging

from backend.agents.brandshield.agent import BrandShieldAgent
from backend.agents.brandshield.scanning import search_brand_evidence
from backend.services.report_builder import ReportBuilder


def fail_pipeline(monkeypatch):
    from backend.services import research

    def fail(_request):
        raise TypeError('private-api-key-must-not-appear')

    monkeypatch.setattr(research.research_engine, 'investigate', fail)


def test_scanning_preserves_failure_trace_and_tuple_contract(monkeypatch, caplog):
    fail_pipeline(monkeypatch)
    with caplog.at_level(logging.WARNING):
        result = search_brand_evidence({'brand': 'Synthetic Tools', 'resolved_entity': 'Synthetic Tools'})
    evidence, health, plan, syndicated, research_result = result
    assert evidence == [] and health == {} and syndicated == 0 and research_result is None
    acquisition = plan['trace']['acquisition']
    assert acquisition['status'] == 'ACQUISITION_FAILED'
    assert acquisition['reason'] == 'RESEARCH_PIPELINE_ERROR'
    assert acquisition['error_type'] == 'TypeError' and acquisition['acquired_sources'] == 0
    assert 'private-api-key' not in str(result) + caplog.text
    assert 'TypeError' in caplog.text


def test_native_and_shared_brand_report_distinguish_pipeline_failure_from_insufficiency(monkeypatch):
    fail_pipeline(monkeypatch)
    agent = BrandShieldAgent()
    monkeypatch.setattr(agent, '_synthesize_brand_threats', lambda *_args: {
        'threats': [], 'claims': [], 'assessment_status': 'INSUFFICIENT_EVIDENCE'})
    native = agent.scan(brand_name='Synthetic Tools')
    assert native['status'] == native['investigation_status'] == 'ACQUISITION_FAILED'
    assert native['assessment_status'] == 'ACQUISITION_FAILED'
    assert native['evidence'] == native['findings'] == native['findings_structured'] == []
    report = ReportBuilder.from_brandshield_result(query='Synthetic Tools', brand_data=native)
    assert report.investigation_status == 'ACQUISITION_FAILED'
    assert report.processing_notes['acquisition']['reason'] == 'RESEARCH_PIPELINE_ERROR'
    assert 'research pipeline failed' in report.summary
    assert report.findings == [] and report.agent_intelligence == {}
    assert 'private-api-key' not in str(native) + str(report.to_dict())
