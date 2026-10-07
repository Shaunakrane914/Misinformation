"""
Aegis Protocol — Scout Temporal Disambiguation Extractor
=========================================================
Strictly distinguishes between publication time (when article was published)
and event time (when the corporate action took place).
"""

import re
from datetime import datetime, timezone
from typing import Optional, Tuple


class TemporalExtractor:
    """
    Parses and disambiguates timestamps:
    - published_at: web publication timestamp
    - event_at: real-world corporate action timestamp
    """

    def disambiguate(
        self,
        raw_published: str,
        text: str
    ) -> Tuple[str, Optional[str]]:
        """
        Returns:
            (published_at_iso, event_at_iso_or_None)
        """
        pub_iso = self._normalize_timestamp(raw_published) or datetime.now(timezone.utc).isoformat()
        event_iso = None

        if text:
            # Look for explicit event datelines (e.g. "On Tuesday, Feb 18", "effective March 1")
            dateline_match = re.search(
                r"\b(?:effective|announced on|occurred on|dated)\s+([A-Za-z]+ \d{1,2},? \d{4})",
                text,
                re.IGNORECASE
            )
            if dateline_match:
                event_iso = self._normalize_timestamp(dateline_match.group(1))

        return pub_iso, event_iso

    def _normalize_timestamp(self, ts_str: Optional[str]) -> Optional[str]:
        if not ts_str:
            return None
        clean = ts_str.strip()
        # ISO format already
        if re.match(r"^\d{4}-\d{2}-\d{2}T", clean):
            return clean

        # Standard formats
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
            "%a, %d %b %Y %H:%M:%S %Z",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                continue

        return clean


temporal_extractor = TemporalExtractor()
