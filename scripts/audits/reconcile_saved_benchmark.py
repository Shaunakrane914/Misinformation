"""Read-only recovery of aggregate benchmark output and sealed dossier observations.

No imports of agents, no network or model calls. A depth label is not an actual
read-attempt log, vocabulary is not useful passage yield, and search snippets
cannot establish acquisition of article bodies. Missing metrics remain null.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


CASES = [('financial', x) for x in ('NVDA','AAPL','TSLA','MSFT','AMZN')] + [
    ('brand', x) for x in ('Nike','Rolex','Pfizer','Gucci','Sony')] + [
    ('trending', x) for x in ('Russell Brand','Taylor Swift','OpenAI','Artificial Intelligence','DeepSeek')] + [
    ('personal', x) for x in ('Satya Nadella','Tim Cook','Sam Altman','Sundar Pichai','Jensen Huang')]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def subject_matches(target, expected):
    return expected.casefold() == target.casefold() or bool(re.search(
        r'\(' + re.escape(expected) + r'\)', target, re.I))


def dossier_metrics(data):
    snapshots = data.get('candidate_snapshots') or {}
    nodes = {row['id']:row for row in (data.get('source_lineage') or {}).get('nodes',[])
             if isinstance(row,dict) and row.get('id')}
    refs = [value for row in data.get('findings_provenance',[]) for value in row.get('supporting_evidence_ids',[])]
    summary = re.search(r'with (\d+) deep-read',str(data.get('summary','')))
    return {'target':data.get('target'),'domain':data.get('domain'),'created_at':data.get('created_at'),
        'engine_latency_ms':data.get('latency_ms'),'dossier_status':data.get('status'),
        'snapshot_records':len(snapshots),
        'snapshot_words_not_article_words':sum(len(row.get('content','').split()) for row in snapshots.values()),
        'all_snapshot_hashes_match':all(digest(row.get('content','').encode())==row.get('sha256') for row in snapshots.values()),
        'distinct_observed_publishers':len({urlsplit(row.get('url') or '').hostname for row in nodes.values()}-{None,''}),
        'observed_publishers':sorted({urlsplit(row.get('url') or '').hostname for row in nodes.values()}-{None,''}),
        'citation_references':len(refs),
        'references_with_snapshot_and_url':sum(value in snapshots and bool(nodes.get(value,{}).get('url')) for value in refs),
        'citation_entailment':'NOT_VERIFIABLE_WITHOUT_ACQUIRED_BODY_AND_PASSAGE_OFFSETS',
        'article_bodies_actually_acquired':None,'raw_article_words':None,
        'qualified_relevant_source_count':None,'deduplicated_relevant_passage_words':None,
        'actual_read_attempts':None,'native_http_admissions':None,
        'summary_reported_document_count_NOT_attempts':int(summary.group(1)) if summary else None,
        'query_statuses':dict(Counter(row.get('status','UNKNOWN') for row in data.get('queries_executed',[]))),
        'channel_statuses':dict(Counter(row.get('status','UNKNOWN') for row in data.get('capability_graph',[]))),
        'failure_observations':[{ 'platform':row.get('platform'),'status':row.get('status'),
            'has_failure_reason':bool(row.get('failure_reason'))} for row in data.get('capability_graph',[])
            if row.get('failure_reason') or row.get('status') not in {'SUCCESS','EMPTY'}],
        'code_revision':'NOT_ATTESTED_BY_SAVED_RUN; ROOT_HEAD_AND_CURRENT_DIRTY_DIFF_ARE_SEPARATE_OBSERVATIONS'}


def recover(results, dossier_directory):
    encoded=results.read_bytes();summary=json.loads(encoded)
    candidates=[]
    for path in dossier_directory.glob('*.json'):
        # Read-only. A separate archive inventory reports malformed historical
        # JSON; those files cannot supply case metrics and are never repaired.
        try:
            raw=path.read_bytes();data=json.loads(raw)
        except (OSError,ValueError):
            continue
        if str(data.get('created_at','')).startswith('2026-10-28') and any(
                data.get('domain')==domain and subject_matches(str(data.get('target','')),subject)
                for domain,subject in CASES):
            candidates.append((data.get('created_at',''),path.name,raw,data))
    candidates.sort()
    sequences=[]
    for start in range(len(candidates)):
        rows=candidates[start:start+20]
        if len(rows)==20 and all(data.get('domain')==domain and subject_matches(str(data.get('target','')),subject)
                for (_,_,_,data),(domain,subject) in zip(rows,CASES)):
            sequences.append({'start':rows[0][0],'end':rows[-1][0],
                'status':'TWENTY_COMPLETED_ENGINE_DOSSIERS_ONLY; RUNNER_COMPLETION_NOT_ATTESTED',
                'cases':[{'dossier_file':name,'dossier_sha256':digest(raw),**dossier_metrics(data)} for _,name,raw,data in rows]})
    reported=summary.get('test_cases') or []
    complete=len(reported)==20 and {(r.get('agent'),r.get('prompt')) for r in reported} == {
        ({'financial':'Scout','brand':'BrandShield','trending':'Trending','personal':'PersonalWatch'}[d],s) for d,s in CASES}
    return {'mode':'OFFLINE_READ_ONLY_AGGREGATE_AND_DOSSIER_RECOVERY','new_network_calls':0,'model_calls':0,
        'completed_summary':{'sha256':digest(encoded),'timestamp':summary.get('timestamp'),
            'status':'COMPLETE_20_CASE_SUMMARY' if complete else 'INCOMPLETE_OR_INVALID_CASE_SUMMARY',
            'case_count':len(reported),'cases':reported,
            'metric_limitations':['total_words includes content OR snippet, not independently confirmed article text',
                'unique_words is distinct vocabulary, not deduplicated relevant passages',
                'deep_reads counts depth labels on returned records, not actual attempted HTTP reads',
                'EXCELLENT/GOOD are raw-length thresholds, not research-quality acceptance',
                'runner sets AEGIS_MOCK_LLM=true; historical results are not live AI proof']},
        'ordered_twenty_engine_sequences':sequences,
        'separate_subject_demonstrations':[{'dossier_file':name,'dossier_sha256':digest(raw),**dossier_metrics(data)}
            for _,name,raw,data in candidates if data.get('target') in {'Tim Cook','Russell Brand'}],
        'limitations':['Only one aggregate output path exists in the runner and is overwritten on every completed run.',
            'Engine dossier completion does not establish later agent/runner completion.',
            'No per-run code fingerprint, native HTTP admissions, read ledger, article structures or published passage offsets in these dossiers.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--dossiers',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output path; saved evidence must not be overwritten')
    report=recover(args.results,args.dossiers)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=True,indent=2)
    print(json.dumps({'status':report['completed_summary']['status'],
        'completed_summary_cases':report['completed_summary']['case_count'],
        'ordered_twenty_engine_sequences':len(report['ordered_twenty_engine_sequences']),
        'separate_tim_russell_dossiers':len(report['separate_subject_demonstrations'])}))


if __name__=='__main__':
    main()
