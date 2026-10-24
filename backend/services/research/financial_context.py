"""Observed financial context, not filing reconciliation or financial truth.

The rolling 366-day publication window is a display/synthesis heuristic for a
default current-company investigation. It is not a claim that old results are
false, that newer reporting is complete, or that a fiscal period is comparable.
Exact fiscal/date/currency labels and sentence spans are retained independently;
the helper never normalizes an ambiguous fiscal year, issuer, or currency.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from decimal import Decimal
from backend.services.research.content_roles import paragraph_role


CURRENT_REPORTING_CONTEXT_DAYS = 366
PERIOD_PATTERN = re.compile(
    r"\bquarter ended\s+[A-Za-z]+\s+\d{1,2},?\s+20\d\d\b"
    r"|\b(?:first|second|third|fourth)[ -]quarter(?:\s+(?:of\s+)?20\d\d)?\b"
    r"|\bQ[1-4]\s*(?:FY\s*)?\d{2,4}\b|\bQ[1-4]\b"
    r"|\b(?:FY|fiscal\s+)\s*\d{2,4}\b|\b20\d\d/\d{2,4}\b", re.I)
FORECAST_PATTERN = re.compile(
    r"\b(?:forecast\w*|project\w*|guidance|estimat\w*|expect\w*|will|would|could|may|target prices?)\b", re.I)
REPORTED_PATTERN = re.compile(
    r"\b(?:reported|posted|recorded|earned|generated|delivered|rose|fell|grew|increased|decreased)\b"
    r"|\bannounced\s+(?:its\s+)?financial\s+results\b", re.I)


def _observed_datetime(value):
    """Parse a recorded timestamp; never replace an unknown date with today."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        clean = value.strip()
        # Some saved native publishers declare a date followed by Z, not time.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}Z", clean):
            clean = clean[:-1]
        try:
            parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(clean)
            except (TypeError, ValueError, OverflowError):
                return None
    else:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _scope(text):
    forecast = bool(FORECAST_PATTERN.search(text))
    reported = bool(REPORTED_PATTERN.search(text))
    if forecast and reported:
        return "MIXED_REPORTED_AND_FORECAST"
    if forecast:
        return "FORECAST_OR_CONDITIONAL"
    return "REPORTED_SOURCE_ASSERTION" if reported else "SOURCE_CONTEXT"


SCALE_MULTIPLIERS = {
    "trillion": 1e12, "tn": 1e12,
    "billion": 1e9, "bn": 1e9,
    "million": 1e6, "mn": 1e6,
    "crore": 1e7, "cr": 1e7,
    "lakh": 1e5, "lac": 1e5,
    "thousand": 1e3, "k": 1e3,
}

METRIC_NAME_PATTERN = r"(?:operating profit|net profit|gross profit|operating income|net income|revenues?|profits?|sales|cash flow|debt|assets|earnings)"


