"""The live direct-adapter audit retains only bounded, non-content observations."""

import json

from backend.services.agent_reach.channels import EvidenceFragment, FetchedDocument
from scripts.audits.run_phase8_auxiliary_adapter_probe import probe
from scripts.audits.run_phase8_github_issue_comment_probe import summarize


class _StubAdapter:
    def acquire(self, candidate, request):
        return FetchedDocument(
            url=candidate.url,
            status="SUCCESS",
            raw_content="private response sentinel",
            failure_reason="private error sentinel",
        )

    def normalize(self, document, candidate, request):
        return [EvidenceFragment(
            platform="web", url=candidate.url, title="private title sentinel",
            content="private evidence sentinel", author="private author sentinel",
            raw_metadata={"observed_field": "private metadata sentinel"},
        )]


def test_probe_does_not_persist_response_or_evidence_values():
    summary = probe(_StubAdapter(), "https://example.com/", "web")
    serialized = json.dumps(summary)
    assert "private" not in serialized
    assert summary["raw_body_chars"] == len("private response sentinel")
    assert summary["fragments"][0]["metadata_keys"] == ["observed_field"]
    assert summary["failure_reason_present"] is True


def test_comment_probe_summary_omits_issue_and_comment_text():
    fragment = EvidenceFragment(
        platform="GitHub", url="https://github.com/owner/repo/issues/4",
        title="private issue title sentinel", content="private issue body sentinel",
        raw_metadata={"provider_fields": {
            "number": 4, "comment_lookup_status": "SUCCESS",
            "comment_samples": [{
                "body": "private reply sentinel", "author": "public-author",
                "url": "https://github.com/owner/repo/issues/4#issuecomment-9",
                "created_at": "2026-10-13T00:00:00Z",
            }],
            "comment_transport": {"network_observed_this_attempt": True},
        }},
    )
    summary = summarize([fragment], {"status": "SUCCESS", "follow_up_requests": 1})
    assert "private" not in json.dumps(summary)
    assert summary["follow_up_requests"] == 1
    assert summary["records"][0]["sampled_comment_body_chars"] == [len("private reply sentinel")]
    assert summary["records"][0]["comment_transport_observed"] is True
