"""Offline planner ablation and optional genuine saved-world acquisition replay.

Eight-topic fixtures are synthetic routing calibration, not source-body proof.
Optional saved batches use the existing replay simulator with unknown outcomes
explicit, identical inputs/permissions and modeled costs; never fresh requests.
"""
import argparse
import hashlib
import importlib.util
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_previous(path):
    spec = importlib.util.spec_from_file_location('_aegis_previous_source_planner', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    previous = module.SourcePlanningEngine()

    class PreviousPlannerAdapter:
        def plan(self, *args, **kwargs):
            kwargs.pop('routing_hints', None)
            kwargs.pop('observed_titles', None)
            value = previous.plan(*args, **kwargs)
            value.research_context, value.source_family_decisions = {}, []
            return value

        def refine_topics(self, *args, **kwargs):
            return []

    return PreviousPlannerAdapter()


def project(plan):
    rows = [dict(channel=channel, **row) for channel, values in plan.to_channel_queries().items() for row in values]
    return {'intent': plan.intent_class, 'context': plan.research_context,
            'actions': rows, 'selected_families': sorted({r['source_family'] for r in rows if r.get('source_family')}),
            'source_decisions': plan.source_family_decisions,
            'native_body_quality': 'NOT_MEASURED_BY_ROUTING_CALIBRATION'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-planner', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=ROOT/'tests/unit/fixtures/topic_routing_cases_20261026.json')
    parser.add_argument('--saved-batch', type=Path)
    parser.add_argument('--recorded-claims', type=Path, help='Optional case-id to exact original claim mapping from a recorded command; not source URLs')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from scripts.validation.isolated_runtime import block_live_network, isolated_environment
    from scripts.audits.requalify_raw_pool import _safe_output_path
    output = _safe_output_path(args.output)
    baseline_hash = hashlib.sha256(args.baseline_planner.read_bytes()).hexdigest()
    block_live_network()
    with tempfile.TemporaryDirectory(prefix='aegis-topic-offline-') as directory:
        env = isolated_environment(Path(directory))
        env.update(AEGIS_MOCK_LLM='false', AEGIS_SEARCH_ADVISOR_ENABLED='false', AEGIS_EVIDENCE_ADVISOR_ENABLED='false',
                   AEGIS_SOURCE_REVIEWS_FILE='', AEGIS_SOURCE_ALLOWED_FAMILIES='')
        os.environ.update(env)
        module = importlib.import_module('backend.services.agent_reach.source_planner')
        previous, current = load_previous(args.baseline_planner), module.SourcePlanningEngine()
        matrix = json.loads(args.cases.read_text(encoding='utf-8'))
        rows = []
        for case in matrix['cases'] + matrix['controls']:
            kwargs = dict(entity=case['target'], agent=case['agent'], domain=case['domain'], use_llm=False,
                          routing_hints=case.get('hints', {}))
            before = project(previous.plan(case['claim'], **kwargs))
            after = project(current.plan(case['claim'], **kwargs))
            rows.append({'case': case['id'], 'before': before, 'after': after,
                         'expected_topic': case['expected_topic'],
                         'topic_calibration_match': case['expected_topic'] in after['context']['topics'] if case['expected_topic'] else
                                                   not after['context']['topics']})
        replay_rows, inputs = [], {}
        claims = json.loads(args.recorded_claims.read_text(encoding='utf-8')) if args.recorded_claims else {}
        if args.saved_batch:
            from scripts.audits import acquisition_replay as replay
            for label, case, path in replay.baseline.load_batch('genuine-saved', str(args.saved_batch)):
                inputs[path.name] = replay.baseline.sha256_file(path)
                report = json.loads(path.read_text(encoding='utf-8'))
                for name, engine in [('previous_planner', previous), ('topic_planner', current)]:
                    with patch.object(module, 'source_planning_engine', engine):
                        row = replay.replay_one(report, agent=case['agent'], label=label+'-'+path.stem+'-'+name,
                                                spec='pipelined:r2:d1', scale=.03, claim_text=claims.get(path.stem))
                    row['planner_version'] = name
                    if path.stem in claims:
                        row['reconstructed_claim_from_recorded_command'] = claims[path.stem]
                    replay_rows.append(row)
                assert replay.baseline.sha256_file(path) == inputs[path.name]
        payload = {'mode': 'OFFLINE_PLANNER_ABLATION', 'network_calls': 0, 'model_calls': 0,
                   'baseline_planner_sha256': baseline_hash, 'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
                   'routing_matrix': rows, 'saved_world_replays': replay_rows, 'saved_input_hashes': inputs,
                   'limitations': ['Synthetic routing cases do not prove acquisition or accuracy.',
                     'Saved replays share current controller/permission policy; only planner version differs.',
                     'Unobserved search/read outcomes remain unknown; replay admissions/latency are modeled.',
                     'Eight-topic genuine body acceptance is not established by this routing matrix.']}
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, default=str)
        print(json.dumps({'routing_rows': len(rows), 'matches': sum(r['topic_calibration_match'] for r in rows),
                          'saved_replays': len(replay_rows), 'network_calls': 0, 'model_calls': 0}))


if __name__ == '__main__':
    main()
