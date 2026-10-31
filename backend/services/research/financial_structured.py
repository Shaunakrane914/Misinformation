"""Exact SEC XBRL source assertions and conservative, reproducible comparisons.

Readable rows are explicitly a structured-data projection, not publisher prose.
JSON pointers, original units, accessions and payload/body hashes remain attached.
No currency conversion, fiscal-calendar inference or generated financial values.
"""
import copy
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from urllib.parse import urlsplit


CONCEPTS = {
    "us-gaap": {"RevenueFromContractWithCustomerExcludingAssessedTax": "REVENUE", "Revenues": "REVENUE",
        "SalesRevenueNet": "REVENUE", "OperatingIncomeLoss": "OPERATING_INCOME", "NetIncomeLoss": "NET_INCOME",
        "EarningsPerShareDiluted": "EPS_DILUTED", "EarningsPerShareBasic": "EPS_BASIC", "GrossProfit": "GROSS_PROFIT"},
    "ifrs-full": {"RevenueFromContractsWithCustomers": "REVENUE", "Revenue": "REVENUE", "ProfitLoss": "NET_INCOME", "ProfitLossFromOperatingActivities": "OPERATING_INCOME",
        "DilutedEarningsLossPerShare": "EPS_DILUTED", "BasicEarningsLossPerShare": "EPS_BASIC", "GrossProfit": "GROSS_PROFIT"},
}


def sec_financial_locator(url):
    try:
        parsed = urlsplit(url)
    except (ValueError, TypeError):
        return None
    match = re.fullmatch(r"/api/xbrl/(?:companyfacts/CIK(?P<all>\d{10})\.json|companyconcept/CIK(?P<cik>\d{10})/(?P<taxonomy>us-gaap|ifrs-full)/(?P<concept>[A-Za-z0-9]+)\.json)", parsed.path)
    if (parsed.scheme != "https" or parsed.netloc != "data.sec.gov" or parsed.query or parsed.fragment or not match):
        return None
    values = match.groupdict()
    if values["concept"] and values["concept"] not in CONCEPTS[values["taxonomy"]]:
        return None
    return {"cik": values["cik"] or values["all"], "taxonomy": values["taxonomy"], "concept": values["concept"]}


def _duration(start, end):
    try:
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    except (ValueError, TypeError):
        return None
    return days if 1 <= days <= 380 else None


def _number(value):
    try:
        result = Decimal(str(value))
        return str(result) if result.is_finite() and -20 <= result.adjusted() <= 30 and len(result.as_tuple().digits) <= 50 else None
    except InvalidOperation:
        return None


def _fact_text(fact):
    return (f"{fact['issuer']} | {fact['metric']} | {fact['concept']} | {fact['period_start']} to {fact['period_end']} | "
            f"{fact['original_value']} {fact['unit']} | {fact['filing_form']} | {fact['accession']} | filed {fact['filing_date']} | JSON {fact['json_pointer']}")


def _document_header(issuer, cik, source_url, payload_sha256):
    return (f"SEC XBRL structured financial data — {issuer} | CIK {cik}\n"
            f"Source: {source_url}\nJSON SHA-256: {payload_sha256}\n\n")


