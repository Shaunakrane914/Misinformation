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
        clean_target = (target_name or "").lower().strip()
        target_tokens = set(w for w in clean_target.split() if len(w) >= 3)
        intent_tokens = set(w for w in (intent or "").lower().split() if len(w) >= 4)

        for item in items:
            raw_text = item.content or item.snippet
            if not raw_text:
                item.relevant_excerpt = item.title
                item.extraction_status = "EMPTY"
                continue

            # Split into paragraphs or sentences
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if len(p.strip()) > 60]
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
                p_lower = p.lower()
                score = 0.0

                # Target presence
                if clean_target and clean_target in p_lower:
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

                if score > best_score:
                    best_score = score
                    best_p = p
                    best_idx = idx

            # Clean and truncate best excerpt
            clean_excerpt = re.sub(r'\s+', ' ', best_p).strip()
            if len(clean_excerpt) > 450:
                clean_excerpt = clean_excerpt[:450] + "..."

            item.relevant_excerpt = clean_excerpt
            item.excerpt_start = raw_text.find(best_p) if best_p in raw_text else 0
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
