"""
Aegis Protocol — Research Replay Dossier & Provenance Ledger
=============================================================
Stores and re-executes deterministic research traces under immutable IDs (R-2026-XXXX).
Captures SHA-256 candidate content hashes, the decision ledger (why sources were selected
or rejected), primary source escalations, and the exact query sequence for auditable replay.
"""

import hashlib
import json
import logging
import os
import re
import secrets
import tempfile
from copy import deepcopy
from pathlib import Path
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DOSSIER_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dossiers")
DOSSIER_ID = re.compile(r"R-\d{4}-[A-Za-z0-9_-]{1,64}\Z", re.ASCII)


def _payload_hash(data: Dict[str, Any]) -> str:
    payload = {key: value for key, value in data.items() if key != "integrity"}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_dossier_structure(data: Any) -> None:
    """Validate traversed record shapes before treating a legacy trace as readable.

    Older dossiers may omit modern fields, but provided containers and their
    entries must have the documented types. Errors name fields, never contents.
    """
    if not isinstance(data, dict):
        raise ValueError("Dossier must be an object")

    def object_value(value: Any, path: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        return value

    def object_list(value: Any, path: str) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            raise ValueError(f"{path} must be a list")
        for index, entry in enumerate(value):
            object_value(entry, f"{path}[{index}]")
        return value

    def text_fields(record: Dict[str, Any], path: str, fields: List[str]) -> None:
        for field_name in fields:
            value = record.get(field_name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{path}.{field_name} must be text or null")

    def string_list(value: Any, path: str) -> None:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"{path} must be a list of strings")

    text_fields(data, "dossier", ["session_id", "target", "domain", "created_at", "summary", "status"])
    queries = object_list(data.get("queries_executed", []), "queries_executed")
    for index, query in enumerate(queries):
        text_fields(query, f"queries_executed[{index}]", ["channel", "query_text"])
    decisions = object_list(data.get("decision_log", []), "decision_log")
    for index, decision in enumerate(decisions):
        path = f"decision_log[{index}]"
        text_fields(decision, path, ["stage", "decision_type", "rationale", "entity_or_query"])
        if "evidence_ids_affected" in decision:
            string_list(decision["evidence_ids_affected"], f"{path}.evidence_ids_affected")

    hashes = object_value(data.get("candidate_hashes", {}), "candidate_hashes")
    for candidate_id, digest in hashes.items():
        if (not isinstance(candidate_id, str) or not candidate_id
                or not isinstance(digest, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{16}|[0-9a-fA-F]{64})", digest)):
            raise ValueError("candidate_hashes must map nonempty string IDs to 16/64-character hexadecimal hashes")
    snapshots = object_value(data.get("candidate_snapshots", {}), "candidate_snapshots")
    for candidate_id, snapshot in snapshots.items():
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate_snapshots keys must be nonempty strings")
        snapshot = object_value(snapshot, "candidate_snapshots entry")
        if not isinstance(snapshot.get("content"), str):
            raise ValueError("candidate_snapshots content must be text")
        if not isinstance(snapshot.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot["sha256"]):
            raise ValueError("candidate_snapshots sha256 must be a hexadecimal SHA-256 digest")

    lineage = object_value(data.get("source_lineage", {}), "source_lineage")
    nodes = object_list(lineage.get("nodes", []), "source_lineage.nodes")
    for index, node in enumerate(nodes):
        text_fields(node, f"source_lineage.nodes[{index}]", ["id", "url"])
    object_list(lineage.get("edges", []), "source_lineage.edges")
    object_value(lineage.get("metrics", {}), "source_lineage.metrics")

    findings = object_list(data.get("findings_provenance", []), "findings_provenance")
    for index, finding in enumerate(findings):
        path = f"findings_provenance[{index}]"
        text_fields(finding, path, ["finding_id", "title", "epistemic_state"])
        for field_name in ("primary_sources", "supporting_evidence_ids", "contradicting_evidence_ids"):
            if field_name in finding:
                string_list(finding[field_name], f"{path}.{field_name}")
        if finding.get("quality_tensor") is not None:
            object_value(finding["quality_tensor"], f"{path}.quality_tensor")

    saturation = object_value(data.get("saturation_summary", {}), "saturation_summary")
    if "saturation_curve" in saturation:
        object_list(saturation["saturation_curve"], "saturation_summary.saturation_curve")
    object_list(data.get("capability_graph", []), "capability_graph")
    if data.get("integrity") is not None:
        object_value(data["integrity"], "integrity")


def verify_dossier_integrity(data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify new snapshots/checksums without pretending legacy traces are sealed.

    Checksums detect drift; they do not authenticate a writer or prove that
    external statements are true. Historical JSON records are never rewritten.
    """
    try:
        _validate_dossier_structure(data)
    except ValueError as error:
        return {"status": "FAILED", "valid": False, "reason": str(error)}
    manifest = data.get("integrity")
    if manifest is None:
        return {"status": "LEGACY_UNSEALED", "valid": False,
                "reason": "Historical dossier has no verifiable integrity manifest"}
    try:
        expected = manifest["payload_sha256"]
        if (manifest.get("version") != 1 or manifest.get("algorithm") != "sha256"
                or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or not secrets.compare_digest(expected, _payload_hash(data))):
            raise ValueError("Dossier payload checksum mismatch")
        snapshots = data["candidate_snapshots"]
        hashes = data["candidate_hashes"]
        if set(snapshots) != set(hashes):
            raise ValueError("Candidate snapshot/hash membership mismatch")
        for candidate_id, snapshot in snapshots.items():
            digest = hashlib.sha256(snapshot["content"].encode("utf-8")).hexdigest()
            if not secrets.compare_digest(digest, snapshot["sha256"]):
                raise ValueError("Candidate content checksum mismatch")
            legacy_hash = hashes[candidate_id]
            if not isinstance(legacy_hash, str) or len(legacy_hash) not in (16, 64):
                raise ValueError("Invalid candidate content hash")
            if not secrets.compare_digest(digest[:len(legacy_hash)], legacy_hash):
                raise ValueError("Candidate content/hash mismatch")
    except (KeyError, TypeError, AttributeError, ValueError, UnicodeError) as error:
        return {"status": "FAILED", "valid": False, "reason": str(error)}
    return {"status": "VERIFIED", "valid": True, "reason": "Payload and captured candidate checksums match"}


@dataclass(slots=True)
class DecisionRecord:
    """An explicit automated investigative decision taken during research."""
    timestamp: float
    stage: str
    decision_type: str  # DEDUPLICATION | PRIMARY_ESCALATION | ADAPTIVE_QUERY | DEEP_READ_SELECTION | SATURATION_HALT
    entity_or_query: str
    rationale: str
    evidence_ids_affected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 3),
            "stage": self.stage,
            "decision_type": self.decision_type,
            "entity_or_query": self.entity_or_query,
            "rationale": self.rationale,
            "evidence_ids_affected": self.evidence_ids_affected,
        }


@dataclass
class ResearchDossier:
    """Immutable, reproducible record of an intelligence investigation."""
    session_id: str  # Format: R-2026-XXXXX
    target: str
    domain: str
    created_at: str
    latency_ms: int
    summary: str
    queries_executed: List[Dict[str, Any]]
    candidate_hashes: Dict[str, str]  # ev_id -> sha256
    decision_log: List[Dict[str, Any]]
    findings_provenance: List[Dict[str, Any]]
    source_lineage: Dict[str, Any]
    saturation_summary: Dict[str, Any]
    capability_graph: List[Dict[str, Any]]
    status: str = "COMPLETED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReplayLedger:
    """
    Persistent ledger storing and replaying research dossiers.

    Each investigation is assigned a canonical session ID in the format
    ``R-<YEAR>-<32HEX>``. Existing shorter historical IDs remain readable.

    Storage Strategy
    ----------------
    - **In-memory cache** (``_memory_cache``): O(1) retrieval for recently
      recorded dossiers within the same process lifetime.
    - **Disk persistence** (``storage_dir``): JSON files written atomically;
      ignored by git via ``.gitignore`` to keep the repository clean.

    Thread Safety
    -------------
    The in-memory cache is a plain ``dict`` — safe for single-threaded async
    use. Under true multi-process deployments, rely on disk files as the
    authoritative source of truth.
    """

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir: str = storage_dir or os.getenv("AEGIS_DOSSIER_DIR") or DOSSIER_STORAGE_DIR
        os.makedirs(self.storage_dir, exist_ok=True)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def _generate_dossier_id(self, target: str) -> str:
        """Create collision-resistant research dossier IDs, retaining the prefix."""
        year = time.strftime("%Y")
        full_uuid = uuid.uuid4().hex.upper()
        return f"R-{year}-{full_uuid}"

    def _dossier_path(self, session_id: str) -> Optional[Path]:
        if not isinstance(session_id, str) or not DOSSIER_ID.fullmatch(session_id):
            return None
        storage = Path(self.storage_dir).resolve()
        path = (storage / f"{session_id}.json").resolve()
        # Also reject existing symlinks targeting files outside the storage root.
        return path if path.parent == storage else None

    def record_investigation(
        self,
        target: str,
        domain: str,
        summary: str,
        candidates: List[Any],
        findings: List[Any],
        queries: List[Dict[str, Any]],
        telemetry: Dict[str, Any],
        lineage_graph: Dict[str, Any],
    ) -> str:
        """Compile and persist an immutable research dossier."""
        dossier_id = self._generate_dossier_id(target)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # 1. Compute candidate content SHA-256 hashes
        candidate_hashes = {}
        candidate_snapshots = {}
        for c in candidates:
            c_dict = c if isinstance(c, dict) else {}
            c_id = getattr(c, "id", None) or c_dict.get("id", "ev_unknown")
            text_to_hash = (getattr(c, "snippet", "") or c_dict.get("snippet")
                            or getattr(c, "content", "") or c_dict.get("content") or str(c))
            text_to_hash = str(text_to_hash).encode("utf-8", errors="replace").decode("utf-8")
            digest = hashlib.sha256(text_to_hash.encode("utf-8")).hexdigest()
            # Retain legacy hash field for old readers; new manifests verify the
            # complete SHA-256 against the exact captured text, not a live page.
            candidate_hashes[c_id] = digest[:16]
            candidate_snapshots[c_id] = {"content": text_to_hash, "sha256": digest}

        # 2. Build decision log from telemetry & lineage
        decision_log = []
        # Query planning decision
        decision_log.append(DecisionRecord(
            timestamp=time.time(),
            stage="QueryPlanning",
            decision_type="QUERY_GENERATION",
            entity_or_query=target,
            rationale=f"Generated {len(queries)} multi-channel targeted queries for domain '{domain}'.",
            evidence_ids_affected=[]
        ).to_dict())

        # Lineage deduplication decisions
        echo_count = lineage_graph.get("metrics", {}).get("echo_count", 0)
        if echo_count > 0:
            decision_log.append(DecisionRecord(
                timestamp=time.time(),
                stage="SourceLineage",
                decision_type="DEDUPLICATION",
                entity_or_query=f"{echo_count} syndicated echo(es)",
                rationale="Collapsed downstream republished wire dispatches into their primary source parent node.",
                evidence_ids_affected=[n.get("id") for n in lineage_graph.get("nodes", []) if n.get("citation_depth", 0) > 1]
            ).to_dict())

        # Saturation decision
        sat = telemetry.get("saturation", {})
        if sat.get("is_saturated"):
            decision_log.append(DecisionRecord(
                timestamp=time.time(),
                stage="EvidenceSaturation",
                decision_type="SATURATION_HALT",
                entity_or_query=target,
                rationale=sat.get("halt_reason", "Evidence novelty saturation reached."),
                evidence_ids_affected=[]
            ).to_dict())

        # 3. Compile findings provenance
        findings_prov = []
        for f in findings:
            f_dict = f.to_dict() if hasattr(f, "to_dict") else f
            findings_prov.append({
                "finding_id": f_dict.get("finding_id"),
                "title": f_dict.get("title"),
                "epistemic_state": f_dict.get("epistemic_state", "SUPPORTED"),
                "quality_tensor": f_dict.get("quality_tensor", {}),
                "supporting_evidence_ids": f_dict.get("supporting_evidence_ids", []),
                "contradicting_evidence_ids": f_dict.get("contradicting_evidence_ids", []),
                "primary_sources": f_dict.get("primary_sources", []),
            })

        # 4. Construct complete dossier
        dossier = ResearchDossier(
            session_id=dossier_id,
            target=target,
            domain=domain,
            created_at=now_iso,
            latency_ms=telemetry.get("total_latency_ms", 0),
            summary=summary,
            queries_executed=queries,
            candidate_hashes=candidate_hashes,
            decision_log=decision_log,
            findings_provenance=findings_prov,
            source_lineage=lineage_graph,
            saturation_summary=sat,
            capability_graph=telemetry.get("execution_graph", []),
        )

        dossier_data = dossier.to_dict()
        dossier_data["status"] = telemetry.get("acquisition", {}).get("status", "COMPLETED")
        dossier_data["acquisition"] = telemetry.get("acquisition", {})
        dossier_data["timing"] = {key: telemetry.get(key, {}) for key in
                                  ("stage_timings_ms", "budget_observations", "acquisition_timing", "pre_research_timings_ms")}
        dossier_data["candidate_snapshots"] = candidate_snapshots
        _validate_dossier_structure(dossier_data)
        # Publish a complete file atomically without replacing any existing ID.
        temporary_path = None
        try:
            for _ in range(8):
                file_path = self._dossier_path(dossier_id)
                if file_path is None:
                    raise ValueError("Invalid generated dossier ID")
                dossier_data["session_id"] = dossier_id
                dossier_data["integrity"] = {"version": 1, "algorithm": "sha256",
                                             "payload_sha256": _payload_hash(dossier_data)}
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.storage_dir,
                                                 prefix=".dossier-", suffix=".tmp", delete=False) as fp:
                    temporary_path = fp.name
                    json.dump(dossier_data, fp, indent=2, allow_nan=False)
                    fp.flush()
                    os.fsync(fp.fileno())
                try:
                    os.link(temporary_path, file_path)
                except FileExistsError:
                    os.unlink(temporary_path)
                    temporary_path = None
                    dossier_id = self._generate_dossier_id(target)
                    continue
                self._memory_cache[dossier_id] = deepcopy(dossier_data)
                logger.info("[ReplayLedger] Saved research dossier '%s'", dossier_id)
                return dossier_id
            raise FileExistsError("Could not allocate an unused dossier ID")
        finally:
            if temporary_path is not None:
                os.unlink(temporary_path)

    def get_dossier(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored dossier by its R-YYYY-XXXX ID."""
        file_path = self._dossier_path(session_id)
        if file_path is None:
            return None
        if session_id in self._memory_cache:
            return deepcopy(self._memory_cache[session_id])

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    if not isinstance(data, dict) or data.get("session_id") != session_id:
                        return None
                    self._memory_cache[session_id] = data
                    return deepcopy(data)
            except Exception as e:
                logger.error(f"[ReplayLedger] Failed loading dossier {session_id}: {e}")

        return None

    def list_recent_dossiers(self, limit: int = 15) -> List[Dict[str, Any]]:
        """List recently executed research dossiers."""
        summaries = []
        # Check disk
        if os.path.exists(self.storage_dir):
            files = sorted(
                [f for f in os.listdir(self.storage_dir) if f.endswith(".json")],
                key=lambda f: os.path.getmtime(os.path.join(self.storage_dir, f)),
                reverse=True
            )
            for f in files[:limit]:
                sid = f.replace(".json", "")
                d = self.get_dossier(sid)
                if d:
                    summaries.append({
                        "session_id": d["session_id"],
                        "target": d["target"],
                        "domain": d["domain"],
                        "created_at": d["created_at"],
                        "latency_ms": d["latency_ms"],
                        "findings_count": len(d.get("findings_provenance", [])),
                        "saturated": d.get("saturation_summary", {}).get("is_saturated", False),
                    })
        return summaries

    list_dossiers = list_recent_dossiers


    def replay_investigation(self, session_id: str, mode: str = "trace_playback") -> Dict[str, Any]:
        """
        Replay an investigation step-by-step to verify determinism and provenance.

        Modes:
        - 'trace_playback': Reconstructs stored trace, verifies hashes and structural integrity without live network requests.
        - 'refetch_verification': Re-fetches source URLs using agent_reach_service.read, recomputes SHA-256 hashes, and compares against stored hashes.
        """
        dossier = self.get_dossier(session_id)
        if not dossier:
            return {"status": "error", "error": f"Dossier {session_id} not found"}

        norm_mode = mode.lower().strip()
        if norm_mode not in ("trace_playback", "refetch_verification"):
            norm_mode = "trace_playback"

        integrity = verify_dossier_integrity(dossier)
        if integrity["status"] == "FAILED":
            return {
                "status": "failed", "session_id": session_id,
                "replay_mode": norm_mode, "integrity_status": "FAILED",
                "integrity_check": integrity, "error": "Dossier integrity or structure validation failed",
                "deterministic_reproducibility": "UNVERIFIED_TRACE_PLAYBACK",
                "total_queries_replayed": 0, "queries_replayed": 0,
                "candidates_integrity_verified": 0, "findings_verified": 0,
                "sources_checked": 0, "hash_matches": 0,
                "playback_steps": [], "verification_details": [],
            }

        if norm_mode == "trace_playback":
            verified = integrity["valid"]
            replay_steps = []
            # Step 1: Query Execution Sequence
            for idx, q in enumerate(dossier.get("queries_executed", [])):
                replay_steps.append({
                    "step_number": idx + 1,
                    "type": "QUERY_EXECUTION",
                    "channel": q.get("channel", "web"),
                    "query_text": q.get("query_text", ""),
                    "verified": verified,
                })

            # Step 2: Evidence Verification via Hash Check
            candidate_hashes = dossier.get("candidate_hashes", {})
            verified_candidates = len(candidate_hashes) if verified else 0

            # Step 3: Decision Ledger Playback
            for d in dossier.get("decision_log", []):
                replay_steps.append({
                    "step_number": len(replay_steps) + 1,
                    "type": "DECISION_CHECKPOINT",
                    "stage": d.get("stage"),
                    "rationale": d.get("rationale"),
                    "decision_type": d.get("decision_type"),
                })

            return {
                "status": "success",
                "session_id": session_id,
                "target": dossier.get("target"),
                "domain": dossier.get("domain"),
                "replayed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "replay_mode": "trace_playback",
                "integrity_status": "TRACE_VERIFIED" if verified else integrity["status"],
                "integrity_check": integrity,
                "deterministic_reproducibility": "CHECKSUM_VERIFIED_TRACE_PLAYBACK" if verified else "UNVERIFIED_TRACE_PLAYBACK",
                "total_queries_replayed": len(dossier.get("queries_executed", [])),
                "candidates_integrity_verified": verified_candidates,
                "findings_verified": len(dossier.get("findings_provenance", [])) if verified else 0,
                "playback_steps": replay_steps,
                "audit_disclosure": "Replay checks captured content and payload checksums when available. Historical unsealed dossiers remain unverified. Checksums do not authenticate writers or establish external truth; no live sources are queried.",
            }

        # ── Refetch Verification Mode ──
        from backend.services.agent_reach import agent_reach_service

        candidate_hashes = dossier.get("candidate_hashes", {})
        queries_executed = dossier.get("queries_executed", [])
        sources_checked = 0
        hash_matches = 0
        content_changed = 0
        unavailable = 0
        auth_required = 0

        verification_details = []

        candidate_urls: Dict[str, str] = {}
        for node in dossier.get("source_lineage", {}).get("nodes", []):
            if node.get("id") and node.get("url"):
                candidate_urls[node["id"]] = node["url"]

        for fnd in dossier.get("findings_provenance", []):
            for p_url in fnd.get("primary_sources", []):
                if p_url and p_url.startswith("http"):
                    candidate_urls[f"prim_{hashlib.md5(p_url.encode()).hexdigest()[:8]}"] = p_url

        items_to_check = list(candidate_hashes.items())[:10]
        for ev_id, orig_hash in items_to_check:
            sources_checked += 1
            url = candidate_urls.get(ev_id)
            if not url or not url.startswith("http"):
                unavailable += 1
                verification_details.append({
                    "evidence_id": ev_id,
                    "url": url or "unavailable",
                    "status": "SOURCE_UNAVAILABLE",
                    "original_hash": orig_hash,
                    "refetched_hash": None,
                })
                continue

            try:
                read_res = agent_reach_service.read(url, max_chars=2500)
                st = read_res.get("status")
                if st == "blocked_ssrf":
                    unavailable += 1
                    verification_details.append({
                        "evidence_id": ev_id,
                        "url": url,
                        "status": "BLOCKED_SSRF",
                        "original_hash": orig_hash,
                        "refetched_hash": None,
                    })
                elif "auth" in str(read_res.get("error", "")).lower() or st == "auth_required":
                    auth_required += 1
                    verification_details.append({
                        "evidence_id": ev_id,
                        "url": url,
                        "status": "AUTH_REQUIRED",
                        "original_hash": orig_hash,
                        "refetched_hash": None,
                    })
                elif st in ("success", "fallback_soup") and read_res.get("markdown"):
                    content = read_res["markdown"].strip()
                    refetched_hash = hashlib.sha256(content[:300].encode("utf-8", errors="ignore")).hexdigest()[:16]
                    if refetched_hash == orig_hash or orig_hash in hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()[:16]:
                        hash_matches += 1
                        v_st = "MATCH"
                    else:
                        content_changed += 1
                        v_st = "CONTENT_CHANGED"

                    verification_details.append({
                        "evidence_id": ev_id,
                        "url": url,
                        "status": v_st,
                        "original_hash": orig_hash,
                        "refetched_hash": refetched_hash,
                    })
                else:
                    unavailable += 1
                    verification_details.append({
                        "evidence_id": ev_id,
                        "url": url,
                        "status": "SOURCE_UNAVAILABLE",
                        "original_hash": orig_hash,
                        "refetched_hash": None,
                    })
            except Exception as e_rf:
                unavailable += 1
                verification_details.append({
                    "evidence_id": ev_id,
                    "url": url,
                    "status": "FETCH_ERROR",
                    "error": str(e_rf),
                    "original_hash": orig_hash,
                    "refetched_hash": None,
                })

        if sources_checked == 0:
            overall_status = "NO_SOURCES_TO_CHECK"
        elif hash_matches == sources_checked:
            overall_status = "REPRODUCED_MATCH"
        elif hash_matches > 0 and (content_changed > 0 or unavailable > 0 or auth_required > 0):
            overall_status = "REPLAY_PARTIAL"
        elif content_changed > 0:
            overall_status = "CONTENT_CHANGED"
        elif auth_required > 0:
            overall_status = "AUTH_REQUIRED"
        else:
            overall_status = "SOURCE_UNAVAILABLE"

        return {
            "status": "success",
            "session_id": session_id,
            "target": dossier.get("target"),
            "domain": dossier.get("domain"),
            "replayed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "replay_mode": "refetch_verification",
            "integrity_status": overall_status,
            "queries_replayed": len(queries_executed),
            "sources_checked": sources_checked,
            "hash_matches": hash_matches,
            "content_changed": content_changed,
            "unavailable": unavailable,
            "auth_required": auth_required,
            "verification_details": verification_details,
            "audit_disclosure": f"Refetch verification re-queried {sources_checked} source URLs live. Result: {hash_matches} matched, {content_changed} modified, {unavailable} unavailable, {auth_required} auth required.",
        }


# Global singleton ledger
replay_ledger = ReplayLedger()
