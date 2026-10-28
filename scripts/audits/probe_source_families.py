"""Inventory every source family and individually probe reviewed text sources.

Direct website diagnostics, NOT autonomous discovery or claim verification.
No model calls, paid readers, access bypasses, fixture responses or audit retry.
Each explicitly selected family has at most 90 seconds, six native admissions
and two reads. CPSC API records are counted separately from article bodies.
"""
import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def inventory(registry):
    rows = []
    for source in registry.sources:
        assessment = registry.assess(source['id'], 'body')
        status = ('EXISTING_ROUTE_NOT_RETESTED' if source['permission_status'] == 'EXISTING_ROUTE_POLICY' else
                  'PENDING_EXPLICIT_SELECTION' if assessment['eligible_for_bounded_probe'] else
                  'NOT_PROBED_PERMISSION_REQUIRED' if assessment['status'] == 'PERMISSION_REQUIRED' else
                  'NOT_PROBED_UNVERIFIED')
        rows.append({'family': source['id'], 'name': source['name'], 'hosts': source['hosts'],
            'configured_permission': source['permission_status'], 'body_permission_status': assessment['status'],
            'review_basis': assessment['review_basis'], 'probe_status': status,
            'network_access': 'NOT_TESTED', 'reads': [], 'body_words': 0, 'article_body_words': 0,
            'structured_records': 0, 'structured_words': 0,
            'published_evidence_words': 0, 'findings_generated': 0})
    return rows


def select_families(registry, families):
    """Explicit scope cannot turn a missing review into source authorization."""
    if not families or len(families) > 4 or len(set(families)) != len(families):
        raise ValueError('Select one to four distinct source families explicitly')
    for family in families:
        if family not in registry.by_id or not registry.assess(family, 'body')['eligible_for_bounded_probe']:
            raise ValueError('Every selected family must have a current body-access review')
        if registry.by_id[family]['permission_status'] == 'EXISTING_ROUTE_POLICY':
            raise ValueError('Existing native routes require their own diagnostic runner')
    return list(families)


def bounded_seconds(value):
    seconds = float(value)
    if not 0 < seconds <= 90:
        raise argparse.ArgumentTypeError('Use a per-family ceiling above zero and at most 90 seconds')
    return seconds


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live', action='store_true', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--family', action='append', required=True,
                        help='Explicit reviewed source family; repeat at most four times')
    parser.add_argument('--seconds-per-family', type=bounded_seconds, default=60.0)
    return parser


def article_capture(url,page):
    """An extraction category, not relevance, independent truth or freshness."""
    from urllib.parse import urlsplit
    from backend.services.research.publisher_links import is_publisher_hub
    kind=(page.get('body_quality') or {}).get('body_kind') or page.get('body_kind')
    path=urlsplit(url).path
    return (kind=='ARTICLE_BODY' and not is_publisher_hub(url)
        and not re.search(r'/(?:about|help|copyright|privacy|terms)(?:/|-|$)',path,re.I)
        and page.get('content_scope') not in {'FEED_INDEX','SITEMAP_INDEX','PUBLIC_DISCOVERY_INDEX'})