def extract_financial_metrics_and_scales(text: str) -> list:
    """Observe explicitly denominated amounts, never growth rates or year labels.

    Magnitudes are arithmetic observations, not verified financial facts. Keep
    comparison roles and exact spans; a bare dollar symbol never implies USD.
    Ambiguous unlabelled numbers are left out rather than invented as money.
    """
    if not text:
        return []
    if paragraph_role(text) in {"QUESTION_PROMPT", "INSTRUCTIONAL_PROMPT"}:
        return []
    results = []
    metrics = list(re.finditer(rf"\b({METRIC_NAME_PATTERN})\b", text, re.I))
    amount_pattern = re.compile(
        r"(?<![\w.])(?P<currency>USD|INR|EUR|GBP|KRW|US\$|[$\u20ac\u00a3\u20b9]|Rs\.?)?\s*"
        r"(?P<number>-?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*"
        r"(?P<scale>trillion|billion|million|crore|lakh|thousand|tn|bn|mn|cr|lac|k)?\b", re.I)
    currency_codes = {"US$": "USD", "USD": "USD", "INR": "INR", "EUR": "EUR", "GBP": "GBP",
                      "KRW": "KRW", "\u20ac": "EUR", "\u00a3": "GBP", "\u20b9": "INR",
                      "$": "DOLLAR_SYMBOL_UNSPECIFIED", "RS": "RUPEE_LABEL_UNSPECIFIED"}
    for index, metric_match in enumerate(metrics):
        start = metric_match.end()
        stop = min(len(text), start + 100, metrics[index + 1].start() if index + 1 < len(metrics) else len(text))
        tail = text[start:stop]
        boundary = re.search(r"[;!?\n]|\.(?:\s|$)", tail)
        tail = tail[:boundary.start()] if boundary else tail
        for match in amount_pattern.finditer(tail):
            currency, scale = match.group("currency"), (match.group("scale") or "").lower()
            following = tail[match.end():].lstrip()
            if (not currency and not scale) or following.startswith("%") or re.match(r"percent\b", following, re.I):
                continue
            before = tail[:match.start()].rstrip()
            # A nearby analyst consensus/range is not the company's reported
            # amount. Preserve exact spans and the range context rather than
            # assigning every number following "revenue" the same actual role.
            clause_start = max(text.rfind(";", 0, metric_match.start()),
                               text.rfind("\n", 0, metric_match.start()),
                               text.rfind(". ", 0, metric_match.start()) + 1)
            metric_context = text[clause_start:start] + before
            estimate = re.search(r"\b(?:consensus|estimates?|forecast\w*|guidance|expects?|expected|projects?|projected|targets?)\b", metric_context, re.I)
            role = ("COMPARATIVE_BASELINE" if re.search(r"\bfrom\s*$", before, re.I)
                    else "FORECAST_OR_ESTIMATE" if estimate else "REPORTED_AMOUNT")
            amount = Decimal(match.group("number").replace(",", ""))
            multiplier = Decimal(str(SCALE_MULTIPLIERS.get(scale, 1)))
            absolute_start, absolute_end = start + match.start(), start + match.end()
            results.append({"metric": metric_match.group().lower(), "raw_amount": float(amount),
                "scale": scale or "units", "multiplier": float(multiplier),
                "normalized_value": float(amount * multiplier), "amount_role": role,
                "currency": currency_codes.get((currency or "").upper().rstrip("."), "UNSPECIFIED"),
                "matched_text": text[metric_match.start():absolute_end].strip(),
                "amount_text": text[absolute_start:absolute_end], "start": absolute_start, "end": absolute_end,
                "verification_status": "UNVERIFIED_SOURCE_ASSERTION"})
            if len(results) >= 8:
                return results
    return results


def reconcile_period_and_filing(observed_periods: list, title_periods: list, filing_record: dict = None) -> tuple:
    """Compare explicit period metadata; never infer an issuer's fiscal calendar.

    A report date/form alone does not specify a fiscal quarter or fiscal year.
    Even an exact metadata match is not comparison of financial amounts.
    """
    if not filing_record:
        return "NOT_RECONCILED", "NOT_PERFORMED"
    form = str(filing_record.get("form") or "").upper().strip()
    report_date = str(filing_record.get("report_date") or "").strip()
    all_periods = " ".join(observed_periods + title_periods).upper()
    if not all_periods.strip():
        return "PERIOD_UNSPECIFIED", "INCONCLUSIVE"
    quarters = set(re.findall(r"\bQ[1-4]", all_periods))
    ordinal = {"FIRST": "Q1", "SECOND": "Q2", "THIRD": "Q3", "FOURTH": "Q4"}
    quarters.update(ordinal[q] for q in re.findall(r"\b(FIRST|SECOND|THIRD|FOURTH)[ -]QUARTER", all_periods))
    years = set(re.findall(r"(?:FY\s*|FISCAL\s+)(\d{2,4})\b", all_periods))
    years.update(re.findall(r"\b(?:Q[1-4]\s*)(20\d\d)\b", all_periods))
    # Do not silently decide that FY26 belongs to the 2000s.
    if any(len(year) != 4 for year in years):
        return "FISCAL_YEAR_AMBIGUOUS", "INCONCLUSIVE"
    annual = bool(re.search(r"\b(?:FY\s*\d|ANNUAL|FULL YEAR)", all_periods)) and not quarters
    if form in {"10-K", "10K", "20-F"} and quarters:
        return "PERIOD_MISMATCH", "MISMATCH"
    if form in {"10-Q", "10Q"} and annual:
        return "PERIOD_MISMATCH", "MISMATCH"
    filing_period = str(filing_record.get("fiscal_period") or "").upper()
    filing_year = str(filing_record.get("fiscal_year") or "")
    if (quarters or annual) and years and filing_period and filing_year:
        expected = quarters or {"FY"}
        if expected != {filing_period} or years != {filing_year}:
            return "PERIOD_MISMATCH", "MISMATCH"
        return "PERIOD_RECONCILED_MATCH", "RECONCILED"
    date_labels = re.findall(r"QUARTER ENDED\s+([A-Z]+\s+\d{1,2},?\s+20\d\d)", all_periods)
    if date_labels and report_date:
        try:
            dates = {datetime.strptime(label.replace(",", ""), "%B %d %Y").replace(tzinfo=timezone.utc)
                     for label in date_labels}
        except ValueError:
            dates = {None}
        report = _observed_datetime(report_date)
        if report and all(dates):
            return ("PERIOD_RECONCILED_MATCH", "RECONCILED") if dates == {report} else ("PERIOD_MISMATCH", "MISMATCH")
    return "FISCAL_METADATA_REQUIRED", "INCONCLUSIVE"


