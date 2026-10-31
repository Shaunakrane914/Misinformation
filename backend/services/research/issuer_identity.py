"""Provenanced issuer identities; incorporation does not determine SEC eligibility.

Exact aliases only. Authoritative submissions/index captures can populate the
bounded cache for any issuer. Missing CIK means no verified SEC route, not proof
that an issuer has no US reporting obligation. This module never makes requests.
"""
import copy
import json
import re
import threading
import time
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlsplit


def identity_key(value):
    value = re.sub(r"\s*\([A-Z0-9.^-]+\)\s*$", "", str(value or ""), flags=re.I)
    value = re.sub(r"^(?:NASDAQ|NYSE|NSE|BSE):\s*", "", value, flags=re.I)
    if value.isdigit() and len(value) <= 10:
        value = value.zfill(10)
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def clean_base_name(name: str) -> List[str]:
    """Strip common corporate entity suffixes to match informal entity queries."""
    clean = re.sub(r"[^\w\s]", " ", str(name or ""))
    suffix_pattern = re.compile(
        r"\s+(?:INC|INCORPORATED|CORP|CORPORATION|LTD|LIMITED|CO|COMPANY|LLC|PLC|NEW|OLD|VA|DE|HOLDINGS?|GROUP)\s*$",
        re.I,
    )
    stem_pattern = re.compile(
        r"\s+(?:WHOLESALE|RETAIL|TECHNOLOGIES|NETWORKS|SYSTEMS|INTERNATIONAL|ENTERPRISES|COM)\s*$",
        re.I,
    )
    base = clean.strip()
    while True:
        subbed = suffix_pattern.sub("", base).strip()
        if subbed == base:
            break
        base = subbed
    results = []
    if len(base) >= 2 and base.upper() != clean.strip().upper():
        results.append(base)
    stem = stem_pattern.sub("", base).strip()
    if len(stem) >= 2 and stem.upper() != base.upper():
        results.append(stem)
    return results


