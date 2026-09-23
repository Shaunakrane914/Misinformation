"""
Aegis Protocol — Native Agent Reach Runtime Environment Inspector
==================================================================
Identifies the execution profile (LOCAL_DESKTOP vs CLOUD_HEADLESS),
resolves upstream Agent-Reach commit/version, and probes binary tool availability.
"""

import enum
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional

UPSTREAM_COMMIT_PINNED = "a19a171fa980a0785849596492e0af4db800c82f"


class RuntimeProfile(str, enum.Enum):
    LOCAL_DESKTOP = "local_desktop"
    CLOUD_HEADLESS = "cloud_headless"


def get_runtime_profile() -> RuntimeProfile:
    """
    Determine whether the current environment supports desktop-only capabilities
    (real logged-in Chrome sessions, OpenCLI, interactive browser automation)
    or is running in a headless cloud/container/server environment.
    """
    # Explicit override takes precedence
    override = os.getenv("AEGIS_RUNTIME_PROFILE")
    if override:
        return RuntimeProfile.LOCAL_DESKTOP if override.lower() in ("local", "desktop", "local_desktop") else RuntimeProfile.CLOUD_HEADLESS

    # Headless signals
    is_ci = bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("NETLIFY"))
    is_docker = os.path.exists("/.dockerenv")
    
    # Windows Desktop detection: if on Windows without CI and with interactive window station
    if sys.platform == "win32":
        if is_ci:
            return RuntimeProfile.CLOUD_HEADLESS
        return RuntimeProfile.LOCAL_DESKTOP

    # Linux Desktop detection: needs DISPLAY or WAYLAND_DISPLAY
    if sys.platform.startswith("linux"):
        has_display = bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
        if has_display and not is_ci and not is_docker:
            return RuntimeProfile.LOCAL_DESKTOP
        return RuntimeProfile.CLOUD_HEADLESS

    # macOS Desktop detection
    if sys.platform == "darwin":
        if is_ci:
            return RuntimeProfile.CLOUD_HEADLESS
        return RuntimeProfile.LOCAL_DESKTOP

    return RuntimeProfile.CLOUD_HEADLESS


def get_upstream_info() -> Dict[str, Any]:
    """Inspect the installed Agent Reach package and upstream commit."""
    installed = False
    version = "unknown"
    commit = UPSTREAM_COMMIT_PINNED

    try:
        import agent_reach
        installed = True
        version = getattr(agent_reach, "__version__", "1.5.0")
    except ImportError:
        installed = False

    # Check git commit if available in git repo
    git_head = None
    try:
        import importlib.util
        spec = importlib.util.find_spec("agent_reach")
        if spec and spec.origin:
            pkg_dir = os.path.dirname(spec.origin)
            git_dir = os.path.join(os.path.dirname(pkg_dir), ".git")
            if os.path.exists(git_dir):
                res = subprocess.run(
                    ["git", "--git-dir", git_dir, "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if res.returncode == 0 and res.stdout.strip():
                    git_head = res.stdout.strip()
    except Exception:
        pass

    return {
        "installed": installed,
        "version": version,
        "commit": git_head or UPSTREAM_COMMIT_PINNED,
        "runtime": get_runtime_profile().value,
        "python_executable": sys.executable,
    }


def find_tool_binary(binary_name: str) -> Optional[str]:
    """Find absolute path to tool binary on system PATH."""
    return shutil.which(binary_name)


def is_tool_available(binary_name: str) -> bool:
    """Check if tool exists and is executable."""
    return find_tool_binary(binary_name) is not None


class NativeRuntime:
    """Inspector for the native agent-reach execution environment."""

    @property
    def profile(self) -> RuntimeProfile:
        return get_runtime_profile()

    def is_agent_reach_installed(self) -> bool:
        return get_upstream_info()["installed"]

    def get_upstream_version(self) -> str:
        return get_upstream_info()["version"]

    def get_upstream_commit(self) -> str:
        return get_upstream_info()["commit"]

    def get_runtime_summary(self) -> Dict[str, Any]:
        info = get_upstream_info()
        info["tools"] = {
            "gh": is_tool_available("gh"),
            "yt_dlp": is_tool_available("yt-dlp"),
            "agent_reach": is_tool_available("agent-reach"),
        }
        return info


native_runtime = NativeRuntime()

