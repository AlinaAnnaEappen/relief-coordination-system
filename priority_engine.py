"""
priority_engine.py (Owner: Member C)
=====================================
Simple Additive Weighting (SAW) Priority Ranking Engine for Relief Camps.

This is a PURE FUNCTION module with no direct database calls.
It takes raw camp data and weights, normalizes the 6 criteria into [0, 1] scales,
computes weighted composite scores [0, 100], and produces an ordered priority ranking.

Reference: DisasterRelief Team Guide - Section 8
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Default placeholder weights and time cap (Guide Section 8.2)
DEFAULT_SAW_WEIGHTS = {
    "people": 0.20,
    "vulnerable": 0.25,
    "damage": 0.20,
    "access": 0.15,
    "time": 0.10,
    "escalation": 0.10,
}
DEFAULT_TIME_CAP_HOURS = 72.0

try:
    from config import SAW_WEIGHTS, TIME_CAP_HOURS
except ImportError:
    SAW_WEIGHTS = DEFAULT_SAW_WEIGHTS
    TIME_CAP_HOURS = DEFAULT_TIME_CAP_HOURS


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Converts a datetime to UTC-aware.
    If naive, attaches timezone.utc. If aware, converts to UTC.
    If None, returns None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_weights(weights: Dict[str, float]) -> None:
    """
    Validates that all 6 required criteria exist and weights sum to 1.0.
    Raises ValueError with a clear explanation if invalid.
    """
    required_keys = {"people", "vulnerable", "damage", "access", "time", "escalation"}
    missing = required_keys - set(weights.keys())
    if missing:
        raise ValueError(f"Missing required weight keys: {sorted(list(missing))}")

    total = sum(weights[k] for k in required_keys)
    if abs(total - 1.0) > 1e-5:
        raise ValueError(
            f"SAW weights must sum to 1.00 (got {total:.4f}). "
            f"Please adjust weights in config."
        )


def compute_priority(
    camps: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    now: Optional[datetime] = None,
    time_cap_hours: float = DEFAULT_TIME_CAP_HOURS,
) -> List[Dict[str, Any]]:
    """
    Calculates SAW priority scores and ranking for a list of active camps.

    Parameters:
    -----------
    camps: List of dicts, each containing:
        - camp_id (int)
        - occupancy (int or None)
        - children_count (int or None)
        - elderly_count (int or None)
        - pregnant_count (int or None)
        - disabled_count (int or None)
        - damage_level (int: 1 to 5, or None)
        - access_difficulty (int: 1 to 5, or None)
        - last_supply_at (datetime or None)
        - created_at (datetime or None)
        - has_escalation (bool)
        - oldest_open_request_at (datetime or None)
    weights: Dict of 6 criteria weights summing to 1.00.
             If None, SAW_WEIGHTS is used.
    now: Current reference datetime. If None, datetime.now(timezone.utc) is used.
    time_cap_hours: Maximum hours cap for the time criterion (default 72).

    Returns:
    --------
    List of dicts sorted from highest priority (Rank 1) to lowest:
        {
            "camp_id": int,
            "score": float,       # 0.00 to 100.00
            "rank": int,          # 1-indexed
            "breakdown": {
                "people": float,      # [0, 1]
                "vulnerable": float,  # [0, 1]
                "damage": float,      # [0, 1]
                "access": float,      # [0, 1]
                "time": float,        # [0, 1]
                "escalation": float   # 0 or 1
            }
        }
    """
    if weights is None:
        weights = SAW_WEIGHTS
    validate_weights(weights)

    if now is None:
        now = datetime.now(timezone.utc)
    else:
        now = to_utc(now)

    if not camps:
        return []

    # 1. Determine highest occupancy across active camps for normalization
    max_occ = 0
    for c in camps:
        raw_o = c.get("occupancy")
        if raw_o is not None:
            try:
                val = int(raw_o)
                if val > max_occ:
                    max_occ = val
            except (ValueError, TypeError):
                pass
    max_occupancy = max_occ

    scored_camps = []

    for camp in camps:
        camp_id = camp.get("camp_id")

        # Safe int conversion for occupancy
        raw_occ = camp.get("occupancy")
        occupancy = 0
        if raw_occ is not None:
            try:
                occupancy = max(0, int(raw_occ))
            except (ValueError, TypeError):
                occupancy = 0

        # --- Criterion 1: People ---
        if len(camps) == 1:
            people_norm = 1.0 if occupancy > 0 else 0.0
        elif max_occupancy > 0:
            people_norm = min(1.0, occupancy / max_occupancy)
        else:
            people_norm = 0.0

        # --- Criterion 2: Vulnerable share ---
        def safe_count(key):
            v = camp.get(key)
            if v is not None:
                try:
                    return max(0, int(v))
                except (ValueError, TypeError):
                    return 0
            return 0

        vuln_sum = (
            safe_count("children_count")
            + safe_count("elderly_count")
            + safe_count("pregnant_count")
            + safe_count("disabled_count")
        )
        if occupancy > 0:
            vuln_norm = min(1.0, vuln_sum / occupancy)
        else:
            vuln_norm = 0.0

        # --- Criterion 3: Damage ---
        raw_dmg = camp.get("damage_level")
        damage_level = 1
        if raw_dmg is not None:
            try:
                damage_level = max(1, min(5, int(raw_dmg)))
            except (ValueError, TypeError):
                damage_level = 1
        damage_norm = (damage_level - 1.0) / 4.0

        # --- Criterion 4: Access difficulty ---
        raw_acc = camp.get("access_difficulty")
        access_difficulty = 1
        if raw_acc is not None:
            try:
                access_difficulty = max(1, min(5, int(raw_acc)))
            except (ValueError, TypeError):
                access_difficulty = 1
        access_norm = (access_difficulty - 1.0) / 4.0

        # --- Criterion 5: Time since last supply ---
        ref_time = camp.get("last_supply_at")
        if ref_time is None:
            ref_time = camp.get("created_at")
        ref_time = to_utc(ref_time)

        if ref_time is not None:
            delta = now - ref_time
            elapsed_hours = max(0.0, delta.total_seconds() / 3600.0)
            time_norm = min(elapsed_hours, time_cap_hours) / time_cap_hours
        else:
            time_norm = 0.0

        # --- Criterion 6: Escalation ---
        has_escalation = bool(camp.get("has_escalation", False))
        escalation_norm = 1.0 if has_escalation else 0.0

        # --- Composite SAW Score [0 to 100] ---
        raw_score = 100.0 * (
            weights["people"] * people_norm
            + weights["vulnerable"] * vuln_norm
            + weights["damage"] * damage_norm
            + weights["access"] * access_norm
            + weights["time"] * time_norm
            + weights["escalation"] * escalation_norm
        )
        final_score = round(raw_score, 2)

        oldest_req = to_utc(camp.get("oldest_open_request_at"))

        scored_camps.append(
            {
                "camp_id": camp_id,
                "score": final_score,
                "oldest_req": oldest_req,
                "breakdown": {
                    "people": round(people_norm, 4),
                    "vulnerable": round(vuln_norm, 4),
                    "damage": round(damage_norm, 4),
                    "access": round(access_norm, 4),
                    "time": round(time_norm, 4),
                    "escalation": round(escalation_norm, 4),
                },
            }
        )

    # --- Sorting and Tie-breaking (Guide Section 8.5) ---
    def sort_key(item):
        req_time = item["oldest_req"]
        req_timestamp = req_time.timestamp() if req_time is not None else float("inf")
        cid = item["camp_id"] if item["camp_id"] is not None else 0
        return (-item["score"], req_timestamp, cid)

    scored_camps.sort(key=sort_key)

    results = []
    for rank, item in enumerate(scored_camps, start=1):
        results.append(
            {
                "camp_id": item["camp_id"],
                "score": item["score"],
                "rank": rank,
                "breakdown": item["breakdown"],
            }
        )

    return results