def probe(row,registry,service, *, seconds=60):
    from backend.infrastructure.acquisition.network.budget import acquisition_deadline,public_request_budget,PublicRequestBudget
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.candidate_selection import article_shaped
    if not 0 < seconds <= 90:
        raise ValueError('Invalid per-family ceiling')
    if row['family'] == 'cpsc':
        return probe_cpsc(row, registry, seconds=seconds)
    source=registry.by_id[row['family']]
    initial=next(iter(source['discovery'].get('entrypoints',[])),source['reference'])
    row['probe_kind']='DIRECT_PUBLISHER_DIRECTORY_AND_AT_MOST_ONE_OBSERVED_ARTICLE'
    row['initial_url']=initial
    started=time.monotonic();budget=PublicRequestBudget(total=6,per_host=6)
    reader=DeepReader();queue=[initial];seen=set()
    try:
        with public_request_budget(budget),acquisition_deadline(started+seconds):
            while queue and len(row['reads'])<2:
                url=queue.pop(0)
                if url in seen:continue
                seen.add(url)
                item=EvidenceItem(id='site_probe_'+hashlib.sha256(url.encode()).hexdigest()[:12],
                    canonical_url=url,title='Explicit individual website probe',channel='web',content_depth='METADATA',
                    metadata={'publisher_basis':'OPERATOR_SITE_PROBE','candidate_score':.5})
                captures,trace=reader.deep_read([item],max_reads=1,timeout_per_read=min(30,max(.01,started+seconds-time.monotonic())),service=service)
                attempt=dict(trace['acquisition_attempts'][0]) if trace['acquisition_attempts'] else {'failure_kind':'NOT_SELECTED'}
                result={k:attempt.get(k) for k in ['url','status','failure_kind','http_status','duration_ms',
                    'network_observed','robots_access','source_permission','runtime_decision',
                    'rejection_layer','backend','transport_success','error_message']}
                if isinstance(attempt.get('provider_failures'),list):
                    result['provider_failures']=attempt['provider_failures'][:3]
                result.update(words=0,kb_utf8=0,article_body=False,excerpt_permission=False)
                for capture in captures:
                    page=capture.metadata.get('page_metadata') or {}
                    body=capture.content or ''
                    kind=(page.get('body_quality') or {}).get('body_kind') or page.get('body_kind')
                    article=article_capture(capture.canonical_url,page)
                    permission=registry.excerpt_decision(capture.canonical_url,page)
                    result.update(title=page.get('title') or capture.title,body_kind=kind,content_scope=page.get('content_scope'),
                        words=len(body.split()),kb_utf8=round(len(body.encode('utf-8'))/1000,3),article_body=article,
                        excerpt_permission=permission['eligible'],excerpt_permission_reason=permission.get('reason'),
                        body_sha256=hashlib.sha256(body.encode('utf-8')).hexdigest(),publication=page.get('published'))
                    row['body_words']+=result['words']
                    row['article_body_words']+=result['words'] if article else 0
                    # Only follow a link actually captured from this family.
                    links=page.get('observed_links',[])
                    for link in links[:200]:
                        candidate=link.get('url','');matched=registry.match_url(candidate)
                        if matched and matched['id']==source['id'] and candidate not in seen and article_shaped(candidate):
                            if not any(x in candidate.casefold() for x in ['/about','/help','copyright','/terms','/privacy']):
                                queue.append(candidate);break
                row['reads'].append(result)
    except Exception as error:
        from backend.infrastructure.acquisition.network.http import transport_failure_kind
        row['probe_error']=transport_failure_kind(error)
    row['seconds']=round(time.monotonic()-started,2)
    row['native_http_admissions']=sum(budget.hosts.values())
    row['native_http_by_host']=dict(budget.hosts)
    row['probe_status']='BODY_EXTRACTED' if row['body_words'] else 'NO_BODY_ACQUIRED'
    row['network_access']='BODY_OBSERVED' if row['body_words'] else 'FAILED_OR_BLOCKED_SEE_READS'
    return row


def probe_cpsc(row, registry, *, seconds=60):
    """One public API lookup, then only its observed records; no HTML fallback."""
    from urllib.parse import urlencode
    from backend.infrastructure.acquisition.adapters.consumer.cpsc_recalls import CpscRecallsAdapter, CPSC_API_URL
    from backend.infrastructure.acquisition.adapters.expansion_safety import capture_adapter_fetches
    from backend.infrastructure.acquisition.network.budget import acquisition_deadline, public_request_budget, PublicRequestBudget
    from backend.services.agent_reach.channels import RetrievalRequest
    from backend.services.research.source_registry import source_body_scope
    api_url = CPSC_API_URL + '?' + urlencode({'format': 'json', 'RecallTitle': 'battery'})
    started = time.monotonic()
    budget = PublicRequestBudget(total=6, per_host=6)
    row.update(initial_url=api_url, probe_kind='DIRECT_CPSC_API_RECORD_DIAGNOSTIC', records=[])
    observations = []
    try:
        with public_request_budget(budget), acquisition_deadline(started + seconds), source_body_scope(registry):
            if not registry.body_decision(api_url)['eligible']:
                row['probe_error'] = 'API_OUTSIDE_REVIEWED_BODY_SCOPE'
            else:
                adapter = CpscRecallsAdapter()
                with capture_adapter_fetches() as observations:
                    candidates = adapter.discover('battery', limit=2)
                row['candidate_records'] = len(candidates)
                permission = registry.excerpt_decision(api_url)
                for candidate in candidates[:2]:
                    document = adapter.acquire(candidate, RetrievalRequest(task_type='READ'))
                    for fragment in adapter.normalize(document, candidate, RetrievalRequest(task_type='READ')):
                        body = fragment.content or ''
                        row['structured_records'] += 1
                        row['structured_words'] += len(body.split())
                        row['records'].append({'RecallID': fragment.raw_metadata['RecallID'],
                            'url': fragment.url, 'title': fragment.title, 'issue_date': fragment.published,
                            'api_url': api_url, 'content_depth': fragment.content_depth,
                            'structured_words': len(body.split()), 'kb_utf8': round(len(body.encode('utf-8')) / 1000, 3),
                            'record_sha256': hashlib.sha256(document.raw_content.encode('utf-8')).hexdigest(),
                            'field_provenance': fragment.raw_metadata['field_provenance'],
                            'source_assertion_only': True, 'article_body_acquired': False,
                            'excerpt_permission': permission['eligible'],
                            'excerpt_permission_reason': permission.get('reason')})
    except Exception as error:
        from backend.infrastructure.acquisition.network.http import transport_failure_kind
        row['probe_error'] = transport_failure_kind(error)
    row['reads'] = observations
    row['seconds'] = round(time.monotonic() - started, 2)
    row['native_http_admissions'] = sum(budget.hosts.values())
    row['native_http_by_host'] = dict(budget.hosts)
    row['probe_status'] = 'STRUCTURED_RECORDS_OBSERVED' if row['structured_records'] else 'NO_STRUCTURED_RECORD_ACQUIRED'
    row['network_access'] = ('STRUCTURED_API_OBSERVED' if row['structured_records'] else
                             'FAILED_OR_EMPTY_SEE_OBSERVATIONS' if observations else 'TRANSPORT_OUTCOME_UNOBSERVED')
    return row


