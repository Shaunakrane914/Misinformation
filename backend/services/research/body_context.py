"""Reconcile observed body metadata without changing raw text or source identity."""
import hashlib

from backend.infrastructure.acquisition.adapters.web.page_extraction import observe_anchored_article_body, observe_text_structure


def reconcile_captured_context(item):
    if not item.metadata.get("read_success") or not item.content:
        return
    page = item.metadata.get("page_metadata")
    if not isinstance(page, dict):
        page = item.metadata["page_metadata"] = {}
    previous_recovery = page.get("article_body_recovery")
    if isinstance(previous_recovery, dict) and previous_recovery.get("source_text_sha256") != hashlib.sha256(item.content.encode("utf-8")).hexdigest():
        # Replaced bytes cannot inherit an earlier capture's extraction label.
        page.pop("article_body_recovery", None)
        original_quality = page.pop("original_body_quality", None)
        page["body_quality"] = dict(original_quality) if isinstance(original_quality, dict) else {"body_kind": "UNCLASSIFIED_PAGE"}
        page["body_kind"] = page["body_quality"].get("body_kind", "UNCLASSIFIED_PAGE")
    title = page.get("title")
    if isinstance(title, str) and title.strip() and title.strip().casefold() not in {"read more", "learn more", "continue reading"}:
        title = " ".join(title.split())[:500]
        if title != item.title:
            item.metadata.setdefault("discovery_title", item.title)
            item.title = title
    conflict = page.get("publication_metadata_conflict")
    published = None if conflict else page.get("published")
    if not published:
        # Only unambiguous Article/NewsArticle declarations from this capture.
        declared = [node.get("datePublished") for node in page.get("declared_structured_data", [])
                    if isinstance(node, dict) and node.get("@type") in {"Article", "NewsArticle", "ReportageNewsArticle", "AnalysisNewsArticle", "BlogPosting", "ScholarlyArticle"}
                    and node.get("datePublished")]
        if not conflict and declared and len(set(declared)) == 1:
            published = declared[0]
    if item.metadata.get("temporal_required") and not published:
        # A news-feed/index date is useful for selecting a provisional read,
        # but cannot establish the captured article's original publication.
        # Fetch time, sitemap lastmod and editorial update are never substitutes.
        if item.published_at:
            item.metadata.setdefault("discovery_published_at", item.published_at)
        item.published_at = ""
        item.metadata["publication_time_basis"] = ("CONFLICTING_CAPTURED_DECLARATIONS" if conflict
                                                   else "CAPTURED_PUBLICATION_NOT_OBSERVED")
    if conflict:
        if item.published_at:
            item.metadata.setdefault("discovery_published_at", item.published_at)
        item.published_at = ""
        item.metadata["publication_time_basis"] = "CONFLICTING_CAPTURED_DECLARATIONS"
    if isinstance(published, str) and published.strip() and published != item.published_at:
        if item.published_at:
            item.metadata.setdefault("discovery_published_at", item.published_at)
        item.published_at = published.strip()[:100]
        item.metadata["publication_time_basis"] = "CAPTURED_PUBLISHER_DECLARATION_UNVERIFIED"
        item.metadata["publication_time_source"] = page.get("publication_time_source") or (
            "JSONLD:datePublished" if not page.get("published") else "CAPTURED_PAGE_METADATA")
    # These are properties of acquired text, never source credibility scores.
    item.metadata["readable_word_count"] = len(item.content.split())
    item.metadata["readable_character_count"] = len(item.content)
    item.metadata["readable_text_sha256"] = hashlib.sha256(item.content.encode("utf-8")).hexdigest()
    # A visible date line is inspectable but not automatically a publication
    # timestamp. In particular, never promote a future event date to freshness.
    observed = observe_text_structure(item.content, page.get("headings", []))
    for key, value in observed.items():
        if key not in page:
            page[key] = value
    recovery = observe_anchored_article_body(item.content, page)
    if recovery:
        # Keep the original DOM-quality observation and every captured byte.
        # Only exact title/byline-anchored prose spans acquire an article-body
        # extraction label; relevance, attribution and evidence gates still run.
        page.setdefault("original_body_quality", dict(page.get("body_quality") or {}))
        page["article_body_recovery"] = recovery
        page["body_kind"] = "ARTICLE_BODY"
        page["body_quality"] = {"body_kind": "ARTICLE_BODY", "paragraph_count": len(recovery["spans"]),
            "scope": recovery["scope"], "basis": recovery["basis"], "evidence_qualified": False}
