"""
Aegis Protocol — Authoritative Primary Source Adapters Package
==============================================================
Exports authoritative primary adapters:
- SEC EDGAR: Official corporate filings and regulatory records
- NIST NVD: National Vulnerability Database / CVE disclosures
- arXiv: Academic papers and scientific preprints
- Fact Check: ClaimReview structured fact-checking aggregations
"""

from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import (
    fetch_sec_submissions,
    normalize_sec_items,
    resolve_cik,
)
from backend.infrastructure.acquisition.adapters.authoritative.nist_nvd import (
    fetch_nist_cve,
    normalize_nist_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.arxiv_preprints import (
    fetch_arxiv_preprints,
    normalize_arxiv_items,
)
from backend.infrastructure.acquisition.adapters.authoritative.fact_check import (
    fetch_fact_check_claims,
    normalize_fact_check_items,
)

__all__ = [
    "fetch_arxiv_preprints",
    "fetch_fact_check_claims",
    "fetch_nist_cve",
    "fetch_sec_submissions",
    "normalize_arxiv_items",
    "normalize_fact_check_items",
    "normalize_nist_items",
    "normalize_sec_items",
    "resolve_cik",
]
