"""
priority_engine.py (Owner: Member C)
=====================================
Simple Additive Weighting (SAW) Priority Ranking Engine for Relief Camps.

This is a PURE FUNCTION module with no direct database calls.
It takes raw camp data and weights, normalizes the 6 criteria into [0, 1] scales,
computes weighted composite scores [0, 100], and produces an ordered priority ranking.

Reference: DisasterReliefMVP Team Guide - Section 8
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

# Default placeholder weights and time cap (from Guide Section 8.2)
# Official weights will be confirmed by DDMA.
DEFAULT_SAW_WEIGHTS = {
    "people": 0.20,
    "vulnerable": 0.25,
    "damage": 0.20,
    "access": 0.15,
    "time": 0.10,
    "escalation": 0.10,
}
DEFAULT_TIME_CAP_HOURS = 72.0


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
        - occupancy (int)
        - children_count (int)
        - elderly_count (int)
        - pregnant_count (int)
        - disabled_count (int)
        - damage_level (int: 1 to 5)
        - access_difficulty (int: 1 to 5)
        - last_supply_at (datetime or None)
        - created_at (datetime)
        - has_escalation (bool)
        - oldest_open_request_at (datetime or None)
    weights: Dict of 6 criteria weights summing to 1.00.
             If None, DEFAULT_SAW_WEIGHTS is used.
    now: Current reference datetime. If None, datetime.now() is used.
    time_cap_hours: Maximum hours cap for the time criterion (default 72).

    Returns:
    --------
    List of dicts sorted from highest priority (Rank 1) to lowest, each with:
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
        weights = DEFAULT_SAW_WEIGHTS
    validate_weights(weights)

    if now is None:
        now = datetime.now()

    if not camps:
        return []

    # 1. Determine highest occupancy across active camps for normalization
    max_occupancy = max(c.get("occupancy", 0) for c in camps)

    scored_camps = []

    for camp in camps:
        camp_id = camp.get("camp_id")
        occupancy = max(0, int(camp.get("occupancy", 0)))

        # --- Criterion 1: People ---
        # occupancy / highest occupancy among active camps
        # Special edge case: If only 1 camp exists, people = 1.0 if occupancy > 0 (Section 8.5)
        if len(camps) == 1:
            people_norm = 1.0 if occupancy > 0 else 0.0
        elif max_occupancy > 0:
            people_norm = min(1.0, occupancy / max_occupancy)
        else:
            people_norm = 0.0

        # --- Criterion 2: Vulnerable share ---
        # (children + elderly + pregnant + disabled) / occupancy, capped at 1.0
        # If occupancy is 0, vulnerable share is 0.0
        vuln_sum = (
            max(0, int(camp.get("children_count", 0)))
            + max(0, int(camp.get("elderly_count", 0)))
            + max(0, int(camp.get("pregnant_count", 0)))
            + max(0, int(camp.get("disabled_count", 0)))
        )
        if occupancy > 0:
            vuln_norm = min(1.0, vuln_sum / occupancy)
        else:
            vuln_norm = 0.0

        # --- Criterion 3: Damage ---
        # damage_level between 1 and 5 -> (damage_level - 1) / 4.0
        damage_level = max(1, min(5, int(camp.get("damage_level", 1))))
        damage_norm = (damage_level - 1.0) / 4.0

        # --- Criterion 4: Access difficulty ---
        # access_difficulty between 1 and 5 -> (access_difficulty - 1) / 4.0
        access_difficulty = max(1, min(5, int(camp.get("access_difficulty", 1))))
        access_norm = (access_difficulty - 1.0) / 4.0

        # --- Criterion 5: Time since last supply ---
        # now - last_supply_at (if empty, use created_at)
        ref_time = camp.get("last_supply_at")
        if ref_time is None:
            ref_time = camp.get("created_at")

        if ref_time is not None:
            # Handle possible timezone differences cleanly
            delta = now - ref_time
            elapsed_hours = max(0.0, delta.total_seconds() / 3600.0)
            time_norm = min(elapsed_hours, time_cap_hours) / time_cap_hours
        else:
            time_norm = 0.0

        # --- Criterion 6: Escalation ---
        # 1.0 if camp has at least one open request with escalated = True, else 0.0
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

        # Record for tie-breaking:
        # Older oldest_open_request_at ranks higher (smaller datetime),
        # if None, put it after camps with open requests
        oldest_req = camp.get("oldest_open_request_at")

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
    # 1. Higher score first (-score)
    # 2. Older oldest_open_request_at first (smaller datetime; None treated as far future datetime.max)
    # 3. Lower camp_id (+camp_id)
    def sort_key(item):
        req_time = item["oldest_req"]
        req_timestamp = req_time.timestamp() if req_time is not None else float("inf")
        # Ensure camp_id is an integer for sorting
        cid = item["camp_id"] if item["camp_id"] is not None else 0
        return (-item["score"], req_timestamp, cid)

    scored_camps.sort(key=sort_key)

    # Assign 1-indexed ranks and construct final output
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


if __name__ == "__main__":
    # Interactive CLI demonstration and visual ranking breakdown
    from datetime import timedelta

    current_time = datetime.now()
    demo_camps = [
        {
            "camp_id": 1,
            "name": "Chengannur Relief Camp (Govt HS)",
            "occupancy": 400,
            "children_count": 90,
            "elderly_count": 60,
            "pregnant_count": 10,
            "disabled_count": 5,
            "damage_level": 4,
            "access_difficulty": 5,
            "last_supply_at": current_time - timedelta(hours=48),
            "created_at": current_time - timedelta(hours=72),
            "has_escalation": True,
            "oldest_open_request_at": current_time - timedelta(hours=8),
        },
        {
            "camp_id": 2,
            "name": "Kuttanad Relief Camp (Kainakary Church)",
            "occupancy": 500,
            "children_count": 120,
            "elderly_count": 80,
            "pregnant_count": 15,
            "disabled_count": 10,
            "damage_level": 5,
            "access_difficulty": 5,
            "last_supply_at": current_time - timedelta(hours=60),
            "created_at": current_time - timedelta(hours=96),
            "has_escalation": True,
            "oldest_open_request_at": current_time - timedelta(hours=14),
        },
        {
            "camp_id": 3,
            "name": "Thiruvalla Camp (MGM HSS)",
            "occupancy": 150,
            "children_count": 30,
            "elderly_count": 20,
            "pregnant_count": 2,
            "disabled_count": 1,
            "damage_level": 2,
            "access_difficulty": 2,
            "last_supply_at": current_time - timedelta(hours=12),
            "created_at": current_time - timedelta(hours=36),
            "has_escalation": False,
            "oldest_open_request_at": current_time - timedelta(hours=4),
        },
        {
            "camp_id": 4,
            "name": "Pathanamthitta Camp (Catholicate College)",
            "occupancy": 220,
            "children_count": 50,
            "elderly_count": 40,
            "pregnant_count": 5,
            "disabled_count": 3,
            "damage_level": 3,
            "access_difficulty": 3,
            "last_supply_at": current_time - timedelta(hours=24),
            "created_at": current_time - timedelta(hours=48),
            "has_escalation": False,
            "oldest_open_request_at": current_time - timedelta(hours=6),
        },
        {
            "camp_id": 5,
            "name": "Alappuzha Camp (SDV College)",
            "occupancy": 300,
            "children_count": 70,
            "elderly_count": 45,
            "pregnant_count": 8,
            "disabled_count": 4,
            "damage_level": 3,
            "access_difficulty": 4,
            "last_supply_at": current_time - timedelta(hours=36),
            "created_at": current_time - timedelta(hours=60),
            "has_escalation": True,
            "oldest_open_request_at": current_time - timedelta(hours=10),
        },
        {
            "camp_id": 6,
            "name": "Changanassery Camp (SB College)",
            "occupancy": 80,
            "children_count": 15,
            "elderly_count": 12,
            "pregnant_count": 1,
            "disabled_count": 0,
            "damage_level": 1,
            "access_difficulty": 1,
            "last_supply_at": current_time - timedelta(hours=4),
            "created_at": current_time - timedelta(hours=24),
            "has_escalation": False,
            "oldest_open_request_at": None,
        },
    ]

    camp_names = {c["camp_id"]: c["name"] for c in demo_camps}
    ranked = compute_priority(demo_camps, DEFAULT_SAW_WEIGHTS, now=current_time)

    print("\n" + "=" * 90)
    print("      DISASTER RELIEF MVP - CAMP PRIORITY RANKING (SAW ENGINE DEMO)")
    print("=" * 90)
    print(f"{'Rank':<5} {'Score':<8} {'Camp Name':<42} {'People':<7} {'Vuln':<7} {'Dmg':<6} {'Acc':<6} {'Time':<6} {'Esc'}")
    print("-" * 90)
    for r in ranked:
        cid = r["camp_id"]
        b = r["breakdown"]
        cname = camp_names.get(cid, f"Camp {cid}")
        esc_str = "YES" if b["escalation"] > 0 else "NO"
        print(f"#{r['rank']:<4} {r['score']:<8.2f} {cname:<42} {b['people']:<7.2f} {b['vulnerable']:<7.2f} {b['damage']:<6.2f} {b['access']:<6.2f} {b['time']:<6.2f} {esc_str}")
    print("-" * 90)
    print("Interpretation Guide:")
    print(" - Score: Priority score out of 100. Higher score = More urgent relief needed.")
    print(" - Weights used: People=20%, Vulnerable=25%, Damage=20%, Access=15%, Time=10%, Escalation=10%.")
    print(" - Notice Rank #1 (Kuttanad) has severe flood damage (1.00), severe access difficulty (1.00),")
    print("   high vulnerability (0.45), long waiting time (0.83), and an urgent escalation flag.")
    print(" - Rank #6 (Changanassery) has low damage (0.00), easy access (0.00), and recent supply (0.06).")
    print("=" * 90 + "\n")

