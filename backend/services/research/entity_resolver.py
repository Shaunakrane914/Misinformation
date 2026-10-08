"""
Aegis Protocol — Canonical Entity Resolution & Disambiguation Engine
=====================================================================
Parses user requests and investigation targets into strongly typed TargetEntity
contracts. Distinguishes target entities, action verbs, intents, and topics.
Enforces multi-word entity disambiguation rules and general negative entity/context
filtering to prevent false-positive contamination.
"""

import re
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple


# Known action/intent verbs that MUST NOT be treated as entity tokens
ACTION_VERBS: Set[str] = {
    "investigate", "investigating", "investigation",
    "audit", "auditing",
    "analyze", "analyzing", "analysis",
    "scan", "scanning",
    "search", "searching",
    "find", "finding",
    "check", "checking",
    "monitor", "monitoring",
    "detect", "detecting",
    "verify", "verifying", "verification",
    "examine", "examining",
    "explore", "exploring",
    "report", "reporting",
    "track", "tracking",
    "assess", "assessing", "assessment",
    "review", "reviewing",
    "probe", "probing",
    "look", "looking",
    "show", "showing",
    "identify", "identifying",
}

# Stopwords to exclude from entity tokenization
GENERAL_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "at", "to",
    "from", "by", "with", "about", "using", "current", "public", "information",
    "info", "data", "any", "important", "notable", "recent", "what", "is",
    "are", "around", "involving", "latest", "new", "online", "threats",
    "threat", "developments", "activity", "activities"
}


@dataclass
class TargetEntity:
    """
    Canonical entity contract representing the unambiguous subject of an investigation.
    """
    canonical_name: str
    entity_type: str = "general"             # "person" | "company" | "brand" | "concept" | "product" | "general"
    aliases: List[str] = field(default_factory=list)
    handles: Dict[str, List[str]] = field(default_factory=dict)     # e.g. {"twitter": ["satyanadella"]}
    organizations: List[str] = field(default_factory=list)          # e.g. ["Microsoft"]
    roles: List[str] = field(default_factory=list)                  # e.g. ["CEO", "chairman"]
    ticker: Optional[str] = None                                    # e.g. "MSFT"
    positive_context: List[str] = field(default_factory=list)       # terms supporting entity presence
    negative_entities: List[str] = field(default_factory=list)      # known confusable entities
    negative_context: List[str] = field(default_factory=list)       # terms signaling wrong entity domain

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_multi_word(self) -> bool:
        """Returns True if the canonical name has 2 or more meaningful words."""
        tokens = [w for w in re.split(r'[^a-zA-Z0-9]', self.canonical_name) if len(w) >= 2]
        return len(tokens) >= 2


@dataclass
class ParsedInvestigationRequest:
    """
    Structured outcome of parsing a user prompt or agent request.
    """
    raw_query: str
    action_verb: Optional[str] = None
    target_entity: TargetEntity = field(default_factory=lambda: TargetEntity(canonical_name="Unknown"))
    intent: str = ""
    topic: str = ""
    domain: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "action_verb": self.action_verb,
            "target_entity": self.target_entity.to_dict(),
            "intent": self.intent,
            "topic": self.topic,
            "domain": self.domain,
        }


