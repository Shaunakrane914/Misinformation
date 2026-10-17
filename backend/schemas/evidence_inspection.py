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
    "SEARCH_INDEX_DISCOVERY", "SEARCH_DISCOVERY_ONLY", "SYNDICATED_SUMMARY", "FEED_ENTRY_SUMMARY",
})
MAX_CAPTURE_CHARS = 100_000
MAX_PASSAGES = 8
PASSAGE_CHARS = 600
SOURCE_FIELDS = (
    "operation", "repo", "number", "state", "sha", "readme_sha", "comment_count",
    "comment_lookup_status", "comment_has_next_page", "answer_count", "answers_acquired",
    "answer_lookup_status", "sampled_answer_count", "answer_has_more", "question_id", "answer_id",
    "is_accepted", "content_license", "discussion_completeness", "parent_id", "subreddit",
    "tweet_id", "screen_name", "followers", "tweets_count", "likes", "retweets", "replies", "views",
    "mirror_backend", "account_created_at", "video_id", "duration", "caption_language", "caption_origin",
    "feed_title", "feed_content_present", "linked_article_retrieved", "item_type", "podcast",
    "transcript_available", "episode_count", "source_contract", "arxiv_id", "category", "doi",
    "content_depth_detail", "cve_id", "cvss_score", "filing_type", "form", "accession_number",
    "referenced_url_acquired", "has_more", "page",
    "observed_body_marker", "content_status", "content_role", "passage_selection_method", "content_completeness",
)


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
    raw = meta.get("raw_capture")
    raw = raw if isinstance(raw, dict) else {}
    raw_text = raw.get("text") if isinstance(raw.get("text"), str) else content
    # Counts describe retained public text, not the HTTP envelope, relevance,
    # independent corroboration, or the remote document's complete size.
    text_metrics = {
        "raw_words": len(raw_text.split()), "raw_utf8_bytes": len(raw_text.encode("utf-8")),
        "readable_words": len(content.split()), "readable_utf8_bytes": len(content.encode("utf-8")),
        "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "raw_capture_truncated": raw.get("truncated") if isinstance(raw.get("truncated"), bool) else None,
        "selection_method": raw.get("selection_method", "NATIVE_SOURCE_TEXT"),
        "content_scope": page.get("content_scope", "SOURCE_RECORD"),
        "quality_assessment": "NOT_ASSESSED",
    }
    observations = {}
    for key in ("quotations", "potential_corrections", "media_captions"):
        values = page.get(key)
        if isinstance(values, list):
            observations[key] = [value[:500] for value in values[:5] if isinstance(value, str)]
    # Explicit allowlist: never forward cookies, auth headers or arbitrary
    # provider metadata. These are observed fields, not verified conclusions.
    source_observations = {
        key: (meta[key][:300] if isinstance(meta[key], str) else meta[key])
        for key in SOURCE_FIELDS if key in meta and isinstance(meta[key], (str, bool, int, float))
    }
    tables = page.get("tables")
    if isinstance(tables, list):
        observations["tables"] = [
            [[cell[:120] for cell in row[:6] if isinstance(cell, str)] for row in table[:10] if isinstance(row, list)]
            for table in tables[:3] if isinstance(table, list)
        ]
    mentions = []
    pdf_pages = page.get("pdf_pages")
    if isinstance(pdf_pages, list):
        observations["pdf_pages"] = [
            {"page": p["page"], "start": p["start"], "end": min(p["end"], len(captured)),
             "text_truncated": bool(p.get("text_truncated")) or p["end"] > len(captured)}
            for p in pdf_pages[:8] if isinstance(p, dict)
            and all(type(p.get(key)) is int for key in ("page", "start", "end"))
            and 0 <= p["start"] < min(p["end"], len(captured)) and p["page"] >= 1]
        for key in ("pdf_page_count", "pdf_truncated", "pdf_source_sha256", "table_structure_verified", "extraction_method"):
            if isinstance(page.get(key), (str, bool, int)):
                source_observations[key] = page[key]
    for match in re.finditer(r"(?<!\w)(?:[$€£₹]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*(?:%|billion|million|thousand|bps))?(?!\w)", captured):
        mentions.append({"text": match.group(0), "start": match.start(), "end": match.end(),
                         "context": captured[max(0, match.start() - 60):min(len(captured), match.end() + 60)]})
        if len(mentions) == 12:
            break
    return {
        "schema_version": SCHEMA, "document_id": document_id,
        "captured_text_sha256": fingerprint, "content_depth": depth,
        "evidentiary_use": "DISCOVERY_ONLY" if depth in METADATA_DEPTHS or meta.get("content_role") in {
            "DOCUMENT_INDEX", "LANDING_PAGE", "PROFILE", "AUTHOR_BIO", "NAVIGATION"} else "REQUIRES_PASSAGE_REVIEW",
        "captured_chars": len(content), "inspected_chars": len(captured),
        "inspection_truncated": len(content) > MAX_CAPTURE_CHARS,
        "provider_truncated": provider_truncated,
        "source_completeness": "UNKNOWN",
        "observed_fields": [key for key, present in fields.items() if present],
        "missing_fields": [key for key, present in fields.items() if not present],
        "passages": passages,
        "observed_numeric_mentions": mentions,
        "page_observations": observations,
        "text_metrics": text_metrics,
        "source_observations": source_observations,
        "observation_warning": "Extracted mentions and page declarations are not independently verified facts.",
        "passages_omitted": max(0, len(chunks) - len(passages)),
        "support_assessment": "NOT_ASSESSED",
    }


