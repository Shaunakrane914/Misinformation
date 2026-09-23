"""
Aegis Protocol — Native Agent Reach Subsystem
=============================================
Provides clean native integration with the upstream Agent Reach capability layer:
- Live Doctor health & active backend detection (`native_doctor`)
- Allowlisted secure tool execution (`native_executor`)
- Upstream output normalization (`native_normalizer`)
- Capability-aware domain router (`native_router`)
- Runtime profile & upstream commit inspection
"""

from backend.services.agent_reach.native.channel_capabilities import (
    CAPABILITY_MATRIX,
    PlatformCapability,
    get_capability,
)
from backend.services.agent_reach.native.doctor import DoctorBridge, native_doctor
from backend.services.agent_reach.native.errors import (
    AuthRequiredError,
    BackendExecutionError,
    ChannelDegradedError,
    FallbackTriggered,
    NativeReachError,
    SecurityPolicyViolation,
)
from backend.services.agent_reach.native.executor import NativeExecutor, native_executor
from backend.services.agent_reach.native.normalizer import NativeNormalizer, native_normalizer
from backend.services.agent_reach.native.router import NativeRouter, native_router
from backend.services.agent_reach.native.runtime import (
    NativeRuntime,
    RuntimeProfile,
    find_tool_binary,
    get_runtime_profile,
    get_upstream_info,
    is_tool_available,
    native_runtime,
)

__all__ = [
    "native_doctor",
    "native_executor",
    "native_normalizer",
    "native_router",
    "native_runtime",
    "DoctorBridge",
    "NativeExecutor",
    "NativeNormalizer",
    "NativeRouter",
    "NativeRuntime",
    "RuntimeProfile",
    "get_runtime_profile",
    "get_upstream_info",
    "find_tool_binary",
    "is_tool_available",
    "PlatformCapability",
    "CAPABILITY_MATRIX",
    "get_capability",
    "NativeReachError",
    "AuthRequiredError",
    "BackendExecutionError",
    "ChannelDegradedError",
    "FallbackTriggered",
    "SecurityPolicyViolation",
]
