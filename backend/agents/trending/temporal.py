"""
Aegis Protocol — Trending Temporal Analytics & Velocity
=======================================================
Robust timestamp parsing and real historical velocity tracking.
Strictly adheres to observation-backed calculations with zero Math.random().
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_timestamp_epoch(ts: Any) -> float:
    """Robustly parse ISO, RFC-2822, or date strings to UTC epoch for monotonic comparisons."""
    if not ts:
        return 0.0
    ts_str = str(ts).strip()
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        pass
    try:
        import email.utils
        dt = email.utils.parsedate_to_datetime(ts_str)
        if dt:
            return dt.timestamp()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            pass
    rel_match = re.search(r'(\d+)\s*(hour|hr|minute|min|day|sec)', ts_str.lower())
    if rel_match:
        val = int(rel_match.group(1))
        unit = rel_match.group(2)
        sec = val * 3600 if "h" in unit else (val * 60 if "m" in unit else (val * 86400 if "d" in unit else val))
        return time.time() - sec
    return 0.0


def calculate_velocity(
    topic: str,
    signal_count: int,
    source_count: int,
    platform_count: int,
    entity_key: Optional[str] = None,
    history_store: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Compute real trend velocity and momentum from actual historical snapshots.
    Never generates fake numbers or Math.random().
    """
    now_ts = datetime.now(timezone.utc).isoformat()
    if entity_key:
        clean_key = re.sub(r'[^a-zA-Z0-9]', '_', entity_key.lower())
    else:
        clean_key = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower()[:30])

    if history_store is None:
        history_store = {}

    history = history_store.get(clean_key, [])

    # Record current snapshot
    current_snap = {
        "timestamp": now_ts,
        "signal_count": signal_count,
        "source_count": source_count,
        "platform_count": platform_count
    }

    if not history:
        # First observation: insufficient history to compute rate of change
        history_store[clean_key] = [current_snap]
        return {
            "signals_per_hour": 0.0,
            "growth_rate_pct": 0.0,
            "status": "INSUFFICIENT_HISTORY",
            "velocity_status": "INSUFFICIENT_HISTORY",
            "message": "First observation recorded. Minimum 2 scans required for velocity tracking; rate of change cannot be measured from a single scan.",
            "history": [current_snap]
        }

    # Compare with previous snapshot
    prev_snap = history[-1]
    try:
        prev_time = datetime.fromisoformat(prev_snap["timestamp"])
        curr_time = datetime.fromisoformat(now_ts)
        delta_hours = max((curr_time - prev_time).total_seconds() / 3600.0, 0.01)
    except Exception:
        delta_hours = 1.0

    signal_delta = signal_count - prev_snap.get("signal_count", 0)
    signals_per_hour = round(max(0.0, signal_delta / delta_hours), 2)
    prev_count = max(1, prev_snap.get("signal_count", 1))
    growth_pct = round((signal_delta / prev_count) * 100.0, 1)

    if growth_pct >= 25.0:
        status = "ACCELERATING"
    elif growth_pct > 0.0:
        status = "ACTIVE"
    elif growth_pct == 0.0:
        status = "STABLE"
    else:
        status = "DECLINING"

    # Update history up to 10 snapshots
    history.append(current_snap)
    if len(history) > 10:
        history = history[-10:]
    history_store[clean_key] = history

    return {
        "signals_per_hour": signals_per_hour,
        "growth_rate_pct": growth_pct,
        "status": status,
        "velocity_status": status,
        "message": f"Momentum measured across {len(history)} verified scan intervals.",
        "history": history
    }