def xbrl_document(data, source_url, payload_sha256, *, max_chars=20000):
    locator = sec_financial_locator(source_url)
    if (not locator or str(data.get("cik", "")).zfill(10) != locator["cik"]
            or not isinstance(data.get("entityName"), str) or not re.fullmatch(r"[a-f0-9]{64}", payload_sha256)):
        raise ValueError("XBRL issuer/endpoint/hash mismatch")
    cik, issuer = locator["cik"], data["entityName"][:300]
    all_facts = data.get("facts")
    if locator["concept"]:
        if data.get("tag") != locator["concept"] or data.get("taxonomy") != locator["taxonomy"]:
            raise ValueError("Concept endpoint and returned taxonomy/tag disagree")
        all_facts = {locator["taxonomy"]: {locator["concept"]: data}}
    if not isinstance(all_facts, dict):
        raise ValueError("No structured facts")
    candidates = []
    for taxonomy, concepts in CONCEPTS.items():
        for concept, metric in concepts.items():
            definition = (all_facts.get(taxonomy) or {}).get(concept)
            if not isinstance(definition, dict):
                continue
            for unit, values in (definition.get("units") or {}).items():
                if not re.fullmatch(r"[A-Z]{3}(?:/shares)?", unit):
                    continue
                if metric.startswith("EPS_") != unit.endswith("/shares"):
                    continue
                for index, value in enumerate(values):
                    if not isinstance(value, dict):
                        continue
                    original = _number(value.get("val"))
                    duration = _duration(value.get("start"), value.get("end"))
                    accession, form, filed = str(value.get("accn", "")), str(value.get("form", "")), str(value.get("filed", ""))
                    if (original is None or duration is None or form not in {"10-K", "10-Q", "20-F", "40-F", "6-K", "8-K", "10-K/A", "10-Q/A", "20-F/A"}
                            or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession)
                            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", filed)):
                        continue
                    pointer = ("" if locator["concept"] else "/facts/" + taxonomy + "/" + concept)
                    pointer += "/units/" + unit.replace("~", "~0").replace("/", "~1") + "/" + str(index) + "/val"
                    candidates.append({"cik": cik, "issuer": issuer, "metric": metric, "concept": concept,
                        "taxonomy": taxonomy, "value": original, "original_value": original, "unit": unit,
                        "currency": unit.split("/")[0], "scale": "ORIGINAL_API_UNIT_NO_FX_CONVERSION",
                        "period_start": value["start"], "period_end": value["end"], "duration_days": duration,
                        "scope": "REPORTED_ACTUAL", "statement_type": "ENTITY_WIDE_STANDARD_TAXONOMY",
                        "accounting_basis": "US_GAAP" if taxonomy == "us-gaap" else "IFRS",
                        "filing_form": form, "accession": accession, "filing_date": filed,
                        "filing_fiscal_year": value.get("fy"), "filing_fiscal_period": value.get("fp"),
                        "fiscal_fields_scope": "FILING_CONTEXT_NOT_ASSIGNED_TO_COMPARATIVE_FACT",
                        "source_url": source_url, "json_pointer": pointer, "payload_sha256": payload_sha256,
                        "extraction_method": "SEC_STANDARD_XBRL_JSON", "independently_verified": False})
    # Newest source observations first, retaining comparative periods and conflicts.
    candidates.sort(key=lambda f: (f["period_end"], f["filing_date"], f["period_start"]), reverse=True)
    facts, seen, text = [], set(), _document_header(issuer, cik, source_url, payload_sha256)
    for fact in candidates:
        key = tuple(fact[k] for k in ("metric", "unit", "period_start", "period_end", "taxonomy", "concept")) + (Decimal(fact["value"]),)
        if key in seen:
            continue
        line = _fact_text(fact)
        if len(text) + len(line) + 2 > min(20000, max_chars) or len(facts) >= 40:
            continue
        start = len(text)
        text += line + "\n\n"
        facts.append({**fact, "start": start, "end": start + len(line), "text": line})
        seen.add(key)
    text = text.rstrip()
    document = {"schema": "sec-xbrl-facts-v1", "source_url": source_url, "cik": cik, "issuer": issuer,
        "payload_sha256": payload_sha256, "body_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "facts": facts, "projection": "STRUCTURED_RECORDS_NOT_PUBLISHER_PROSE",
        "facts_omitted": len(candidates) - len(facts)}
    return text, document


