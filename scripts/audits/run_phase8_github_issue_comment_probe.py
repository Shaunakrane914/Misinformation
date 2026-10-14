"""Probe bounded public GitHub issue-comment follow-up without saving content.

Run from the repository root as a module. This is one target and not a
discussion-completeness, rate-limit, or Phase 8B acceptance test.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from backend.infrastructure.acquisition.routing.router import NativeRouter


def summarize(fragments, telemetry):
    """Keep source-presence and budget observations, never issue/comment text."""
    records = []
    for fragment in fragments:
        detail = fragment.raw_metadata.get("provider_fields") or {}
        comments = detail.get("comment_samples") or []
        records.append({
            "issue_number": detail.get("number"),
            "issue_url": fragment.url,
            "content_depth": fragment.content_depth,
            "comment_lookup_status": detail.get("comment_lookup_status"),
            "sampled_comment_count": len(comments),
            "comment_has_next_page": detail.get("comment_has_next_page"),
            "sampled_comment_body_chars": [len(comment.get("body") or "") for comment in comments],
            "comment_source_url_present": [bool(comment.get("url")) for comment in comments],
            "comment_author_present": [bool(comment.get("author")) for comment in comments],
            "comment_date_present": [bool(comment.get("created_at")) for comment in comments],
            "comment_transport_observed": bool((detail.get("comment_transport") or {}).get(
                "network_observed_this_attempt"
            )),
        })
    return {
        "router_status": telemetry.get("status"),
        "follow_up_requests": telemetry.get("follow_up_requests", 0),
        "fragment_count": len(fragments),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="artifacts/phase8_issue_comment_probes")
    args = parser.parse_args()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, check=True).stdout.strip())
    target = "openai/openai-python"
    fragments, telemetry = NativeRouter().execute_channel_query(
        "github", target, operation="issues", limit=3,
        include_comments=True, comment_limit=2,
    )
    report = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": revision,
        "dirty_worktree": dirty,
        "target": target,
        "scope": "One bounded public repository list; at most two follow-up calls and two comments per issue",
        **summarize(fragments, telemetry),
    }
    output_dir = Path(args.output_root) / datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%SZ")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"summary={output_dir / 'summary.json'}")
    print(f"status={report['router_status']} fragments={report['fragment_count']} "
          f"follow_up_requests={report['follow_up_requests']}")


if __name__ == "__main__":
    main()
