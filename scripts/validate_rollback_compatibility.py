#!/usr/bin/env python3
"""Compatibility wrapper redirecting to scripts.validation.validate_rollback_compatibility."""
import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scripts.validation.validate_rollback_compatibility import main

if __name__ == "__main__":
    sys.exit(main())
