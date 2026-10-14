"""
allocation_engine.py (Owner: Member D)
=======================================
Resource Allocation Engine for DisasterReliefMVP.

Contract Reference: DisasterRelief Team Guide - Section 9 & Section 11 (Task D2, D4)
- Deterministic allocation from nearest available hub in strict priority order.
- ACID transaction guarantee: atomic stock deductions, stock movement ledger entries,
  request item allocations (oldest request first), and request status updates.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor


def calculate_haversine_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance in metres between two coordinate pairs
    using the Haversine formula (fallback when PostGIS is unavailable).
    """
    R = 6371000.0  # Earth's mean radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def plan_allocation(
    ranked_camp_ids: List[int],
    open_needs: Dict[int, Dict[int, int]],
    hub_stock: Dict[int, Dict[int, int]],
    distances: Dict[Tuple[int, int], float],
) -> List[Dict[str, int]]:
    """
    PURE function (no database), deterministic and easy to unit test.

    Parameters:
        ranked_camp_ids: [camp_id, ...] from highest priority (rank 1) to lowest
        open_needs:      {camp_id: {item_id: qty_needed}}
        hub_stock:       {hub_id: {item_id: qty_available}}
        distances:       {(camp_id, hub_id): metres}

    Returns:
        List of planned allocations:
        [{"camp_id": 1, "hub_id": 2, "item_id": 5, "qty": 60}, ...]

    Rules (Guide Section 9.1 - 9.4):
    1. Iterate camps strictly from highest priority (rank 1) downwards.
    2. For each needed item:
       - Find all hubs with available stock (> 0).
       - Sort candidate hubs by distance (ascending).
       - Tie-break equal distances by lowest hub_id.
       - Allocate min(still_needed, hub_stock).
       - Decrement hub stock and remaining camp need.
       - Stop when need is zero or all hubs exhausted.
    3. Caller dictionaries are never mutated.
    """
    # Create isolated copy of hub stock so caller dictionaries remain unchanged
    stock_avail: Dict[int, Dict[int, int]] = {}
    for hid, items in hub_stock.items():
        stock_avail[hid] = dict(items)

    allocations: List[Dict[str, int]] = []

    for camp_id in ranked_camp_ids:
        camp_needs = open_needs.get(camp_id, {})
        if not camp_needs:
            continue

        for item_id, requested_qty in camp_needs.items():
            if requested_qty <= 0:
                continue

            still_needed = requested_qty

            # Find candidate hubs that have stock for this item
            candidate_hubs = [
                hid for hid, items in stock_avail.items()
                if items.get(item_id, 0) > 0
            ]

            if not candidate_hubs:
                continue

            # Sort candidate hubs by distance (ascending), then by lowest hub_id
            def get_dist_key(hid: int) -> Tuple[float, int]:
                # Try (camp_id, hid), fallback to (hid, camp_id), else infinity
                d = distances.get((camp_id, hid))
                if d is None:
                    d = distances.get((hid, camp_id))
                if d is None:
                    d = float("inf")
                return (d, hid)

            candidate_hubs.sort(key=get_dist_key)

            for hid in candidate_hubs:
                available_here = stock_avail[hid].get(item_id, 0)
                if available_here <= 0:
                    continue

                take_qty = min(still_needed, available_here)
                if take_qty > 0:
                    allocations.append({
                        "camp_id": camp_id,
                        "hub_id": hid,
                        "item_id": item_id,
                        "qty": take_qty,
                    })
                    stock_avail[hid][item_id] -= take_qty
                    still_needed -= take_qty

                if still_needed <= 0:
                    break

    return allocations


