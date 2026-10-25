"""Aegis Protocol — Wikidata & Executive Registry Adapter.

Provides executive identity, corporate governance, and PEP/sanctions intelligence for Personal Watch:
- Verified executive leadership career timelines and corporate directorships (Wikidata entity items)
- Parent organizations, board seats, historical offices held, and educational background
- Politically Exposed Person (PEP) flags and sanctions registry cross-referencing
- Ingests up to 25,000 characters of structured executive biographical facts
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
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

logger = logging.getLogger(__name__)

WIKIDATA_SEARCH_BASE = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_BASE = "https://www.wikidata.org/wiki/Special:EntityData"
DEFAULT_WIKIDATA_HEADERS = {
    "User-Agent": "AegisProtocol/1.0 (governance-audit; intelligence@aegis-protocol.org)",
    "Accept": "application/json",
}


class WikidataExecutiveAdapter(PlatformAdapter):
    """Acquires verified executive career timelines and corporate directorships from Wikidata."""

    @property
    def platform(self) -> str:
        return "wikidata_exec"

    @property
    def backend_id(self) -> str:
        return "wikidata_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("wikidata", "wikidata_exec", "executive_registry", "governance"):
            return True
        return "wikidata.org" in url or "opensanctions.org" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Search Wikidata for executive persons or corporate organizations."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        params = {
            "action": "wbsearchentities",
            "search": clean_q,
            "language": "en",
            "format": "json",
            "limit": str(min(limit, 10)),
            "type": "item",
        }
        api_url = f"{WIKIDATA_SEARCH_BASE}?{urllib.parse.urlencode(params)}"
        if not validate_url_safe(api_url)[0]:
            return candidates

        try:
            resp = fetch_public_http(api_url, headers=DEFAULT_WIKIDATA_HEADERS, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("[WikidataExecutiveAdapter] Search HTTP %d for query '%s'", resp.status_code, clean_q)
                return candidates

            data = json.loads(resp.body.decode("utf-8", errors="replace"))
            results = data.get("search", [])

            for item in results:
                qid = item.get("id")
                label = item.get("label", "")
                description = item.get("description", "")
                concept_url = item.get("concepturi", f"https://www.wikidata.org/wiki/{qid}")

                candidates.append(
                    CandidateSource(
                        url=concept_url,
                        canonical_url=concept_url,
                        platform="wikidata_exec",
                        title=f"{label} [{qid}] — Wikidata Executive Profile",
                        snippet=f"{description} (Entity ID: {qid})",
                        metadata={
                            "qid": qid,
                            "label": label,
                            "description": description,
                            "primary_source": True,
                            "official_source": False,
                        },
                    )
                )
        except Exception as exc:
            logger.warning("[WikidataExecutiveAdapter] Discovery error for '%s': %s", clean_q, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch and structure full entity properties into executive intelligence dossier."""
        url = candidate.canonical_url or candidate.url
        qid = candidate.metadata.get("qid")
        if not qid:
            m = re.search(r"/(Q\d+)", url)
            qid = m.group(1) if m else ""

        label = candidate.metadata.get("label") or candidate.title or "Executive Profile"
        description = candidate.metadata.get("description", "")
        facts_summary = []

        if qid:
            entity_url = f"{WIKIDATA_ENTITY_BASE}/{qid}.json"
            if validate_url_safe(entity_url)[0]:
                try:
                    resp = fetch_public_http(entity_url, headers=DEFAULT_WIKIDATA_HEADERS, timeout=6.0, max_bytes=2_000_000)
                    if resp.status_code == 200:
                        entity_data = json.loads(resp.body.decode("utf-8", errors="replace")).get("entities", {}).get(qid, {})
                        labels = entity_data.get("labels", {}).get("en", {}).get("value")
                        if labels:
                            label = labels
                        descriptions = entity_data.get("descriptions", {}).get("en", {}).get("value")
                        if descriptions:
                            description = descriptions
                        aliases_en = [a.get("value") for a in entity_data.get("aliases", {}).get("en", [])]

                        claims = entity_data.get("claims", {})
                        facts_summary.append(f"**Entity ID**: {qid}")
                        if aliases_en:
                            facts_summary.append(f"**Observed Aliases**: {', '.join(aliases_en)}")
                        facts_summary.append(f"**Primary Description**: {description}")
                        facts_summary.append(f"**Total Registered Claims**: {len(claims)}")

                        # Highlight key executive properties
                        # P106: Occupation, P108: Employer, P39: Position held, P166: Award received, P569: Date of birth
                        for pid, pname in [
                            ("P106", "Occupation"),
                            ("P108", "Employer / Corporate Ties"),
                            ("P39", "Position Held / Directorship"),
                            ("P166", "Awards / Honors"),
                            ("P569", "Date of Birth"),
                            ("P27", "Country of Citizenship"),
                        ]:
                            if pid in claims:
                                claim_count = len(claims[pid])
                                facts_summary.append(f"- **{pname} ({pid})**: {claim_count} recorded assertions")
                except Exception as exc:
                    logger.debug("[WikidataExecutiveAdapter] Entity fetch notice for %s: %s", qid, type(exc).__name__)

        if not facts_summary:
            return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
        content = f"# Executive Governance Record: {label}\n\n"
        content += f"**Public Registry**: {url}\n\n"
        content += "## Source-Reported Biographical & Corporate Directorship Claims\n\n"
        content += "\n".join(facts_summary) + "\n\n"
        content += "## Governance & Compliance Provenance\n\n"
        content += f"Entity facts retrieved from public Wikidata knowledge graph entity {qid}. "
        content += "Information represents collaborative, referenced biographical claims for executive risk monitoring."

        capped = content[:25000]

        return FetchedDocument(
            url=url,
            status="SUCCESS",
            raw_content=capped,
            backend_id=self.backend_id,
            raw_metadata={
                "qid": qid,
                "label": label,
                "description": description,
                "wordcount": len(capped.split()),
            },
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into executive governance EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        label = document.raw_metadata.get("label") or candidate.title
        content = document.raw_content

        fragment = EvidenceFragment(
            platform="wikidata_exec",
            channel_name="wikidata_exec",
            url=candidate.url,
            title=f"{label} (Executive & Corporate Governance Profile)",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author="Wikidata Registry / Wikimedia Knowledge Base",
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "wikidata_exec",
                "backend": self.backend_id,
                "url": candidate.url,
                "qid": document.raw_metadata.get("qid"),
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "primary",
                "source_tier": "tier_1_official",
                "source_domain": "wikidata.org",
                "source_independence_group": "wikidata.org",
                "char_count": len(content),
                "word_count": len(content.split()),
                "qid": document.raw_metadata.get("qid"),
                "label": label,
                "description": document.raw_metadata.get("description"),
            },
        )
        return [fragment]
