"""Rebuild only shared reports from saved native responses; no acquisition/AI.

Preserves native evidence, IDs, findings and traces. Emits explicitly synthetic
result-only SSE for offline frontend validation, not live progress evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    # Fail closed even if a future import starts using the network.
    def blocked(*_args, **_kwargs):
        raise RuntimeError("Network forbidden in saved-report reprojection")
    socket.getaddrinfo = blocked
    socket.create_connection = blocked
    socket.socket.connect = blocked
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from backend.services.report_builder import ReportBuilder
    factories = {
        "scout": (ReportBuilder.from_scout_result, "scout_data"),
        "trending": (ReportBuilder.from_trending_result, "trend_data"),
        "brandshield": (ReportBuilder.from_brandshield_result, "brand_data"),
        "personal_watch": (ReportBuilder.from_personal_result, "personal_data"),
    }
    rows = []
    for path in sorted(args.capture_dir.glob("[0-9][0-9]-*.json")):
        agent = path.stem[3:]
        if agent not in factories:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        factory, field = factories[agent]
        previous = data.get("unified_report") or {}
        query = previous.get("query") or (previous.get("_meta") or {}).get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Saved report has no original query: " + path.name)
        native_hash = hashlib.sha256(json.dumps({k: v for k, v in data.items() if k not in {
            "unified_report", "investigation_status"}}, sort_keys=True).encode()).hexdigest()
        report = factory(query=query, **{field: data}).to_dict()
        data["unified_report"] = report
        data["investigation_status"] = report.get("investigation_status")
        for name, value in ((path.name, data), (path.stem + "-events.json", [
                {"event": "result", "data": {"result": data}}])):
            with (args.output_dir / name).open("x", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
        rows.append({"case_id": path.stem, "agent": agent, "input": query,
                     "original_response_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "unchanged_native_fields_sha256": native_hash,
                     "investigation_status": report.get("investigation_status")})
    with (args.output_dir / "projection.json").open("x", encoding="utf-8") as handle:
        json.dump({"mode": "REPORT_ONLY_SAVED_NATIVE_REPROJECTION", "cases": rows,
                   "network_and_ai_calls": 0, "progress_events": "NOT_REPLAYED"}, handle, indent=2)
    print(json.dumps({"mode": "REPORT_ONLY_SAVED_NATIVE_REPROJECTION", "cases": len(rows)}))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
