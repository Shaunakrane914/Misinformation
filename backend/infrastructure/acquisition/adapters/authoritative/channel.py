"""Bridge authoritative native routes into the shared service's channel registry."""
from backend.services.agent_reach.channels import Channel, ChannelStatus


class AcquisitionOutcomeError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Authoritative acquisition outcome: {status}")


class AuthoritativeChannel(Channel):
    def __init__(self, name):
        if name not in {"sec_edgar", "nist_cve", "arxiv", "fact_check"}:
            raise ValueError("Unsupported authoritative channel")
        self._name = name

    @property
    def name(self):
        return self._name

    def search(self, query, limit=5, **kwargs):
        from backend.services.agent_reach.native import native_router
        fragments, telemetry = native_router.execute_channel_query(platform=self.name, query=query, limit=limit, **kwargs)
        status = telemetry.get("status", "FAILED")
        if status not in {"SUCCESS", "EMPTY_RESULT", "DEGRADED"}:
            raise AcquisitionOutcomeError(status)
        return fragments

    def health_check(self):
        return ChannelStatus.NOT_PROBED