def run_allocation(conn, priority_run_id: Optional[int] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Executes a complete allocation cycle against the database inside ONE transaction.

    Steps (Guide Section 9.2):
    1. Fetch latest priority ranking (or specified priority_run_id).
    2. Determine open needs per active camp from open requests (status in 'pending', 'partially_allocated').
    3. Load available stock for all active hubs.
    4. Compute distance matrix using PostGIS (with Haversine fallback).
    5. Call pure plan_allocation().
    6. In one atomic transaction:
       - Insert allocation_runs row.
       - Deduct stock and write stock_movements (reason 'allocation').
       - Allocate quantity across open requests, oldest request first.
       - Insert allocations rows (status 'planned').
       - Update request status ('fulfilled' or 'partially_allocated').
    7. Roll back on any error.

    Returns:
        Summary dict containing run_id, priority_run_id, allocations count, and items planned.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Step 1: Identify priority run
        if priority_run_id is None:
            cur.execute("SELECT run_id FROM priority_runs ORDER BY run_at DESC, run_id DESC LIMIT 1;")
            latest_run = cur.fetchone()
            if not latest_run:
                raise ValueError("No priority ranking found. Admin must run Priority Ranking before Allocation.")
            p_run_id = latest_run["run_id"]
        else:
            p_run_id = priority_run_id

        # Get ranked camp IDs
        cur.execute(
            """
            SELECT camp_id, rank, score
            FROM priority_scores
            WHERE run_id = %s
            ORDER BY rank ASC, camp_id ASC;
            """,
            (p_run_id,)
        )
        ranked_camps = cur.fetchall()
        if not ranked_camps:
            raise ValueError(f"Priority run #{p_run_id} contains no ranked camps.")

        ranked_camp_ids = [row["camp_id"] for row in ranked_camps]

        # Step 2: Open needs per camp
        cur.execute(
            """
            SELECT r.camp_id, ri.item_id,
                   SUM(ri.qty_requested - ri.qty_allocated) AS still_needed
            FROM requests r
            JOIN request_items ri ON r.request_id = ri.request_id
            JOIN camps c ON r.camp_id = c.camp_id
            WHERE c.status = 'active'
              AND r.status IN ('pending', 'partially_allocated')
              AND (ri.qty_requested - ri.qty_allocated) > 0
            GROUP BY r.camp_id, ri.item_id;
            """
        )
        needs_rows = cur.fetchall()
        open_needs: Dict[int, Dict[int, int]] = {}
        for row in needs_rows:
            cid = row["camp_id"]
            iid = row["item_id"]
            qty = int(row["still_needed"])
            if cid not in open_needs:
                open_needs[cid] = {}
            open_needs[cid][iid] = qty

        # Step 3: Current stock for active hubs
        cur.execute(
            """
            SELECT s.hub_id, s.item_id, s.qty_available
            FROM stock s
            JOIN hubs h ON s.hub_id = h.hub_id
            WHERE h.active = TRUE AND s.qty_available > 0;
            """
        )
        stock_rows = cur.fetchall()
        hub_stock: Dict[int, Dict[int, int]] = {}
        for row in stock_rows:
            hid = row["hub_id"]
            iid = row["item_id"]
            qty = int(row["qty_available"])
            if hid not in hub_stock:
                hub_stock[hid] = {}
            hub_stock[hid][iid] = qty

        # Step 4: Distances between active camps and active hubs
        distances: Dict[Tuple[int, int], float] = {}
        try:
            cur.execute(
                """
                SELECT c.camp_id, h.hub_id,
                       ST_Distance(
                         ST_SetSRID(ST_MakePoint(h.longitude, h.latitude), 4326)::geography,
                         ST_SetSRID(ST_MakePoint(c.longitude, c.latitude), 4326)::geography
                       ) AS metres
                FROM camps c
                CROSS JOIN hubs h
                WHERE c.status = 'active' AND h.active = TRUE;
                """
            )
            for row in cur.fetchall():
                distances[(row["camp_id"], row["hub_id"])] = float(row["metres"])
        except Exception:
            # Fallback to pure Python Haversine calculation if PostGIS extension is absent
            conn.rollback()
            cur.execute("SELECT camp_id, latitude, longitude FROM camps WHERE status = 'active';")
            camps_geo = {r["camp_id"]: (float(r["latitude"]), float(r["longitude"])) for r in cur.fetchall()}
            cur.execute("SELECT hub_id, latitude, longitude FROM hubs WHERE active = TRUE;")
            hubs_geo = {r["hub_id"]: (float(r["latitude"]), float(r["longitude"])) for r in cur.fetchall()}
            for cid, (clat, clon) in camps_geo.items():
                for hid, (hlat, hlon) in hubs_geo.items():
                    distances[(cid, hid)] = calculate_haversine_metres(clat, clon, hlat, hlon)

    # Step 5: Execute pure planning algorithm
    planned_allocations = plan_allocation(ranked_camp_ids, open_needs, hub_stock, distances)

    # Step 6 & 7: Commit plan to database in ONE transaction
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Insert allocation run record
            cur.execute(
                """
                INSERT INTO allocation_runs (priority_run_id, run_at, run_by, note)
                VALUES (%s, now(), %s, %s)
                RETURNING run_id;
                """,
                (p_run_id, user_id, f"Allocated {len(planned_allocations)} supply batches")
            )
            alloc_run_id = cur.fetchone()["run_id"]

            affected_request_ids = set()

            for item_alloc in planned_allocations:
                cid = item_alloc["camp_id"]
                hid = item_alloc["hub_id"]
                iid = item_alloc["item_id"]
                alloc_qty = item_alloc["qty"]

                # 1. Deduct stock at hub
                cur.execute(
                    """
                    UPDATE stock
                    SET qty_available = qty_available - %s, updated_at = now()
                    WHERE hub_id = %s AND item_id = %s;
                    """,
                    (alloc_qty, hid, iid)
                )

                # 2. Write stock movement ledger row
                cur.execute(
                    """
                    INSERT INTO stock_movements (hub_id, item_id, change_qty, reason, ref_id, created_by, created_at)
                    VALUES (%s, %s, %s, 'allocation', %s, %s, now());
                    """,
                    (hid, iid, -alloc_qty, alloc_run_id, user_id)
                )

                # 3. Apportion allocated quantity across camp's open requests, oldest request first
                cur.execute(
                    """
                    SELECT r.request_id, ri.request_item_id, ri.qty_requested, ri.qty_allocated
                    FROM requests r
                    JOIN request_items ri ON r.request_id = ri.request_id
                    WHERE r.camp_id = %s
                      AND ri.item_id = %s
                      AND r.status IN ('pending', 'partially_allocated')
                      AND (ri.qty_requested - ri.qty_allocated) > 0
                    ORDER BY r.created_at ASC, r.request_id ASC;
                    """,
                    (cid, iid)
                )
                open_req_items = cur.fetchall()

                qty_left_to_assign = alloc_qty
                for req_item in open_req_items:
                    req_id = req_item["request_id"]
                    ri_id = req_item["request_item_id"]
                    needed_here = req_item["qty_requested"] - req_item["qty_allocated"]

                    assign_here = min(qty_left_to_assign, needed_here)
                    if assign_here > 0:
                        cur.execute(
                            """
                            UPDATE request_items
                            SET qty_allocated = qty_allocated + %s
                            WHERE request_item_id = %s;
                            """,
                            (assign_here, ri_id)
                        )

                        cur.execute(
                            """
                            INSERT INTO allocations (run_id, camp_id, hub_id, item_id, request_item_id, qty, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, 'planned', now());
                            """,
                            (alloc_run_id, cid, hid, iid, ri_id, assign_here)
                        )

                        affected_request_ids.add(req_id)
                        qty_left_to_assign -= assign_here

                    if qty_left_to_assign <= 0:
                        break

            # 4. Update status for all affected requests
            for req_id in affected_request_ids:
                cur.execute(
                    """
                    SELECT qty_requested, qty_allocated
                    FROM request_items
                    WHERE request_id = %s;
                    """,
                    (req_id,)
                )
                items = cur.fetchall()
                all_fulfilled = all(it["qty_allocated"] >= it["qty_requested"] for it in items)
                any_allocated = any(it["qty_allocated"] > 0 for it in items)

                new_status = "fulfilled" if all_fulfilled else ("partially_allocated" if any_allocated else "pending")
                cur.execute(
                    "UPDATE requests SET status = %s WHERE request_id = %s;",
                    (new_status, req_id)
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e

    return {
        "run_id": alloc_run_id,
        "priority_run_id": p_run_id,
        "allocations_count": len(planned_allocations),
        "allocations": planned_allocations,
    }