class IssuerIdentityResolver:
    def __init__(self, records=(), capacity: int = 16384):
        self.capacity = capacity
        self._records: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._alias_to_keys: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._last_sync_failed_at: Optional[float] = None
        self._last_sync_error: Optional[str] = None
        self._last_sync_provenance: Optional[Dict[str, Any]] = None
        for record in records:
            self.register(record)

    def _extract_alias_keys(self, row: Dict[str, Any]) -> Set[str]:
        keys = set()
        for raw in [
            row.get("legal_name"),
            row.get("cik"),
            *row.get("aliases", []),
            *[listing["symbol"] for listing in row.get("listings", []) if isinstance(listing, dict)],
        ]:
            if raw:
                k = identity_key(raw)
                if k:
                    keys.add(k)
                for base in clean_base_name(raw):
                    bk = identity_key(base)
                    if bk:
                        keys.add(bk)
        return keys

    def register(self, record):
        row = copy.deepcopy(record)
        if not row.get("legal_name") or not row.get("provenance"):
            raise ValueError("Identity requires legal name and observed provenance")
        cik = row.get("cik")
        if cik is not None and not re.fullmatch(r"\d{10}", cik):
            raise ValueError("Invalid CIK")
        for evidence in row["provenance"]:
            u = urlsplit(evidence.get("source_url", ""))
            if u.scheme != "https" or not u.hostname or u.username or u.password:
                raise ValueError("Invalid identity provenance")
        row["provenance"] = (
            row["provenance"][:4] + row["provenance"][-12:]
            if len(row["provenance"]) > 16
            else row["provenance"]
        )
        key = cik or identity_key(row["legal_name"])
        with self._lock:
            if key in self._records:
                old = self._records[key]
                for ak in self._extract_alias_keys(old):
                    self._alias_to_keys[ak].discard(key)
                    if not self._alias_to_keys[ak]:
                        self._alias_to_keys.pop(ak, None)

            self._records[key] = row
            self._records.move_to_end(key)

            for ak in self._extract_alias_keys(row):
                self._alias_to_keys[ak].add(key)

            while len(self._records) > self.capacity:
                popped_key, popped_row = self._records.popitem(last=False)
                for ak in self._extract_alias_keys(popped_row):
                    self._alias_to_keys[ak].discard(popped_key)
                    if not self._alias_to_keys[ak]:
                        self._alias_to_keys.pop(ak, None)
        return copy.deepcopy(row)

    def resolve(self, query):
        key = identity_key(query)
        if not key:
            return {
                "status": "UNRESOLVED",
                "query": query,
                "cik": None,
                "candidate_legal_names": [],
                "sec_reporting_status": "UNKNOWN",
                "provenance": [],
            }
        with self._lock:
            matching_keys = self._alias_to_keys.get(key, set())
            matches = [self._records[k] for k in matching_keys if k in self._records]
        if len(matches) != 1:
            return {
                "status": "AMBIGUOUS" if len(matches) > 1 else "UNRESOLVED",
                "query": query,
                "cik": None,
                "candidate_legal_names": [r["legal_name"] for r in matches],
                "sec_reporting_status": "UNKNOWN",
                "provenance": [],
            }
        result = copy.deepcopy(matches[0])
        result.update(
            status="RESOLVED_WITH_PROVENANCE",
            query=query,
            sec_reporting_status="CONFIRMED" if result.get("cik") else "NO_VERIFIED_ROUTE",
        )
        return result

    def observe_submissions(self, data, requested_cik, source_url, body_sha256):
        parsed = urlsplit(source_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "data.sec.gov"
            or parsed.path != f"/submissions/CIK{requested_cik}.json"
            or parsed.query
            or not re.fullmatch(r"[a-f0-9]{64}", body_sha256)
        ):
            raise ValueError("Submissions identity lacks exact endpoint/hash")
        if str(data.get("cik", "")).zfill(10) != requested_cik or not isinstance(data.get("name"), str):
            raise ValueError("Returned issuer CIK/name mismatch")
        previous = self.resolve(requested_cik)
        listings = previous.get("listings", [])
        tickers, exchanges = data.get("tickers", []), data.get("exchanges", [])
        for i, ticker in enumerate(tickers):
            if not isinstance(ticker, str):
                continue
            exchange = exchanges[i] if i < len(exchanges) else None
            row = {"symbol": ticker, "exchange": exchange, "jurisdiction": "US"}
            if row not in listings:
                listings.append(row)
        former_names = [
            row["name"][:300]
            for row in data.get("formerNames", [])[:20]
            if isinstance(row, dict) and isinstance(row.get("name"), str)
        ]
        declared_domains = []
        for field in ("website", "investorWebsite"):
            value = data.get(field)
            if not isinstance(value, str) or not value:
                continue
            try:
                website = urlsplit(value if "://" in value else "https://" + value)
                if (
                    website.scheme in {"http", "https"}
                    and website.hostname
                    and not website.username
                    and not website.password
                ):
                    declared_domains.append(website.hostname.lower())
            except ValueError:
                pass
        return self.register(
            {
                **previous,
                "legal_name": data["name"][:300],
                "cik": requested_cik,
                "aliases": list(
                    dict.fromkeys(
                        previous.get("aliases", []) + [data["name"], *tickers, *former_names]
                    )
                )[:100],
                "listings": listings[:30],
                "fiscal_year_end": data.get("fiscalYearEnd"),
                "country_of_incorporation": previous.get("country_of_incorporation"),
                "incorporation_label": data.get("stateOfIncorporationDescription"),
                "incorporation_code": data.get("stateOfIncorporation"),
                "source_declared_domains": list(dict.fromkeys(declared_domains)),
                "domain_scope": "SEC_DECLARATION_NOT_CURRENT_CONTROL_OR_BODY_PERMISSION",
                "reporting_jurisdictions": sorted(
                    set(previous.get("reporting_jurisdictions", []) + ["US"])
                ),
                "provenance": previous.get("provenance", [])
                + [
                    {
                        "source_url": source_url,
                        "body_sha256": body_sha256,
                        "basis": "CAPTURED_SEC_SUBMISSIONS",
                    }
                ],
            }
        )

    def observe_ticker_index(self, data, source_url, body_sha256, query=None):
        """Ingest an actually captured official company_tickers_exchange index."""
        if (
            source_url != "https://www.sec.gov/files/company_tickers_exchange.json"
            or not re.fullmatch(r"[a-f0-9]{64}", body_sha256)
        ):
            raise ValueError("Unrecognized issuer index provenance")
        fields = data.get("fields", [])
        if not {"cik", "name", "ticker", "exchange"} <= set(fields):
            raise ValueError("Missing issuer-index fields")
        grouped = {}
        for values in data.get("data", []):
            row = dict(zip(fields, values))
            if not str(row.get("cik", "")).isdigit() or not row.get("name") or not row.get("ticker"):
                continue
            bases = clean_base_name(row["name"])
            if query and identity_key(query) not in {
                identity_key(row["name"]),
                *[identity_key(b) for b in bases],
                identity_key(row["ticker"]),
                identity_key(str(row["cik"]).zfill(10)),
            }:
                continue
            cik = str(row["cik"]).zfill(10)
            previous = self._records.get(cik, {})
            record = grouped.setdefault(
                cik,
                {
                    **previous,
                    "legal_name": previous.get("legal_name") or row["name"],
                    "cik": cik,
                    "aliases": list(dict.fromkeys(previous.get("aliases", []))),
                    "listings": copy.deepcopy(previous.get("listings", [])),
                    "reporting_jurisdictions": sorted(
                        set(previous.get("reporting_jurisdictions", []) + ["US"])
                    ),
                    "official_domains": list(dict.fromkeys(previous.get("official_domains", []))),
                    "provenance": previous.get("provenance", [])
                    + [
                        {
                            "source_url": source_url,
                            "body_sha256": body_sha256,
                            "basis": "CAPTURED_SEC_TICKER_INDEX",
                        }
                    ],
                },
            )
            if row["ticker"] not in record["aliases"]:
                record["aliases"].append(row["ticker"])
            for base in bases:
                if base not in record["aliases"]:
                    record["aliases"].append(base)
            listing = {
                "symbol": row["ticker"],
                "exchange": row["exchange"],
                "jurisdiction": "US",
            }
            if listing not in record["listings"]:
                record["listings"].append(listing)
        for record in grouped.values():
            self.register(record)
        with self._lock:
            self._last_sync_provenance = {
                "source_url": source_url,
                "body_sha256": body_sha256,
                "distinct_issuers_ingested": len(grouped),
                "synced_at": time.time(),
            }
            self._last_sync_failed_at = None
            self._last_sync_error = None
        return len(grouped)

    def record_sync_failure(self, error: Exception, endpoint: str):
        with self._lock:
            self._last_sync_failed_at = time.time()
            self._last_sync_error = f"{type(error).__name__}: {str(error)}"

    def can_attempt_sync(self, cooldown_seconds: float = 300.0) -> bool:
        with self._lock:
            if self._last_sync_failed_at is None:
                return True
            return (time.time() - self._last_sync_failed_at) > cooldown_seconds

    def load_cached_index_file(self, file_path: Optional[str] = None) -> int:
        """Load saved genuine capture of company_tickers_exchange.json without network I/O."""
        import hashlib

        candidates = [file_path] if file_path else [
            Path(__file__).parents[3] / "tests" / "unit" / "fixtures" / "sec_company_tickers_exchange.json",
            Path(__file__).parents[2] / "tests" / "unit" / "fixtures" / "sec_company_tickers_exchange.json",
            Path(__file__).parent / "fixtures" / "sec_company_tickers_exchange.json",
            Path("tests/unit/fixtures/sec_company_tickers_exchange.json"),
        ]
        for p in candidates:
            if not p:
                continue
            path = Path(p)
            if path.is_file():
                raw = path.read_bytes()
                sha = hashlib.sha256(raw).hexdigest()
                parsed = json.loads(raw.decode("utf-8"))
                return self.observe_ticker_index(
                    parsed,
                    "https://www.sec.gov/files/company_tickers_exchange.json",
                    sha,
                )
        return 0

    def remember_filings(self, cik, filings):
        with self._lock:
            if cik in self._records:
                self._records[cik]["observed_filings"] = copy.deepcopy(filings[:20])

    def observe_companyfacts(self, data, source_url, payload_sha256, decoded_bytes):
        cik = str(data.get("cik", "")).zfill(10)
        if source_url != f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json" or not re.fullmatch(
            r"[a-f0-9]{64}", payload_sha256
        ):
            raise ValueError("Companyfacts issuer/source mismatch")
        from backend.services.research.financial_structured import CONCEPTS

        preferred = {}
        for taxonomy, concepts in CONCEPTS.items():
            for concept, metric in concepts.items():
                definition = (data.get("facts", {}).get(taxonomy) or {}).get(concept) or {}
                ends = [
                    row["end"]
                    for values in definition.get("units", {}).values()
                    for row in values
                    if isinstance(row.get("end"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["end"])
                ]
                if ends and (metric not in preferred or max(ends) > preferred[metric]["latest_observed_period"]):
                    preferred[metric] = {
                        "taxonomy": taxonomy,
                        "concept": concept,
                        "latest_observed_period": max(ends),
                    }
        identity = self.resolve(cik)
        identity.update(
            legal_name=data["entityName"],
            cik=cik,
            reporting_jurisdictions=sorted(set(identity.get("reporting_jurisdictions", []) + ["US"])),
            preferred_financial_concepts=preferred,
            structured_financial_profile={
                "preferred_mode": "COMPANYFACTS",
                "observed_decoded_bytes": decoded_bytes,
                "source_url": source_url,
                "payload_sha256": payload_sha256,
            },
            provenance=identity.get("provenance", [])
            + [
                {
                    "source_url": source_url,
                    "body_sha256": payload_sha256,
                    "basis": "CAPTURED_SEC_COMPANYFACTS",
                }
            ],
        )
        return self.register(identity)


CATALOG_PATH = Path(__file__).with_name("issuer_identity_catalog.json")


def _reviewed_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["issuers"]


issuer_identity_resolver = IssuerIdentityResolver(_reviewed_catalog())


def resolve_issuer(query):
    return issuer_identity_resolver.resolve(query)
