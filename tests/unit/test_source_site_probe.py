"""Offline probe-report semantics; never a live website test."""
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from backend.services.research.source_registry import SourceRegistry
from scripts.audits.probe_source_families import (
    inventory, article_capture, build_parser, select_families, probe, probe_cpsc,
)


def test_inventory_distinguishes_configuration_gates_from_unmeasured_network():
    rows=inventory(SourceRegistry(reviews={}))
    assert len(rows)==62
    assert any(r['probe_status']=='NOT_PROBED_PERMISSION_REQUIRED' for r in rows)
    assert any(r['probe_status']=='NOT_PROBED_UNVERIFIED' for r in rows)
    assert not any(r['probe_status']=='PENDING_EXPLICIT_SELECTION' for r in rows)
    assert sum(r['probe_status']=='EXISTING_ROUTE_NOT_RETESTED' for r in rows)==8
    assert all(r['network_access']=='NOT_TESTED' and not r['reads'] for r in rows)
    assert all(r['published_evidence_words']==0 and r['findings_generated']==0 for r in rows)


def test_homepage_and_policy_prose_cannot_count_as_article_yield():
    page={'body_quality':{'body_kind':'ARTICLE_BODY'},'content_scope':'article'}
    assert not article_capture('https://publisher.example/',page)
    assert not article_capture('https://publisher.example/help/reuse-policy',page)
    assert not article_capture('https://publisher.example/article',dict(page,content_scope='FEED_INDEX'))
    assert article_capture('https://publisher.example/2026/10/26/observed-article',page)


def reviewed_registry():
    source = deepcopy(SourceRegistry().by_id['cpsc'])
    source.update(permission_status='PUBLIC_LICENSE_REVIEWED', hosts=['cpsc.gov', 'saferproducts.gov'],
                  allowed_paths={'body': ['/RestWebServices/Recall'], 'excerpt': ['/RestWebServices/Recall']})
    review = {'decision': 'APPROVED', 'scopes': ['discovery', 'body', 'excerpt'],
              'reviewed_at': '2026-10-26', 'expires_at': '2099-01-01T00:00:00Z',
              'basis_url': 'https://policy.example.test/public-records'}
    return SourceRegistry(sources=[source], reviews={'cpsc': review})


def test_cli_requires_explicit_source_selection_and_bounded_time():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['--allow-live', '--output-dir', 'unused'])
    for seconds in ['0', '91', '-2', 'nan', 'inf']:
        with pytest.raises(SystemExit):
            parser.parse_args(['--allow-live', '--output-dir', 'unused', '--family', 'cpsc',
                               '--seconds-per-family', seconds])
    args = parser.parse_args(['--allow-live', '--output-dir', 'unused', '--family', 'cpsc',
                              '--seconds-per-family', '90'])
    assert args.family == ['cpsc'] and args.seconds_per_family == 90


def test_selection_cannot_grant_unreviewed_sources_or_implicitly_sweep():
    registry = reviewed_registry()
    assert select_families(registry, ['cpsc']) == ['cpsc']
    assert inventory(registry)[0]['probe_status'] == 'PENDING_EXPLICIT_SELECTION'
    for families in [[], ['cpsc', 'cpsc'], ['unknown'], ['a', 'b', 'c', 'd', 'e']]:
        with pytest.raises(ValueError):
            select_families(registry, families)
    registry._reviews = {}
    with pytest.raises(ValueError):
        select_families(registry, ['cpsc'])


def test_cpsc_probe_counts_observed_structured_records_not_article_bodies(monkeypatch):
    from backend.infrastructure.acquisition.adapters.consumer import cpsc_recalls as cpsc
    registry = reviewed_registry()
    record = {'RecallID': 12345, 'Title': 'Synthetic battery recall',
              'URL': 'https://www.cpsc.gov/Recalls/2026/Synthetic-Battery-Recall',
              'RecallDate': '2026-10-01T00:00:00', 'Description': 'Synthetic battery safety fixture.',
              'Hazards': [{'Name': 'Synthetic fire hazard.'}], 'Remedies': [{'Name': 'Synthetic refund.'}]}
    calls = []
    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=200, endpoint=url, redirect_chain=[],
                               content_type='application/json', body=json.dumps([record]).encode())
    monkeypatch.setattr(cpsc, 'safe_fetch', fetch)
    row = inventory(registry)[0]
    probe(row, registry, service=None, seconds=90)
    from urllib.parse import parse_qs, urlsplit
    assert len(calls) == 1
    assert parse_qs(urlsplit(calls[0][0]).query) == {'format': ['json'], 'RecallTitle': ['battery']}
    assert row['structured_records'] == 1 and row['structured_words'] > 0
    assert row['body_words'] == row['article_body_words'] == row['published_evidence_words'] == 0
    assert row['probe_status'] == 'STRUCTURED_RECORDS_OBSERVED'
    assert row['records'][0]['RecallID'] == 12345
    assert row['records'][0]['field_provenance']['recall_id'] == '/0/RecallID'
    assert row['records'][0]['excerpt_permission']
    assert len(row['records'][0]['record_sha256']) == 64
    assert 'original_record' not in row['records'][0] and 'content' not in row['records'][0]


def test_cpsc_probe_does_not_fetch_or_fallback_when_api_scope_is_missing(monkeypatch):
    from backend.infrastructure.acquisition.adapters.consumer import cpsc_recalls as cpsc
    registry = reviewed_registry()
    registry.by_id['cpsc']['allowed_paths']['body'] = ['/different-path']
    monkeypatch.setattr(cpsc, 'safe_fetch', lambda *a, **k: pytest.fail('No authorized API transport'))
    row = inventory(registry)[0]
    probe_cpsc(row, registry, seconds=5)
    assert row['probe_error'] == 'API_OUTSIDE_REVIEWED_BODY_SCOPE'
    assert row['structured_records'] == row['article_body_words'] == row['body_words'] == 0
    assert row['native_http_admissions'] == 0


@pytest.mark.parametrize('seconds', [0, 91, float('nan')])
def test_programmatic_probe_ceiling_is_bounded(seconds):
    with pytest.raises(ValueError):
        probe({}, None, None, seconds=seconds)
