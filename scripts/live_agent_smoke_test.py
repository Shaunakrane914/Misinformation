#!/usr/bin/env python3
"""Compatibility wrapper redirecting to scripts.validation.live_agent_smoke_test."""
import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scripts.validation.live_agent_smoke_test import (
    main,
    run_live_smoke_suite,
    sanitize_artifact_data,
    verify_brandshield_live,
    verify_trending_live,
    verify_scout_live,
    verify_personal_watch_live,
)

if __name__ == "__main__":
    sys.exit(main())