# Knowledge base of canonical profiles for standard tech & business entities
KNOWN_CANONICAL_PROFILES: Dict[str, TargetEntity] = {
    "satya nadella": TargetEntity(
        canonical_name="Satya Nadella",
        entity_type="person",
        aliases=["Satya Nadella", "Nadella"],
        handles={"twitter": ["satyanadella"], "linkedin": ["satyanadella"]},
        organizations=["Microsoft", "Microsoft Corporation"],
        roles=["CEO", "Chief Executive Officer", "Chairman", "Executive"],
        positive_context=[
            "microsoft", "ceo", "executive", "azure", "copilot", "windows",
            "openai", "ai", "cloud", "redmond", "earnings", "keynote", "board"
        ],
        negative_entities=[
            "Satya (1998 film)",
            "Satya (film)",
            "Satya Hindi Movie",
            "Satya Sanskrit concept",
            "Satya truth philosophy"
        ],
        negative_context=[
            "movie", "film", "hindi movie", "manoj bajpayee", "urmila matondkar",
            "ram gopal varma", "songs", "lyrics", "box office", "cinema",
            "sanskrit", "hinduism", "jainism", "buddhism", "truthfulness", "virtue",
            "incense", "agarbatti", "sai baba"
        ]
    ),
    "microsoft": TargetEntity(
        canonical_name="Microsoft",
        entity_type="company",
        aliases=["Microsoft", "Microsoft Corporation", "Microsoft Corp", "MSFT"],
        handles={"twitter": ["Microsoft", "MSFTNews", "Azure"], "youtube": ["Microsoft"]},
        organizations=["Microsoft"],
        roles=["Technology Company", "Cloud Provider", "Software Giant"],
        ticker="MSFT",
        positive_context=[
            "msft", "windows", "azure", "office", "copilot", "xbox", "surface",
            "satya nadella", "cloud", "software", "redmond", "security", "patch tuesday",
            "cybersecurity", "phishing", "scam", "impersonation", "counterfeit", "earnings"
        ],
        negative_entities=[
            "Magic: The Gathering Investigate",
            "MTG Investigate mechanic",
            "Investigate EDH deck"
        ],
        negative_context=[
            "magic the gathering", "mtg", "innistrad", "clue token", "edh", "commander",
            "tireless tracker", "graf mole", "deck building", "card game", "trading card"
        ]
    ),
    "msft": TargetEntity(
        canonical_name="Microsoft",
        entity_type="company",
        aliases=["Microsoft", "Microsoft Corporation", "Microsoft Corp", "MSFT"],
        handles={"twitter": ["Microsoft", "MSFTNews"]},
        organizations=["Microsoft"],
        ticker="MSFT",
        positive_context=["microsoft", "stock", "shares", "earnings", "nasdaq", "cloud", "azure"],
        negative_entities=[],
        negative_context=[]
    ),
    "sam altman": TargetEntity(
        canonical_name="Sam Altman",
        entity_type="person",
        aliases=["Sam Altman", "Samuel Altman", "Altman"],
        handles={"twitter": ["sama"]},
        organizations=["OpenAI", "Y Combinator", "Worldcoin"],
        roles=["CEO", "Founder", "Executive"],
        positive_context=["openai", "chatgpt", "gpt-4", "ai", "ceo", "worldcoin", "y combinator"],
        negative_entities=["Samwise Gamgee", "Sam (Lord of the Rings)"],
        negative_context=["lord of the rings", "lotr", "frodo", "hobbit", "chrome download", "printer driver"]
    ),
    "jensen huang": TargetEntity(
        canonical_name="Jensen Huang",
        entity_type="person",
        aliases=["Jensen Huang", "Jen-Hsun Huang", "Jensen"],
        handles={},
        organizations=["Nvidia", "NVIDIA Corporation"],
        roles=["CEO", "Founder", "President"],
        positive_context=["nvidia", "gpu", "blackwell", "cuda", "semiconductor", "ai chips", "geforce"],
        negative_entities=["Jensen (League of Legends)"],
        negative_context=["league of legends", "esports", "c9 jensen", "mid laner", "bank of baroda", "unesco"]
    ),
    "nvidia": TargetEntity(
        canonical_name="Nvidia",
        entity_type="company",
        aliases=["Nvidia", "NVIDIA Corporation", "NVDA"],
        ticker="NVDA",
        organizations=["Nvidia"],
        positive_context=["nvda", "blackwell", "geforce", "gpu", "semiconductor", "cuda", "jensen huang"],
        negative_entities=[],
        negative_context=["bank of baroda", "unesco", "teams tenant", "kiosk", "mortgage"]
    ),
    "nvda": TargetEntity(
        canonical_name="Nvidia",
        entity_type="company",
        aliases=["Nvidia", "NVIDIA Corporation", "NVDA"],
        ticker="NVDA",
        organizations=["Nvidia"],
        positive_context=["nvidia", "gpu", "semiconductor", "blackwell", "earnings", "nasdaq"],
        negative_entities=[],
        negative_context=["bank of baroda", "unesco"]
    ),
    "elon musk": TargetEntity(
        canonical_name="Elon Musk",
        entity_type="person",
        aliases=["Elon Musk", "Musk"],
        handles={"twitter": ["elonmusk"]},
        organizations=["Tesla", "SpaceX", "xAI", "X", "Neuralink"],
        roles=["CEO", "Founder"],
        positive_context=["tesla", "spacex", "xai", "cybertruck", "starship", "robotaxi"],
        negative_entities=[],
        negative_context=["recipe", "horoscope", "cricket score"]
    ),
    "tesla": TargetEntity(
        canonical_name="Tesla",
        entity_type="company",
        aliases=["Tesla", "Tesla Motors", "TSLA"],
        ticker="TSLA",
        organizations=["Tesla"],
        positive_context=["tsla", "elon musk", "ev", "robotaxi", "cybertruck", "fsd", "model 3"],
        negative_entities=["Nikola Tesla"],
        negative_context=["19th century", "inventor alternating current", "wardenclyffe"]
    ),
    "tsla": TargetEntity(
        canonical_name="Tesla",
        entity_type="company",
        aliases=["Tesla", "Tesla Motors", "TSLA"],
        ticker="TSLA",
        organizations=["Tesla"],
        positive_context=["tesla", "ev", "stock", "nasdaq", "elon musk"],
        negative_entities=[],
        negative_context=[]
    ),
}


