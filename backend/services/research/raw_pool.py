"""Bounded acquisition snapshots before evidence qualification.

This is a source buffer, not a verdict engine. Discovery snippets never become
readable bodies, source-type labels never establish ownership or claim support,
and publisher counts never establish source independence. Default use is entirely
in memory. Persistence is explicit, atomic and restricted to an owned new temp
directory; loading/reprocessing makes no network or model calls.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from backend.schemas.evidence_inspection import METADATA_DEPTHS
from backend.services.research.content_roles import document_role
from backend.services.research.source_identity import source_url_key


SCHEMA_VERSION = "raw-acquisition-pool-v1"
MAX_POOL_BYTES = 20_000_000
MAX_SOURCE_BYTES = 1_000_000
MAX_RECORDS = 500
_PREFIX = "aegis-raw-pool-"
_SENSITIVE = re.compile(r"(?:token|api[_-]?key|secret|password|authorization|cookie|signature|credential)", re.I)
_BODY_TYPES = {"ARTICLE_BODY", "OFFICIAL_DOCUMENT", "COMMUNITY_POST", "STRUCTURED_PUBLIC_DATA"}
_ROUTING_TASKS = {"COUNTERFEIT", "PHISHING", "COMPLAINT", "PRODUCT_SAFETY", "PUBLIC_STATEMENT",
                  "FALSE_QUOTE", "IMPERSONATION", "DEEPFAKE", "BRAND_ABUSE", "IDENTITY_THREAT"}


def _routing_snapshot(metadata):
    """Retain bounded query intent, not an assertion about captured content."""
    result = {}
    if metadata.get('topic_source_controlled') is True:
        result['topic_source_controlled'] = True
    family = metadata.get('source_family')
    if isinstance(family, str) and re.fullmatch(r'[a-z0-9_]{1,70}', family):
        result['source_family'] = family
    for key in ("specialist_tasks", "requested_specialist_tasks", "acquisition_objectives", "source_plan_action_ids"):
        values = metadata.get(key, [])
        if not isinstance(values, (list, tuple)):
            continue
        allowed = {"PUBLIC_STATEMENT", "IDENTITY_THREAT"} if key == "acquisition_objectives" else _ROUTING_TASKS
        values = [value for value in values if isinstance(value, str) and (
            bool(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value)) if key == "source_plan_action_ids" else value in allowed)]
        if values:
            result[key] = list(dict.fromkeys(values))[:16]
    return result


class RawSourceType(str, Enum):
    DISCOVERY_LEAD = "DISCOVERY_LEAD"
    SOURCE_INDEX = "SOURCE_INDEX"
    PUBLISHER_HOMEPAGE = "PUBLISHER_HOMEPAGE"
    FEED_ENTRY = "FEED_ENTRY"
    ARTICLE_BODY = "ARTICLE_BODY"
    OFFICIAL_DOCUMENT = "OFFICIAL_DOCUMENT"
    STRUCTURED_PUBLIC_DATA = "STRUCTURED_PUBLIC_DATA"
    COMMUNITY_POST = "COMMUNITY_POST"
    BACKGROUND_REFERENCE = "BACKGROUND_REFERENCE"
    BLOCKED_OR_FAILED = "BLOCKED_OR_FAILED"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _value(item, key, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _text(value):
    return value if isinstance(value, str) else ""


def _public_url(url):
    """No network/permission decision here; reject credential-bearing locators.

    Actual acquisition still requires the network SSRF/access checks. Do not
    silently redact a URL into a different resource and present that as exact.
    """
    try:
        parsed = urlsplit(url)
        return (len(url) <= 8192 and parsed.scheme in {"http", "https"}
                and bool(parsed.hostname) and not parsed.username and not parsed.password
                and not any(_SENSITIVE.search(key) for key, _ in parse_qsl(parsed.query)))
    except (ValueError, TypeError):
        return False


def _source_type(item, captured):
    meta = _value(item, "metadata", {}) or {}
    page = meta.get("page_metadata") or {}
    role = document_role(item)
    depth = str(_value(item, "content_depth", "")).upper()
    if role == "BACKGROUND_REFERENCE":
        return "BACKGROUND_REFERENCE"
    if role == "LANDING_PAGE":
        return "PUBLISHER_HOMEPAGE"
    if role in {"DOCUMENT_INDEX", "NEWS_INDEX"}:
        return "SOURCE_INDEX"
    if depth in {"FEED_ENTRY_SUMMARY", "FEED_ENTRY_CONTENT"}:
        return "FEED_ENTRY"
    if not captured or depth in METADATA_DEPTHS:
        return "DISCOVERY_LEAD"
    if depth in {"SOCIAL_POST", "COMMENT", "TWEET_STATUS"}:
        return "COMMUNITY_POST"
    if depth in {"STRUCTURED_METADATA", "STRUCTURED_PUBLIC_DATA"}:
        return "STRUCTURED_PUBLIC_DATA"
    if depth in {"REGULATORY_FILING", "OFFICIAL_STATEMENT", "PRIMARY_DOCUMENT"} or page.get("extraction_method") == "PDF_TEXT":
        return "OFFICIAL_DOCUMENT"
    # Acquisition depth is only a raw-content label. It does not mean complete,
    # relevant, fresh, official, independent, or supported by a usable passage.
    if "article_body_recovery" in page:
        from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed
        recovery = page["article_body_recovery"]
        spans = recovery.get("spans") if isinstance(recovery, dict) else None
        content = _value(item, "content", "") or ""
        if (not isinstance(spans, list) or len(spans) < 3
                or not all(isinstance(row, dict) and recovered_span_allowed(content, page, row.get("start"), row.get("end"))
                           for row in spans[:50])):
            return "DISCOVERY_LEAD"
    quality = page.get("body_quality") or {}
    if page.get("body_kind") == "ARTICLE_BODY" or isinstance(quality, dict) and quality.get("body_kind") == "ARTICLE_BODY":
        return "ARTICLE_BODY"
    return "DISCOVERY_LEAD"


def _safe_scalar(value, limit=1000):
    if isinstance(value, str):
        return value[:limit]
    return value if type(value) in {bool, int, float} else None


def _error_detail(value):
    # A diagnostic may contain an echoed request locator/header. Retain useful
    # categories, never known credential fields or Bearer authentication values.
    text = _text(value)[:2000]
    text = re.sub(r"(?i)\b(Bearer|Basic)\s+\S+", r"\1 [REDACTED]", text)
    text = re.sub(r"(?i)((?:api[_-]?key|token|secret|password|authorization|cookie|credential|signature)\s*[=:]\s*)[^\s&;,]+", r"\1[REDACTED]", text)
    return re.sub(r"https?://[^\s/]+:[^\s/@]+@", "https://[REDACTED]@", text)[:500]


def _transport_snapshot(transport):
    """Keep observed boundary facts only; never headers or credential locators."""
    safe = {}
    if not isinstance(transport, dict):
        return safe
    for field in ("endpoint", "requested_endpoint"):
        url = transport.get(field)
        if isinstance(url, str) and _public_url(url):
            safe[field] = url
    chain = transport.get("redirect_chain")
    if isinstance(chain, list):
        safe["redirect_chain"] = [url for url in chain[:10] if isinstance(url, str) and _public_url(url)]
    for field in ("http_status", "raw_body_bytes", "decoded_body_bytes", "attempts"):
        value = transport.get(field)
        if type(value) is int and value >= 0:
            safe[field] = value
    latency = transport.get("network_latency_ms")
    if type(latency) in {int, float} and 0 <= latency < 1_000_000_000:
        safe["network_latency_ms"] = latency
    digest = transport.get("raw_body_sha256")
    if isinstance(digest, str) and re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        safe["raw_body_sha256"] = digest
    for field in ("content_type", "cache_status", "protocol"):
        if isinstance(transport.get(field), str):
            safe[field] = transport[field][:200]
    if type(transport.get("network_observed_this_attempt")) is bool:
        safe["network_observed_this_attempt"] = transport["network_observed_this_attempt"]
    return safe


class RawAcquisitionPool:
    """Thread-safe per-investigation source snapshots with explicit hard caps.

    Existing native IDs are retained where unique, with canonical URL aliases.
    Repeated observations do not destroy original text; changed same-URL bodies
    become distinct capture revisions. Exact-copy cross-URL sources remain
    inspectable but are excluded from unique article/qualified-source statistics.
    """

    def __init__(self, investigation_id, *, max_bytes=MAX_POOL_BYTES,
                 max_records=300, max_source_bytes=MAX_SOURCE_BYTES):
        if not isinstance(investigation_id, str) or not investigation_id or len(investigation_id) > 200:
            raise ValueError("A bounded investigation ID is required")
        if not 1024 <= max_bytes <= MAX_POOL_BYTES or not 1 <= max_records <= MAX_RECORDS:
            raise ValueError("Invalid acquisition pool limits")
        if not 1 <= max_source_bytes <= MAX_SOURCE_BYTES:
            raise ValueError("Invalid source text limit")
        self.investigation_id = investigation_id
        self.max_bytes, self.max_records, self.max_source_bytes = max_bytes, max_records, max_source_bytes
        self.created_at = _now()
        self._sources, self._url_ids, self._aliases = {}, {}, {}
        self._body_ids = {}
        self._dropped = Counter()
        self._lock = threading.RLock()
        self._owned_dir = None
        self._owner_token = None
        self.acquisition_mode = "OBSERVED_ACQUISITION"
        self._ambiguous_aliases = []
        self._excluded_aliases = set()

    def _refresh_duplicates(self):
        self._body_ids = {}
        for source_id, record in self._sources.items():
            digest = record.get("raw_content_hash")
            duplicate = self._body_ids.get(digest) if record["utf8_bytes"] >= 100 else None
            record["duplicate_of"] = duplicate
            record["duplicate_reason"] = "EXACT_CAPTURE" if duplicate else None
            if digest and record["utf8_bytes"] >= 100:
                self._body_ids.setdefault(digest, source_id)

    def _size(self):
        return len(json.dumps(list(self._sources.values()), ensure_ascii=False).encode("utf-8"))

    def _commit(self, source_id, record):
        old = self._sources.get(source_id)
        self._sources[source_id] = record
        if self._size() > self.max_bytes - 512:
            if old is None:
                del self._sources[source_id]
            else:
                self._sources[source_id] = old
            self._dropped["POOL_BYTES"] += 1
            return None
        return source_id

    def add_candidate(self, item, query_id=None):
        """Snapshot a discoverable locator/snippet; it is never a body read."""
        with self._lock:
            url = item if isinstance(item, str) else (_value(item, "canonical_url") or _value(item, "url") or _value(item, "source_url"))
            if not isinstance(url, str) or not _public_url(url):
                self._dropped["INVALID_OR_SENSITIVE_URL"] += 1
                return None
            canonical = source_url_key(url)
            native_id = _text(_value(item, "id"))[:200]
            source_id = self._url_ids.get(canonical)
            meta = _value(item, "metadata", {}) or {}
            discovery_url = _text(meta.get("discovery_url"))
            resolution = meta.get("wrapper_resolution") or {}
            if not source_id and discovery_url and source_url_key(resolution.get("selected_url")) == canonical:
                source_id = self._url_ids.get(source_url_key(discovery_url))
            if not source_id:
                if len(self._sources) >= self.max_records:
                    self._dropped["SOURCE_COUNT"] += 1
                    return None
                source_id = native_id if native_id and native_id not in self._sources and native_id not in self._aliases else "raw_" + hashlib.sha256(canonical.encode()).hexdigest()[:24]
            old = self._sources.get(source_id)
            snippet = _text(_value(item, "snippet"))
            if len(snippet.encode("utf-8")) > self.max_source_bytes:
                self._dropped["SNIPPET_BYTES"] += 1
                snippet = ""
            record = copy.deepcopy(old) if old else {
                "source_id": source_id, "aliases": [], "source_url": url,
                "canonical_url": canonical, "source_urls": [], "query_id": "", "query_ids": [],
                "publisher": "", "publisher_host": urlsplit(url).hostname or "", "title": "",
                "source_type": _source_type(item, False), "published_at": None,
                "publication_time_basis": None, "acquired_at": None, "discovered_at": _now(),
                "raw_content_hash": None, "readable_text": "", "raw_text": "",
                "word_count": 0, "utf8_bytes": 0, "char_count": 0,
                "discovery_snippet": snippet, "extraction_status": "NOT_ATTEMPTED",
                "qualification_status": "PENDING", "qualification_reasons": [],
                "useful_words": 0, "acquisition_method": "", "content_depth": "",
                "read_attempts": 0, "errors": [], "observations": [], "prior_captures": [],
                "duplicate_of": None, "duplicate_reason": None,
            }
            if native_id and native_id != source_id and native_id not in record["aliases"] and len(record["aliases"]) < 32:
                record["aliases"].append(native_id)
            qid = _text(query_id or _value(item, "query_id"))[:200]
            if qid and qid not in record["query_ids"] and len(record["query_ids"]) < 32:
                record["query_ids"].append(qid)
                record["query_id"] = record["query_id"] or qid
            for key, values in _routing_snapshot(meta).items():
                # Routing has scalar permission/family observations as well as
                # repeatable task IDs. Never unpack a bool, or split a family
                # string into characters, when merging another discovery.
                if key in {'topic_source_controlled', 'source_family'}:
                    record[key] = values
                else:
                    previous = record.get(key, [])
                    previous = previous if isinstance(previous, list) else []
                    record[key] = list(dict.fromkeys([*previous, *values]))[:16]
            if url not in record["source_urls"] and len(record["source_urls"]) < 16:
                record["source_urls"].append(url)
            record["title"] = record["title"] or _text(_value(item, "title"))[:2000]
            record["publisher"] = record["publisher"] or _text(_value(item, "source_name") or _value(item, "publisher"))[:500]
            if not record["published_at"]:
                record["published_at"] = _text(_value(item, "published_at"))[:200] or None
            if self._commit(source_id, record):
                self._url_ids[canonical] = source_id
                for alias in record["aliases"]:
                    if alias not in self._excluded_aliases:
                        self._aliases.setdefault(alias, source_id)
                return source_id
            return None

    def add_capture(self, item, query_id=None, source_type=None):
        """Snapshot actual acquired content, never a candidate's fallback snippet.

        Explicit source_type can only narrow/label captured content; metadata,
        homes/indexes/references cannot be overridden into an ARTICLE_BODY.
        """
        with self._lock:
            source_id = self.add_candidate(item, query_id)
            if not source_id:
                return None
            content = _text(_value(item, "content"))
            meta = _value(item, "metadata", {}) or {}
            depth = str(_value(item, "content_depth", "")).upper()
            read_status = _text(_value(item, "read_status"))
            # Feed summaries / metadata often occupy the native content field;
            # preserve them as discovery, never as an acquired article body.
            acquisition_observed = (meta.get("read_success") is True or read_status == "SUCCESS"
                                    or bool(_value(item, "acquired_id")))
            observed = bool(content and acquisition_observed and (depth not in METADATA_DEPTHS))
            actual_type = _source_type(item, observed)
            if not observed:
                return source_id
            if source_type is not None:
                requested_type = RawSourceType(source_type).value
                if actual_type == "ARTICLE_BODY" and requested_type in _BODY_TYPES:
                    actual_type = requested_type
            raw = meta.get("raw_capture") or {}
            raw_text = _text(raw.get("text")) or content
            if max(len(content.encode("utf-8")), len(raw_text.encode("utf-8"))) > self.max_source_bytes:
                self._dropped["SOURCE_BYTES"] += 1
                self.add_failure(item, "STORAGE_LIMIT", "Captured text exceeds per-source retention limit", query_id=query_id)
                return source_id
            record = copy.deepcopy(self._sources[source_id])
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # Preserve the first snapshot and exact alternate revisions. Repeated
            # same-byte calls record provenance without repeated storage/counts.
            if record["readable_text"] and record["raw_content_hash"] != digest:
                if len(record["prior_captures"]) >= 5:
                    self._dropped["CAPTURE_REVISIONS"] += 1
                    return source_id
                record["prior_captures"].append({key: record[key] for key in
                    ("readable_text", "raw_text", "raw_content_hash", "acquired_at", "source_type", "acquisition_method",
                     "transport", "actual_final_url", "raw_capture_sha256", "http_status", "page_metadata", "published_at", "publication_time_basis")
                    if key in record})
            page = meta.get("page_metadata") or {}
            transport = meta.get("transport") or {}
            safe_transport = _transport_snapshot(transport)
            record.update({
                "source_url": _value(item, "canonical_url") or record["source_url"],
                "canonical_url": source_url_key(_value(item, "canonical_url") or record["source_url"]),
                "publisher_host": urlsplit(_value(item, "canonical_url") or record["source_url"]).hostname or "",
                "source_type": actual_type, "readable_text": content, "raw_text": raw_text,
                "raw_content_hash": digest, "raw_capture_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "word_count": len(content.split()), "utf8_bytes": len(content.encode("utf-8")), "char_count": len(content),
                "acquired_at": _text(meta.get("acquired_at") or transport.get("acquired_at")) or _now(),
                "acquired_at_basis": "ADAPTER_OBSERVED" if meta.get("acquired_at") or transport.get("acquired_at") else "CAPTURE_SNAPSHOT_UTC",
                "acquisition_method": _text(page.get("extraction_method") or meta.get("extraction_method") or _value(item, "retrieval_mode"))[:200],
                "content_depth": depth, "extraction_status": "SUCCESS",
                "read_attempts": record["read_attempts"] + (0 if record["raw_content_hash"] == digest else 1),
                "read_status": read_status or "CAPTURED",
                "acquisition_objective": meta.get("acquisition_objective") if meta.get("acquisition_objective") in {"PUBLIC_STATEMENT", "IDENTITY_THREAT"} else None,
                "http_status": _safe_scalar(transport.get("http_status") or meta.get("http_status")),
                "publication_time_basis": _safe_scalar(meta.get("publication_time_basis") or page.get("publication_time_basis")),
                "provider_truncated": raw.get("truncated") if type(raw.get("truncated")) is bool else None,
                "transport": safe_transport,
                # A mirror's observed final transport URL is not silently
                # relabeled as the publisher's source URL.
                "actual_final_url": safe_transport.get("endpoint"),
            })
            # Whitelisted structure/date observations are needed to re-run the
            # strict filter offline. Never retain arbitrary headers or cookies.
            record["page_metadata"] = {}
            for key in ("title", "author", "published", "publication_time_basis", "publication_time_source", "content_scope", "extraction_method", "body_kind", "language", "language_basis"):
                if isinstance(page.get(key), str):
                    record["page_metadata"][key] = page[key][:2000]
            if isinstance(page.get('licence_urls'), list):
                record['page_metadata']['licence_urls'] = [s[:200] for s in page['licence_urls'][:4]
                    if isinstance(s, str) and s.startswith('https://creativecommons.org/licenses/')]
            if page.get('rights_exception_observed') is True:
                record['page_metadata']['rights_exception_observed'] = True
            if type(page.get("publication_metadata_conflict")) is bool:
                record["page_metadata"]["publication_metadata_conflict"] = page["publication_metadata_conflict"]
            observed_publications = page.get("publication_observations")
            if isinstance(observed_publications, list):
                record["page_metadata"]["publication_observations"] = [{
                    "value": _text(observation.get("value"))[:200],
                    "source": _text(observation.get("source"))[:200]}
                    for observation in observed_publications[:12] if isinstance(observation, dict)]
            declared = page.get("declared_structured_data")
            if isinstance(declared, list):
                record["page_metadata"]["declared_structured_data"] = [{
                    key: _safe_scalar(observation[key], 200) for key in ("@type", "datePublished", "dateModified") if key in observation}
                    for observation in declared[:12] if isinstance(observation, dict)]
            for quality_key in ("body_quality", "original_body_quality"):
                quality = page.get(quality_key)
                if isinstance(quality, dict):
                    record["page_metadata"][quality_key] = {key: _safe_scalar(quality[key]) for key in
                        ("body_kind", "paragraph_count", "link_text_ratio", "basis", "scope", "evidence_qualified") if key in quality}
            recovery = page.get("article_body_recovery")
            if (isinstance(recovery, dict)
                    and recovery.get("basis") == "OBSERVED_CAPTURED_TITLE_BYLINE_PROSE_SPANS"
                    and recovery.get("source_text_sha256") == digest):
                # Retain bounded structural observations, not arbitrary adapter
                # metadata. These spans do not by themselves qualify evidence.
                observed_spans = recovery.get("spans")
                spans = [{"start": row["start"], "end": row["end"]}
                    for row in (observed_spans if isinstance(observed_spans, list) else [])[:50] if isinstance(row, dict)
                    and type(row.get("start")) is int and type(row.get("end")) is int
                    and 0 <= row["start"] < row["end"] <= len(content)]
                if len(spans) >= 3:
                    safe_recovery = {"basis": recovery["basis"], "scope": "PARTIAL_ARTICLE_SPANS",
                        "source_text_sha256": digest, "spans": spans,
                        "publication_timestamp_inferred": False, "evidence_qualified": False}
                    for boundary in ("byline_start", "byline_end", "selection_end"):
                        value = recovery.get(boundary)
                        if type(value) is int and 0 <= value <= len(content):
                            safe_recovery[boundary] = value
                    heading = recovery.get("title_heading")
                    if (isinstance(heading, dict) and type(heading.get("start")) is int
                            and type(heading.get("end")) is int
                            and 0 <= heading["start"] < heading["end"] <= len(content)):
                        safe_recovery["title_heading"] = {"start": heading["start"], "end": heading["end"], "role": "HEADING"}
                    record["page_metadata"]["article_body_recovery"] = safe_recovery
            for key in ("text_blocks", "date_observations"):
                observed_blocks = page.get(key)
                if isinstance(observed_blocks, list):
                    record["page_metadata"][key] = []
                    for block in observed_blocks[:100 if key == "text_blocks" else 4]:
                        if (not isinstance(block, dict) or type(block.get("start")) is not int or type(block.get("end")) is not int
                                or not 0 <= block["start"] < block["end"] <= len(content)):
                            continue
                        safe = {"start": block["start"], "end": block["end"]}
                        for name in ("role", "meaning", "text"):
                            if isinstance(block.get(name), str):
                                safe[name] = block[name][:500]
                        record["page_metadata"][key].append(safe)
            if page.get("published"):
                record["published_at"] = _text(page["published"])[:200]
            if page.get("publication_metadata_conflict"):
                record["discovery_published_at"] = record["published_at"]
                record["published_at"] = None
                record["publication_time_basis"] = "CONFLICTING_CAPTURED_DECLARATIONS"
            record["redirect_chain"] = [url for url in (transport.get("redirect_chain") or [])[:10] if isinstance(url, str) and _public_url(url)]
            duplicate = self._body_ids.get(digest) if len(content.encode()) >= 100 else None
            if duplicate and duplicate != source_id:
                record["duplicate_of"], record["duplicate_reason"] = duplicate, "EXACT_CAPTURE"
            else:
                record["duplicate_of"], record["duplicate_reason"] = None, None
            if len(record["observations"]) < 32:
                record["observations"].append({"query_id": _text(query_id or _value(item, "query_id"))[:200],
                    "acquired_at": record["acquired_at"], "source_id": _text(_value(item, "id"))[:200],
                    "raw_content_hash": digest, "method": record["acquisition_method"]})
            if self._commit(source_id, record):
                self._refresh_duplicates()
            return source_id

    def add_failure(self, item, error_type, detail="", query_id=None, *, http_status=None):
        """Record an explicit failed attempt without discarding a prior body."""
        with self._lock:
            source_id = self.add_candidate(item, query_id)
            if not source_id:
                return None
            record = copy.deepcopy(self._sources[source_id])
            record["read_attempts"] += 1
            if not record["readable_text"]:
                record["source_type"] = "BLOCKED_OR_FAILED"
                record["extraction_status"] = "FAILED"
            # Details are caller-sanitized categories, never arbitrary provider
            # response bodies, auth headers, or credential-bearing URLs.
            category = re.sub(r"[^A-Za-z0-9_-]", "_", str(error_type))[:100]
            if len(record["errors"]) < 20:
                record["errors"].append({"type": category, "detail": _error_detail(detail),
                    "at": _now(), "query_id": _text(query_id or _value(item, "query_id"))[:200],
                    "http_status": http_status if type(http_status) is int else None})
            self._commit(source_id, record)
            return source_id

    def mark_qualification(self, source_id, status, reasons=(), useful_words=0):
        """Attach a downstream decision; do not mutate raw text or invent support."""
        with self._lock:
            source_id = self._aliases.get(source_id, source_id)
            if source_id not in self._sources:
                return False
            if status not in {"PENDING", "QUALIFIED", "REJECTED", "BACKGROUND", "DUPLICATE"}:
                raise ValueError("Unknown qualification status")
            record = copy.deepcopy(self._sources[source_id])
            if status == "QUALIFIED" and (not record["readable_text"] or record["source_type"] not in _BODY_TYPES or record["duplicate_of"]):
                raise ValueError("Discovery, duplicate or failed records cannot be qualified evidence")
            record["qualification_status"] = status
            record["qualification_reasons"] = [str(value)[:300] for value in list(reasons)[:20]]
            record["useful_words"] = min(record["word_count"], max(0, int(useful_words))) if status == "QUALIFIED" else 0
            return bool(self._commit(source_id, record))

    def get(self, source_id):
        with self._lock:
            return copy.deepcopy(self._sources.get(self._aliases.get(source_id, source_id)))

    def stats(self):
        with self._lock:
            records = list(self._sources.values())
            unique = [r for r in records if not r["duplicate_of"]]
            articles = [r for r in unique if r["source_type"] == "ARTICLE_BODY" and r["readable_text"]]
            qualified = [r for r in unique if r["qualification_status"] == "QUALIFIED"]
            return {
                "source_count": len(records), "candidate_urls": len(self._url_ids),
                "by_type": dict(Counter(r["source_type"] for r in records)),
                "reads_attempted": sum(r["read_attempts"] for r in records),
                "successful_captures": sum(bool(r["readable_text"]) for r in records),
                "article_bodies": len(articles), "raw_article_words": sum(r["word_count"] for r in articles),
                "raw_source_words": sum(r["word_count"] for r in unique),
                "duplicate_captures": sum(bool(r["duplicate_of"]) for r in records),
                "qualified_source_count": len(qualified), "relevant_words": sum(r["useful_words"] for r in qualified),
                "unique_publishers": len({r["publisher_host"] for r in qualified if r["publisher_host"]}),
                "publisher_independence": "NOT_ESTABLISHED", "storage_bytes": self._size(),
                "acquisition_mode": self.acquisition_mode,
                "ambiguous_alias_count": len(self._ambiguous_aliases),
                "failed_reads_by_cause": dict(Counter(e["type"] for r in records for e in r["errors"])),
                "dropped_by_limit": dict(self._dropped),
            }

    def export(self, include_text=True):
        with self._lock:
            records = copy.deepcopy(list(self._sources.values()))
            if not include_text:
                for record in records:
                    for key in ("readable_text", "raw_text", "discovery_snippet", "prior_captures"):
                        record.pop(key, None)
            return {"schema_version": SCHEMA_VERSION, "investigation_id": self.investigation_id,
                "created_at": self.created_at, "limits": {"max_bytes": self.max_bytes,
                    "max_records": self.max_records, "max_source_bytes": self.max_source_bytes},
                "stats": self.stats(), "sources": records,
                **({"ambiguous_aliases": copy.deepcopy(self._ambiguous_aliases)} if self._ambiguous_aliases else {})}

    def to_evidence_items(self):
        """Reconstruct captured native items for strict offline requalification.

        Discovery snippets/URLs without captured text are not returned. Original
        bytes, canonical source IDs and declared publication basis survive;
        prior qualification is not promoted into the reconstructed evidence.
        """
        from backend.services.research.research_models import EvidenceItem
        with self._lock:
            result = []
            for record in self._sources.values():
                if not record["readable_text"]:
                    continue
                result.append(EvidenceItem(
                    id=record["source_id"], canonical_url=record["source_url"], title=record["title"],
                    source_name=record["publisher"], source_domain=record["publisher_host"],
                    query_id=record["query_id"], published_at=record["published_at"] or "",
                    # Requalification must not advance the acquisition clock.
                    # Unknown historical clocks stay unknown, never "now".
                    discovered_at=record.get("discovered_at") or record.get("acquired_at") or "",
                    content=record["readable_text"], snippet=record["discovery_snippet"],
                    content_depth=record["content_depth"], read_status="SUCCESS",
                    retrieval_mode=record["acquisition_method"],
                    metadata={"read_success": True, "raw_pool_source_type": record["source_type"],
                        **_routing_snapshot(record),
                        "acquisition_objective": record.get("acquisition_objective"),
                        "raw_pool_aliases": list(record["aliases"]), "raw_pool_origin": self.acquisition_mode,
                        "page_metadata": copy.deepcopy(record.get("page_metadata", {})),
                        "publication_time_basis": record["publication_time_basis"],
                        "acquired_at": record["acquired_at"],
                        "transport": copy.deepcopy(record.get("transport", {})),
                        "raw_capture": {"text": record["raw_text"], "truncated": record["provider_truncated"]},
                        "duplicate_of": record["duplicate_of"]}))
            return result

    def iter_evidence(self):
        return iter(self.to_evidence_items())

    def save_temporary(self):
        """Atomically save in this instance's new private system-temp directory."""
        with self._lock:
            payload = json.dumps(self.export(), ensure_ascii=False).encode("utf-8")
            if len(payload) > self.max_bytes:
                raise ValueError("Serialized pool exceeds storage limit")
            if self._owned_dir is None:
                self._owned_dir = Path(tempfile.mkdtemp(prefix=_PREFIX)).resolve()
                self._owner_token = uuid.uuid4().hex
                (self._owned_dir / "owner").write_text(self._owner_token, encoding="ascii")
            self._validate_owned_directory()
            target, pending = self._owned_dir / "pool.json", self._owned_dir / "pool.pending"
            with pending.open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(pending, target)
            return target

    @classmethod
    def load(cls, path, *, allow_ambiguous_aliases=False):
        """Bounded opt-in import for offline requalification, never cleanup ownership."""
        path = Path(path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_POOL_BYTES:
            raise ValueError("Invalid or oversized pool file")
        with path.open("rb") as stream:
            encoded = stream.read(MAX_POOL_BYTES + 1)
        if len(encoded) > MAX_POOL_BYTES:
            raise ValueError("Oversized pool file")
        return cls.from_export(json.loads(encoded), allow_ambiguous_aliases=allow_ambiguous_aliases)

    @classmethod
    def from_export(cls, payload, *, allow_ambiguous_aliases=False):
        """Import a report's embedded raw pool without writing intermediate files.

        Strict default rejects ambiguous native aliases. Explicit offline rescue
        can exclude them from alias lookups while retaining every original
        record/alias and validating all unique raw IDs, URLs and body hashes.
        It does not repair historical citation joins or prior verdicts.
        """
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_POOL_BYTES:
            raise ValueError("Oversized pool data")
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported raw pool schema")
        payload = copy.deepcopy(payload)
        pool = cls(payload["investigation_id"], **payload.get("limits", {}))
        pool.acquisition_mode = "OFFLINE_REPROCESSING"
        records = payload.get("sources")
        if not isinstance(records, list) or len(records) > pool.max_records or len(encoded) > pool.max_bytes:
            raise ValueError("Invalid raw pool inventory")
        pool.created_at = _text(payload.get("created_at"))[:200] or pool.created_at
        all_ids = {record.get("source_id") for record in records if isinstance(record, dict) and isinstance(record.get("source_id"), str)}
        alias_targets = {}
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("source_id"), str) or not isinstance(record.get("aliases"), list):
                continue
            for alias in record["aliases"]:
                if not isinstance(alias, str) or len(alias) > 200:
                    raise ValueError("Conflicting source alias")
                alias_targets.setdefault(alias, set()).add(record["source_id"])
                if alias in all_ids:
                    alias_targets[alias].add(alias)
        ambiguous = {alias for alias, targets in alias_targets.items() if len(targets) > 1 or alias in all_ids}
        if ambiguous and not allow_ambiguous_aliases:
            raise ValueError("Conflicting source alias")
        pool._ambiguous_aliases = [{"alias": alias, "source_ids": sorted(alias_targets[alias]),
            "excluded_from_alias_lookup": True} for alias in sorted(ambiguous)]
        pool._excluded_aliases = ambiguous
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("source_id"), str):
                raise ValueError("Invalid source record")
            source_id, url = record["source_id"], record.get("source_url")
            if not source_id or len(source_id) > 200 or source_id in pool._sources or not isinstance(url, str) or not _public_url(url):
                raise ValueError("Duplicate ID or invalid source URL")
            RawSourceType(record.get("source_type"))
            for field in ("readable_text", "raw_text"):
                if not isinstance(record.get(field), str) or len(record[field].encode()) > pool.max_source_bytes:
                    raise ValueError("Invalid captured text")
            if record["readable_text"] and hashlib.sha256(record["readable_text"].encode()).hexdigest() != record.get("raw_content_hash"):
                raise ValueError("Capture hash mismatch")
            if record["raw_text"] and hashlib.sha256(record["raw_text"].encode()).hexdigest() != record.get("raw_capture_sha256"):
                raise ValueError("Raw capture hash mismatch")
            for field, cap in (("aliases", 32), ("query_ids", 32), ("source_urls", 16), ("errors", 20), ("observations", 32), ("prior_captures", 5)):
                if not isinstance(record.get(field), list) or len(record[field]) > cap:
                    raise ValueError("Invalid source observation history")
            for alias in record["aliases"]:
                if (not isinstance(alias, str) or len(alias) > 200
                        or alias not in ambiguous and (alias in all_ids or alias in pool._aliases)):
                    raise ValueError("Conflicting source alias")
            for locator in record["source_urls"]:
                if not isinstance(locator, str) or not _public_url(locator):
                    raise ValueError("Invalid source locator")
            for prior in record["prior_captures"]:
                if not isinstance(prior, dict):
                    raise ValueError("Invalid prior capture")
                for field in ("readable_text", "raw_text"):
                    if not isinstance(prior.get(field), str) or len(prior[field].encode()) > pool.max_source_bytes:
                        raise ValueError("Oversized prior capture")
                if hashlib.sha256(prior["readable_text"].encode()).hexdigest() != prior.get("raw_content_hash"):
                    raise ValueError("Prior capture hash mismatch")
            for field in ("read_attempts", "word_count", "utf8_bytes"):
                if type(record.get(field)) is not int or record[field] < 0:
                    raise ValueError("Invalid source counts")
            if record["word_count"] != len(record["readable_text"].split()) or record["utf8_bytes"] != len(record["readable_text"].encode()):
                raise ValueError("Source counts do not match exact text")
            canonical = source_url_key(url)
            if canonical in pool._url_ids:
                raise ValueError("Duplicate canonical source")
            # Stored qualification is inspectable prior output, not trusted
            # acceptance. Every imported record requires fresh Layer 2 review.
            record["previous_qualification_status"] = record.get("qualification_status")
            record["qualification_status"], record["useful_words"] = "PENDING", 0
            pool._sources[source_id], pool._url_ids[canonical] = record, source_id
            for alias in record.get("aliases", [])[:32]:
                if isinstance(alias, str) and alias not in ambiguous:
                    pool._aliases.setdefault(alias, source_id)
        pool._refresh_duplicates()
        return pool

    def _validate_owned_directory(self):
        directory = self._owned_dir
        temp_root = Path(tempfile.gettempdir()).resolve()
        if (directory.is_symlink() or directory.parent != temp_root or not directory.name.startswith(_PREFIX)
                or (directory / "owner").is_symlink() or not (directory / "owner").is_file()
                or (directory / "owner").read_text(encoding="ascii") != self._owner_token):
            raise ValueError("Raw-pool cleanup ownership check failed")
        names = {"owner", "pool.json", "pool.pending"}
        if any(entry.name not in names or entry.is_symlink() or not entry.is_file() for entry in directory.iterdir()):
            raise ValueError("Unexpected files in owned raw-pool directory; preserve for inspection")

    def cleanup(self):
        """Delete only the exact files in the temp directory this object created.

        Never recurse and never remove unknown files, imported files, user paths,
        historical dossiers or an enclosing temporary directory.
        """
        with self._lock:
            directory = self._owned_dir
            if directory is None:
                return False
            self._validate_owned_directory()
            for name in ("pool.pending", "pool.json", "owner"):
                target = directory / name
                if target.exists():
                    target.unlink()
            directory.rmdir()
            self._owned_dir, self._owner_token = None, None
            return True

    close = cleanup
