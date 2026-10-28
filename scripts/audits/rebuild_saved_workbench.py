"""Build a fresh evidence-only UI projection from saved bodies, with no network/AI.

This does not rerun an agent, discover sources or regenerate verdicts. Original
reports remain immutable; all passages pass current qualification and inspection.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def rebuild_payload(payload, target, domain, agent):
    from scripts.audits.requalify_raw_pool import locate_pool, requalify_payload
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.body_context import reconcile_captured_context
    from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage
    from backend.services.research.source_quality import source_quality_engine
    from backend.schemas.unified_report import UnifiedEvidenceItem
    from backend.services.research.evidence_workbench import build_evidence_workbench

    original = locate_pool(payload)
    reference = datetime.fromisoformat(original['created_at'])
    qualified = requalify_payload(payload, target=target, domain=domain, reference_time=reference)
    accepted = {r['source_id'] for r in qualified['requalification']['decisions']
                if r['qualification_status'] == 'QUALIFIED'}
    evidence = []
    for item in RawAcquisitionPool.from_export(original).to_evidence_items():
        if item.id not in accepted:
            continue
        reconcile_captured_context(item)
        item.snippet = item.content[:12000]
        source_quality_engine.classify_and_score(item, target_name=target)
        item.metadata.update(layer2_eligible=True, temporal_required=domain == 'trending', temporal_eligible=True)
        PassageExtractor().extract_passages([item], target, domain=domain)
        if has_usable_passage(item):
            evidence.append(UnifiedEvidenceItem.from_evidence_item(item).to_dict())
    workbench = build_evidence_workbench(evidence)
    return {'mode': 'OFFLINE_SAVED_BODY_WORKBENCH_REBUILD', 'new_network_calls': 0, 'model_calls': 0,
        'original_pool_sha256': qualified['original_pool_sha256'],
        'research_corpus': {'raw_acquisition_pool': original},
        'unified_report': {'_meta': {'agent': agent, 'mode': 'OFFLINE_SAVED_BODY_REBUILD'},
            'target': target, 'summary': 'Offline evidence-only projection of saved sources; no new investigation or claim adjudication.',
            'findings': [], 'evidence': {'primary': [], 'independent': evidence, 'community': []},
            'evidence_workbench': workbench},
        'limitations': ['Not a native agent rerun or fresh discovery.',
                       'Historical event text does not establish a current publication date.',
                       'Source assertions and attribution remain unverified.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--domain', choices=['financial','brand','personal','trending'], required=True)
    parser.add_argument('--agent', choices=['scout','brandshield','personal_watch','trending'], required=True)
    args = parser.parse_args()
    from scripts.audits.requalify_raw_pool import MAX_INPUT_BYTES, _safe_output_path
    if args.input.is_symlink() or not args.input.is_file() or args.input.stat().st_size > MAX_INPUT_BYTES:
        parser.error('Use a bounded regular saved response')
    output = _safe_output_path(args.output)
    before = args.input.read_bytes()
    from scripts.audits.acquisition_baseline import _isolate
    _isolate()
    result = rebuild_payload(json.loads(before), args.target, args.domain, args.agent)
    result['input_sha256'] = hashlib.sha256(before).hexdigest()
    if args.input.read_bytes() != before:
        raise ValueError('Original changed during rebuilding')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=True, indent=2)
    print(json.dumps({'mode': result['mode'], 'accounting': result['unified_report']['evidence_workbench']['accounting']}))


if __name__ == '__main__':
    main()
