"""Offline permission controls; synthetic reviews never grant real-site access."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.source_registry import SourceRegistry


NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)
SCOPES = ('discovery', 'body', 'excerpt', 'model_processing')
BODY = ('Acme reported quarterly revenue of $12 million, but comparative figures remain under review.\n\n'
        'Acme denied the rumored acquisition and confirmed that no agreement had been signed.')


def source(family='agency', host='agency.example', permission='UNVERIFIED'):
    return {
        'id': family, 'hosts': [host], 'permission_status': permission,
        'discovery': {'channel': 'web', 'operation': 'search'},
        'body': {'channel': 'web', 'operation': 'read'},
        'allowed_paths': {scope: ['/press/'] for scope in SCOPES},
    }


def review(scopes=SCOPES, **changes):
    result = {'decision': 'APPROVED', 'scopes': list(scopes),
              'reviewed_at': '2026-10-26', 'expires_at': '2027-01-01T00:00:00Z',
              'basis_url': 'https://agency.example/published-policy'}
    result.update(changes)
    return result


def registry(reviews=None, sources=None):
    return SourceRegistry(sources=sources or [source()], reviews=reviews or {}, clock=lambda: NOW)


def evidence(url='https://agency.example/press/results', evidence_id='ev_public'):
    return EvidenceItem(id=evidence_id, canonical_url=url, title='Acme quarterly results',
                        content=BODY, content_depth='PARTIAL_CONTENT')


def install(monkeypatch, value):
    # Explicit injection into a test-only registry, never the public review JSON.
    import backend.services.research.source_registry as module
    monkeypatch.setattr(module, 'source_registry', value)


@pytest.mark.parametrize('decision,status,basis', [
    (None, 'UNVERIFIED', 'NO_REVIEW'),
    ('PENDING', 'UNVERIFIED', 'REVIEW_NOT_APPROVED'),
    ('DENIED', 'PERMISSION_REQUIRED', 'EXPLICIT_PERMISSION_DENIED'),
    ('REJECTED', 'PERMISSION_REQUIRED', 'EXPLICIT_PERMISSION_DENIED'),
])
def test_unknown_review_is_distinct_from_explicit_denial(decision, status, basis):
    reviews = {} if decision is None else {'agency': review(decision=decision)}
    outcome = registry(reviews).assess('agency')
    assert outcome['status'] == status
    assert outcome['review_basis'] == basis
    assert outcome['eligible_for_bounded_probe'] is False
    assert outcome['runtime_availability'] == 'UNVERIFIED'
    assert outcome['network_calls'] == 0


def test_static_permission_requirement_is_not_reported_as_transport_failure():
    value = registry(sources=[source(permission='PERMISSION_REQUIRED')])
    outcome = value.assess('agency')
    assert outcome['status'] == 'PERMISSION_REQUIRED'
    assert outcome['runtime_availability'] == 'UNVERIFIED'
    assert outcome['review_basis'] == 'NO_REVIEW'


def test_approved_review_does_not_claim_network_or_body_success():
    outcome = registry({'agency': review()}).assess('agency')
    assert outcome['eligible_for_bounded_probe'] is True
    assert outcome['status'] == 'REVIEW_APPROVED'
    assert outcome['runtime_availability'] == 'UNVERIFIED'
    assert outcome['network_calls'] == 0


@pytest.mark.parametrize('scopes', [('discovery',), ('discovery', 'body'),
                                    ('discovery', 'body', 'excerpt')])
def test_non_model_scopes_never_imply_model_permission(scopes):
    value = registry({'agency': review(scopes)})
    assert not value.model_decision('https://agency.example/press/results')['eligible']
    assert value.assess('agency', 'model_processing')['review_basis'] == 'SCOPE_NOT_APPROVED'


def test_legacy_native_route_never_implicitly_grants_external_model_processing():
    value = registry(sources=[source(permission='EXISTING_ROUTE_POLICY')])
    assert value.body_decision('https://agency.example/press/results')['eligible']
    assert value.excerpt_decision('https://agency.example/press/results')['eligible']
    assert not value.model_decision('https://agency.example/press/results')['eligible']


@pytest.mark.parametrize('injected_gateway', [False, True])
def test_unapproved_passage_never_reaches_any_gateway(monkeypatch, injected_gateway):
    from backend.services.research.evidence_advisor import EvidenceAdvisor
    import backend.infrastructure.llm.gateway as gateway_module
    install(monkeypatch, registry({'agency': review(('discovery', 'body', 'excerpt'))}))
    generate = Mock(side_effect=AssertionError('Unapproved text must never reach a model'))
    load_gateway = Mock(side_effect=AssertionError('No model gateway should be loaded'))
    monkeypatch.setattr(gateway_module, 'get_llm_gateway', load_gateway)
    item = evidence()
    original = deepcopy(item.to_dict())
    outcome = EvidenceAdvisor(SimpleNamespace(generate_structured=generate) if injected_gateway else None).advise(
        ResearchRequest('Acme', domain='financial'), [item])
    assert outcome['status'] == 'SKIPPED_SOURCE_PERMISSION'
    assert outcome['source_permission_skips'] == 1
    assert item.to_dict() == original
    generate.assert_not_called()
    load_gateway.assert_not_called()


def test_mixed_batch_sends_only_explicitly_reviewed_source_text(monkeypatch):
    from backend.services.research.evidence_advisor import EvidenceAdvisor, PassageAdvice
    value = registry({'agency': review()}, sources=[source(), source('restricted', 'restricted.example')])
    install(monkeypatch, value)
    permitted = evidence()
    restricted = evidence('https://restricted.example/press/results', 'ev_restricted')
    restricted.content = ('Acme reported revenue of $99 million in a document whose paragraphs '
                          'must remain absent from any model prompt.')
    generate = Mock(return_value=PassageAdvice(selections=[]))
    outcome = EvidenceAdvisor(SimpleNamespace(generate_structured=generate)).advise(
        ResearchRequest('Acme', domain='financial'), [restricted, permitted])
    assert outcome['status'] == 'VALIDATED'
    prompt = generate.call_args.args[0]
    assert 'ev_public' in prompt and permitted.content.split('\n\n')[0] in prompt
    assert 'ev_restricted' not in prompt and '$99 million' not in prompt
    assert restricted.relevant_excerpt == ''


def test_approved_passage_keeps_exact_source_bytes_and_identity(monkeypatch):
    from backend.services.research.evidence_advisor import EvidenceAdvisor, PassageAdvice
    install(monkeypatch, registry({'agency': review()}))
    item = evidence()
    selected = BODY.split('\n\n')[0]
    generate = Mock(return_value=PassageAdvice(selections=[{
        'evidence_id': item.id, 'start': 0, 'end': len(selected)}]))
    outcome = EvidenceAdvisor(SimpleNamespace(generate_structured=generate)).advise(
        ResearchRequest('Acme', domain='financial'), [item])
    assert outcome['accepted'] == 1
    assert outcome['entailment_verified'] is False
    assert item.content == BODY and item.id == 'ev_public'
    assert item.relevant_excerpt == selected
    assert item.relevant_excerpt == item.content[item.excerpt_start:item.excerpt_end]
    assert item.primary_source is False


def test_imported_restricted_body_cannot_bypass_display_gate_without_control_flag(monkeypatch):
    from backend.services.research.passage_extractor import PassageExtractor
    install(monkeypatch, registry())
    item = evidence()
    item.relevant_excerpt = BODY
    item.metadata['evidence_passages'] = [{'text': BODY}]
    assert 'topic_source_controlled' not in item.metadata
    PassageExtractor().extract_passages([item], 'Acme', domain='financial')
    assert item.extraction_status == 'SOURCE_PERMISSION_REQUIRED'
    assert item.relevant_excerpt == ''
    assert item.excerpt_start == item.excerpt_end == -1
    assert 'evidence_passages' not in item.metadata
    assert item.content == BODY and item.id == 'ev_public'


@pytest.mark.parametrize('url', ['https://agency.example/press/results',
                                'https://outside.example/press/results'])
def test_article_rights_exception_overrides_otherwise_usable_excerpt(monkeypatch, url):
    from backend.services.research.passage_extractor import PassageExtractor
    install(monkeypatch, registry({'agency': review()}))
    item = evidence(url)
    item.metadata['page_metadata'] = {'rights_exception_observed': True}
    PassageExtractor().extract_passages([item], 'Acme', domain='financial')
    assert item.relevant_excerpt == ''
    assert item.extraction_status == 'SOURCE_PERMISSION_REQUIRED'
    assert item.metadata['post_read_qualification_reason'] == 'ARTICLE_RIGHTS_EXCEPTION_REVIEW_REQUIRED'
    assert item.content == BODY


@pytest.mark.parametrize('path', [
    '/press-archive/results', '/private/press/results', '/Press/results',
    '/press/../private/filing', '/press/%2e%2e/private/filing',
    '/press/%252e%252e/private/filing', '/press/%5c../private',
])
def test_static_path_scope_cannot_escape_via_prefix_collision_or_encoding(path):
    value = registry({'agency': review()})
    url = 'https://agency.example' + path
    assert not value.body_decision(url)['eligible']
    assert not value.excerpt_decision(url)['eligible']
    assert not value.model_decision(url)['eligible']


@pytest.mark.parametrize('path', ['/press/results', '/press/releases/agency-statement',
                                '/press/results?next=/private/filing'])
def test_reviewed_path_scope_accepts_only_observed_canonical_location(path):
    value = registry({'agency': review()})
    url = 'https://agency.example' + path
    assert value.body_decision(url)['eligible']
    assert value.excerpt_decision(url)['eligible']
    assert value.model_decision(url)['eligible']


def test_external_review_cannot_expand_static_path_scope():
    value = registry({'agency': review()})
    assert value.assess('agency', 'body')['eligible_for_bounded_probe']
    assert not value.body_decision('https://agency.example/court-filings/private')['eligible']
    assert not value.excerpt_decision('https://agency.example/court-filings/private')['eligible']
    assert not value.model_decision('https://agency.example/court-filings/private')['eligible']


@pytest.fixture
def versioned_registry(monkeypatch):
    """Read actual reviewed host/path data without making an access probe."""
    monkeypatch.delenv('AEGIS_SOURCE_REVIEWS_FILE', raising=False)
    monkeypatch.delenv('AEGIS_SOURCE_ALLOWED_FAMILIES', raising=False)
    return SourceRegistry(clock=lambda: NOW)


@pytest.mark.parametrize('url,family', [
    ('https://www.justice.gov/opa/pr/observed-agency-release', 'doj'),
    ('https://www.ftc.gov/news-events/news/press-releases/2026/10/observed-agency-release', 'ftc'),
])
def test_versioned_agency_press_scope_permits_text_without_claiming_live_availability(versioned_registry, url, family):
    assert versioned_registry.match_url(url)['id'] == family
    assert versioned_registry.body_decision(url)['eligible']
    assert versioned_registry.excerpt_decision(url)['eligible']
    assert versioned_registry.model_decision(url)['eligible']
    assert versioned_registry.assess(family)['runtime_availability'] == 'UNVERIFIED'


@pytest.mark.parametrize('url', [
    'https://www.justice.gov/foia/observed-document',
    'https://www.justice.gov/court-filings/observed-document',
    'https://www.justice.gov/opa/pr/%252e%252e/%252e%252e/court-filings/document',
    'https://media.justice.gov/opa/pr/observed-agency-release',
    'https://www.ftc.gov/policy/public-comments/observed-comment',
    'https://www.ftc.gov/legal-library/browse/cases-proceedings/observed-filing',
    'https://www.ftc.gov/news-events/news/press-releases/%2e%2e/public-comments/document',
    'https://media.ftc.gov/news-events/news/press-releases/observed-release',
])
def test_versioned_agency_grants_exclude_unreviewed_paths_and_subdomains(versioned_registry, url):
    assert not versioned_registry.body_decision(url)['eligible']
    assert not versioned_registry.excerpt_decision(url)['eligible']
    assert not versioned_registry.model_decision(url)['eligible']


@pytest.mark.parametrize('url', [
    'https://www.justice.gov/opa/pr/observed-agency-release',
    'https://www.ftc.gov/news-events/news/press-releases/2026/10/observed-agency-release',
])
def test_agency_rights_exception_never_inherits_press_grant(versioned_registry, url):
    captured_notice = {'rights_exception_observed': True}
    assert not versioned_registry.excerpt_decision(url, captured_notice)['eligible']
    assert not versioned_registry.model_decision(url, captured_notice)['eligible']


def test_cpsc_versioned_grant_is_api_scoped_not_agency_wide_html(versioned_registry):
    api_url = 'https://www.saferproducts.gov/RestWebServices/Recall?format=json&Title=synthetic'
    assert versioned_registry.body_decision(api_url)['eligible']
    assert versioned_registry.excerpt_decision(api_url)['eligible']
    assert versioned_registry.model_decision(api_url)['eligible']
    for html_url in ('https://www.cpsc.gov/Recalls/2026/observed-recall',
                     'https://www.cpsc.gov/Newsroom/observed-release',
                     'https://www.saferproducts.gov/other-api/Recall'):
        assert not versioned_registry.body_decision(html_url)['eligible']
        assert not versioned_registry.excerpt_decision(html_url)['eligible']
        assert not versioned_registry.model_decision(html_url)['eligible']


def test_explicit_denial_overrides_native_legacy_body_and_excerpt_defaults():
    value = registry({'agency': review(decision='DENIED')},
                     sources=[source(permission='EXISTING_ROUTE_POLICY')])
    url = 'https://agency.example/press/results'
    assert value.assess('agency')['review_basis'] == 'EXPLICIT_PERMISSION_DENIED'
    assert not value.body_decision(url)['eligible']
    assert not value.excerpt_decision(url)['eligible']
    assert not value.model_decision(url)['eligible']


@pytest.mark.parametrize('body_path', ['/press/observed-incident',
                                       '/RestWebServices/Recall?format=json&Title=synthetic'])
@pytest.mark.parametrize('robots_status,allowed', [(200, True), (404, True), (403, False)])
def test_scoped_robots_lease_is_exact_temporary_cached_and_non_redirecting(
        monkeypatch, body_path, robots_status, allowed):
    from backend.services.research.source_registry import (
        SourcePermissionError, enforce_scoped_body_access, source_body_scope)

    # Synthetic scopes intentionally exclude /robots.txt as acquired content.
    row = source()
    row['allowed_paths'] = {scope: ['/press/', '/RestWebServices/Recall'] for scope in SCOPES}
    monkeypatch.setenv('AEGIS_SOURCE_ALLOWED_FAMILIES', 'agency')
    robots_url = 'https://agency.example/robots.txt'
    fetched = []

    def fetch_policy(url, **kwargs):
        fetched.append((url, kwargs))
        assert url == robots_url
        assert kwargs['max_redirects'] == 0 and kwargs['max_attempts'] == 1
        assert kwargs['timeout'] == 5.0 and kwargs['max_bytes'] == 128_000
        # Only this exact in-flight policy URL receives the temporary lease.
        enforce_scoped_body_access(url)
        for unrelated in ('https://agency.example/private/document',
                          'https://agency.example/robots.txt?redirect=/private/document',
                          'https://agency.example/robots.txt/another-document',
                          'https://unapproved.example/robots.txt'):
            with pytest.raises(SourcePermissionError):
                enforce_scoped_body_access(unrelated)
        return SimpleNamespace(status_code=robots_status, body=b'User-agent: *\nAllow: /')

    value = SourceRegistry(sources=[row], reviews={'agency': review()}, clock=lambda: NOW,
                           robots_fetcher=fetch_policy)
    body_url = 'https://agency.example' + body_path
    with source_body_scope(value):
        if allowed:
            enforce_scoped_body_access(body_url)
            enforce_scoped_body_access(body_url)
        else:
            with pytest.raises(SourcePermissionError):
                enforce_scoped_body_access(body_url)
            with pytest.raises(SourcePermissionError):
                enforce_scoped_body_access(body_url)
        # Completed policy checking never grants /robots.txt as article content.
        with pytest.raises(SourcePermissionError):
            enforce_scoped_body_access(robots_url)
    assert len(fetched) == 1
    assert not value.body_decision(robots_url)['eligible']