def project_financial_document(document, body):
    if (not isinstance(document, dict) or document.get("schema") != "sec-xbrl-facts-v1"
            or not isinstance(document.get("issuer"), str) or not 1 <= len(document["issuer"]) <= 300
            or not sec_financial_locator(document.get("source_url", ""))
            or document.get("body_sha256") != hashlib.sha256(body.encode()).hexdigest()
            or not re.fullmatch(r"[a-f0-9]{64}", str(document.get("payload_sha256", "")))):
        return None
    if sec_financial_locator(document["source_url"])["cik"] != document.get("cik"):
        return None
    if not body.startswith(_document_header(document.get("issuer"), document["cik"], document["source_url"], document["payload_sha256"])):
        return None
    fields = {"cik", "issuer", "metric", "concept", "taxonomy", "value", "original_value", "unit", "currency", "scale",
        "period_start", "period_end", "duration_days", "scope", "statement_type", "accounting_basis", "filing_form", "accession",
        "filing_date", "filing_fiscal_year", "filing_fiscal_period", "fiscal_fields_scope", "source_url", "json_pointer",
        "payload_sha256", "extraction_method", "independently_verified", "start", "end", "text"}
    fields.update({"filing_document_url", "filing_locator_basis"})
    facts = []
    source_facts = document.get("facts")
    for fact in (source_facts if isinstance(source_facts, list) else [])[:40]:
        if (not isinstance(fact, dict) or fact.get("source_url") != document["source_url"]
                or fact.get("cik") != document.get("cik") or fact.get("payload_sha256") != document["payload_sha256"]
                or fact.get("issuer") != document.get("issuer")
                or type(fact.get("start")) is not int or type(fact.get("end")) is not int
                or not 0 <= fact["start"] < fact["end"] <= len(body)
                or body[fact["start"]:fact["end"]] != fact.get("text")
                or _number(fact.get("value")) is None
                or _number(fact.get("value")) != _number(fact.get("original_value"))
                or fact.get("duration_days") != _duration(fact.get("period_start"), fact.get("period_end"))
                or not re.fullmatch(r"[A-Z]{3}(?:/shares)?", str(fact.get("unit", "")))
                or fact.get("currency") != fact["unit"].split("/")[0]
                or fact.get("scope") != "REPORTED_ACTUAL"
                or fact.get("statement_type") != "ENTITY_WIDE_STANDARD_TAXONOMY"
                or fact.get("accounting_basis") != {"us-gaap": "US_GAAP", "ifrs-full": "IFRS"}.get(fact.get("taxonomy"))
                or not re.fullmatch(r"(?:/facts/(?:us-gaap|ifrs-full)/[A-Za-z0-9]+)?/units/[A-Z]{3}(?:~1shares)?/\d+/val", str(fact.get("json_pointer", "")))
                or fact.get("metric") != CONCEPTS.get(fact.get("taxonomy"), {}).get(fact.get("concept"))):
            continue
        if not {"issuer", "metric", "concept", "period_start", "period_end", "original_value", "unit", "filing_form", "accession", "filing_date", "json_pointer"} <= fact.keys() or fact["text"] != _fact_text(fact):
            continue
        projected = {**{key: copy.deepcopy(value) for key, value in fact.items() if key in fields and type(value) in {str, int, bool, float, type(None)}}, "independently_verified": False}
        if projected.get("filing_document_url"):
            locator = urlsplit(projected["filing_document_url"])
            prefix = f"/Archives/edgar/data/{int(document['cik'])}/{fact['accession'].replace('-', '')}/"
            if (locator.scheme != "https" or locator.netloc != "www.sec.gov" or locator.query or locator.fragment
                    or not locator.path.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", locator.path[len(prefix):])):
                projected.pop("filing_document_url", None)
                projected.pop("filing_locator_basis", None)
        facts.append(projected)
    return {**{key: document[key] for key in ("schema", "source_url", "cik", "issuer", "payload_sha256", "body_sha256", "projection")}, "facts": facts}


def qualified_document(item, subject):
    from backend.services.research.issuer_identity import resolve_issuer
    metadata = item.get("metadata", {}) if isinstance(item, dict) else getattr(item, "metadata", {})
    body = item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
    url = (item.get("url") or item.get("canonical_url")) if isinstance(item, dict) else getattr(item, "canonical_url", "")
    document = project_financial_document((metadata.get("page_metadata") or {}).get("financial_document"), body)
    identity = resolve_issuer(subject)
    from backend.services.research.source_registry import source_registry
    if (document and document["facts"] and document["source_url"] == url and identity.get("cik") == document["cik"]
            and metadata.get("read_success") and not metadata.get("temporal_required")
            and metadata.get("layer2_eligible") is not False and source_registry.excerpt_decision(url, metadata.get("page_metadata"))["eligible"]):
        return document
    return None


def reconcile_financial_facts(facts):
    """Source agreement/growth only; no independent truth or investment verdict."""
    results, unique = [], {}
    for fact in facts:
        key = tuple(str(fact.get(k)) for k in ("cik", "concept", "metric", "unit", "period_start", "period_end", "statement_type", "accounting_basis")) + (Decimal(fact["value"]),)
        unique.setdefault(key, fact)
    values = list(unique.values())
    for current in values:
        for prior in values:
            fields = ("cik", "metric", "concept", "unit", "statement_type", "accounting_basis")
            if current is prior or any(current.get(k) != prior.get(k) for k in fields):
                continue
            if current.get("scope") != "REPORTED_ACTUAL" or prior.get("scope") != "REPORTED_ACTUAL":
                continue
            refs = [{k: f.get(k) for k in ("evidence_id", "source_url", "payload_sha256", "json_pointer", "accession", "period_start", "period_end", "value", "unit")} for f in (current, prior)]
            if current["period_start"] == prior["period_start"] and current["period_end"] == prior["period_end"]:
                if Decimal(current["value"]) != Decimal(prior["value"]) and current["value"] < prior["value"]:
                    results.append({"kind": "CONFLICTING_SOURCE_VALUES", "metric": current["metric"], "inputs": refs,
                                    "status": "REVIEW_RESTATEMENT_OR_CONTEXT_REQUIRED", "formula": None})
                continue
            end_gap = (date.fromisoformat(current["period_end"]) - date.fromisoformat(prior["period_end"])).days
            start_gap = (date.fromisoformat(current["period_start"]) - date.fromisoformat(prior["period_start"])).days
            if not (350 <= end_gap <= 378 and 350 <= start_gap <= 378 and abs(current["duration_days"] - prior["duration_days"]) <= 8):
                continue
            # Conflicting values for either input interval make growth unavailable.
            if any(f.get("scope") == "REPORTED_ACTUAL" and all(f.get(k) == current.get(k) for k in fields)
                   and f["period_start"] == base["period_start"] and f["period_end"] == base["period_end"]
                   and Decimal(f["value"]) != Decimal(base["value"]) for base in (current, prior) for f in values):
                continue
            denominator = Decimal(prior["value"])
            if denominator <= 0:
                continue
            with localcontext() as ctx:
                ctx.prec = 80
                percent = ((Decimal(current["value"]) - denominator) / denominator * Decimal(100)).quantize(Decimal("0.0001"))
            results.append({"kind": "SAME_PERIOD_PRIOR_YEAR_CHANGE", "metric": current["metric"], "inputs": refs,
                "formula": "(current - prior) / prior * 100", "result_percent": str(percent),
                "status": "COMPUTED_FROM_CAPTURED_SOURCE_ASSERTIONS", "independent_verification": False})
    # Derived margins require a single revenue concept/value and compatible
    # numerator, issuer, unit, statement basis and exact duration interval.
    margins = []
    for revenue in values:
        if revenue["metric"] != "REVENUE" or Decimal(revenue["value"]) <= 0:
            continue
        context = ("cik", "unit", "period_start", "period_end", "statement_type", "accounting_basis")
        peers = [f for f in values if all(f.get(k) == revenue.get(k) for k in context)]
        revenue_values = {(f["concept"], Decimal(f["value"])) for f in peers if f["metric"] == "REVENUE"}
        if len(revenue_values) != 1:
            continue
        for metric, kind in (("OPERATING_INCOME", "OPERATING_MARGIN"), ("GROSS_PROFIT", "GROSS_MARGIN")):
            numerators = [f for f in peers if f["metric"] == metric]
            if len({(f["concept"], Decimal(f["value"])) for f in numerators}) != 1:
                continue
            numerator = numerators[0]
            with localcontext() as ctx:
                ctx.prec = 80
                percent = (Decimal(numerator["value"]) / Decimal(revenue["value"]) * Decimal(100)).quantize(Decimal("0.0001"))
            refs = [{k: f.get(k) for k in ("evidence_id", "metric", "source_url", "payload_sha256", "json_pointer", "accession", "period_start", "period_end", "value", "unit")} for f in (numerator, revenue)]
            record = {"kind": kind, "metric": kind, "inputs": refs, "result_percent": str(percent),
                "formula": f"{metric.lower()} / revenue * 100", "status": "COMPUTED_FROM_CAPTURED_SOURCE_ASSERTIONS",
                "independent_verification": False}
            margins.append((revenue, record))
            results.append(record)
    for current, margin in margins:
        for prior, earlier in margins:
            if (margin["kind"] == earlier["kind"] and all(current.get(k) == prior.get(k) for k in ("cik", "unit", "statement_type", "accounting_basis"))
                    and 350 <= (date.fromisoformat(current["period_end"]) - date.fromisoformat(prior["period_end"])).days <= 378
                    and abs(current["duration_days"] - prior["duration_days"]) <= 8):
                with localcontext() as ctx:
                    ctx.prec = 80
                    current_margin = Decimal(margin["inputs"][0]["value"]) / Decimal(margin["inputs"][1]["value"]) * 100
                    prior_margin = Decimal(earlier["inputs"][0]["value"]) / Decimal(earlier["inputs"][1]["value"]) * 100
                    change = (current_margin - prior_margin).quantize(Decimal("0.0001"))
                results.append({"kind": "MARGIN_CHANGE_PERCENTAGE_POINTS", "metric": margin["kind"],
                    "result_percentage_points": str(change),
                    "formula": "current margin percent - prior-year margin percent", "inputs": margin["inputs"] + earlier["inputs"],
                    "status": "COMPUTED_FROM_CAPTURED_SOURCE_ASSERTIONS", "independent_verification": False})
    results.sort(key=lambda row: max((item.get("period_end", "") for item in row["inputs"]), default=""), reverse=True)
    return results[:40]


def scout_financial_disclosures(items, subject):
    documents, facts = [], []
    for item in items:
        document = qualified_document(item, subject)
        if document:
            source_id = item.get("evidence_id") or item.get("id") if isinstance(item, dict) else item.id
            documents.append({key: value for key, value in document.items() if key != "facts"})
            facts.extend({**fact, "evidence_id": source_id} for fact in document["facts"])
    raw_occurrences = len(facts)
    distinct = {}
    for fact in facts:
        key = tuple(fact.get(k) for k in ("cik", "concept", "taxonomy", "unit", "period_start", "period_end", "value"))
        reference = {k: fact.get(k) for k in ("evidence_id", "source_url", "json_pointer", "payload_sha256", "accession")}
        if key in distinct:
            distinct[key]["source_occurrences"].append(reference)
        else:
            distinct[key] = {**fact, "source_occurrences": [reference]}
    facts = sorted(distinct.values(), key=lambda f: (f["period_end"], f["filing_date"]), reverse=True)
    comparisons = reconcile_financial_facts(facts)
    from backend.services.research.issuer_identity import resolve_issuer
    from backend.infrastructure.acquisition.adapters.expansion_safety import policy_status
    identity = resolve_issuer(subject)
    blockers = ["SEC_CONTACT_NOT_CONFIGURED"] if identity.get("cik") and policy_status("sec_edgar") else []
    coverage = {metric: max(f["period_end"] for f in facts if f["metric"] == metric) for metric in {f["metric"] for f in facts}}
    return {"issuer_identity": identity, "documents": documents, "facts": facts[:120], "facts_omitted": max(0, len(facts) - 120), "comparisons": comparisons,
            "raw_fact_occurrences": raw_occurrences, "distinct_facts": len(facts), "duplicates_collapsed": raw_occurrences - len(facts),
            "latest_captured_period_by_metric": coverage, "current_period_adjudication": "NOT_PERFORMED",
            "status": "CAPTURED_SOURCE_ASSERTIONS" if facts else "NO_QUALIFIED_STRUCTURED_DISCLOSURES",
            "blockers": blockers if not documents else [],
            "comparison_status": "COMPUTED_FROM_SOURCE_INPUTS" if comparisons else "NO_COMPATIBLE_COMPARISON",
            "unavailable_comparisons": ["GUIDANCE_NOT_CAPTURED", "SECONDARY_REPORTING_NOT_RECONCILED"],
            "limitations": ["Source assertions; no independent financial audit.", "Filing fiscal labels are not assigned to comparative fact periods.",
                "Latest captured intervals do not establish the latest available financial results. Comparisons are bounded to 40 most recent entries."]}