def main():
    parser = build_parser()
    args = parser.parse_args()
    out = args.output_dir.resolve()
    protected = [ROOT / p for p in ['research', 'artifacts', 'backend/data/dossiers', 'tests/retrieval_benchmark']]
    if out.exists() or any(out == p or out.is_relative_to(p) for p in protected):
        parser.error('Use a fresh output directory outside protected data')
    with tempfile.TemporaryDirectory(prefix='aegis-site-probe-runtime-') as temp:
        from scripts.validation.isolated_runtime import isolated_environment
        os.environ.update(isolated_environment(Path(temp)))
        os.environ.update(AEGIS_MOCK_LLM='false', AEGIS_SOURCE_REVIEWS_FILE='',
            AEGIS_SOURCE_ALLOWED_FAMILIES=','.join(args.family), FIRECRAWL_API_KEY='', HUGINN_ENABLED='false')
        for key in ['AEGIS_LIVE_ADVISORY_ENABLED', 'AEGIS_SEARCH_ADVISOR_ENABLED',
                    'AEGIS_SOURCE_PLANNER_LLM_ENABLED', 'AEGIS_EVIDENCE_ADVISOR_ENABLED']:
            os.environ[key] = 'false'
        from backend.services.research.source_registry import source_registry
        try:
            selected = select_families(source_registry, args.family)
        except ValueError as error:
            parser.error(str(error))
        out.mkdir(parents=True)
        from backend.services.agent_reach import agent_reach_service
        rows = inventory(source_registry)
        for row in rows:
            if row['family'] in selected:
                print('START ' + row['family'], flush=True)
                probe(row, source_registry, agent_reach_service, seconds=args.seconds_per_family)
                print(json.dumps({'family': row['family'], 'status': row['probe_status'], 'words': row['body_words'],
                    'structured_records': row['structured_records'], 'structured_words': row['structured_words'],
                    'seconds': row['seconds'], 'native_http_admissions': row['native_http_admissions']}), flush=True)
            elif row['probe_status'] == 'PENDING_EXPLICIT_SELECTION':
                row['probe_status'] = 'NOT_SELECTED_NOT_PROBED'
        result = {'mode': 'INDIVIDUAL_SOURCE_DIAGNOSTIC', 'model_calls': 0, 'source_families': len(rows), 'rows': rows,
            'limits': {'selected_families': selected, 'seconds_per_family': args.seconds_per_family,
                      'reads_per_family': 2, 'native_http_admissions_per_family': 6},
            'limitations': ['Directory text is not necessarily article content or topic evidence.',
                'CPSC records are structured issuing-agency assertions, not acquired publisher articles or fraud verdicts.',
                'No query-based investigation, finding synthesis, independent corroboration or relevance acceptance.',
                'Unselected sources were not fetched; their network access is unknown. Existing native routes were not rerun.',
                'Body/structured words are retained extraction words, not published evidence. No raw source text is exported.']}
        (out / 'measurements.json').write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
        with (out / 'sites.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['family', 'name', 'configured_permission', 'body_permission_status',
                'probe_status', 'body_words', 'article_body_words', 'structured_records', 'structured_words', 'published_evidence_words'])
            writer.writeheader()
            writer.writerows({k: r[k] for k in writer.fieldnames} for r in rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
