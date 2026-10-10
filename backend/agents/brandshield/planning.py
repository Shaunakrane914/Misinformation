"""
Aegis Protocol — BrandShield Entity Resolution & Planning
=========================================================
Resolves brand and product entities and plans domain query strategies.
"""

from typing import Any, Dict, List
from backend.agents.brandshield.models import KNOWN_BRAND_CATALOG


def resolve_brand_entity(raw_input: str) -> Dict[str, Any]:
    """
    Normalize and resolve brand vs product distinctions.
    E.g. 'Nike Air Max' -> brand: 'Nike', product: 'Air Max', type: 'product'.
    """
    from backend.services.research.entity_resolver import entity_resolver
    parsed_req = entity_resolver.parse_request(raw_input, domain="brand")
    canonical_target = parsed_req.target_entity.canonical_name

    clean_text = canonical_target if canonical_target != "Unknown" else raw_input.strip()
    upper_text = clean_text.upper()

    detected_brand = clean_text
    detected_product = None
    entity_type = "brand"
    aliases: List[str] = parsed_req.target_entity.aliases or []
    confidence = 0.85

    for key, info in KNOWN_BRAND_CATALOG.items():
        if key in upper_text or upper_text.startswith(key):
            detected_brand = info["brand"]
            confidence = 0.95
            for prod in info["products"]:
                if prod in upper_text:
                    detected_product = prod.title()
                    entity_type = "product"
                    break
            break

    # Fallback heuristic: check if input has 2+ words (likely brand + product)
    if entity_type == "brand" and len(clean_text.split()) >= 2 and detected_brand not in [b["brand"] for b in KNOWN_BRAND_CATALOG.values()]:
        parts = clean_text.split()
        detected_brand = parts[0]
        detected_product = " ".join(parts[1:])
        entity_type = "product"
        confidence = 0.80

    resolved_entity = f"{detected_brand} {detected_product}".strip() if detected_product else detected_brand

    return {
        "input": raw_input,
        "resolved_entity": resolved_entity,
        "brand": detected_brand,
        "product": detected_product,
        "entity_type": entity_type,
        "aliases": aliases,
        "confidence": confidence,
    }
