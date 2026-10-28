"""Explicit bounded public-source diagnostics; never production activation.

Each family gets at most two shared HTTP function invocations, one attempt and
zero redirects. Raw responses stay in a fresh private output directory. Source
reviews precede this tool; an HTTP success is not a permission decision.
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-live', action='store_true', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    from backend.infrastructure.acquisition.network import http
    from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget, acquisition_deadline
    from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch
    from backend.infrastructure.acquisition.adapters.expanded_catalog import get_expanded_adapters
    from backend.services.agent_reach.channels import RetrievalRequest
    from backend.services.research.reference_fallback import select_entity
    from scripts.audits.website_yield_observer import WebsiteYieldObserver
    original = http._fetch_public_http
    state = {'family': '', 'calls': 0}
    rows = []
    budget = PublicRequestBudget(total=100, per_host=10)

    def bounded(url, **kwargs):
        if state['calls'] >= 2:
            raise TimeoutError('SOURCE_FAMILY_TWO_ATTEMPT_CAP')
        state['calls'] += 1
        kwargs.update(max_attempts=1, max_redirects=0, timeout=min(5., kwargs.get('timeout', 5.)),
                      max_bytes=min(1_000_000, kwargs.get('max_bytes', 1_000_000)))
        response = original(url, **kwargs)
        (args.output_dir / f"{state['family']}-{state['calls']}.bin").write_bytes(response.body)
        state['statuses'].append(response.status_code)
        return response

    adapters = get_expanded_adapters()
    families = [('wikipedia', 'Mary Barra'), ('wikidata_exec', 'Mary Barra'),
                ('govuk', 'artificial intelligence'), ('cpsc_recalls', 'Dyson'), ('bluesky', 'semiconductor')]
    endpoints = {
        'openfda': 'https://api.fda.gov/drug/enforcement.json?limit=1',
        'hackernews': 'https://hacker-news.firebaseio.com/v0/topstories.json',
        'stackexchange': 'https://api.stackexchange.com/2.3/search/advanced?site=stackoverflow&q=python&filter=withbody&pagesize=1',
    }
    with public_request_budget(budget), patch.object(http, '_fetch_public_http', bounded), WebsiteYieldObserver() as observer:
        for family, subject in families + [(name, '') for name in endpoints]:
            state.update(family=family, calls=0, statuses=[])
            started = time.monotonic()
            row = {'source_family': family, 'subject': subject, 'status': 'BODY_EMPTY', 'candidates': 0,
                   'body_words': 0, 'task_qualified_words': 0, 'permission': 'APPROVED_FOR_BOUNDED_TEST',
                   'production_enabled': False}
            try:
                with acquisition_deadline(started + 20):
                    if family in endpoints:
                        response = safe_fetch(endpoints[family])
                        payload = json.loads(response.body)
                        if response.status_code == 200:
                            if family == 'hackernews' and isinstance(payload, list) and payload:
                                response = safe_fetch('https://hacker-news.firebaseio.com/v0/item/' + str(int(payload[0])) + '.json')
                                payload = json.loads(response.body)
                            content = (payload.get('results') or payload.get('items') or [payload]) if isinstance(payload, dict) else []
                            row.update(status='STRUCTURED_EVIDENCE_VERIFIED', candidates=len(content),
                                body_words=len(json.dumps(content).split()), content_scope='STRUCTURED_API_RECORD_NOT_ARTICLE')
                    else:
                        adapter = adapters[family]
                        candidates = adapter.discover(subject, limit=3)
                        row['candidates'] = len(candidates)
                        selected = select_entity(candidates, subject) if family in {'wikipedia', 'wikidata_exec'} else next(iter(candidates), None)
                        if selected is not None:
                            document = adapter.acquire(selected, RetrievalRequest(task_type='READ'))
                            fragments = adapter.normalize(document, selected, RetrievalRequest(task_type='READ'))
                            row.update(status='BODY_ACQUISITION_VERIFIED' if fragments else document.status,
                                body_words=sum(len(f.content.split()) for f in fragments), url=selected.url,
                                content_scope=fragments[0].content_depth if fragments else None)
                            (args.output_dir / f'{family}-fragments.json').write_text(json.dumps(
                                [f.to_dict() for f in fragments], ensure_ascii=True, default=str), encoding='utf-8')
            except Exception as error:
                row['failure_category'] = type(error).__name__
                row['status'] = 'FAILED'
            if any(status in {401, 403, 429} for status in state['statuses']):
                row['status'] = 'RATE_LIMITED' if 429 in state['statuses'] else 'ACCESS_DENIED'
            row.update(http_attempts=state['calls'], http_statuses=state['statuses'], seconds=round(time.monotonic()-started, 3))
            rows.append(row)
            print(json.dumps(row), flush=True)
    result = {'sources': rows, 'native_budget': budget.snapshot(), 'transport': observer.export()}
    (args.output_dir / 'results.json').write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding='utf-8')
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with (args.output_dir / 'source_family_probe_results.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
