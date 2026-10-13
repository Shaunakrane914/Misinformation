"""The live direct-adapter audit retains only bounded, non-content observations."""

import json

from backend.services.agent_reach.channels import EvidenceFragment, FetchedDocument
from scripts.audits.run_phase8_auxiliary_adapter_probe import probe


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
