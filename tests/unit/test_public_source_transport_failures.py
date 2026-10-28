"""Synthetic offline route-failure controls; no new publisher observations."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.infrastructure.acquisition.adapters.web import jina
from backend.infrastructure.acquisition.network.http import ProviderHTTPError
from backend.services.research.deep_reader import DeepReader
from backend.services.research.research_models import EvidenceItem
from backend.services.research.source_registry import SourcePermissionError


URL = 'https://agency.example.test/article'


@pytest.fixture(autouse=True)
def offline_transport(monkeypatch):
    monkeypatch.setattr(jina, 'is_safe_url', lambda _: (True, 'SYNTHETIC_OFFLINE_CONTROL'))
    monkeypatch.setattr(jina, 'fetch_public_http', Mock(side_effect=AssertionError('No network in controls')))


def unavailable_firecrawl():
    return SimpleNamespace(is_configured=lambda: False)


def executor_error(kind, status=None):
    return SimpleNamespace(execute_web_read=Mock(side_effect=ProviderHTTPError(
        'Exception includes private header token that must never enter observations', endpoint=URL,
        failure_kind=kind, status_code=status, network_observed=status is not None)))


@pytest.mark.parametrize('kind,status', [('TIMEOUT', None), ('DNS_TIMEOUT', None), ('CONNECTION_FAILURE', None),
                                        ('HTTP_FAILURE', 404)])
def test_first_native_cause_survives_later_nonterminal_fallback_failure(monkeypatch, kind, status):
    monkeypatch.setattr(jina, 'read_article_via_jina', lambda *a, **k: {
        'status': 'failed', 'failure_kind': 'CONNECTION_FAILURE', 'error': 'sensitive debug text',
        'transport': {'http_status': None, 'headers': {'Authorization': 'do-not-export'}}})
    result = jina.execute_web_read(URL, executor=executor_error(kind, status), firecrawl_adapter=unavailable_firecrawl())
    assert result['failure_kind'] == kind
    assert result['transport']['http_status'] == status
    assert [r['stage'] for r in result['provider_failures']] == ['NATIVE_READER', 'JINA_READER']
    assert result['provider_failures'][0]['failure_kind'] == kind
    assert 'sensitive' not in str(result) and 'Authorization' not in str(result) and 'private header' not in str(result)


def test_terminal_native_access_denial_never_calls_another_reader(monkeypatch):
    fallback = Mock(side_effect=AssertionError('Denial cannot trigger a fallback'))
    monkeypatch.setattr(jina, 'read_article_via_jina', fallback)
    result = jina.execute_web_read(URL, executor=executor_error('ACCESS_DENIED', 403), firecrawl_adapter=unavailable_firecrawl())
    assert result['failure_kind'] == 'ACCESS_DENIED' and result['transport']['http_status'] == 403
    assert result['provider_failures'][0]['network_observed'] is True
    fallback.assert_not_called()


def test_policy_denial_on_native_reader_never_falls_through(monkeypatch):
    denial = SourcePermissionError({'status': 'PERMISSION_REQUIRED'})
    monkeypatch.setattr(jina, 'read_article_via_jina', Mock(side_effect=AssertionError('No rights bypass')))
    with pytest.raises(SourcePermissionError):
        jina.execute_web_read(URL, executor=SimpleNamespace(execute_web_read=Mock(side_effect=denial)),
                              firecrawl_adapter=unavailable_firecrawl())


def test_mirror_policy_denial_is_rethrown_with_earlier_typed_cause(monkeypatch):
    denial = SourcePermissionError({'status': 'UNVERIFIED'})
    monkeypatch.setattr(jina, 'fetch_public_http', Mock(side_effect=denial))
    with pytest.raises(SourcePermissionError) as caught:
        jina.execute_web_read(URL, executor=executor_error('TIMEOUT'), firecrawl_adapter=unavailable_firecrawl())
    failures = caught.value.provider_failures
    assert [r['failure_kind'] for r in failures] == ['TIMEOUT', 'UNVERIFIED']
    assert failures[1]['network_observed'] is False


def test_firecrawl_policy_denial_cannot_trigger_mirror(monkeypatch):
    denial = SourcePermissionError({'status': 'PERMISSION_REQUIRED'})
    firecrawl = SimpleNamespace(is_configured=lambda: True, scrape_article=Mock(side_effect=denial))
    monkeypatch.setattr(jina, 'read_article_via_jina', Mock(side_effect=AssertionError('No rights bypass')))
    with pytest.raises(SourcePermissionError):
        jina.execute_web_read(URL, executor=executor_error('TIMEOUT'), firecrawl_adapter=firecrawl)


def test_successful_fallback_remains_success_with_native_failure_context(monkeypatch):
    text = 'Synthetic captured article text. ' * 8
    monkeypatch.setattr(jina, 'read_article_via_jina', lambda *a, **k: {'status': 'success', 'content': text})
    result = jina.execute_web_read(URL, executor=executor_error('TIMEOUT'), firecrawl_adapter=unavailable_firecrawl())
    assert result['status'] == 'success' and result['content'] == text
    assert result['provider_failures'][0]['failure_kind'] == 'TIMEOUT'


def test_failure_observation_only_copies_bounded_whitelisted_fields():
    row = jina._failure_observation('NATIVE_READER', {'failure_kind': 'unknown-secret-kind',
        'error': 'secret', 'transport': {'http_status': '403', 'network_observed_this_attempt': 'yes',
                                        'Authorization': 'secret'}})
    assert row == {'stage': 'NATIVE_READER', 'failure_kind': 'PROVIDER_FAILURE',
                   'http_status': None, 'network_observed': None}
    assert len(jina._with_failures({}, [row] * 10)['provider_failures']) == 3


def test_deep_reader_preserves_direct_typed_exception_http_observation():
    error = ProviderHTTPError('Sensitive response text', endpoint=URL, status_code=503,
                              network_observed=True)
    item = EvidenceItem(id='synthetic-observation', canonical_url=URL, title='Synthetic article',
                        channel='web', metadata={'candidate_score': .8})
    captures, trace = DeepReader().deep_read([item], max_reads=1, timeout_per_read=1,
                                            service=SimpleNamespace(read=Mock(side_effect=error)))
    assert not captures
    attempt = trace['acquisition_attempts'][0]
    assert attempt['failure_kind'] == 'HTTP_FAILURE' and attempt['http_status'] == 503
    assert attempt['network_observed'] is True and 'Sensitive' not in str(trace)


def test_deep_reader_keeps_failed_route_history_when_later_gate_denies():
    error = SourcePermissionError({'status': 'UNVERIFIED'})
    error.provider_failures = [{'stage': 'NATIVE_READER', 'failure_kind': 'TIMEOUT',
                               'http_status': None, 'network_observed': False}]
    item = EvidenceItem(id='synthetic-policy', canonical_url=URL, title='Synthetic article',
                        channel='web', metadata={'candidate_score': .8})
    _, trace = DeepReader().deep_read([item], max_reads=1, timeout_per_read=1,
                                     service=SimpleNamespace(read=Mock(side_effect=error)))
    attempt = trace['acquisition_attempts'][0]
    assert attempt['failure_kind'] == 'UNVERIFIED'
    assert attempt['provider_failures'][0]['failure_kind'] == 'TIMEOUT'


@pytest.mark.parametrize('kind', ['PERMISSION_REQUIRED', 'UNVERIFIED', 'ROBOTS_UNVERIFIED',
                                  'ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED'])
def test_returned_rights_denial_cannot_trigger_alternate_route(monkeypatch, kind):
    monkeypatch.setattr(jina, 'read_article_via_jina', Mock(side_effect=AssertionError('No rights bypass')))
    executor = SimpleNamespace(execute_web_read=lambda *a, **k: {'status': 'failed', 'failure_kind': kind})
    result = jina.execute_web_read(URL, executor=executor, firecrawl_adapter=unavailable_firecrawl())
    assert result['failure_kind'] == kind


def test_budget_expiration_in_fallback_keeps_first_native_cause_and_stops(monkeypatch):
    def expire(*a, **k):
        raise TimeoutError('Acquisition deadline exhausted')
    monkeypatch.setattr(jina, 'read_article_via_jina', expire)
    result = jina.execute_web_read(URL, executor=executor_error('TIMEOUT'), firecrawl_adapter=unavailable_firecrawl())
    assert result['failure_kind'] == 'TIMEOUT'
    assert [r['failure_kind'] for r in result['provider_failures']] == ['TIMEOUT', 'BUDGET_EXHAUSTED']
