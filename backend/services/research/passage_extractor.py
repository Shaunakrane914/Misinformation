"""
Aegis Protocol — Relevant Passage & Entity Extraction Engine
============================================================
Extracts high-signal, relevant passages, factual claims, and named entities
from full-text articles rather than dumping raw markdown to reasoning models.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import EvidenceItem

# High-signal action verbs and investigative indicators
SIGNAL_MARKERS: Set[str] = {
    "announced", "reported", "disclosed", "filed", "confirmed", "denied",
    "investigating", "lawsuit", "alleged", "probe", "regulatory", "earnings",
    "revenue", "profit", "loss", "plunged", "surged", "counterfeit", "scam",
    "warning", "advisory", "recalled", "halted", "resigned", "settlement"
}

DISCLOSURE_CONTEXT = ("forward-looking statements", "certain statements in this press release",
                      "safe harbor statement")

# This is an explicitly heuristic passage-quality filter, not entailment or
# calibrated confidence. Preserve rejected text in the corpus for inspection.
NAVIGATION_MARKERS = ("toggle navigation", "switch to dark", "switch to light", "shop all",
                      "privacy policy", "contact us", "men women", "add to cart", "browse select")


def has_usable_passage(item) -> bool:
    from backend.schemas.evidence_inspection import METADATA_DEPTHS
    value = item.get if isinstance(item, dict) else lambda key, default=None: getattr(item, key, default)
    depth = str(value("content_depth", "UNKNOWN") or "UNKNOWN").upper()
    if depth in METADATA_DEPTHS | {"SEARCH_SNIPPET", "SEARCH_INDEX_DISCOVERY", "SYNDICATED_SUMMARY"}:
        return False
    if value("extraction_status") in {"EMPTY", "NO_RELEVANT_PASSAGE", "METADATA_ONLY"}:
        return False
    text = value("relevant_excerpt") or value("content") or value("snippet") or ""
    lower = text.lower()
    return (len(text.strip()) >= 40
            and sum(marker in lower for marker in NAVIGATION_MARKERS) < 2
            and bool(re.search(r"\b(?:is|are|was|were|has|have|allows|contains|includes|limits|rated)\b", lower)
                     or any(re.search(r"\b" + marker + r"\b", lower) for marker in SIGNAL_MARKERS)))


class PassageExtractor:
    """Extracts target-relevant passages and key factual claims from source text."""

    def __init__(self):
        pass

    def extract_passages(
        self,
        items: List[EvidenceItem],
        target_name: str,
        intent: str = ""
    ) -> List[EvidenceItem]:
        """
        Processes each evidence item, finding the most relevant excerpt and entities.
        """
        clean_target = re.sub(r"\([^)]*\)", "", target_name or "").lower().strip()
        target_tokens = set(re.findall(r"[a-z0-9]{3,}", clean_target)) - {"inc", "ltd", "limited", "corp", "corporation", "company"}
        intent_tokens = set(w for w in (intent or "").lower().split() if len(w) >= 4)
        from backend.services.research.entity_resolver import entity_resolver
        profile = entity_resolver.parse_request(target_name).target_entity
        topic_aliases = profile.aliases if profile.entity_type == "topic" else []

        for item in items:
            from backend.schemas.evidence_inspection import METADATA_DEPTHS
            if item.content_depth in METADATA_DEPTHS | {"SEARCH_SNIPPET", "SEARCH_INDEX_DISCOVERY", "SYNDICATED_SUMMARY"}:
                item.relevant_excerpt = ""
                item.extraction_status = "METADATA_ONLY"
                continue
            raw_text = item.content or item.snippet
            if not raw_text:
                item.relevant_excerpt = item.title
                item.extraction_status = "EMPTY"
                continue

            # Split into paragraphs or sentences
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n|(?<=[.?!])\s+(?=[A-Z])', raw_text) if len(p.strip()) >= 40]
            if not paragraphs:
                paragraphs = [p.strip() for p in re.split(r'(?<=[.?!])\s+', raw_text) if len(p.strip()) > 60]

            if not paragraphs:
                item.relevant_excerpt = raw_text[:350]
                item.extraction_status = "FALLBACK"
                continue

            # Score each paragraph
            best_p = paragraphs[0]
            best_score = -1.0
            best_idx = 0

            for idx, p in enumerate(paragraphs):
                if not has_usable_passage({"content": p, "content_depth": item.content_depth}):
                    continue
                p_lower = p.lower()
                present = target_tokens & set(re.findall(r"[a-z0-9]{3,}", p_lower))
                topic_match = any(re.search(r"\b" + re.escape(alias.casefold()) + r"\b", p_lower) for alias in topic_aliases)
                if target_tokens and len(present) < min(2, len(target_tokens)) and clean_target not in p_lower and not topic_match:
                    continue
                score = 0.0

                # Target presence
                if topic_match or (clean_target and clean_target in p_lower):
                    score += 3.0
                elif any(t in p_lower for t in target_tokens):
                    score += 1.5

                # Intent presence
                if any(it in p_lower for it in intent_tokens):
                    score += 1.0

                # Action markers
                matched_signals = sum(1 for m in SIGNAL_MARKERS if m in p_lower)
                score += min(2.0, 0.5 * matched_signals)

                # Numbers / currency / statistics presence
                if re.search(r'[\$₹€£]|\b\d+(\.\d+)?%|\b\d{4}\b|\bcrore\b|\bbillion\b|\bmillion\b', p_lower):
                    score += 1.0

                # Quotes presence
                if '"' in p or '“' in p or "'" in p:
                    score += 0.5

                # Keyword-dense legal disclosures must not crowd out the
                # substantive announcement. Keep them in captured source text;
                # this is selection priority, never prose deletion or truth.
                if any(marker in p_lower for marker in DISCLOSURE_CONTEXT):
                    score -= 3.0

                if score > best_score:
                    best_score = score
                    best_p = p
                    best_idx = idx

            if best_score < 1.5:
                item.relevant_excerpt = ""
                item.extraction_status = "NO_RELEVANT_PASSAGE"
                continue

            # Clean and truncate best excerpt
            # Preserve exact offsets and qualifications. A short display
            # preview must not silently delete a later negation/date. The full
            # captured source remains available even if this bounded window ends.
            clean_excerpt = best_p[:2000]
            if len(best_p) > 2000:
                item.metadata["excerpt_truncated"] = True

            item.relevant_excerpt = clean_excerpt
            item.excerpt_start = raw_text.find(best_p)
            item.excerpt_end = item.excerpt_start + len(clean_excerpt)
            item.extraction_status = "SUCCESS"

            # Extract named entities & factual numbers
            entities = set()
            # Find capitalized entity sequences
            cap_entities = re.findall(r'\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*\b', clean_excerpt)
            for ce in cap_entities:
                if len(ce) > 3 and ce.lower() not in clean_target and ce not in ("The", "This", "That", "According", "However"):
                    entities.add(ce)
            item.entities = list(entities)[:5]

            # Extract numerical figures as topics
            facts = re.findall(r'[\$₹€£]\s*[\d\.,]+(?:\s*(?:billion|million|crore|lakh))?|\b\d+(?:\.\d+)?%', clean_excerpt, flags=re.IGNORECASE)
            item.topics = list(set(facts))[:4]

        return items


passage_extractor = PassageExtractor()
