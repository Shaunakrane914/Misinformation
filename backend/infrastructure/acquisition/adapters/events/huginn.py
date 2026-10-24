"""
Aegis Protocol — Huginn Continuous Source Monitoring Adapter
============================================================
Provides secure ingestion, deduplication, and raw pool routing for background
events pushed from external Huginn monitoring agents (RSS, Newsroom, Security, Disclosures).

Key Invariants:
1. Non-Replacement: Enhances continuous situational awareness; does not replace
   Aegis's active investigative intelligence agents.
2. Secure Ingestion: Compares a shared bearer token before event parsing.
3. Integrity: Verifies SHA-256 checksums, not signatures or proof of truth.
4. Anti-Amplification Deduplication: Tracks seen content hashes and canonical URLs to
   prevent repeated feed polls or syndicated articles from registering as independent
   corroborating sources.
5. Bounded Storage: Count/byte-bounded records with FIFO retention (not a TTL).
6. Honest Provenance: Distinguishes background event provenance from on-demand deep reads.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.research.source_identity import source_url_key
from backend.services.url_validator import is_safe_url

logger = logging.getLogger(__name__)

HUGINN_WEBHOOK_SECRET_ENV = "HUGINN_WEBHOOK_SECRET"
MAX_STORED_HUGINN_EVENTS = 500
MAX_HUGINN_PAYLOAD_BYTES = 128_000
MAX_HUGINN_CONTENT_BYTES = 100_000
_EVENT_TABLE = "huginn_events_v2"


def _validate_payload(payload):
    """Validate without coercing objects into evidence or silently truncating it."""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_HUGINN_PAYLOAD_BYTES:
        raise ValueError("Monitoring payload too large")
    limits = {
        "source_url": 8192, "url": 8192, "huginn_event_id": 200, "event_id": 200,
        "source_identity": 500, "feed_name": 500, "event_type": 100, "title": 2000,
        "content_text": MAX_HUGINN_CONTENT_BYTES, "content": MAX_HUGINN_CONTENT_BYTES,
        "text": MAX_HUGINN_CONTENT_BYTES, "content_hash": 64, "agent_target": 50,
        "target_entity": 500, "provenance": 200, "retrieved_at": 100,
        "observed_published_at": 100, "published_at": 100, "date": 100,
    }
    for key, limit in limits.items():
        value = payload.get(key)
        if value is not None and (not isinstance(value, str) or len(value.encode("utf-8")) > limit):
            raise ValueError("Invalid or oversized monitoring field: " + key)
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict) or len(json.dumps(metadata).encode("utf-8")) > 8192:
        raise ValueError("Monitoring metadata must be a bounded JSON object")
    # A byte cap alone permits deeply nested inputs that break serializers.
    def bounded_structure(value, depth=0):
        if depth > 6:
            raise ValueError("Monitoring metadata is too deeply nested")
        if isinstance(value, (dict, list)):
            if len(value) > 100:
                raise ValueError("Too many monitoring metadata entries")
            for child in (value.values() if isinstance(value, dict) else value):
                bounded_structure(child, depth + 1)
    bounded_structure(metadata)
    if payload.get("agent_target") not in {None, "", "scout", "trending", "brandshield", "personal_watch"}:
        raise ValueError("Unknown monitoring agent target")
    if payload.get("content_hash") and not re.fullmatch(r"[0-9a-fA-F]{64}", payload["content_hash"]):
        raise ValueError("Invalid monitoring content checksum")
    for key in ("observed_published_at", "published_at", "date", "retrieved_at"):
        if payload.get(key):
            datetime.fromisoformat(payload[key].replace("Z", "+00:00"))
    return payload


@dataclass
class HuginnEvent:
    """Canonical model for continuous monitoring events received from Huginn."""
    huginn_event_id: str
    source_url: str
    source_identity: str
    event_type: str                     # newsroom, financial_disclosure, rss_article, security_advisory, brand_mention
    content_text: str
    retrieved_at: str
    content_hash: str
    provenance: str = "huginn_agent"
    title: str = ""
    observed_published_at: Optional[str] = None
    target_entity: Optional[str] = None
    agent_target: Optional[str] = None  # scout, brandshield, trending, personal_watch
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_duplicate: bool = False
    # Only a later explicit source-independence assessment could establish it.
    independent_confirmation: bool = False
    duplicate_reference: Optional[str] = None

    def __post_init__(self):
        if not self.content_hash and self.content_text:
            self.content_hash = hashlib.sha256(self.content_text.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "huginn_event_id": self.huginn_event_id,
            "source_url": self.source_url,
            "source_identity": self.source_identity,
            "event_type": self.event_type,
            "title": self.title,
            "content_text": self.content_text,
            "content_hash": self.content_hash,
            "observed_published_at": self.observed_published_at,
            "retrieved_at": self.retrieved_at,
            "provenance": self.provenance,
            "target_entity": self.target_entity,
            "agent_target": self.agent_target,
            "is_duplicate": self.is_duplicate,
            "independent_confirmation": self.independent_confirmation,
            "duplicate_reference": self.duplicate_reference,
            "metadata": self.metadata,
        }


class HuginnMonitoringIngestor:
    """
    Thread-safe ingestion manager for background Huginn monitoring streams.
    Enforces secret authentication, bounded capacity, and strict deduplication.
    """

    def __init__(self, max_capacity: int = MAX_STORED_HUGINN_EVENTS, db_path: Optional[str] = None):
        if not isinstance(max_capacity, int) or not 1 <= max_capacity <= MAX_STORED_HUGINN_EVENTS:
            raise ValueError("Invalid monitoring retention capacity")
        self._max_capacity = max_capacity
        self._lock = threading.Lock()
        self._events: Dict[str, HuginnEvent] = {}               # event_id -> HuginnEvent
        self._seen_hashes: Dict[str, str] = {}                  # content_hash -> event_id
        self._seen_urls: Dict[str, str] = {}                    # canonical_url_key -> event_id
        self._event_order: List[str] = []                       # FIFO eviction queue

        # SQLite durable backing
        if db_path is None:
            db_path = os.environ.get("HUGINN_DB_PATH")
            if not db_path:
                # Importing this disabled optional adapter creates no disk data.
                db_path = (str(Path(__file__).resolve().parents[4] / "data" / "huginn_events.db")
                           if os.environ.get("HUGINN_ENABLED", "").lower() == "true" else ":memory:")
        self._db_path = db_path
        self._init_db()
        self._load_from_db()

    def _init_db(self):
        """Initialize SQLite backing table and indexes."""
        if not self._db_path or self._db_path == ":memory:":
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                existed = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                                       (_EVENT_TABLE,)).fetchone()
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS huginn_events_v2 (
                        huginn_event_id TEXT PRIMARY KEY,
                        source_url TEXT NOT NULL,
                        url_key TEXT NOT NULL,
                        source_identity TEXT,
                        event_type TEXT,
                        title TEXT,
                        content_text TEXT,
                        content_hash TEXT NOT NULL,
                        retrieved_at TEXT,
                        observed_published_at TEXT,
                        target_entity TEXT,
                        agent_target TEXT,
                        is_duplicate INTEGER NOT NULL,
                        duplicate_reference TEXT,
                        independent_confirmation INTEGER NOT NULL,
                        provenance TEXT,
                        metadata_json TEXT
                    )
                """)
                # Preserve legacy rows/table. v2 removes hash uniqueness, which
                # previously replaced originals whenever a duplicate arrived.
                legacy = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='huginn_events'").fetchone()
                if not existed and legacy:
                    conn.execute("INSERT OR IGNORE INTO huginn_events_v2 SELECT * FROM huginn_events")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_huginn_v2_url ON huginn_events_v2(url_key)")
                conn.commit()
        except Exception:
            logger.warning("[HuginnIngestor] Could not initialize monitoring storage")

    def _load_from_db(self):
        """Load retained state from SQLite for crash recovery and restart idempotency."""
        if not self._db_path or self._db_path == ":memory:" or not os.path.exists(self._db_path):
            return
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Load newest retained rows, then restore chronological order.
                cursor = conn.execute(
                    "SELECT * FROM huginn_events_v2 ORDER BY rowid DESC LIMIT ?",
                    (self._max_capacity,)
                )
                for row in reversed(cursor.fetchall()):
                    metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
                    evt = HuginnEvent(
                        huginn_event_id=row["huginn_event_id"],
                        source_url=row["source_url"],
                        source_identity=row["source_identity"] or "",
                        event_type=row["event_type"] or "rss_article",
                        content_text=row["content_text"] or "",
                        retrieved_at=row["retrieved_at"] or "",
                        content_hash=row["content_hash"],
                        provenance=row["provenance"] or "huginn_agent",
                        title=row["title"] or "",
                        observed_published_at=row["observed_published_at"],
                        target_entity=row["target_entity"],
                        agent_target=row["agent_target"],
                        metadata=metadata,
                        is_duplicate=bool(row["is_duplicate"]),
                        independent_confirmation=False,
                        duplicate_reference=row["duplicate_reference"],
                    )
                    self._events[evt.huginn_event_id] = evt
                    if evt.huginn_event_id not in self._event_order:
                        self._event_order.append(evt.huginn_event_id)
                self._rebuild_seen()
        except Exception:
            logger.warning("[HuginnIngestor] Could not load monitoring storage")

    def _rebuild_seen(self):
        """Indexes cover retained records only; duplicates keep original lineage."""
        self._seen_hashes.clear()
        self._seen_urls.clear()
        for event_id in self._event_order:
            event = self._events[event_id]
            original = event.duplicate_reference or event_id
            self._seen_hashes.setdefault(event.content_hash, original)
            self._seen_urls.setdefault(source_url_key(event.source_url), original)

    def _save_to_db(self, event: HuginnEvent, url_key: str):
        """Persist an ingested event into SQLite."""
        if not self._db_path or self._db_path == ":memory:":
            return True
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    INSERT INTO huginn_events_v2 (
                        huginn_event_id, source_url, url_key, source_identity, event_type,
                        title, content_text, content_hash, retrieved_at, observed_published_at,
                        target_entity, agent_target, is_duplicate, duplicate_reference,
                        independent_confirmation, provenance, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.huginn_event_id,
                    event.source_url,
                    url_key,
                    event.source_identity,
                    event.event_type,
                    event.title,
                    event.content_text,
                    event.content_hash,
                    event.retrieved_at,
                    event.observed_published_at,
                    event.target_entity,
                    event.agent_target,
                    1 if event.is_duplicate else 0,
                    event.duplicate_reference,
                    1 if event.independent_confirmation else 0,
                    event.provenance,
                    json.dumps(event.metadata),
                ))
                # Bounded retention in DB
                conn.execute("""
                    DELETE FROM huginn_events_v2 WHERE rowid NOT IN (
                        SELECT rowid FROM huginn_events_v2 ORDER BY rowid DESC LIMIT ?
                    )
                """, (self._max_capacity,))
                conn.commit()
            return True
        except Exception:
            logger.warning("[HuginnIngestor] Monitoring storage write failed")
            return False

    def verify_auth(self, provided_secret: Optional[str]) -> bool:
        """
        Verify incoming webhook credentials using constant-time comparison.
        If no secret is configured in the environment, rejects external pushes by default.
        """
        configured_secret = os.environ.get(HUGINN_WEBHOOK_SECRET_ENV, "").strip()
        if not configured_secret:
            logger.warning("[HuginnIngestor] Webhook rejected: HUGINN_WEBHOOK_SECRET not configured")
            return False
        if not isinstance(provided_secret, str) or len(provided_secret) > 1024:
            return False
        # Remove Bearer prefix if present
        clean_secret = provided_secret.removeprefix("Bearer ").strip()
        return hmac.compare_digest(clean_secret.encode("utf-8"), configured_secret.encode("utf-8"))

    def ingest(
        self,
        payload: Dict[str, Any],
        auth_secret: Optional[str] = None,
        bypass_auth_for_testing: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingest, validate, hash, deduplicate, and store a Huginn monitoring event.
        """
        if not bypass_auth_for_testing and not self.verify_auth(auth_secret):
            return {
                "status": "rejected",
                "reason": "AUTHENTICATION_FAILED",
                "message": "Invalid or missing Huginn webhook secret",
            }

        try:
            payload = _validate_payload(payload)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return {"status": "rejected", "reason": "INVALID_PAYLOAD", "message": "Invalid or oversized monitoring payload"}

        source_url = (payload.get("source_url") or payload.get("url") or "").strip()
        if not source_url:
            return {"status": "rejected", "reason": "MISSING_SOURCE_URL", "message": "Source URL required"}

        # Basic URL safety check (no private loopbacks / SSRF vectors)
        safe, reason = is_safe_url(source_url)
        if not safe:
            return {"status": "rejected", "reason": "SSRF_BLOCKED", "message": reason}

        event_id = str(payload.get("huginn_event_id") or payload.get("event_id") or f"huginn_{uuid.uuid4().hex[:10]}")
        source_identity = str(payload.get("source_identity") or payload.get("feed_name") or "generic_huginn_source")
        event_type = str(payload.get("event_type") or "rss_article")
        content_text = str(payload.get("content_text") or payload.get("content") or payload.get("text") or "").strip()
        observed_published = payload.get("observed_published_at") or payload.get("published_at") or payload.get("date")
        retrieved_at = datetime.now(timezone.utc).isoformat()
        title = str(payload.get("title") or "")
        agent_target = payload.get("agent_target")
        target_entity = payload.get("target_entity")

        # A checksum detects a mismatch; it is not a cryptographic signature.
        provided_hash = payload.get("content_hash")
        computed_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
        if provided_hash and provided_hash.lower() != computed_hash.lower():
            return {"status": "rejected", "reason": "CONTENT_HASH_MISMATCH", "message": "Monitoring content checksum mismatch"}

        content_hash = computed_hash
        url_key = source_url_key(source_url)

        with self._lock:
            existing = self._events.get(event_id)
            if existing:
                same = (existing.content_hash == content_hash and source_url_key(existing.source_url) == url_key
                        and existing.title == title and existing.event_type == event_type
                        and existing.source_identity == source_identity and existing.target_entity == target_entity
                        and existing.agent_target == agent_target and existing.observed_published_at == observed_published
                        and existing.metadata == payload.get("metadata", {}))
                if not same:
                    return {"status": "rejected", "reason": "EVENT_ID_CONFLICT", "message": "Monitoring event ID already exists with different content"}
                return {"status": "success", "event_id": event_id, "idempotent": True,
                        "is_duplicate": existing.is_duplicate, "independent_confirmation": False,
                        "duplicate_reference": existing.duplicate_reference, "content_hash": content_hash,
                        "retained_events_count": len(self._events)}
            # Check for deduplication
            is_dup = False
            dup_ref = None
            if content_hash in self._seen_hashes:
                is_dup = True
                dup_ref = self._seen_hashes[content_hash]
            elif url_key in self._seen_urls:
                is_dup = True
                dup_ref = self._seen_urls[url_key]

            # Anti-amplification rule:
            # Duplicate events must NOT provide independent confirmation to agents
            independent = False

            event = HuginnEvent(
                huginn_event_id=event_id,
                source_url=source_url,
                source_identity=source_identity,
                event_type=event_type,
                content_text=content_text,
                retrieved_at=retrieved_at,
                content_hash=content_hash,
                provenance="huginn_agent",
                title=title,
                observed_published_at=observed_published,
                target_entity=target_entity,
                agent_target=agent_target,
                metadata=payload.get("metadata", {}),
                is_duplicate=is_dup,
                independent_confirmation=independent,
                duplicate_reference=dup_ref,
            )

            # Do not acknowledge success if explicit durable storage failed.
            if not self._save_to_db(event, url_key):
                return {"status": "rejected", "reason": "PERSISTENCE_FAILED", "message": "Monitoring storage unavailable"}

            # Evict oldest if capacity reached
            if len(self._events) >= self._max_capacity and self._event_order:
                oldest_id = self._event_order.pop(0)
                self._events.pop(oldest_id, None)

            # Register in memory
            self._events[event_id] = event
            self._event_order.append(event_id)
            self._rebuild_seen()

            return {
                "status": "success",
                "event_id": event_id,
                "is_duplicate": is_dup,
                "independent_confirmation": independent,
                "duplicate_reference": dup_ref,
                "content_hash": content_hash,
                "retained_events_count": len(self._events),
            }

    def get_events(
        self,
        agent_target: Optional[str] = None,
        target_entity: Optional[str] = None,
        limit: int = 50,
    ) -> List[HuginnEvent]:
        """Query retained events filtered by agent or entity."""
        limit = max(0, min(int(limit), self._max_capacity))
        if not limit:
            return []
        with self._lock:
            matched = []
            for eid in reversed(self._event_order):
                evt = self._events.get(eid)
                if not evt:
                    continue
                if agent_target and (not evt.agent_target or evt.agent_target.lower() != agent_target.lower()):
                    continue
                if target_entity and (not evt.target_entity or evt.target_entity.casefold() != target_entity.casefold()):
                    continue
                matched.append(evt)
                if len(matched) >= limit:
                    break
            return matched

    def inject_into_raw_pool(
        self,
        raw_pool: Any,
        agent_target: Optional[str] = None,
        target_entity: Optional[str] = None,
        limit: int = 20,
    ) -> List[str]:
        """
        Inject matching retained Huginn monitoring events directly into an investigation's RawAcquisitionPool.
        Duplicate events preserve duplicate_of markers so they NEVER inflate independent evidence counts.
        """
        events = self.get_events(agent_target=agent_target, target_entity=target_entity, limit=limit)
        # Originals must precede copies when the pool computes canonical body
        # duplicates; newest-first feed presentation is not evidence lineage.
        events.sort(key=lambda evt: evt.is_duplicate)
        added_ids = []
        event_source_ids = {}
        duplicate_ids = []
        for evt in events:
            words = len(evt.content_text.split())
            depth = "FEED_ENTRY_CONTENT" if words >= 30 else "SNIPPET"

            item = {
                "id": f"huginn_{evt.huginn_event_id}",
                "url": evt.source_url,
                "canonical_url": evt.source_url,
                "source_name": evt.source_identity,
                "title": evt.title or f"Huginn Monitoring: {evt.source_identity}",
                "content": evt.content_text,
                "snippet": evt.content_text[:300],
                "published_at": evt.observed_published_at,
                "content_depth": depth,
                "read_status": "SUCCESS",
                "metadata": {
                    "read_success": True,
                    "raw_capture": {
                        "text": evt.content_text,
                        "format": "text",
                        "sha256": evt.content_hash,
                        "source": "huginn_event",
                    },
                    "provenance": evt.provenance,
                    "is_duplicate": evt.is_duplicate,
                    "duplicate_reference": evt.duplicate_reference,
                    "independent_confirmation": evt.independent_confirmation,
                    "target_entity": evt.target_entity,
                    "agent_target": evt.agent_target,
                },
            }
            # Snapshot into raw pool
            source_id = raw_pool.add_capture(item, query_id=f"huginn_{agent_target or 'monitor'}")
            if source_id:
                event_source_ids[evt.huginn_event_id] = source_id
                if evt.is_duplicate:
                    duplicate_ids.append((source_id, evt.duplicate_reference))
                added_ids.append(source_id)
        with getattr(raw_pool, "_lock", threading.Lock()):
            # Complete the batch before annotations; add_capture refreshes exact
            # duplicate hashes and used to erase the marker on every later row.
            for source_id, original in duplicate_ids:
                original_id = event_source_ids.get(original)
                if original_id and original_id != source_id and source_id in raw_pool._sources:
                    raw_pool._sources[source_id]["duplicate_of"] = original_id
                    raw_pool._sources[source_id]["duplicate_reason"] = "HUGINN_DUPLICATE_FEED"
        return added_ids

    def clear(self, clear_db: bool = True):
        """Clear retained events (testing helper)."""
        with self._lock:
            self._events.clear()
            self._seen_hashes.clear()
            self._seen_urls.clear()
            self._event_order.clear()
            if clear_db and self._db_path and self._db_path != ":memory:" and os.path.exists(self._db_path):
                try:
                    with sqlite3.connect(self._db_path) as conn:
                        conn.execute("DELETE FROM huginn_events_v2")
                        conn.commit()
                except Exception as err:
                    logger.debug("[HuginnIngestor] Could not clear DB: %s", err)


# Global singleton instance
huginn_ingestor = HuginnMonitoringIngestor()


class HuginnMonitoringAdapter(PlatformAdapter):
    """
    Platform adapter interfacing Huginn background streams with Aegis's acquisition fabric.
    Allows agents to inspect background feed events as EvidenceFragments.
    """

    def __init__(self, ingestor: Optional[HuginnMonitoringIngestor] = None):
        self._ingestor = ingestor or huginn_ingestor

    @property
    def platform(self) -> str:
        return "huginn_events"

    @property
    def backend_id(self) -> str:
        return "huginn-stream"

    def can_handle(self, candidate: CandidateSource) -> bool:
        return candidate.platform == "huginn_events"

    def health(self) -> Dict[str, Any]:
        has_secret = bool(os.environ.get(HUGINN_WEBHOOK_SECRET_ENV))
        return {
            "platform": self.platform,
            "backend_id": self.backend_id,
            "status": "AVAILABLE" if has_secret else "AUTH_REQUIRED",
            "auth_configured": has_secret,
            "retained_events": len(self._ingestor._events),
            "cloud_safe": True,
        }

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Retrieve stored event from ingestor."""
        event_id = candidate.metadata.get("huginn_event_id")
        evt = self._ingestor._events.get(event_id)
        if not evt:
            return FetchedDocument(
                url=candidate.url,
                status="FAILED",
                backend_id=self.backend_id,
                failure_reason="EVENT_NOT_FOUND_IN_BUFFER",
            )

        return FetchedDocument(
            url=evt.source_url,
            status="SUCCESS",
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.RSS_FEED.value,
            raw_content=evt.content_text,
            raw_metadata={
                "huginn_event_id": evt.huginn_event_id,
                "source_identity": evt.source_identity,
                "event_type": evt.event_type,
                "content_hash": evt.content_hash,
                "is_duplicate": evt.is_duplicate,
                "independent_confirmation": False,
                "observed_published_at": evt.observed_published_at,
            },
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize event document into canonical EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        meta = document.raw_metadata or {}
        frag = EvidenceFragment(
            platform=self.platform,
            title=candidate.title or f"Huginn Event: {meta.get('source_identity', 'Source')}",
            content=document.raw_content,
            snippet=document.raw_content[:400],
            url=document.url,
            published=meta.get("observed_published_at") or "",
            score=30.0,
            retrieval_method="huginn_event_stream",
            retrieval_mode=RetrievalMode.RSS_FEED.value,
            native_backend_id=self.backend_id,
            channel_name="rss",
            actual_retrieval_channel="huginn",
            content_depth="FEED_ENTRY_CONTENT",
            query_id=request.query or "",
            raw_metadata={
                "source_role": "BACKGROUND_MONITORING",
                "canonical_url": document.url,
                "content_hash": meta.get("content_hash"),
                "is_duplicate": meta.get("is_duplicate", False),
                "independent_confirmation": False,
                "backend": self.backend_id,
            },
        )
        return [frag]
