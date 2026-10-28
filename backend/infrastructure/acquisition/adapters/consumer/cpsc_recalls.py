"""Bounded CPSC recall JSON records, with no webpage or article-body fallback.

The documented public endpoint is described at:
https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information
Recall notices remain issuing-agency assertions, not counterfeit adjudications.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch
from backend.services.agent_reach.channels import (
    CandidateSource, EvidenceFragment, FetchedDocument, RetrievalMode, RetrievalRequest,
)


CPSC_API_URL = "https://www.saferproducts.gov/RestWebServices/Recall"
MAX_RESPONSE_BYTES = 1_000_000
MAX_RESULTS = 5
MAX_SCANNED_RECORDS = 100
MAX_CONTENT_CHARS = 25_000
MAX_QUERY_CHARS = 300
ISSUING_AGENCY = "U.S. Consumer Product Safety Commission"


def _canonical_recall_url(value):
    """Accept observed individual CPSC recall pages, never a claimed platform."""
    if not isinstance(value, str) or any(ord(character) < 32 for character in value):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"}
                or parsed.hostname not in {"cpsc.gov", "www.cpsc.gov"}
                or parsed.username or parsed.password
                or parsed.port not in {None, 80, 443}
                or "\\" in parsed.path
                or not re.fullmatch(r"/(?:en/)?recalls/\d{4}/[^/]+/?", parsed.path, re.I)):
            return None
        return urlunsplit(("https", "www.cpsc.gov", parsed.path.rstrip("/"), "", ""))
    except ValueError:
        return None


def _is_api_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        parameters = parse_qs(parsed.query, keep_blank_values=True)
        return (parsed.scheme == "https" and parsed.netloc == "www.saferproducts.gov"
                and parsed.path == "/RestWebServices/Recall" and not parsed.fragment
                and set(parameters) == {"format", "RecallTitle"}
                and parameters["format"] == ["json"] and len(parameters["RecallTitle"]) == 1
                and 0 < len(parameters["RecallTitle"][0].strip()) <= MAX_QUERY_CHARS)
    except ValueError:
        return False


def _record_fields(record):
    """Validate genuine-schema fields without paraphrasing the source values."""
    if not isinstance(record, dict):
        return None
    try:
        if len(json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_RESPONSE_BYTES:
            return None
    except (TypeError, ValueError, OverflowError, RecursionError):
        return None
    recall_id = record.get("RecallID")
    title, issue_date = record.get("Title"), record.get("RecallDate")
    canonical_url = _canonical_recall_url(record.get("URL"))
    if (not isinstance(recall_id, int) or isinstance(recall_id, bool) or recall_id <= 0
            or not isinstance(title, str) or not title.strip()
            or not isinstance(issue_date, str) or not canonical_url):
        return None
    try:
        datetime.fromisoformat(issue_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    description = record.get("Description", "")
    if not isinstance(description, str):
        return None
    narratives = {}
    for key in ("Hazards", "Remedies"):
        entries = record.get(key, [])
        if not isinstance(entries, list) or any(
                not isinstance(entry, dict) or not isinstance(entry.get("Name"), str)
                for entry in entries):
            return None
        narratives[key] = [entry["Name"] for entry in entries]
    if not any(text.strip() for text in [description, *narratives["Hazards"], *narratives["Remedies"]]):
        return None
    return {"recall_id": recall_id, "title": title, "canonical_url": canonical_url,
            "issue_date": issue_date, "description": description,
            "hazards": narratives["Hazards"], "remedies": narratives["Remedies"]}


class CpscRecallsAdapter(PlatformAdapter):
    """Discover notices once, then normalize only the observed API records."""

    @property
    def platform(self):
        return "cpsc_recalls"

    @property
    def backend_id(self):
        return "cpsc_recall_api"

    def can_handle(self, candidate: CandidateSource):
        return _canonical_recall_url(candidate.canonical_url or candidate.url) is not None

    def health(self):
        return {"platform": self.platform, "backend_id": self.backend_id,
                "status": "NOT_PROBED", "auth_required": False,
                "live_health_verified": False, "content_scope": "OFFICIAL_RECALL_RECORD"}

    def discover(self, query: str, limit: int = MAX_RESULTS):
        try:
            limit = min(MAX_RESULTS, max(0, int(limit)))
        except (TypeError, ValueError, OverflowError):
            return []
        if not isinstance(query, str) or not query.strip() or not limit:
            return []
        query = query.strip()[:MAX_QUERY_CHARS]
        api_url = CPSC_API_URL + "?" + urlencode({"format": "json", "RecallTitle": query})
        try:
            from backend.services.research.source_registry import source_body_scope, source_registry
            if not source_registry.body_decision(api_url)['eligible']:
                return []
            with source_body_scope(source_registry):
                response = safe_fetch(api_url, headers={"Accept": "application/json", "User-Agent": "AegisProtocol/1.0"},
                                      timeout=5.0, max_bytes=MAX_RESPONSE_BYTES, max_redirects=0)
            if (response.status_code != 200 or response.endpoint != api_url
                    or len(response.redirect_chain) > 1 or len(response.body) > MAX_RESPONSE_BYTES
                    or (response.content_type or "").split(";", 1)[0].strip().lower()
                    not in {"application/json", "text/json"}):
                return []
            records = json.loads(response.body)
            if not isinstance(records, list):
                return []
        except Exception:
            # A blocked/failed/oversized response supplies no positive evidence.
            return []
        candidates = []
        seen = set()
        for index, record in enumerate(records[:MAX_SCANNED_RECORDS]):
            fields = _record_fields(record)
            if not fields or fields["recall_id"] in seen:
                continue
            seen.add(fields["recall_id"])
            candidates.append(CandidateSource(
                url=fields["canonical_url"], canonical_url=fields["canonical_url"],
                platform=self.platform, title=fields["title"],
                snippet=fields["description"][:400], discovery_query=query,
                metadata={"cpsc_record": deepcopy(record), "api_url": api_url,
                          "record_index": index, "discovery_only": True,
                          "cpsc_recall_id": fields["recall_id"], "cpsc_api_url": api_url,
                          "cpsc_record_index": index, "cpsc_issue_date": fields["issue_date"],
                          "content_scope": "OFFICIAL_RECALL_RECORD", "article_body_acquired": False},
            ))
            if len(candidates) == limit:
                break
        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest):
        """No inferred RecallID, repeated request, or canonical-webpage fallback."""
        url = _canonical_recall_url(candidate.canonical_url or candidate.url)
        record = candidate.metadata.get("cpsc_record")
        api_url = candidate.metadata.get("api_url")
        index = candidate.metadata.get("record_index")
        fields = _record_fields(record)
        if (not url or not fields or fields["canonical_url"] != url or not _is_api_url(api_url)
                or not isinstance(index, int) or isinstance(index, bool)
                or not 0 <= index < MAX_SCANNED_RECORDS):
            return FetchedDocument(url=candidate.canonical_url or candidate.url,
                                   status="NO_ELIGIBLE_API_RECORD", backend_id=self.backend_id,
                                   failure_reason="An observed matching CPSC API record is required")
        encoded = json.dumps(record, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_RESPONSE_BYTES:
            return FetchedDocument(url=url, status="RESPONSE_TOO_LARGE", backend_id=self.backend_id)
        return FetchedDocument(
            url=url, status="SUCCESS", backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.DIRECT_API.value, raw_content=encoded,
            raw_metadata={"cpsc_record": deepcopy(record), "api_url": api_url, "record_index": index,
                          "content_scope": "OFFICIAL_RECALL_RECORD", "article_body_acquired": False},
        )

    def normalize(self, document: FetchedDocument, candidate: CandidateSource, request: RetrievalRequest):
        if document.status != "SUCCESS" or document.backend_id != self.backend_id:
            return []
        record = document.raw_metadata.get("cpsc_record")
        fields = _record_fields(record)
        api_url = document.raw_metadata.get("api_url")
        index = document.raw_metadata.get("record_index")
        if (not fields or not _is_api_url(api_url)
                or not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < MAX_SCANNED_RECORDS
                or fields["canonical_url"] != _canonical_recall_url(document.url)
                or fields["canonical_url"] != _canonical_recall_url(candidate.canonical_url or candidate.url)):
            return []
        content = (f"RecallID: {fields['recall_id']}\nTitle: {fields['title']}\n"
                   f"RecallDate: {fields['issue_date']}\nURL: {fields['canonical_url']}\n"
                   f"Description: {fields['description']}\n"
                   + "\n".join("Hazard: " + value for value in fields["hazards"]) + "\n"
                   + "\n".join("Remedy: " + value for value in fields["remedies"]))
        truncated = len(content) > MAX_CONTENT_CHARS
        content = content[:MAX_CONTENT_CHARS]
        provenance = {name: f"/{index}/{source}" for name, source in (
            ("recall_id", "RecallID"), ("title", "Title"), ("canonical_url", "URL"),
            ("issue_date", "RecallDate"), ("description", "Description"),
            ("hazards", "Hazards"), ("remedies", "Remedies"),
        )}
        return [EvidenceFragment(
            platform=self.platform, channel_name=self.platform, url=fields["canonical_url"],
            title=fields["title"], content=content, snippet=fields["description"][:400],
            author=ISSUING_AGENCY, published=fields["issue_date"],
            content_depth="STRUCTURED_EVIDENCE", retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{"platform": self.platform, "backend": self.backend_id,
                                "url": api_url, "record_index": index,
                                "RecallID": fields["recall_id"], "retrieval_mode": RetrievalMode.DIRECT_API.value}],
            raw_metadata={**fields, "RecallID": fields["recall_id"], "original_record": deepcopy(record),
                          "api_url": api_url, "field_provenance": provenance,
                          "source_role": "ISSUING_AGENCY", "source_assertion_only": True,
                          "primary_source": True, "official_source": True,
                          "source_domain": "cpsc.gov", "source_independence_group": "cpsc.gov",
                          "content_scope": "OFFICIAL_RECALL_RECORD", "article_body_acquired": False,
                          "truncated": truncated, "char_count": len(content), "word_count": len(content.split())},
        )]
