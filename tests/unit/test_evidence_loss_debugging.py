"""Offline reproductions of observed query/reader waste, not live yield proof."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.infrastructure.acquisition.adapters.web import jina
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError, transport_failure_kind
from backend.services.agent_reach.native import executor as native
from backend.services.agent_reach.source_planner import SourcePlanningEngine
from backend.services.research.research_objectives import discovery_objective


DYSON = ('Investigate reported Dyson counterfeit products, phishing promotions and official consumer warnings. '
         'Identify actual documented incidents, relevant dates and source authority.')
MARY = ('Find attributable public statements by Mary Barra about General Motors and the automotive industry. '
        'Clearly distinguish historical statements from recent coverage and unrelated executive speculation.')
URL = 'https://example.com/article'


@pytest.mark.parametrize('claim,entity,domain,agent', [
    (DYSON, 'Dyson', 'brand', 'brandshield'), (MARY, 'Mary Barra', 'personal', 'personal_watch')])
def test_saved_failed_objectives_keep_task_but_remove_report_instructions(claim, entity, domain, agent):
    planner = SourcePlanningEngine()
    plan = planner.plan(claim, entity=entity, domain=domain, agent=agent, use_llm=False)
    assert plan.claim == claim
    queries = [action.query for action in plan.actions if action.operation == 'search']
    assert queries
    assert all('Clearly distinguish' not in query and 'Identify actual' not in query for query in queries)
    assert all(not query.startswith(('Find attributable', 'Investigate reported')) for query in queries)
    compact = discovery_objective(claim, entity)
    assert entity in compact
    assert ('counterfeit' if domain == 'brand' else 'public statements') in compact


@pytest.mark.parametrize('text', [
    'Research shows Dyson did not recall the product in 2025.',
    'Dyson did not recall the product in Q2 2026.',
    'Find whether Mary Barra said "Do not release the product". Preserve the exact quote.',
    'Investigate Dyson site:ftc.gov. Preserve the date.',
    'Research Dyson results. Preserve Q2 2025 figures rather than 2024 figures.',
    'Research Dyson incidents. Include reports since January.',
    'Investigate Dyson reports. Preserve the fact that it was not recalled.',
    'https://example.com/article',
])
def test_literal_claims_quotes_and_source_restrictions_are_unchanged(text):
    assert discovery_objective(text, 'Dyson' if 'Dyson' in text else 'Mary Barra') == text


def test_comparative_research_task_is_not_a_presentation_instruction():
    text = 'Research Dyson results. Compare actual Q2 2025 results with Q1 2025.'
    assert discovery_objective(text, 'Dyson') == text.removeprefix('Research ').rstrip('.')


@pytest.mark.parametrize('kind,status', [('TIMEOUT', None), ('HTTP_FAILURE', 503),
                                       ('ACCESS_DENIED', 403), ('RATE_LIMITED', 429)])
def test_real_native_empty_page_does_not_call_same_reader_twice(monkeypatch, kind, status):
    monkeypatch.setattr(native, 'is_safe_url', lambda _: (True, 'OFFLINE'))
    monkeypatch.setattr(jina, 'is_safe_url', lambda _: (True, 'OFFLINE'))
    empty = BoundedHTTPResponse(b'<html><body></body></html>', URL, 200, 'text/html', {}, 1, 1)
    failure = ProviderHTTPError('Private provider text must not be exported', endpoint='https://r.jina.ai/' + URL,
                                failure_kind=kind, status_code=status, network_observed=status is not None)
    fetch = Mock(side_effect=[empty, failure])
    monkeypatch.setattr(native, 'fetch_public_http', fetch)
    repeated = Mock(side_effect=AssertionError('Repeated reader'))
    monkeypatch.setattr(jina, 'read_article_via_jina', repeated)
    result = jina.execute_web_read(URL, executor=object.__new__(native.NativeExecutor),
                                  firecrawl_adapter=SimpleNamespace(is_configured=lambda: False))
    assert result['failure_kind'] == kind
    assert fetch.call_count == 2  # One original page, one reader; no sockets.
    repeated.assert_not_called()
    assert 'Private provider' not in str(result)
    assert result['provider_failures'][-1]['stage'] == 'JINA_READER'
    if status is not None:
        assert result['transport']['http_status'] == status


def test_short_empty_reader_result_is_not_repeated(monkeypatch):
    monkeypatch.setattr(native, 'is_safe_url', lambda _: (True, 'OFFLINE'))
    monkeypatch.setattr(jina, 'is_safe_url', lambda _: (True, 'OFFLINE'))
    fetch = Mock(side_effect=[
        BoundedHTTPResponse(b'<html><body></body></html>', URL, 200, 'text/html', {}, 1, 1),
        BoundedHTTPResponse(b'Short shell', 'https://r.jina.ai/' + URL, 200, 'text/plain', {}, 1, 1)])
    monkeypatch.setattr(native, 'fetch_public_http', fetch)
    repeated = Mock(side_effect=AssertionError('Repeated reader'))
    monkeypatch.setattr(jina, 'read_article_via_jina', repeated)
    result = jina.execute_web_read(URL, executor=object.__new__(native.NativeExecutor),
                                  firecrawl_adapter=SimpleNamespace(is_configured=lambda: False))
    assert result['status'] == 'error'
    assert fetch.call_count == 2
    repeated.assert_not_called()


@pytest.mark.parametrize('message,expected', [
    ('Public HTTP connection deadline expired', 'TIMEOUT'),
    ('Public HTTP response deadline expired', 'TIMEOUT'),
    ('Native HTTP request budget exhausted', 'BUDGET_EXHAUSTED'),
    ('Acquisition chain deadline exhausted', 'BUDGET_EXHAUSTED'),
])
def test_operation_timeouts_are_distinct_from_investigation_budget_exhaustion(message, expected):
    assert transport_failure_kind(TimeoutError(message)) == expected
