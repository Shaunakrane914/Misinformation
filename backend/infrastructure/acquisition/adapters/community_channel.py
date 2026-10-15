"""Expose community discussion via the canonical native service boundary."""
from backend.services.agent_reach.channels import Channel, ChannelStatus
from backend.infrastructure.acquisition.adapters.authoritative.channel import AcquisitionOutcomeError


class CommunityChannel(Channel):
    def __init__(self, name):
        if name not in {"hackernews", "stackexchange"}:
            raise ValueError("Unsupported community channel")
        self._name = name

    @property
    def name(self):
        return self._name

    def health_check(self):
        return ChannelStatus.NOT_PROBED

    def search(self, query, limit=3, **kwargs):
        from backend.services.agent_reach.native import native_router
        fragments, telemetry = native_router.execute_channel_query(
            platform=self.name, query=query, limit=limit, **kwargs,
        )
        status = telemetry.get("status", "FAILED")
        if status not in {"SUCCESS", "EMPTY_RESULT"}:
            raise AcquisitionOutcomeError(status)
        return fragments
