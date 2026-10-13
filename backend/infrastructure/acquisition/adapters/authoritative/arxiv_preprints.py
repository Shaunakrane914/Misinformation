"""
Aegis Protocol — arXiv Academic & Preprint Acquisition Adapter
==============================================================
Acquires scientific literature, preprints, author attributions, and paper abstracts
directly from the open arXiv API (export.arxiv.org/api/query).
Enforces 15-point source contract, XML sanitization, SSRF safety, and bounded payload limits.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.network.http import (
    decode_bounded_http_body,
    fetch_public_http,
    BoundedHTTPResponse,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode

logger = logging.getLogger(__name__)

# Atom namespace used by arXiv API
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def fetch_arxiv_preprints(
    query: str,
    limit: int = 5,
    http_fetcher: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Acquire scientific preprints from open arXiv API.
    URL: http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={limit}
    """
    fetcher = http_fetcher if http_fetcher is not None else fetch_public_http
    clean_q = query.strip()
    # If query is a raw arXiv ID (e.g. 2301.07041 or hep-th/9901001)
    id_match = re.search(r'\b(?:\d{4}\.\d{4,5}|[a-z\-]+/\d{7})\b', clean_q)
    if id_match:
        url = f"http://export.arxiv.org/api/query?id_list={id_match.group(0)}"
    else:
        encoded = urllib.parse.quote(clean_q)
        url = f"http://export.arxiv.org/api/query?search_query=all:{encoded}&start=0&max_results={min(limit, 10)}"

    headers = {
        "Accept": "application/atom+xml",
        "User-Agent": "AegisProtocol MisinfoResearch/1.0",
        "Accept-Encoding": "identity",
    }

    try:
        response: BoundedHTTPResponse = fetcher(
            url,
            headers=headers,
            timeout=5.0,
            max_bytes=1_000_000,
        )
        raw_bytes = decode_bounded_http_body(response, max_bytes=1_000_000)
        root = ET.fromstring(raw_bytes)
    except Exception as e:
        logger.warning(f"[arXiv] Fetch failure for '{clean_q}': {e}")
        return {
            "status": "FAILED",
            "error": str(e),
            "items": [],
            "transport": {"endpoint": url}
        }

    items: List[Dict[str, Any]] = []

    for entry in root.findall(f"{ATOM_NS}entry")[:limit]:
        entry_id = (entry.findtext(f"{ATOM_NS}id") or "").strip()
        raw_title = (entry.findtext(f"{ATOM_NS}title") or "").strip()
        title = " ".join(raw_title.split())

        raw_summary = (entry.findtext(f"{ATOM_NS}summary") or "").strip()
        summary = " ".join(raw_summary.split())

        published = (entry.findtext(f"{ATOM_NS}published") or "").strip()
        updated = (entry.findtext(f"{ATOM_NS}updated") or "").strip()

        authors = []
        for author_elem in entry.findall(f"{ATOM_NS}author"):
            name = (author_elem.findtext(f"{ATOM_NS}name") or "").strip()
            if name:
                authors.append(name)

        doi_elem = entry.find(f"{ARXIV_NS}doi")
        doi = (doi_elem.text or "").strip() if doi_elem is not None else ""

        cat_elem = entry.find(f"{ARXIV_NS}primary_category")
        category = cat_elem.get("term", "") if cat_elem is not None else ""

        pdf_url = ""
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
                break

        items.append({
            "arxiv_id": entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "published": published,
            "updated": updated,
            "doi": doi,
            "category": category,
            "pdf_url": pdf_url,
            "abs_url": entry_id if entry_id.startswith("http") else f"https://arxiv.org/abs/{entry_id}",
        })

    return {
        "status": "SUCCESS",
        "items": items,
        "transport": {
            "endpoint": url,
            "status_code": response.status_code,
            "latency_ms": response.latency_ms,
        }
    }


def normalize_arxiv_items(
    items: List[Dict[str, Any]],
    query_id: str = "",
    query_class: str = "",
    query_text: str = ""
) -> List[EvidenceFragment]:
    """Normalize arXiv preprint items into typed EvidenceFragments."""
    fragments: List[EvidenceFragment] = []
    for item in items:
        authors_str = ", ".join(item["authors"][:3])
        if len(item["authors"]) > 3:
            authors_str += " et al."

        title = f"[arXiv:{item['arxiv_id']}] {item['title']}"
        snippet = (
            f"Scientific Preprint: {item['title']}. Authors: {authors_str}. "
            f"Published: {item['published']}. Category: {item['category']}. "
            f"Abstract: {item['summary'][:240]}"
        )
        frag = EvidenceFragment(
            platform="arxiv",
            title=title,
            content=item["summary"],
            snippet=snippet,
            url=item["abs_url"],
            author=authors_str or "arXiv Academic Contributor",
            published=item["published"],
            score=90.0,
            retrieval_method="arxiv_atom_api",
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id="arxiv-export-api",
            channel_name="arxiv",
            requested_channel="arxiv",
            actual_retrieval_channel="arxiv",
            content_depth="DIRECT_CONTENT",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            raw_metadata={
                "arxiv_id": item["arxiv_id"],
                "authors": item["authors"],
                "category": item["category"],
                "doi": item["doi"],
                "pdf_url": item["pdf_url"],
                "source_role": "PRIMARY",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_authority": "ACADEMIC_PREPRINT",
                "primary_source": True,
                "reliability_score": 0.90,
                "canonical_url": item["abs_url"],
            }
        )
        fragments.append(frag)
    return fragments
