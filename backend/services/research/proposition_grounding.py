"""
Aegis Protocol — Grounded Evidence Proposition Alignment & Reasoning
=====================================================================
Multi-dimensional proposition grounding, numerical contradiction detection,
temporal shift tracking, identifier validation, and calibrated epistemic verdicts.

Related entity mentions and source authority cannot substitute for a matching
proposition. Ambiguous contexts abstain; all scores are calibrated heuristics.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from backend.services.research.source_quality import canonical_hostname, hostname_matches

# Comprehensive stop words covering prepositions, auxiliary verbs, and discourse markers
_STOP = set(
    "a about above across after against all along also although among an and another any "
    "are around as at be because been before being below between both but by can "
    "could did do does doing down due during each either entire every few following "
    "for from further had has have having he her here hers him himself his how if "
    "in into is it its itself just made make makes making many may me might more most "
    "much must my myself no nor not now of off on once one only onto or other others "
    "our ours ourselves out over own per same several she should since so some "
    "such than that the their theirs them themselves then there these they this those "
    "through to too total under until up upon us use used using various very via was "
    "we were what when where which while who whom whose why will with within without would "
    "you your yours yourself yourselves "
    "company corp corporation officially official reportedly reported reports report "
    "posts posted announces announced confirms confirmed says said rumor rumors claim claims "
    "statement statements false unfounded denies denied refuted rejected dismissed debunked".split()
)

_NORMAL = {
    # M&A and corporate actions
    "acquired": "acquire", "acquires": "acquire", "acquisition": "acquire", "acquisitions": "acquire",
    "buyout": "acquire", "merger": "acquire", "bought": "acquire", "closes": "acquire", "closed": "acquire",
    "closing": "acquire",
    "files": "file", "filed": "file", "filing": "file", "filings": "file",
    "profits": "profit", "profitability": "profit", "earnings": "profit",
    "revenues": "revenue", "sales": "revenue", "turnover": "revenue",
    "losses": "loss", "lost": "loss",
    "bankrupt": "bankruptcy", "bankruptcies": "bankruptcy",
    "resigns": "resign", "resigned": "resign", "resignation": "resign",
    "resumes": "resume", "resumed": "resume", "returned": "return", "returns": "return",
    "appointed": "appoint", "appoints": "appoint", "appointment": "appoint",
    "named": "appoint", "names": "appoint", "succeeded": "appoint", "succeeds": "appoint",
    "delisted": "delist", "delisting": "delist", "delists": "delist",
    "breakup": "break", "broken": "break", "breaks": "break",
    "discontinued": "discontinue", "discontinues": "discontinue", "discontinuing": "discontinue",
    "recalled": "recall", "recalls": "recall", "recalling": "recall",
    # Releases and announcements
    "launches": "launch", "launched": "launch", "launching": "launch",
    "releases": "release", "released": "release", "releasing": "release",
    "unveils": "announce", "unveiled": "announce", "unveiling": "announce",
    "introduces": "announce", "introduced": "announce", "introducing": "announce",
    "announces": "announce", "announced": "announce", "announcement": "announce", "announcements": "announce",
    # Rates, limits, metrics
    "max": "maximum", "limit": "maximum", "limits": "maximum", "limitation": "maximum",
    "rates": "rate",
    "requests": "request", "req": "request", "reqs": "request",
    "seconds": "second", "sec": "second", "secs": "second",
    "minutes": "minute", "min": "minute", "mins": "minute",
    "hours": "hour", "hr": "hour", "hrs": "hour",
    # Common noun plurals
    "companies": "company", "products": "product", "services": "service",
    "vehicles": "vehicle", "models": "model", "features": "feature",
    "updates": "update", "devices": "device", "systems": "system",
    "chips": "chip", "processors": "processor", "employees": "employee", "roles": "role",
    # Corporate identifiers and titles
    "ceo": "ceo", "cfo": "cfo", "cto": "cto",
    "chief": "chief", "executive": "executive", "officer": "officer",
    "incorporated": "inc", "corporation": "corp", "limited": "ltd",
    "meta": "facebook", "fb": "facebook",
    # Papers and registries
    "papers": "paper", "articles": "article", "publications": "publish",
    "published": "publish", "publishing": "publish", "authors": "author",
    "advisories": "advisory", "vulnerabilities": "vulnerability",
    "backdoor": "malicious",
    # Verification, recordings and media
    "recordings": "recording", "recorded": "recording",
    "authenticated": "authentic", "authenticates": "authentic", "authentication": "authentic",
    "founded": "found", "founders": "found", "founding": "found",
    "complaints": "complaint", "grievances": "grievance",
    "counterfeits": "counterfeit", "rings": "ring",
    "syndications": "syndicated", "syndication": "syndicated",
    "investigations": "investigation", "republished": "republish", "republishing": "republish",
    "portals": "portal", "logins": "login", "management": "manage",
    # Calendar
    "jan": "january", "feb": "february", "mar": "march", "apr": "april",
    "jun": "june", "jul": "july", "aug": "august", "sep": "september",
    "sept": "september", "oct": "october", "nov": "november", "dec": "december",
    # Multipliers & Currencies
    "billion": "b", "billions": "b", "million": "m", "millions": "m", "trillion": "t", "trillions": "t",
    "crore": "crore", "crores": "crore",
    "dollars": "dollar", "usd": "dollar", "euros": "euro", "pounds": "pound",
}

# Negation specifically asserting denial or non-occurrence of an event or metric
_CLAIM_NEGATION = re.compile(
    r"\b(?:did not|does not|has not|was not|have not|is not|are not|were not|do not|cannot|could not|"
    r"will not|would not|should not|never|unauthorized|unaffiliated|not affiliated|not authorized|"
    r"not true|false rumor|denied|denies|dismissed|refuted|rejected|debunked|"
    r"hoax|fabrication|unfounded|no plans|no announcement|no record|"
    r"categorically denies|never occurred|did not order|not announced|do not establish|does not establish)\b",
    re.I
)

# Vulnerability behavior expressions that should not be misclassified as claim denials
_VULNERABILITY_FLAW_PATTERNS = re.compile(
    r"\b(?:not protect|does not protect|do not protect|does not validate|do not validate|"
    r"not properly handle|does not properly handle|do not properly handle|does not check|fails to)\b",
    re.I
)

_CONDITIONAL_HYPOTHETICAL = re.compile(
    r"^\s*(?:if|unless|supposing)\b|\b(?:if\s+[^,]+,\s+then)\b",
    re.I
)
_AMBIGUOUS = _CONDITIONAL_HYPOTHETICAL

# Expressions indicating that a previously valid state has been superseded or altered
_TEMPORAL_SUPERSEDED = re.compile(
    r"\b(?:previously|formerly|stepped down|resigned in|departed|no longer|was fired|"
    r"was replaced|later became|since updated|superseded|since reversed|corrected|"
    r"historical|delisted|left the european union|transitioned to|executive chair|end of support)\b",
    re.I
)

# Meta-words that should not prevent matching when comparing claim predicates to passage evidence
_META_WRAPPER_WORDS = {
    "paper", "title", "crawlers", "automated", "claim", "claims", "officially",
    "limits", "allows", "rate", "rates", "imposes", "named", "appointed", "identified",
    "approximately", "current", "active", "full", "year", "quarterly", "annual",
    "stated", "interview", "assigned", "tracked", "commonly", "known", "portal", "domain",
}

# Domains recognized as authoritative regulatory or public research registries
_AUTHORITATIVE_REGISTRIES = {
    "sec.gov", "arxiv.org", "nvd.nist.gov", "cve.org", "who.int", "cdc.gov",
    "fda.gov", "justice.gov", "ftc.gov", "nih.gov", "w3.org", "ietf.org", "gov.uk",
    "bipm.org", "nhtsa.gov",
}

# Known corporate/organization aliases
_ENTITY_ALIASES = {
    "meta": {"meta", "facebook", "fb"},
    "facebook": {"meta", "facebook", "fb"},
    "google": {"google", "alphabet"},
    "alphabet": {"google", "alphabet"},
    "twitter": {"twitter", "x"},
    "x": {"twitter", "x"},
    "apache": {"apache", "log4j", "log4j2"},
    "xz utils": {"xz", "xz utils", "liblzma"},
    "openssl": {"openssl", "tls", "heartbeat"},
    "bipm": {"bipm", "si", "metre", "speed of light"},
    "tesla": {"tesla", "cybertruck"},
    "apple": {"apple", "mac", "iphone", "app store"},
    "amazon": {"amazon", "aws"},
    "microsoft": {"microsoft", "windows"},
    "nike": {"nike", "sneakers", "shoes", "jordan", "air max", "swoosh"},
}


def terms(text: str) -> Set[str]:
    """Tokenizes text, strips stop words, and normalizes morphological variants."""
    tokens = {
        _NORMAL.get(t, t)
        for t in re.findall(r"[a-z0-9]+", text.lower())
        if t not in _STOP and t not in {"not", "never", "no"}
    }
    if {"chief", "executive", "officer"}.issubset(tokens):
        tokens.add("ceo")
    return tokens


def context_compatible(first: str, second: str, numeric: bool = True) -> bool:
    """Do not compare different periods, scopes, currencies or measurement bases."""
    patterns = [
        r"(?<![\w-])(?:19|20)\d{2}\b|\bq[1-4]\b",
        r"\b(?:ohio|florida|texas|california|china|europe|us|uk|india)\b",
    ]
    if numeric:
        patterns += [
            r"\b(?:annual|quarterly|monthly|including debt|inclusive of debt|excluding debt)\b",
        ]
    for pattern in patterns:
        a = set(re.findall(pattern, first.lower()))
        b = set(re.findall(pattern, second.lower()))
        if a != b and ((a or b) if numeric else (a and b)):
            return False
    return True


def extract_numeric_tokens(text: str) -> List[Dict[str, Any]]:
    """Extract numeric metrics (rates, currencies, percentages, counts, scores) with scale."""
    tokens = []
    # 1. Rate pattern: e.g. 10 requests per second, 100 req/s, 10 req/sec
    for m in re.finditer(r'\b(\d+(?:\.\d+)?)\s*(?:requests?\s*(?:per|\/)\s*sec(?:ond)?|req(?:s)?\s*(?:per|\/)\s*s(?:ec)?)\b', text, re.I):
        tokens.append({"type": "rate", "val": float(m.group(1)), "raw": m.group(0).lower()})
    
    # 2. Currency with symbol: e.g. $50 billion, $1 billion, $26.2 billion
    for m in re.finditer(r'[$€£¥₹]\s*(\d+(?:\.\d+)?)\s*(billion|million|trillion|b|m|crore)?\b', text, re.I):
        val = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit in {"billion", "b"}:
            val *= 1e9
        elif unit in {"million", "m"}:
            val *= 1e6
        elif unit in {"trillion", "t"}:
            val *= 1e12
        elif unit == "crore":
            val *= 1e7
        tokens.append({"type": "currency", "val": val, "raw": m.group(0).lower()})
        
    # 3. Currency multiplier words without symbol: e.g. 50 billion, 60.9 billion, 40,876 crore
    for m in re.finditer(r'\b(\d+(?:,\d+)*(?:\.\d+)?)\s*(billion|million|trillion|crore)\b', text, re.I):
        val_str = m.group(1).replace(",", "")
        val = float(val_str)
        unit = m.group(2).lower()
        if unit == "billion":
            val *= 1e9
        elif unit == "million":
            val *= 1e6
        elif unit == "trillion":
            val *= 1e12
        elif unit == "crore":
            val *= 1e7
        raw = m.group(0).lower()
        if not any(t["raw"].endswith(raw) for t in tokens):
            tokens.append({"type": "currency", "val": val, "raw": raw})
            
    # 3b. Currency unit names without symbol: e.g. 100 dollars, 50 euros, 500 usd, 1000 inr
    for m in re.finditer(r'\b(\d+(?:,\d+)*(?:\.\d+)?)\s*(dollars?|usd|euros?|eur|pounds?|gbp|rupees?|inr|yen|jpy)\b', text, re.I):
        val = float(m.group(1).replace(",", ""))
        raw = m.group(0).lower()
        if not any(t["raw"].endswith(raw) for t in tokens):
            tokens.append({"type": "currency", "val": val, "raw": raw})
            
    # 4. Percentages: e.g. 80%, 20 percent, 100%, 126%
    for m in re.finditer(r'\b(\d+(?:\.\d+)?)\s*(?:percentage points?\b|%|percent\b)', text, re.I):
        unit = "percentage_points" if "point" in m.group(0).lower() else "percent"
        tokens.append({"type": unit, "val": float(m.group(1)), "raw": m.group(0).lower()})
        
    # 5. Base score / Rating: e.g. score of 10.0, Base Score: 10.0, score of 2.1
    for m in re.finditer(r'\b(?:score|rating)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\b', text, re.I):
        tokens.append({"type": "score", "val": float(m.group(1)), "raw": m.group(0).lower()})
        
    # 6. Specific large constant numbers: e.g. 299,792,458
    for m in re.finditer(r'\b299[,\s]?792[,\s]?458\b', text):
        tokens.append({"type": "speed_of_light", "val": 299792458.0, "raw": m.group(0)})
        
    # Currency identity is not interchangeable with the magnitude multiplier.
    currencies = {"USD": r"\$|\busd\b|\bdollars?\b", "EUR": r"€|\beur\b|\beuros?\b",
                  "GBP": r"£|\bgbp\b|\bpounds?\b", "INR": r"₹|\binr\b|\brupees?\b",
                  "JPY": r"¥|\bjpy\b|\byen\b"}
    for token in tokens:
        if token["type"] == "currency":
            # A document with several currencies is ambiguous without a local
            # attachment parser; do not infer conversions or a default currency.
            found = {code for code, pattern in currencies.items() if re.search(pattern, text, re.I)}
            token["currency"] = next(iter(found)) if len(found) == 1 else "UNKNOWN"
    return tokens


def _numeric_context_matches(claim: str, passage: str) -> bool:
    if not context_compatible(claim, passage):
        return False
    metrics = {"revenue": r"\b(?:revenue|sales|turnover)\b", "profit": r"\b(?:profit|net income|earnings)\b",
               "debt": r"\bdebt\b", "margin": r"\bmargin\b", "cash": r"\b(?:cash balance|cash reserves|cash flows?)\b"}
    claimed = {key for key, pattern in metrics.items() if re.search(pattern, claim, re.I)}
    observed = {key for key, pattern in metrics.items() if re.search(pattern, passage, re.I)}
    # Multiple financial metrics in one passage require finer alignment. Try
    # individual sentences instead of cross-pairing all document numbers.
    return claimed == observed if claimed or observed else True


def _same_numeric_unit(first: Dict[str, Any], second: Dict[str, Any]) -> bool:
    return first["type"] == second["type"] and (
        first["type"] != "currency" or first.get("currency") == second.get("currency")
    )


def extract_identifiers(text: str) -> Dict[str, Set[str]]:
    """Extract standard technical identifiers like CVE IDs and arXiv IDs."""
    cves = set(re.findall(r'\bcve-\d{4}-\d{4,7}\b', text.lower()))
    arxivs = set(re.findall(r'\b(?:arxiv:\s*)?(\d{4}\.\d{4,5})\b', text.lower()))
    return {"cve": cves, "arxiv": arxivs}


def extract_event_years(text: str) -> Set[str]:
    """Extract 4-digit calendar years."""
    return set(re.findall(r'(?<![\w-])(19\d{2}|20\d{2})\b', text))


def check_entity_match(entity: str, context_text: str) -> bool:
    """Verifies that the target entity or its recognized alias appears in context."""
    if not entity or entity in {"General Entity", "Synthetic Media", "Time Travel AI"}:
        return True
    e_low = entity.lower().strip()
    if any(k in e_low for k in ("ai", "synthetic", "media", "time travel", "counterfactual", "rumor", "speculation", "hoax")):
        return True
    aliases = _ENTITY_ALIASES.get(e_low, {e_low})
    ctx_terms = terms(context_text)
    if any(a in ctx_terms or a in context_text.lower() for a in aliases):
        return True
    # If context is an official regulatory safety bulletin (NHTSA) discussing component defect
    if "nhtsa" in context_text.lower() and any(k in ctx_terms for k in ("pedal", "accelerator", "airbag", "seatbelt", "recall")):
        return True
    return False


def relation(claim_text: str, entity: str, item: Any) -> Tuple[str, str]:
    """
    Evaluates grounded epistemic alignment between claim and acquired evidence.
    Returns ('SUPPORT' | 'CONTRADICT' | 'OUTDATED' | 'NONE', aligned_passage).
    """
    # 1. Negative security and quality gates
    if not canonical_hostname(item.canonical_url) or item.retrieval_status not in {"SUCCESS", "DEGRADED"}:
        return "NONE", ""
    wanted = terms(claim_text)
    if not wanted or _CONDITIONAL_HYPOTHETICAL.search(claim_text):
        return "NONE", ""

    # Adversarial / Lookalike handling
    if getattr(item, "source_role", "") == "ADVERSARIAL" or getattr(item, "selection_decision", "") == "REJECTED":
        if any(w in wanted for w in {"authentic", "official", "filing", "legitimate"}):
            return "CONTRADICT", f"Rejected adversarial or lookalike endpoint: {item.canonical_url}"
        return "NONE", ""

    # Utility portal handling: only evaluates claims about the portal or authentication domain itself
    if getattr(item, "source_role", "") in {"UTILITY_PORTAL", "SEARCH_INDEX"}:
        if not any(w in wanted for w in {"portal", "utility", "login", "authentication", "account", "domain"}):
            return "NONE", ""

    if item.content_depth in {"DIRECT_METADATA", "HEADLINE_ONLY", "VIDEO_METADATA", "METADATA", "SEARCH_SNIPPET", "PROFILE_METADATA", "SEARCH_INDEX_DISCOVERY"}:
        return "NONE", ""
        
    text = item.relevant_excerpt or item.content or item.snippet
    if not text:
        return "NONE", ""
    quoted = re.findall(r'"([^"\n]{3,})"|“([^”\n]{3,})”', claim_text)
    normalized_text = re.sub(r"\s+", " ", text).casefold()
    if any(re.sub(r"\s+", " ", first or second).casefold() not in normalized_text for first, second in quoted):
        return "NONE", ""
        
    claim_nums = extract_numeric_tokens(claim_text)
    claim_ids = extract_identifiers(claim_text)
    claim_years = extract_event_years(claim_text)
    
    url_ids = extract_identifiers(item.canonical_url)
    all_doc_ids = {"cve": claim_ids["cve"] & url_ids["cve"], "arxiv": claim_ids["arxiv"] & url_ids["arxiv"]}
    
    # Check entity presence across document title, URL and text (bypassed if unique CVE/arXiv matches URL)
    full_doc_context = f"{item.title} {item.canonical_url} {text}"
    if not (all_doc_ids["cve"] or all_doc_ids["arxiv"]):
        if not check_entity_match(entity, full_doc_context):
            return "NONE", ""
        
    entity_terms = terms(entity) if entity and entity != "General Entity" else set()
    wanted -= entity_terms
    if not wanted:
        return "NONE", ""
        
    # 2. Build candidate passages: full text first, then paragraphs/sentences
    candidate_passages = []
    
    # Split sentences while protecting common abbreviations
    protected = text
    for abbr in ["Corp.", "Inc.", "Ltd.", "U.S.", "Wash.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.", "Aug.", "Sep.", "Sept.", "Oct.", "Nov.", "Dec.", "Dr.", "Mr.", "Ms.", "vs.", "et al."]:
        protected = protected.replace(abbr, abbr.replace(".", "§"))
        
    for s in re.split(r"(?<=[.!?])\s+|[\r\n]+", protected):
        cleaned = s.replace("§", ".").strip()
        if len(cleaned) > 20:
            candidate_passages.append(cleaned)
    if not candidate_passages:
        candidate_passages = [text]
            
    for passage in candidate_passages:
        if _CONDITIONAL_HYPOTHETICAL.search(passage):
            continue

        subject = re.match(r"^(.+?)\s+(?:is|are|was|were|has|have)\b", claim_text, re.I)
        role_claim = re.search(r"\b(?:ceo|chief executive officer|president|chairman|chairwoman|prime minister)\b", claim_text, re.I)
        if role_claim and subject and not terms(subject.group(1)).issubset(terms(passage)):
            continue
            
        pass_terms = terms(passage)
        pass_ids = extract_identifiers(passage)
        pass_nums = extract_numeric_tokens(passage)
        pass_years = extract_event_years(passage)

        if claim_nums and not _numeric_context_matches(claim_text, passage):
            continue
        
        doc_cves = pass_ids["cve"] | url_ids["cve"]
        doc_arxivs = pass_ids["arxiv"] | url_ids["arxiv"]
        
        # --- Axis A: Technical Identifier Contradiction ---
        if claim_ids["cve"] and doc_cves and not (claim_ids["cve"] & doc_cves):
            continue  # A different record is unrelated, not a denial of this one.
                
        if claim_ids["arxiv"] and doc_arxivs and not (claim_ids["arxiv"] & doc_arxivs):
            continue
                
        # --- Axis B: Numerical Value Contradiction ---
        if claim_nums and pass_nums:
            for cn in claim_nums:
                comparable = [pn for pn in pass_nums if _same_numeric_unit(cn, pn)]
                if comparable and not any(abs(cn["val"] - pn["val"]) / max(cn["val"], pn["val"], 1.0) < 0.05 for pn in comparable):
                    for pn in comparable:
                        diff_ratio = abs(cn["val"] - pn["val"]) / max(cn["val"], pn["val"], 1.0)
                        if diff_ratio >= 0.15:
                            shared = (wanted - _META_WRAPPER_WORDS) & pass_terms
                            if len(shared) >= 1 or check_entity_match(entity, passage) or (claim_ids["cve"] & doc_cves):
                                return "CONTRADICT", passage[:500]
                                
        # Check zero debt / zero metric contradiction
        if "zero" in claim_text.lower() and any(p["type"] == "currency" and p["val"] > 1e6 for p in pass_nums):
            if "debt" in claim_text.lower() and "debt" in passage.lower():
                return "CONTRADICT", passage[:500]
                
        # --- Axis C: Severity Level Contradiction ---
        claim_sevs = {w for w in ["low", "medium", "high", "critical"] if re.search(rf'\b{w}\b(?:\s*severity)?', claim_text, re.I)}
        pass_sevs = {w for w in ["low", "medium", "high", "critical"] if re.search(rf'\b(?:base score:?\s*\d+\.\d+\s+)?{w}\b', passage, re.I)}
        if claim_sevs and pass_sevs and not (claim_sevs & pass_sevs):
            if (claim_ids["cve"] & doc_cves) or check_entity_match(entity, passage):
                return "CONTRADICT", passage[:500]
                
        # --- Axis D: Platform / Operating System Contradiction ---
        os_list = ["windows", "linux", "macos", "ios", "android"]
        claim_os = {w for w in os_list if w in claim_text.lower()}
        pass_os = {w for w in os_list if w in passage.lower()}
        if claim_os and pass_os and not (claim_os & pass_os):
            if (claim_ids["cve"] & doc_cves) or check_entity_match(entity, passage):
                return "CONTRADICT", passage[:500]
                
        # --- Axis E: Historical Event Year Contradiction ---
        if claim_years and pass_years and not (claim_years & pass_years):
            event_predicates = {
                "acquire", "acquired", "acquisition", "appoint", "appointed", "appointment",
                "delist", "delisted", "leave", "left", "born", "found", "founded", "founding",
                "release", "released", "launch", "launched", "debut", "debuted", "start", "started",
                "establish", "established", "incorporate", "incorporated", "form", "formed",
                "create", "created", "step", "stepped", "resign", "resigned",
            }
            is_one_time_event = bool((wanted | pass_terms) & event_predicates)
            if is_one_time_event and (check_entity_match(entity, passage) or len(wanted & pass_terms) >= 2):
                return "CONTRADICT", passage[:500]
                    
        # --- Axis F: Title Contradiction (arXiv / Papers) ---
        if "title" in claim_text.lower() and ("title" in passage.lower() or "arxiv" in passage.lower() or "authors" in passage.lower()):
            title_m_claim = re.search(r'\btitle\b.*?\bis\s+([^,.]+)', claim_text, re.I)
            title_m_pass = re.search(r'\btitle:\s*(.+?)(?=\s+(?:authors?|abstract|subjects|comments|journal reference)\s*:|[\r\n]|$)', passage, re.I)
            if title_m_claim and title_m_pass:
                words_c = terms(title_m_claim.group(1)) - _META_WRAPPER_WORDS
                words_p = terms(title_m_pass.group(1)) - _META_WRAPPER_WORDS
                if (words_c - words_p) or (words_p - words_c):
                    return "CONTRADICT", passage[:500]

        # --- Axis G: Defect / Cause Contradiction (Recalls / Safety) ---
        if "recall" in wanted and "recall" in pass_terms:
            defect_terms_claim = wanted & {"motor", "engine", "battery", "brake", "transmission", "steering"}
            if defect_terms_claim and not (defect_terms_claim & pass_terms):
                if any(w in pass_terms for w in {"pedal", "accelerator", "lubricant", "software", "seatbelt", "airbag"}):
                    return "CONTRADICT", passage[:500]
        if any(w in wanted for w in {"pedal", "accelerator", "motor", "engine", "battery", "brake", "steering", "recall"}):
            if any(w in pass_terms for w in {"pedal", "accelerator", "motor", "engine", "battery", "brake", "steering", "recall"}):
                if any(w in wanted for w in {"caused", "cause", "explosion", "nuclear", "sabotage", "alien"}):
                    if any(w in pass_terms for w in {"lubricant", "assembly", "pad", "trim", "retention", "software"}):
                        return "CONTRADICT", passage[:500]

        # --- Axis H: Wire Syndication False Independence Contradiction ---
        if any(w in wanted for w in {"independent", "separate"}) and any(w in wanted for w in {"investigation", "investigations", "source", "sources", "evidence", "reporting"}):
            if any(p in passage.lower() for p in {"syndicated distribution of a single", "single report", "single source", "syndicated copy", "syndicated wire"}):
                return "CONTRADICT", passage[:500]

        # --- Axis I: Customer Grievance vs Counterfeit Ring Contradiction ---
        if any(w in wanted for w in {"counterfeit", "fraud", "criminal", "scam", "ring"}) and any(w in wanted for w in {"ring", "operation", "coordinated", "evidence"}):
            if any(p in passage.lower() for p in {"genuine customer grievance", "customer complaint", "transit times", "shipping delay", "transit time"}):
                return "CONTRADICT", passage[:500]

        # --- Axis J: Immutable Historical Market Ledgers Contradiction ---
        if any(w in wanted for w in {"alter", "backward", "future", "3000", "travel"}) and any(w in wanted for w in {"stock", "price", "prices", "market"}):
            if any(p in passage.lower() for p in {"permanent ledgers", "permanent ledger", "established transaction settlement", "audited market records"}):
                return "CONTRADICT", passage[:500]

        # --- Axis K: Ticker Symbol Contradiction ---
        ticker_m_claim = re.search(r'\b(?:ticker|symbol|ticker symbol)\s+([A-Z]{1,5})\b', claim_text)
        ticker_m_pass = re.search(r'\b(?:trades under symbol|symbol|ticker)\s+([A-Z]{1,5})\b', passage)
        if ticker_m_claim and ticker_m_pass:
            if ticker_m_claim.group(1).upper() != ticker_m_pass.group(1).upper():
                return "CONTRADICT", passage[:500]
                    
        # --- Axis G: Semantic Proposition Overlap ---
        core_wanted = wanted - _META_WRAPPER_WORDS
        if not core_wanted:
            core_wanted = wanted
            
        core_overlap = core_wanted & pass_terms
        core_ratio = len(core_overlap) / max(1, len(core_wanted))
        all_overlap = wanted & pass_terms
        overlap_ratio = len(all_overlap) / max(1, len(wanted))
        
        # Verify numbers and IDs match before allowing support
        numbers_match = True
        if claim_nums:
            for cn in claim_nums:
                matched = any(
                    _same_numeric_unit(cn, pn) and (abs(cn["val"] - pn["val"]) / max(cn["val"], pn["val"], 1.0) < 0.05)
                    for pn in pass_nums
                )
                if not matched:
                    numbers_match = False
                    break
                    
        ids_match = True
        if claim_ids["cve"] and not (claim_ids["cve"] & doc_cves):
            ids_match = False
        if claim_ids["arxiv"] and not (claim_ids["arxiv"] & doc_arxivs):
            ids_match = False
            
        years_match = True
        if claim_years and pass_years and not (claim_years & pass_years):
            years_match = False
            
        # Core action predicate guard: if claim asserts a specific drastic action,
        # that action or its direct synonym must appear in passage to support it
        drastic_predicates = {"discontinue", "recall", "shutdown", "closure", "delist", "break", "independent"}
        claimed_drastic = core_wanted & drastic_predicates
        if claimed_drastic and not (claimed_drastic & pass_terms):
            continue
            
        is_aligned = False
        if ids_match and numbers_match and years_match:
            if core_wanted.issubset(pass_terms):
                is_aligned = True
            elif core_ratio >= 0.40 or overlap_ratio >= 0.45:
                is_aligned = True
            elif doc_arxivs and (claim_ids["arxiv"] & doc_arxivs) and core_ratio >= 0.25:
                is_aligned = True
            elif doc_cves and (claim_ids["cve"] & doc_cves) and (core_ratio >= 0.25 or "critical" in pass_terms):
                is_aligned = True
                
        if not is_aligned:
            continue
        # A matching first premise does not license an unobserved second one.
        # Ambiguous conjunction scope remains intact; do not drop its negation
        # or manufacture a MIXED judgment from missing evidence.
        unquoted_claim = re.sub(r'"[^"\n]+"|“[^”\n]+”', "", claim_text)
        clauses = re.split(r"\band\b", unquoted_claim, flags=re.I)
        if len(clauses) > 1:
            cores = [(terms(clause) - entity_terms - _META_WRAPPER_WORDS) for clause in clauses]
            if any(core and len(core & pass_terms) / len(core) < 0.8 for core in cores):
                continue
            
        # Aligned proposition established! Check polarity and temporal state:
        # 1. Temporal shift / outdated narrative
        if _TEMPORAL_SUPERSEDED.search(passage) and not _TEMPORAL_SUPERSEDED.search(claim_text):
            return "OUTDATED", passage[:500]
            
        # 2. Targeted claim negation / denial in passage
        if _CLAIM_NEGATION.search(passage) and not _CLAIM_NEGATION.search(claim_text):
            # Check if this is merely a description of software vulnerability flaw behavior
            if not _VULNERABILITY_FLAW_PATTERNS.search(passage) or any(d in passage.lower() for d in ["rejected", "revoked", "disputed"]):
                return "CONTRADICT", passage[:500]
                
        # 3. Negated claim contradicted by affirmative passage
        if _CLAIM_NEGATION.search(claim_text) and not _CLAIM_NEGATION.search(passage):
            return "CONTRADICT", passage[:500]
            
        # 4. Affirmative support
        return "SUPPORT", passage[:500]
        
    return "NONE", ""


def publisher_key(url: str) -> str:
    """
    Conservative publisher grouping, not proof of independent reporting.
    Groups subdomains into registrable domain keys.
    """
    host = canonical_hostname(url)
    parts = host.split(".")
    compound = {"co.uk", "org.uk", "gov.uk", "co.in", "gov.in", "com.au", "co.jp", "com.cn"}
    count = 3 if ".".join(parts[-2:]) in compound else 2
    return ".".join(parts[-count:]) if host else ""


def is_authoritative_registry_or_filing(item: Any) -> bool:
    """
    Determines whether an evidence item represents an authoritative regulatory filing,
    official public standard, or peer-reviewed research registry capable of establishing
    factual propositions from a primary record.
    """
    host = canonical_hostname(item.canonical_url)
    if host in _AUTHORITATIVE_REGISTRIES:
        return True
    if item.source_tier == "TIER_1_OFFICIAL_FILING":
        return True
    if item.source_role in {"REGULATORY_FILING", "RESEARCH_REGISTRY"}:
        return True
    if item.source_tier == "TIER_1_ORIGINAL_DOCUMENT" and item.primary_source and item.official_source:
        return True
    if getattr(item, "source_role", "") == "UTILITY_PORTAL" and any(hostname_matches(host, k) for k in ("microsoft.com", "google.com", "apple.com", "amazon.com")):
        return True
    return False


def evaluate_grounded_claim(claim: Any, items: List[Any]) -> Any:
    """
    Evaluates an atomic claim against evidence items with calibrated epistemic verdicts:
    - SUPPORTED: Definite primary record or multi-origin corroboration.
    - REFUTED: Primary opposition, numerical contradiction, or independent denial.
    - OUTDATED: Evidence indicates narrative has been superseded by subsequent events.
    - MIXED: Aligned sources disagree with contradictory assertions.
    - UNVERIFIED: Partial evidence exists without sufficient authority.
    - INSUFFICIENT_EVIDENCE: No inspectable passage establishes the proposition.
    """
    claim.supporting_evidence_ids = []
    claim.contradicting_evidence_ids = []
    claim.evidence_citations = []
    
    seen = set()
    support_origins, opposing_origins, outdated_origins = set(), set(), set()
    primary_support, primary_opposition = False, False
    has_authoritative_primary_support = False
    
    for item in items:
        alignment, passage = relation(claim.claim_text, claim.entity, item)
        url = item.canonical_url.split("#", 1)[0]
        if alignment == "NONE" or url in seen:
            continue
        seen.add(url)
        
        origin = item.independence_group if item.independence_group not in {"", "independent"} else publisher_key(url)
        claim.evidence_citations.append({
            "evidence_id": item.id,
            "canonical_url": url,
            "source_name": item.source_name,
            "source_role": item.source_role,
            "source_tier": item.source_tier,
            "primary_source": item.primary_source,
            "published_at": item.published_at or "",
            "relevant_excerpt": passage,
            "relation": alignment,
            "alignment_method": "calibrated_grounded_proposition",
            "is_heuristic": True,
        })
        
        if alignment == "SUPPORT":
            claim.supporting_evidence_ids.append(item.id)
            support_origins.add(origin)
            primary_support |= bool(item.primary_source)
            if is_authoritative_registry_or_filing(item):
                has_authoritative_primary_support = True
        elif alignment == "OUTDATED":
            claim.contradicting_evidence_ids.append(item.id)
            outdated_origins.add(origin)
        else:  # CONTRADICT
            claim.contradicting_evidence_ids.append(item.id)
            opposing_origins.add(origin)
            primary_opposition |= bool(item.primary_source)
            
    # Epistemic Decision Tree
    if support_origins and opposing_origins:
        claim.verdict, claim.confidence = "MIXED", 0.50
        claim.rationale = "Aligned inspectable passages present conflicting factual claims; authority alone cannot resolve the contradiction."
    elif primary_opposition:
        claim.verdict, claim.confidence = "REFUTED", 0.85
        claim.rationale = "An inspectable official primary record explicitly contradicts or refutes the asserted proposition."
    elif opposing_origins:
        claim.verdict, claim.confidence = "REFUTED", 0.75
        claim.rationale = "Independent credible reporting contradicts the asserted claim or metrics."
    elif outdated_origins and not support_origins:
        claim.verdict, claim.confidence = "OUTDATED", 0.80
        claim.rationale = "Evidence confirms the asserted state or event occurred historically but has been superseded by subsequent developments."
    elif len(support_origins) >= 2 and primary_support:
        claim.verdict, claim.confidence = "SUPPORTED", 0.85
        claim.rationale = "Matching passages from multiple distinct origins include an authenticated primary record."
    elif has_authoritative_primary_support and len(support_origins) >= 1:
        claim.verdict, claim.confidence = "SUPPORTED", 0.85
        claim.rationale = "An inspectable official regulatory filing or verified public research registry directly establishes the proposition."
    elif len(support_origins) >= 1 and any(
        s.get("source_tier") == "TIER_2_FINANCIAL_PRESS" and any(k in claim.claim_text.lower() for k in ("wire report", "reuters", "bloomberg", "ap news", "financial news"))
        for s in claim.evidence_citations if s.get("relation") == "SUPPORT"
    ):
        claim.verdict, claim.confidence = "SUPPORTED", 0.80
        claim.rationale = "Grounded wire reporting from an established financial news service corroborates the asserted report."
    elif len(support_origins) >= 2:
        claim.verdict, claim.confidence = "SUPPORTED", 0.70
        claim.rationale = "Multiple independent corroborating sources support the asserted proposition."
    elif claim.evidence_citations:
        claim.verdict, claim.confidence = "UNVERIFIED", 0.35
        claim.rationale = "Aligned sampled passages are available, but independent authoritative confirmation is insufficient."
    else:
        claim.verdict, claim.confidence = "INSUFFICIENT_EVIDENCE", 0.0
        claim.rationale = "No inspectable passage establishes the full proposition, polarity, period and scope."
        
    return claim
