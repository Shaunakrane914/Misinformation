"""
Aegis Protocol — Personal Watch Identity Resolution
===================================================
Normalizes subject profile and resolves public entities against verified catalog.
Enforces strict privacy boundaries: NEVER harvests or infers private PII.
"""

from typing import Any, Dict

from backend.agents.personal_watch.models import KNOWN_PUBLIC_PROFILES


def resolve_personal_entity(profile_or_name: Any) -> Dict[str, Any]:
    """
    Resolve subject identity from raw name or structured profile.
    Does NOT harvest or infer private PII (addresses, phone numbers, family).
    Only resolves public aliases, handles, and public organizational affiliations.
    """
    if isinstance(profile_or_name, str):
        profile = {"name": profile_or_name.strip()}
    elif isinstance(profile_or_name, dict):
        profile = dict(profile_or_name)
    else:
        profile = {"name": str(profile_or_name)}

    raw_name = profile.get("name", "").strip()
    upper_name = raw_name.upper()

    resolved = {
        "name": raw_name,
        "canonical_name": raw_name,
        "aliases": profile.get("aliases", []),
        "official_handles": profile.get("official_handles", {}),
        "official_domains": profile.get("official_domains", []),
        "affiliations": profile.get("affiliations", []),
        "category": profile.get("category", "public_figure"),
        "monitoring_terms": profile.get("monitoring_terms", []),
        "alert_preferences": profile.get("alert_preferences", {"level": "HIGH_ONLY"}),
        "confidence": 0.70,
        "resolution_notes": "User-configured subject profile"
    }

    # Check known public figures catalog
    for key, info in KNOWN_PUBLIC_PROFILES.items():
        if upper_name == key or upper_name in [a.upper() for a in info.get("aliases", [])]:
            resolved["canonical_name"] = info["canonical_name"]
            existing_aliases = set(resolved["aliases"])
            for a in info.get("aliases", []):
                if a.lower() != resolved["canonical_name"].lower():
                    existing_aliases.add(a)
            resolved["aliases"] = list(existing_aliases)

            merged_handles = dict(info.get("handles", {}))
            merged_handles.update(resolved["official_handles"])
            resolved["official_handles"] = merged_handles

            merged_domains = set(info.get("domains", []))
            merged_domains.update(resolved["official_domains"])
            resolved["official_domains"] = list(merged_domains)

            resolved["affiliations"] = list(set(info.get("affiliations", []) + resolved["affiliations"]))
            resolved["category"] = info.get("category", resolved["category"])
            resolved["confidence"] = 0.95
            resolved["resolution_notes"] = f"Resolved via verified public figure catalog: {info['canonical_name']}"
            break

    return resolved
