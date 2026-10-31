"""Offline unit tests for Scout Primary-Source Integration & Reconciliation."""
import pytest
from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import resolve_cik
from backend.services.research.financial_context import (
    extract_financial_metrics_and_scales,
    reconcile_period_and_filing,
    financial_passage_context,
)
from backend.agents.scout.financial import resolve_company_identity


def test_sec_edgar_cik_resolution_across_classes_and_adrs():
    # Direct high-volume US tickers
    assert resolve_cik("MSFT") == "0000789019"
    assert resolve_cik("AAPL") == "0000320193"
    assert resolve_cik("NVDA") == "0001045810"

    # Exchange prefixes and suffixes
    assert resolve_cik("NASDAQ:NVDA") == "0001045810"
    assert resolve_cik("GOOG.O") == "0001652044"
    assert resolve_cik("NYSE:JPM") == "0000019617"

    # Dual-class share normalization
    assert resolve_cik("BRK-A") == "0001067983"
    assert resolve_cik("BRK.B") == "0001067983"
    assert resolve_cik("GOOG") == "0001652044"
    assert resolve_cik("GOOGL") == "0001652044"

    # International Foreign Private Issuers & ADRs
    assert resolve_cik("INFY") == "0001067491"
    assert resolve_cik("SKX") == "0001065837"   # Infosys ADR
    assert resolve_cik("TTM") == "0000926042"    # Tata Motors ADR
    assert resolve_cik("LNVGY") == "0001002517"  # Lenovo ADR
    assert resolve_cik("TSM") == "0001046179"    # TSMC ADR

    # Company name resolution
    assert resolve_cik("Johnson & Johnson") == "0000200406"
    assert resolve_cik("Microsoft Corporation") == "0000789019"
    assert resolve_cik("Infosys Limited") == "0001067491"

    # Numeric raw CIK zero-padding
    assert resolve_cik("789019") == "0000789019"
    assert resolve_cik("0000789019") == "0000789019"

    # Unknown
    assert resolve_cik("UNKNOWN_CORP_XYZ_999") is None


def test_financial_metric_scale_extraction_and_normalization():
    # Billions (USD)
    p1 = "Microsoft Cloud as a whole generated quarterly revenue of $59.3 billion, marking a 27% increase."
    m1 = extract_financial_metrics_and_scales(p1)
    assert len(m1) >= 1
    assert m1[0]["metric"] == "revenue"
    assert m1[0]["raw_amount"] == 59.3
    assert m1[0]["scale"] == "billion"
    assert m1[0]["normalized_value"] == 59_300_000_000.0

    # Millions (USD)
    p2 = "The group reported operating profit of USD 250 million."
    m2 = extract_financial_metrics_and_scales(p2)
    assert len(m2) >= 1
    assert m2[0]["metric"] == "operating profit"
    assert m2[0]["raw_amount"] == 250.0
    assert m2[0]["scale"] == "million"
    assert m2[0]["normalized_value"] == 250_000_000.0

    # Crores (INR scale: 1 crore = 10 million)
    p3 = "Tata Motors posted net profit of ₹14 crore during the quarter."
    m3 = extract_financial_metrics_and_scales(p3)
    assert len(m3) >= 1
    assert m3[0]["metric"] == "net profit"
    assert m3[0]["raw_amount"] == 14.0
    assert m3[0]["scale"] == "crore"
    assert m3[0]["normalized_value"] == 140_000_000.0


def test_filing_period_reconciliation():
    # 10-Q Quarterly match
    p_match, f_stat = reconcile_period_and_filing(["Q3 FY2026"], [], {"form": "10-Q", "report_date": "2026-09-30", "fiscal_period": "Q3", "fiscal_year": 2026})
    assert p_match == "PERIOD_RECONCILED_MATCH"
    assert f_stat == "RECONCILED"

    # 10-K Annual match
    p_match, f_stat = reconcile_period_and_filing(["FY2026"], ["Full Year Results"], {"form": "10-K", "report_date": "2026-12-31", "fiscal_period": "FY", "fiscal_year": 2026})
    assert p_match == "PERIOD_RECONCILED_MATCH"
    assert f_stat == "RECONCILED"

    # Period Form Mismatch: Passage claims Q1, but filing is 10-K Annual
    p_match, f_stat = reconcile_period_and_filing(["Q1 2026"], [], {"form": "10-K", "report_date": "2026-12-31"})
    assert p_match == "PERIOD_MISMATCH"
    assert f_stat == "MISMATCH"

    # Year Mismatch: Passage claims 2024, but filing is 2026
    p_match, f_stat = reconcile_period_and_filing(["Q3 2024"], [], {"form": "10-Q", "report_date": "2026-09-30", "fiscal_period": "Q3", "fiscal_year": 2026})
    assert p_match == "PERIOD_MISMATCH"
    assert f_stat == "MISMATCH"

    # Empty filing record keeps backward-compatible default
    p_match, f_stat = reconcile_period_and_filing(["Q3 2026"], [], None)
    assert p_match == "NOT_RECONCILED"
    assert f_stat == "NOT_PERFORMED"


def test_scout_resolve_company_identity_attaches_cik():
    msft = resolve_company_identity("MSFT")
    assert msft["cik"] == "0000789019"
    assert msft["regulatory_filing_source"] == "SEC EDGAR"
    assert "0000789019" in msft["filing_url"]

    aapl = resolve_company_identity("Apple")
    assert aapl["cik"] == "0000320193"

    infy = resolve_company_identity("Infosys")
    assert infy["cik"] == "0001067491"


def test_financial_passage_context_with_filing_verification():
    passage = "Microsoft Cloud generated quarterly revenue of $59.3 billion in Q4 2026."
    filing = {"form": "10-Q", "report_date": "2026-06-30"}
    ctx = financial_passage_context(passage, filing_record=filing)

    assert ctx["period_alignment"] == "FISCAL_METADATA_REQUIRED"
    assert ctx["filing_comparison_status"] == "INCONCLUSIVE"
    assert ctx["financial_verification_status"] == "UNVERIFIED_ASSERTION"
    assert len(ctx["normalized_metrics"]) >= 1
    assert ctx["normalized_metrics"][0]["normalized_value"] == 59_300_000_000.0