def financial_passage_context(passage, *, title="", published_at="", observed_at="", issuer="", intent="", filing_record=None):
    """Return exact context labels while keeping source assertions unverified.

    ``observed_at`` must come from acquisition/retrieval, not publication or an
    invented replay clock. A missing/invalid timestamp stays UNKNOWN. Historical
    intent may include background in a historical assessment; it never changes
    the recorded publication age or calls the article current.
    """
    passage, title = str(passage or ""), str(title or "")
    published, observed = _observed_datetime(published_at), _observed_datetime(observed_at)
    age = (observed - published).total_seconds() / 86400 if published and observed else None
    publication_scope = "UNKNOWN_PUBLICATION_OR_CAPTURE_TIME"
    if age is not None:
        publication_scope = ("FUTURE_PUBLICATION" if age < -1 else "HISTORICAL_BACKGROUND"
            if age > CURRENT_REPORTING_CONTEXT_DAYS else "RECENT_REPORTING_CONTEXT")
    period_spans = [{"text": match.group(), "start": match.start(), "end": match.end(), "origin": origin}
        for origin, text in (("PASSAGE", passage), ("TITLE", title)) for match in PERIOD_PATTERN.finditer(text)]
    periods = list(dict.fromkeys(row["text"] for row in period_spans if row["origin"] == "PASSAGE"))
    title_periods = list(dict.fromkeys(row["text"] for row in period_spans if row["origin"] == "TITLE"))
    explicit_historical = bool(re.search(r"\b(?:historical|history|historically|archive|archived)\b", intent or "", re.I))
    requested_years = set(re.findall(r"\b(?:19|20)\d{2}\b", intent or ""))
    captured_years = set(re.findall(r"\b(?:19|20)\d{2}\b", passage + " " + title))
    historical_request = explicit_historical or bool(requested_years & captured_years)
    currencies, currency_labels = [], []
    for pattern, code in ((r"\bKRW\b|(?<![\w-])won(?![\w-])|₩", "KRW"),
                          (r"\bUSD\b|US\$", "USD"), (r"\bINR\b|₹", "INR"),
                          (r"\bEUR\b|€", "EUR"), (r"\bGBP\b|£", "GBP"),
                          (r"\b(?:Rs\.?|rupees)\b", "RUPEE_LABEL_UNSPECIFIED"),
                          (r"(?<!\w)(?:dollars?\b|\$)", "DOLLAR_SYMBOL_UNSPECIFIED")):
        matches = list(re.finditer(pattern, passage, re.I))
        if matches:
            currencies.append(code)
            currency_labels.extend(match.group() for match in matches)
    statements = []
    for match in re.finditer(r"\S.*?(?=(?:[.!?]\s+(?=[A-Z“\"]))|(?:;\s+)|$)", passage, re.S):
        text = match.group().strip()
        if text:
            start = passage.find(text, match.start())
            statements.append({"text": text, "start": start, "end": start + len(text), "scope": _scope(text)})
        if len(statements) >= 12:
            break
    target = re.sub(r"\([^)]*\)", "", str(issuer or "")).strip()
    mention = bool(target and re.search(r"(?<!\w)" + re.escape(target) + r"(?!\w)", passage + " " + title, re.I))
    current = publication_scope == "RECENT_REPORTING_CONTEXT"
    financial_measure = bool(re.search(r"\b(?:revenues?|profits?|operating income|net income|earnings per share|EPS|margins?|cash flow|assets|debt|dividends?)\b", passage, re.I)
        and (re.search(r"\d", passage) or re.search(r"\b(?:rose|fell|grew|increased|decreased|declined|surged|dropped)\b", passage, re.I)
             or FORECAST_PATTERN.search(passage)))
    corporate_event = bool(re.search(r"\b(?:buyback|merger|acquisition|bankruptcy|regulatory investigation|fraud investigation|resigned|appointed)\b", passage, re.I))
    strategy = bool(re.search(r"\b(?:brand(?:ing)?|brand identity|brand architecture|customer-facing identity|brand proposition|brand strategy)\b", passage + " " + title, re.I))
    non_assertive = paragraph_role(passage) in {"QUESTION_PROMPT", "INSTRUCTIONAL_PROMPT"}
    content_kind = ("NON_ASSERTIVE_PROMPT" if non_assertive else "FINANCIAL_PERFORMANCE_ASSERTION" if financial_measure else "CORPORATE_EVENT_ASSERTION" if corporate_event
        else "CORPORATE_STRATEGY_CONTEXT" if strategy else "FINANCIAL_CONTEXT_INCOMPLETE")

    normalized_metrics = extract_financial_metrics_and_scales(passage)
    period_alignment, filing_comparison_status = reconcile_period_and_filing(periods, title_periods, filing_record)
    financial_verification_status = "NOT_PERFORMED" if filing_comparison_status == "NOT_PERFORMED" else "UNVERIFIED_ASSERTION"

    return {"publication_scope": publication_scope,
        "publication_age_days": round(age, 2) if age is not None else None,
        "observed_at": str(observed_at or "") or None,
        "current_context_policy": {"maximum_publication_age_days": CURRENT_REPORTING_CONTEXT_DAYS,
            "is_heuristic": True, "does_not_establish_current_fiscal_period": True},
        "current_assessment_eligible": current,
        "assessment_eligible": current or (publication_scope == "HISTORICAL_BACKGROUND" and historical_request),
        "historical_intent_requested": historical_request,
        "assessment_scope": "HISTORICAL_REQUEST" if publication_scope == "HISTORICAL_BACKGROUND" and historical_request else publication_scope,
        "content_kind": content_kind, "financial_verification_status": financial_verification_status,
        "financial_assessment_eligible": (current or (publication_scope == "HISTORICAL_BACKGROUND" and historical_request))
            and content_kind in {"FINANCIAL_PERFORMANCE_ASSERTION", "CORPORATE_EVENT_ASSERTION"},
        "observed_period_labels": periods, "title_period_labels": title_periods,
        "period_label_spans": period_spans[:24], "period_alignment": period_alignment,
        "observed_currencies": currencies, "observed_currency_labels": list(dict.fromkeys(currency_labels)),
        "currency_conversion_performed": False, "statement_scopes": statements,
        "result_scope": "FORECAST_OR_MIXED_REPORTED_CONTEXT" if FORECAST_PATTERN.search(passage) else "REPORTED_SOURCE_ASSERTION",
        "issuer_mention": target if mention else None, "issuer_alignment": "MENTION_ONLY_NOT_AUTHENTICATED" if mention else "NOT_ESTABLISHED",
        "source_claim_status": "UNVERIFIED", "filing_comparison_status": filing_comparison_status,
        "normalized_metrics": normalized_metrics}