def public_capture_metadata(item, max_chars=20_000):
    """Bounded public capture context; never forward arbitrary provider metadata.

    Used by native agent serializers that would otherwise discard structural
    context. Inspection is recomputed against the actual exported body later.
    """
    meta = _value(item, "raw_metadata", "metadata") or {}
    meta = meta if isinstance(meta, dict) else {}
    body = _value(item, "content") or ""
    body = body if isinstance(body, str) else ""
    result = {"truncated": bool(meta.get("truncated")) or len(body) > max_chars}
    for key in SOURCE_FIELDS:
        value = meta.get(key)
        if type(value) in (str, bool, int, float):
            result[key] = value[:300] if isinstance(value, str) else value
    raw = meta.get("raw_capture")
    if isinstance(raw, dict) and isinstance(raw.get("text"), str):
        result["raw_capture"] = {"text": raw["text"][:max_chars],
            "truncated": bool(raw.get("truncated")) or len(raw["text"]) > max_chars,
            "selection_method": str(raw.get("selection_method", "NATIVE_SOURCE_TEXT"))[:100]}
    page = meta.get("page_metadata")
    if isinstance(page, dict):
        observed = inspect_evidence(item)
        public_page = dict(observed["page_observations"])
        for key in ("title", "author", "published", "content_scope", "extraction_method", "pdf_source_sha256"):
            if isinstance(page.get(key), str):
                public_page[key] = page[key][:300]
        for key in ("pdf_page_count", "pdf_truncated", "table_structure_verified"):
            if type(page.get(key)) in (int, bool):
                public_page[key] = page[key]
        result["page_metadata"] = public_page
    return result


def summarize_inspections(items: list) -> dict:
    inspections = [inspect_evidence(item) for item in items]
    return {
        "schema_version": SCHEMA, "items": len(inspections),
        "captured_chars": sum(item["captured_chars"] for item in inspections),
        "raw_words": sum(item["text_metrics"]["raw_words"] for item in inspections),
        "raw_utf8_bytes": sum(item["text_metrics"]["raw_utf8_bytes"] for item in inspections),
        "readable_words": sum(item["text_metrics"]["readable_words"] for item in inspections),
        "readable_utf8_bytes": sum(item["text_metrics"]["readable_utf8_bytes"] for item in inspections),
        "discovery_only_items": sum(item["evidentiary_use"] == "DISCOVERY_ONLY" for item in inspections),
        "missing_field_counts": {key: sum(key in item["missing_fields"] for item in inspections)
                                 for key in ("title", "url", "author", "published_at", "captured_text")},
        "inspections_truncated": sum(item["inspection_truncated"] for item in inspections),
        "source_completeness": "UNKNOWN", "claim_accuracy": None,
    }
