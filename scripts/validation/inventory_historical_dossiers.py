"""Build a read-only recovery inventory for malformed historical dossiers.

The inventory records hashes and parser diagnostics without copying dossier
contents. Candidate files and Git blobs are leads for an owner-controlled
recovery review; they are never treated as trusted backups automatically.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = REPO_ROOT / "backend" / "data" / "dossiers"
EXCLUDED_DIRECTORY_NAMES = {
    ".git", ".pytest_cache", ".venv", "__pycache__", "node_modules", "venv",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _json_status(data: bytes) -> dict[str, Any]:
    try:
        json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as error:
        return {
            "status": "MALFORMED",
            "error_type": type(error).__name__,
            "byte_start": error.start,
            "byte_end": error.end,
            "reason": error.reason,
        }
    except json.JSONDecodeError as error:
        return {
            "status": "MALFORMED",
            "error_type": type(error).__name__,
            "line": error.lineno,
            "column": error.colno,
            "character_offset": error.pos,
            "reason": error.msg,
        }
    return {"status": "VALID_JSON"}


def _archive_snapshot(archive: Path) -> dict[str, str]:
    return {
        path.name: _sha256(path.read_bytes())
        for path in sorted(archive.glob("*.json"), key=lambda item: item.name)
    }


def _candidate_files(roots: Iterable[Path], archive: Path) -> Iterable[Path]:
    archive_resolved = archive.resolve()
    seen: set[Path] = set()
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen or archive_resolved in resolved.parents:
                continue
            if EXCLUDED_DIRECTORY_NAMES.intersection(resolved.parts):
                continue
            seen.add(resolved)
            yield resolved


def _filesystem_candidates(
    malformed: list[dict[str, Any]], roots: Iterable[Path], archive: Path
) -> dict[str, list[dict[str, Any]]]:
    by_name = {entry["filename"]: entry for entry in malformed}
    by_size: dict[int, list[dict[str, Any]]] = {}
    for entry in malformed:
        by_size.setdefault(entry["size_bytes"], []).append(entry)
    found = {entry["filename"]: [] for entry in malformed}
    for path in _candidate_files(roots, archive):
        try:
            size = path.stat().st_size
            name_match = by_name.get(path.name)
            possible_hash_matches = by_size.get(size, [])
            if name_match is None and not possible_hash_matches:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        digest = _sha256(data)
        matches = list(possible_hash_matches)
        if name_match is not None and name_match not in matches:
            matches.append(name_match)
        for entry in matches:
            same_name = path.name == entry["filename"]
            same_hash = digest == entry["sha256"]
            if not same_name and not same_hash:
                continue
            found[entry["filename"]].append({
                "kind": "filesystem",
                "path": _portable_path(path),
                "sha256": digest,
                "same_basename": same_name,
                "same_bytes": same_hash,
                **_json_status(data),
            })
    return found


def _git_history_candidates(entry: dict[str, Any], history_limit: int) -> list[dict[str, Any]]:
    source = REPO_ROOT / entry["path"]
    try:
        relative = source.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return []
    try:
        history = subprocess.run(
            ["git", "log", "--all", "--format=%H", "--follow", "--", relative],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if history.returncode != 0:
        return []
    candidates = []
    seen_blobs: set[str] = set()
    for commit in history.stdout.splitlines()[:history_limit]:
        spec = f"{commit}:{relative}"
        try:
            blob = subprocess.run(
                ["git", "rev-parse", spec], cwd=REPO_ROOT, check=False,
                capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            blob_id = blob.stdout.strip()
            if blob.returncode != 0 or not blob_id or blob_id in seen_blobs:
                continue
            content = subprocess.run(
                ["git", "show", spec], cwd=REPO_ROOT, check=False,
                capture_output=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if content.returncode != 0:
            continue
        seen_blobs.add(blob_id)
        data = content.stdout
        candidates.append({
            "kind": "git_history",
            "commit": commit,
            "blob": blob_id,
            "sha256": _sha256(data),
            "same_bytes": _sha256(data) == entry["sha256"],
            **_json_status(data),
        })
    return candidates


def inventory_archive(
    archive: Path = DEFAULT_ARCHIVE,
    candidate_roots: Iterable[Path] = (),
    include_git_history: bool = False,
    history_limit: int = 50,
) -> dict[str, Any]:
    """Inspect an archive without writing to it or importing application state."""
    archive = archive.resolve()
    if not archive.is_dir():
        raise FileNotFoundError(f"Dossier archive is not a directory: {archive}")
    before = _archive_snapshot(archive)
    malformed = []
    for filename, digest in before.items():
        path = archive / filename
        data = path.read_bytes()
        status = _json_status(data)
        if status["status"] == "MALFORMED":
            malformed.append({
                "filename": filename,
                "path": _portable_path(path),
                "sha256": digest,
                "size_bytes": len(data),
                **status,
            })

    roots = [Path(root).resolve() for root in candidate_roots]
    filesystem = _filesystem_candidates(malformed, roots, archive)
    valid_candidate_count = 0
    for entry in malformed:
        candidates = filesystem[entry["filename"]]
        if include_git_history:
            candidates.extend(_git_history_candidates(entry, history_limit))
        candidates.sort(key=lambda item: (
            item["kind"], item.get("path", ""), item.get("commit", "")
        ))
        entry["recovery_candidates"] = candidates
        entry["valid_candidate_count"] = sum(
            candidate["status"] == "VALID_JSON" for candidate in candidates
        )
        valid_candidate_count += entry["valid_candidate_count"]

    after = _archive_snapshot(archive)
    if before != after:
        raise RuntimeError("Historical dossier archive changed during read-only inventory")
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": _portable_path(archive),
        "status": "RECOVERY_ASSESSMENT_REQUIRED" if malformed else "PASS",
        "summary": {
            "total_json_files": len(before),
            "valid_json_files": len(before) - len(malformed),
            "malformed_json_files": len(malformed),
            "valid_recovery_candidates": valid_candidate_count,
            "archive_bytes_unchanged": True,
        },
        "candidate_roots": [_portable_path(root) for root in roots],
        "git_history_examined": include_git_history,
        "disclosure": (
            "Candidates are path/hash leads only. Validate provenance and owner approval "
            "before recovery; never overwrite, repair, or synthesize protected originals."
        ),
        "malformed_files": malformed,
    }


def _write_exclusively(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, indent=2, ensure_ascii=False)
        output.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument(
        "--candidate-root", type=Path, action="append", default=[],
        help="Search a directory read-only for same-name or same-byte JSON candidates",
    )
    parser.add_argument("--include-git-history", action="store_true")
    parser.add_argument("--history-limit", type=int, default=50)
    parser.add_argument("--output", type=Path, help="Create a new JSON report; never overwrite")
    parser.add_argument("--fail-on-invalid", action="store_true")
    args = parser.parse_args(argv)
    if args.history_limit < 1:
        parser.error("--history-limit must be positive")
    report = inventory_archive(
        archive=args.archive,
        candidate_roots=args.candidate_root,
        include_git_history=args.include_git_history,
        history_limit=args.history_limit,
    )
    if args.output:
        _write_exclusively(args.output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.fail_on_invalid and report["summary"]["malformed_json_files"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