class EntityResolver:
    """
    Canonical Entity Resolution & Disambiguation Engine.
    """

    @classmethod
    def parse_request(
        cls,
        raw_input: str,
        domain: str = "general",
        explicit_entity: Optional[str] = None
    ) -> ParsedInvestigationRequest:
        """
        Parse raw user query or agent input into a structured ParsedInvestigationRequest.
        Separates action verb from target entity and extracts intent/topic.
        """
        clean_input = (raw_input or "").strip()
        words = re.findall(r'[a-zA-Z0-9_\-\$]+', clean_input)

        action_verb: Optional[str] = None
        remaining_words: List[str] = []

        # 1. Identify leading action verbs
        if words and words[0].lower() in ACTION_VERBS:
            action_verb = words[0].lower()
            remaining_words = words[1:]
        else:
            remaining_words = words[:]

        # 2. If explicit entity is provided, use it directly
        candidate_entity_str = explicit_entity.strip() if explicit_entity else ""

        # Otherwise extract from remaining words
        if not candidate_entity_str:
            lower_str = clean_input.lower()
            for key in sorted(KNOWN_CANONICAL_PROFILES.keys(), key=len, reverse=True):
                # Ensure word boundary match
                pattern = r'\b' + re.escape(key) + r'\b'
                if re.search(pattern, lower_str):
                    candidate_entity_str = KNOWN_CANONICAL_PROFILES[key].canonical_name
                    break

            if not candidate_entity_str:
                # Fallback: take meaningful non-stopword tokens (up to 3 words)
                filtered = [w for w in remaining_words if w.lower() not in GENERAL_STOPWORDS and w.lower() not in ACTION_VERBS]
                candidate_entity_str = " ".join(filtered[:3]) if filtered else (clean_input or "Unknown")

        target_entity = cls.resolve_entity(candidate_entity_str, domain=domain)

        # 3. Derive intent and topic
        intent = clean_input
        topic = "brand_threats" if domain == "brand" else ("financial" if domain == "financial" else "general")

        return ParsedInvestigationRequest(
            raw_query=clean_input,
            action_verb=action_verb,
            target_entity=target_entity,
            intent=intent,
            topic=topic,
            domain=domain
        )

    @classmethod
    def resolve_entity(
        cls,
        entity_name_or_query: str,
        domain: str = "general"
    ) -> TargetEntity:
        """
        Resolves an entity string to a canonical TargetEntity contract.
        """
        clean_name = (entity_name_or_query or "").strip()
        lower_name = clean_name.lower()

        # 1. Direct match in known catalog
        for key, profile in KNOWN_CANONICAL_PROFILES.items():
            if lower_name == key:
                return profile
        for key, profile in KNOWN_CANONICAL_PROFILES.items():
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, lower_name):
                return profile

        # 2. Check cashtags ($MSFT, $NVDA)
        if clean_name.startswith("$"):
            ticker = clean_name[1:].upper()
            if ticker.lower() in KNOWN_CANONICAL_PROFILES:
                return KNOWN_CANONICAL_PROFILES[ticker.lower()]

        # 3. Dynamic entity construction
        tokens = [w for w in re.split(r'[^a-zA-Z0-9]', clean_name) if w and w.lower() not in ACTION_VERBS and w.lower() not in GENERAL_STOPWORDS]
        clean_canonical = " ".join(tokens).title() if tokens else clean_name

        is_multi = len(tokens) >= 2
        ent_type = "person" if (is_multi and domain == "personal") else ("company" if domain in ("brand", "financial") else "general")

        # Basic positive context defaults
        pos_context = [t.lower() for t in tokens if len(t) >= 3]
        if ent_type == "person":
            pos_context.extend(["executive", "ceo", "founder", "statement", "profile"])
        elif ent_type == "company":
            pos_context.extend(["company", "corp", "corporation", "business", "official"])

        return TargetEntity(
            canonical_name=clean_canonical or clean_name,
            entity_type=ent_type,
            aliases=[clean_canonical] if clean_canonical else [clean_name],
            positive_context=pos_context,
            negative_entities=[],
            negative_context=[]
        )

    @classmethod
    def evaluate_entity_match(
        cls,
        text: str,
        target: TargetEntity
    ) -> Tuple[float, List[str], Optional[str]]:
        """
        Deterministically evaluates candidate text against TargetEntity.
        
        Returns:
            (entity_score: float 0.0-1.0, matched_signals: List[str], rejection_reason: Optional[str])
            
        Enforces:
        - Multi-word entity rule: single token match is INSUFFICIENT for multi-token entities.
        - Negative disambiguation: presence of negative entity/context signals severely penalizes or rejects.
        - Contextual co-occurrence requirement for ambiguous/partial mentions.
        """
        if not text or not target.canonical_name:
            return 0.0, [], "Empty text or target"

        t_lower = text.lower()
        matched_signals: List[str] = []

        # ── Step 1: Explicit Negative Disambiguation ──
        for neg in target.negative_entities:
            if neg.lower() in t_lower:
                return 0.05, [], f"Matches known negative entity: '{neg}'"

        neg_context_hits = [nc for nc in target.negative_context if nc.lower() in t_lower]
        if len(neg_context_hits) >= 2:
            return 0.08, [], f"Multiple negative context indicators present: {neg_context_hits[:3]}"

        canonical_lower = target.canonical_name.lower()
        canonical_tokens = [t.lower() for t in re.split(r'[^a-zA-Z0-9]', target.canonical_name) if len(t) >= 2]

        score = 0.0

        # ── Step 2: Handle Exact Matching ──
        for handle_list in target.handles.values():
            for h in handle_list:
                h_clean = h.lower().lstrip("@")
                if f"@{h_clean}" in t_lower or f"/{h_clean}" in t_lower or f"x.com/{h_clean}" in t_lower:
                    matched_signals.append(f"handle:@{h_clean}")
                    score = max(score, 0.95)

        # ── Step 3: Exact Canonical Phrase Match ──
        # Check whole word boundary for canonical phrase
        can_pattern = r'\b' + re.escape(canonical_lower) + r'\b'
        if re.search(can_pattern, t_lower):
            matched_signals.append(f"canonical_phrase:{canonical_lower}")
            score = max(score, 0.90)

        # ── Step 4: Exact Alias Matches ──
        for alias in target.aliases:
            a_lower = alias.lower()
            if len(a_lower) >= 3 and re.search(r'\b' + re.escape(a_lower) + r'\b', t_lower):
                # If alias is single word of a multi-word entity (e.g. "Nadella"), reward only if context aligns
                if target.is_multi_word and len(a_lower.split()) == 1:
                    matched_signals.append(f"alias_surname:{a_lower}")
                    score = max(score, 0.75)
                else:
                    matched_signals.append(f"alias:{a_lower}")
                    score = max(score, 0.85)

        # ── Step 5: Ticker Match (for companies) ──
        if target.ticker:
            tick_lower = target.ticker.lower()
            if (f"${tick_lower}" in t_lower or 
                f"({tick_lower.upper()})" in text or 
                f"nasdaq:{tick_lower}" in t_lower or 
                f"nyse:{tick_lower}" in t_lower or
                re.search(r'\b' + re.escape(tick_lower) + r'\b', t_lower)):
                matched_signals.append(f"ticker:${target.ticker}")
                score = max(score, 0.88)

        # ── Step 6: Multi-Word Entity Rules ──
        if target.is_multi_word:
            first_name = canonical_tokens[0] if canonical_tokens else ""
            surname = canonical_tokens[-1] if len(canonical_tokens) >= 2 else ""

            first_in_text = bool(re.search(r'\b' + re.escape(first_name) + r'\b', t_lower)) if first_name else False
            surname_in_text = bool(re.search(r'\b' + re.escape(surname) + r'\b', t_lower)) if surname else False

            # If ONLY first name matched (e.g. "Satya" without "Nadella")
            if first_in_text and not surname_in_text and not any("canonical_phrase" in s for s in matched_signals):
                # Check for strong positive co-occurrence (e.g. organization or role)
                org_match = [org for org in target.organizations if re.search(r'\b' + re.escape(org.lower()) + r'\b', t_lower)]
                role_match = [r for r in target.roles if re.search(r'\b' + re.escape(r.lower()) + r'\b', t_lower)]
                pos_hits = [p for p in target.positive_context if re.search(r'\b' + re.escape(p) + r'\b', t_lower)]

                if org_match or role_match or len(pos_hits) >= 2:
                    matched_signals.append(f"first_name_with_context:{first_name}")
                    score = max(score, 0.65)
                else:
                    # Standalone first name without context: STRICTLY UNRESOLVED / REJECTED
                    return 0.15, [f"first_name_only:{first_name}"], f"Ambiguous single-token match on '{first_name}' without surname ('{surname}') or organizational co-occurrence"

            # If BOTH first name and surname are in text (even if separated)
            elif first_in_text and surname_in_text:
                matched_signals.append("token_cooccurrence:full_name")
                score = max(score, 0.85)

        else:
            # Single-word entity (e.g. "Microsoft")
            if re.search(can_pattern, t_lower):
                score = max(score, 0.85)

        # ── Step 7: Apply Positive Context Bonus & Negative Context Penalties ──
        pos_hits = [p for p in target.positive_context if re.search(r'\b' + re.escape(p) + r'\b', t_lower)]
        if pos_hits and score > 0.30:
            score = min(1.0, score + min(0.15, len(pos_hits) * 0.05))

        if neg_context_hits:
            score = max(0.05, score - 0.45)
            return score, matched_signals, f"Doubtful context: matched negative domain terms {neg_context_hits}"

        final_score = round(min(1.0, max(0.0, score)), 3)
        rejection_reason = None
        if final_score < 0.35:
            rejection_reason = f"Insufficient entity match confidence ({final_score} < 0.35)"

        return final_score, matched_signals, rejection_reason


# Singleton instance
entity_resolver = EntityResolver()
