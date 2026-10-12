"""Verify frozen research bytes (allow only Git's cross-platform CRLF conversion)."""

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SHA256 = {
    "candidates.jsonl": "1af58780d8eb4d54b19926bfcdda8a9567690221a859a5a96561bcf03030eafb",
    "labels.jsonl": "1e87f340ed33db6390aa87dd734cfd717d9f3e498ac07c5b557d0c5568929376",
    "scenarios.jsonl": "b2219696a97060896f8e4b04a3dd88e528380f1b3e181ab6974166700fc2f71e",
}


def verify_frozen_benchmarks(root: Path = REPO_ROOT) -> None:
    for filename, expected in FROZEN_SHA256.items():
        path = root / "tests" / "retrieval_benchmark" / filename
        observed = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if observed != expected:
            raise ValueError(f"Frozen benchmark changed: {filename}")


if __name__ == "__main__":
    verify_frozen_benchmarks()
    print("Frozen benchmark content hashes verified")
