"""Bounded live spot-check of the separate AgentReach direct adapters.

Run from the repository root with ``python -m scripts.audits.run_phase8_auxiliary_adapter_probe``.
This does not replace the 16 recovered-operation audit or prove provider completeness.
Only summary metadata is saved; response bodies and evidence text are never written.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest
from backend.services.agent_reach.native.adapters.github import GitHubAdapter
from backend.services.agent_reach.native.adapters.web import WebAdapter
from backend.services.agent_reach.native.adapters.youtube import YouTubeAdapter


def _git_revision():
    revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, check=True).stdout.strip())
    return revision, dirty


def probe(adapter, url, platform):
    """Return observations, never a provider-completeness claim."""
    candidate = CandidateSource(url=url, platform=platform)
    request = RetrievalRequest(agent="diagnostic", task_type="READ", query="Phase 8B adapter probe")
    document = adapter.acquire(candidate, request)
    fragments = adapter.normalize(document, candidate, request)
    return {
        "adapter": adapter.__class__.__name__,
        "target": url,
        "status": document.status,
        "failure_reason_present": bool(document.failure_reason),
        "backend_id": document.backend_id,
        "retrieval_mode": document.retrieval_mode,
        "latency_ms": document.latency_ms,
        "raw_body_chars": len(document.raw_content),
        "normalized_count": len(fragments),
        "fragments": [{
            "content_depth": fragment.content_depth,
            "content_chars": len(fragment.content),
            "has_title": bool(fragment.title),
            "has_author": bool(fragment.author),
            "has_publication": bool(fragment.published),
            "metadata_keys": sorted(fragment.raw_metadata),
        } for fragment in fragments],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="artifacts/phase8_auxiliary_adapter_probes")
    args = parser.parse_args()
    revision, dirty = _git_revision()
    targets = [
        (GitHubAdapter(), "https://github.com/openai/openai-python", "github"),
        (WebAdapter(), "https://example.com/", "web"),
        (YouTubeAdapter(), "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
    ]
    records = [probe(adapter, url, platform) for adapter, url, platform in targets]
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%SZ")
    output_dir = Path(args.output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": revision,
        "dirty_worktree": dirty,
        "scope": "Bounded auxiliary adapter spot-check only; not 16-operation or Phase 8B acceptance",
        "records": records,
    }
    (output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"summary={output_dir / 'summary.json'}")
    for record in records:
        print(f"{record['adapter']}: {record['status']}, fragments={record['normalized_count']}, "
              f"latency_ms={record['latency_ms']}")


if __name__ == "__main__":
    main()
