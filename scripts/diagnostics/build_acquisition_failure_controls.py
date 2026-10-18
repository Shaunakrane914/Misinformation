"""Build labeled synthetic all-timeout SSE controls for offline browser replay.

No provider requests or real source records. Not a captured Lenovo response.
Use with run_phase9_four_agent_browser_audit.py --replay-dir; never deploy fixtures.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    from scripts.validation.isolated_runtime import block_live_network
    block_live_network()
    from backend.services.research.acquisition_status import acquisition_outcome
    from backend.services.report_builder import _complete_agent_report
    from backend.schemas.unified_report import UnifiedReport
    for index, (agent, target) in enumerate((('scout', 'Lenovo'), ('trending', 'NVIDIA'),
                                            ('brandshield', 'Nike'), ('personal_watch', 'Satya Nadella')), 1):
        records = [{"query_id": f"control_{n}", "query_text": target, "channel": "web",
                    "status": "TIMEOUT", "provider_started": True, "error": "Synthetic timeout control"}
                   for n in range(9)]
        trace = {"acquisition": acquisition_outcome(records), "query_records": records, "queries_planned": 9}
        data = {"_control": "SYNTHETIC_ALL_TIMEOUT_NOT_LIVE", "sources": [], "evidence": [],
                "company_name": target, "ticker": "", "brand_name": target,
                "deep_research_trace": trace, "retrieval_trace": trace}
        data["unified_report"] = _complete_agent_report(UnifiedReport(agent=agent, query=target), data, records, 9).to_dict()
        events = [{"event": "result", "data": {"result": data}}]
        (args.output_dir / f"{index:02d}-{agent}-events.json").write_text(json.dumps(events), encoding="utf-8")
    print("SYNTHETIC_ALL_TIMEOUT_CONTROLS_WRITTEN_NO_NETWORK")


if __name__ == "__main__":
    main()
