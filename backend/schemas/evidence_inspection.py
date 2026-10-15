"""Pure, bounded inspection of captured evidence for the public contract.

Offsets address the captured text (not the original remote document). Missing
fields, provider truncation and metadata-only content remain explicit. No model
or network calls and no modification of the evidence used by verdict engines.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any


SCHEMA = "captured-evidence-v1"
METADATA_DEPTHS = frozenset({
    "METADATA", "DIRECT_METADATA", "PROFILE_METADATA", "VIDEO_METADATA", "HEADLINE_ONLY",
    "INDEX_SNIPPET", "SNIPPET", "UNKNOWN", "",
})
MAX_CAPTURE_CHARS = 100_000
MAX_PASSAGES = 8
PASSAGE_CHARS = 600


def _value(item: Any, *names: str) -> Any:
    for name in names:
        value = item.get(name) if isinstance(item, Mapping) else getattr(item, name, None)
        if value is not None and not callable(value) and not hasattr(value, "_mock_name"):
            if isinstance(value, (str, dict, list, int, float, bool)) and value != "":
                return value
    return None


def inspect_evidence(item: Any) -> dict:
    """Return observed-field coverage and exact excerpts, not inferred facts.

    A stored inspection is deliberately not trusted: recompute from the current
    captured text so mutations cannot leave apparently valid stale passage IDs.
    """
    def string(*names):
        value = _value(item, *names)
        return value if isinstance(value, str) else ""

    content = string("content", "body", "relevant_excerpt", "snippet", "summary")
    captured = content[:MAX_CAPTURE_CHARS]
    url = string("canonical_url", "url", "source_url")
    meta = _value(item, "raw_metadata", "metadata") or {}
    meta = meta if isinstance(meta, dict) else {}
    depth_value = string("content_depth") or meta.get("content_depth")
    depth = depth_value.upper() if isinstance(depth_value, str) and depth_value else "UNKNOWN"
    fingerprint = hashlib.sha256(captured.encode("utf-8")).hexdigest()
    document_id = "doc_" + hashlib.sha256((url + "\n" + fingerprint).encode("utf-8")).hexdigest()[:20]
    fields = {
        "title": bool(string("title")), "url": bool(url),
        "author": bool(string("author", "source_author")),
        "published_at": bool(string("published_at", "published", "timestamp")),
        "captured_text": bool(captured.strip()),
    }
    # Select query-matching chunks for inspection only, not relevance acceptance.
    # Lexical matching does not determine claim support or contradiction.
    query = string("query_text", "query")[:2000]
    tokens = set(re.findall(r"\w{3,}", query.casefold()))
    chunks = []
    for start in range(0, len(captured), PASSAGE_CHARS):
        text = captured[start:start + PASSAGE_CHARS]
        overlap = len(tokens & set(re.findall(r"\w{3,}", text.casefold())))
        chunks.append((overlap, start, text))
    selected = sorted(chunks, key=lambda chunk: (-chunk[0], chunk[1]))[:MAX_PASSAGES]
    passages = [{
        "id": f"{document_id}:p{start}", "start": start, "end": start + len(text),
        "text": text,
    } for _, start, text in sorted(selected, key=lambda chunk: chunk[1])]
    provider_truncated = meta.get("truncated")
    if not isinstance(provider_truncated, bool):
        provider_truncated = None
    page = meta.get("page_metadata") or {}
    page = page if isinstance(page, dict) else {}
    observations = {}
    for key in ("quotations", "potential_corrections", "media_captions"):
        values = page.get(key)
        if isinstance(values, list):
            observations[key] = [value[:500] for value in values[:5] if isinstance(value, str)]
    tables = page.get("tables")
    if isinstance(tables, list):
        observations["tables"] = [
            [[cell[:120] for cell in row[:6] if isinstance(cell, str)] for row in table[:10] if isinstance(row, list)]
            for table in tables[:3] if isinstance(table, list)
        ]
    mentions = []
    for match in re.finditer(r"(?<!\w)(?:[$€£₹]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*(?:%|billion|million|thousand|bps))?(?!\w)", captured):
        mentions.append({"text": match.group(0), "start": match.start(), "end": match.end(),
                         "context": captured[max(0, match.start() - 60):min(len(captured), match.end() + 60)]})
        if len(mentions) == 12:
            break
    return {
        "schema_version": SCHEMA, "document_id": document_id,
        "captured_text_sha256": fingerprint, "content_depth": depth,
        "evidentiary_use": "DISCOVERY_ONLY" if depth in METADATA_DEPTHS else "REQUIRES_PASSAGE_REVIEW",
        "captured_chars": len(content), "inspected_chars": len(captured),
        "inspection_truncated": len(content) > MAX_CAPTURE_CHARS,
        "provider_truncated": provider_truncated,
        "source_completeness": "UNKNOWN",
        "observed_fields": [key for key, present in fields.items() if present],
        "missing_fields": [key for key, present in fields.items() if not present],
        "passages": passages,
        "observed_numeric_mentions": mentions,
        "page_observations": observations,
        "observation_warning": "Extracted mentions and page declarations are not independently verified facts.",
        "passages_omitted": max(0, len(chunks) - len(passages)),
        "support_assessment": "NOT_ASSESSED",
    }


def summarize_inspections(items: list) -> dict:
    inspections = [inspect_evidence(item) for item in items]
    return {
        "schema_version": SCHEMA, "items": len(inspections),
        "captured_chars": sum(item["captured_chars"] for item in inspections),
        "discovery_only_items": sum(item["evidentiary_use"] == "DISCOVERY_ONLY" for item in inspections),
        "missing_field_counts": {key: sum(key in item["missing_fields"] for item in inspections)
                                 for key in ("title", "url", "author", "published_at", "captured_text")},
        "inspections_truncated": sum(item["inspection_truncated"] for item in inspections),
        "source_completeness": "UNKNOWN", "claim_accuracy": None,
    }
