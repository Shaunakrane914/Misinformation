"""Aegis Protocol — arXiv Academic Preprints & Research Adapter.

Provides scientific preprint intelligence for Trending and Scout:
- Research paper preprints across AI/ML, computer science, quantitative finance, and economics
- Authors, institutional primary category, publication timestamps, and arXiv IDs
- Comprehensive full abstracts and research methodology descriptions (up to 25,000 characters)
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http
from backend.services.agent_reach.channels import (
    CandidateSource,
    ContentDepth,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.url_validator import validate_url_safe
from backend.infrastructure.acquisition.adapters.expansion_safety import parse_bounded_xml

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "https://export.arxiv.org/api/query"
DEFAULT_ARXIV_HEADERS = {
    "User-Agent": "AegisProtocol/1.0 (academic-research; intelligence@aegis-protocol.org)",
}
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivAdapter(PlatformAdapter):
    """Acquires scientific preprints and technical research from arXiv."""

    @property
    def platform(self) -> str:
        return "arxiv"

    @property
    def backend_id(self) -> str:
        return "arxiv_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("arxiv", "academic_papers", "preprints", "research_papers"):
            return True
        return "arxiv.org" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Search arXiv for papers matching the given query."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        # Format query for arXiv API
        search_terms = re.sub(r"[^\w\s]", " ", clean_q).split()
        arxiv_q = "+AND+".join(f"all:{urllib.parse.quote(term)}" for term in search_terms[:5])
        api_url = f"{ARXIV_API_BASE}?search_query={arxiv_q}&start=0&max_results={min(limit, 10)}&sortBy=relevance&sortOrder=descending"

        if not validate_url_safe(api_url)[0]:
            return candidates

        try:
            resp = fetch_public_http(api_url, headers=DEFAULT_ARXIV_HEADERS, timeout=6.0)
            if resp.status_code != 200:
                logger.warning("[ArxivAdapter] Search HTTP %d for query '%s'", resp.status_code, clean_q)
                return candidates

            root = parse_bounded_xml(resp.body.decode("utf-8", errors="replace"))
            entries = root.findall("atom:entry", ATOM_NS)

            for entry in entries:
                id_elem = entry.find("atom:id", ATOM_NS)
                title_elem = entry.find("atom:title", ATOM_NS)
                summary_elem = entry.find("atom:summary", ATOM_NS)
                published_elem = entry.find("atom:published", ATOM_NS)
                author_elems = entry.findall("atom:author/atom:name", ATOM_NS)
                category_elem = entry.find("atom:category", ATOM_NS)

                raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                paper_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
                title = re.sub(r"\s+", " ", title_elem.text.strip()) if title_elem is not None and title_elem.text else "Untitled Preprint"
                summary = re.sub(r"\s+", " ", summary_elem.text.strip()) if summary_elem is not None and summary_elem.text else ""
                published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
                authors = [a.text.strip() for a in author_elems if a is not None and a.text]
                primary_category = category_elem.attrib.get("term", "") if category_elem is not None else ""

                paper_url = f"https://arxiv.org/abs/{paper_id}"
                pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

                candidates.append(
                    CandidateSource(
                        url=paper_url,
                        canonical_url=paper_url,
                        platform="arxiv",
                        title=f"{title} [arXiv:{paper_id}]",
                        snippet=summary[:350] + ("..." if len(summary) > 350 else ""),
                        metadata={
                            "arxiv_id": paper_id,
                            "authors": authors,
                            "published": published,
                            "primary_category": primary_category,
                            "pdf_url": pdf_url,
                            "full_abstract": summary,
                            "primary_source": True,
                            "official_source": False,
                        },
                    )
                )
        except Exception as exc:
            logger.warning("[ArxivAdapter] Discovery error for '%s': %s", clean_q, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch and structure full preprint document including full abstract and citations."""
        url = candidate.canonical_url or candidate.url
        arxiv_id = candidate.metadata.get("arxiv_id")
        if not arxiv_id:
            m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url)
            arxiv_id = m.group(1) if m else ""

        full_abstract = candidate.metadata.get("full_abstract", "")
        title = candidate.title or "Scientific Preprint"
        authors = candidate.metadata.get("authors", [])
        published = candidate.metadata.get("published", "")
        category = candidate.metadata.get("primary_category", "")

        # If abstract not in metadata, fetch via arXiv API
        if not full_abstract and arxiv_id:
            api_url = f"{ARXIV_API_BASE}?id_list={arxiv_id}"
            if validate_url_safe(api_url)[0]:
                try:
                    resp = fetch_public_http(api_url, headers=DEFAULT_ARXIV_HEADERS, timeout=6.0)
                    if resp.status_code == 200:
                        root = parse_bounded_xml(resp.body.decode("utf-8", errors="replace"))
                        entry = root.find("atom:entry", ATOM_NS)
                        if entry is not None:
                            summary_elem = entry.find("atom:summary", ATOM_NS)
                            if summary_elem is not None and summary_elem.text:
                                full_abstract = re.sub(r"\s+", " ", summary_elem.text.strip())
                            title_elem = entry.find("atom:title", ATOM_NS)
                            if title_elem is not None and title_elem.text:
                                title = re.sub(r"\s+", " ", title_elem.text.strip())
                except Exception as exc:
                    logger.debug("[ArxivAdapter] Detail fetch notice for %s: %s", arxiv_id, type(exc).__name__)

        if not full_abstract.strip():
            return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
        content = f"# {title}\n\n"
        content += f"**arXiv ID**: {arxiv_id} | **Primary Category**: {category}\n"
        if authors:
            content += f"**Authors**: {', '.join(authors)}\n"
        if published:
            content += f"**Published Date**: {published}\n"
        content += f"**Official Paper Record**: {url}\n\n"
        content += "## Abstract & Research Summary\n\n"
        content += full_abstract + "\n\n"
        content += "## Citation & Scientific Provenance\n\n"
        content += f"Preprint archived on open-access repository arXiv.org under identifier {arxiv_id}. "
        content += "Scientific claims, empirical methodologies, and findings described herein are direct author disclosures."

        capped = content[:25000]

        return FetchedDocument(
            url=url,
            status="SUCCESS",
            raw_content=capped,
            backend_id=self.backend_id,
            raw_metadata={
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "published": published,
                "primary_category": category,
                "wordcount": len(capped.split()),
            },
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into academic primary EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        title = document.raw_metadata.get("title") or candidate.title
        content = document.raw_content
        authors = document.raw_metadata.get("authors") or []
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "") if authors else "arXiv Authors"

        fragment = EvidenceFragment(
            platform="arxiv",
            channel_name="arxiv",
            url=candidate.url,
            title=f"{title} (Scientific Preprint)",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author=author_str,
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "arxiv",
                "backend": self.backend_id,
                "url": candidate.url,
                "arxiv_id": document.raw_metadata.get("arxiv_id"),
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "primary",
                "source_tier": "tier_1_official",
                "source_domain": "arxiv.org",
                "source_independence_group": "arxiv.org",
                "char_count": len(content),
                "word_count": len(content.split()),
                "arxiv_id": document.raw_metadata.get("arxiv_id"),
                "authors": authors,
                "published": document.raw_metadata.get("published"),
            },
        )
        return [fragment]
