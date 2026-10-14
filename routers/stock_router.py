"""
stock_router.py (Owner: Member D)
=================================
FastAPI router for Hub Inventory Management, Stock Adjustments, and Donation Receipt.

Endpoints:
  - GET  /stock                         : View stock for a hub (coordinator own hub, admin any)
  - POST /stock/adjust                  : Manual stock correction with required reason (atomic ACID transaction)
  - POST /hub/donations/{id}/receive    : Confirm arrival of assigned donation -> adds stock (Task D3)

Contract Reference: DisasterRelief Team Guide - Sections 6.2, 6.4, 10, 11 (Tasks D1, D3)
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg2.extras

from database import get_conn
from deps import get_current_user, require_role

router = APIRouter(tags=["stock"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))


@router.get("/stock", response_class=HTMLResponse)
async def get_stock(
    request: Request,
    hub_id: Optional[int] = Query(None),
    format: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role("admin", "hub_coordinator")),
):
    """
    List inventory stock by hub.
    - Hub coordinators are restricted to their own hub.
    - Admins can select any hub or view the aggregate.
    """
    role = user.get("role")
    user_hub_id = user.get("hub_id")

    # Determine effective hub_id
    if role == "hub_coordinator":
        if not user_hub_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hub coordinator account is not assigned to any distribution hub.",
            )
        effective_hub_id = user_hub_id
    else:
        # Admin can view specified hub, or defaults to first active hub
        effective_hub_id = hub_id

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch all active hubs for selector
            cur.execute("SELECT hub_id, name, district FROM hubs WHERE active = TRUE ORDER BY hub_id ASC;")
            all_hubs = cur.fetchall()

            if not effective_hub_id and all_hubs:
                effective_hub_id = all_hubs[0]["hub_id"]

            # Fetch current hub metadata
            cur.execute("SELECT * FROM hubs WHERE hub_id = %s;", (effective_hub_id,))
            current_hub = cur.fetchone()
            if not current_hub and effective_hub_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hub #{effective_hub_id} not found.")

            # Fetch stock inventory for this hub
            # Supports both 14-group schema and fallback column names
            cur.execute(
                """
                SELECT s.hub_id, s.item_id, s.qty_available, s.updated_at,
                       i.item_code, i.name AS item_name, i.unit,
                       COALESCE(i.group_code, i.category, 'General') AS category_code,
                       COALESCE(i.group_kind, 'core') AS group_kind,
                       COALESCE(i.emergency_eligible, FALSE) AS emergency_eligible
                FROM stock s
                JOIN items i ON s.item_id = i.item_id
                WHERE s.hub_id = %s
                ORDER BY i.item_code ASC;
                """,
                (effective_hub_id,)
            )
            stock_items = cur.fetchall()

            # Fetch all catalog items (for the stock adjustment modal/form)
            cur.execute(
                """
                SELECT item_id, item_code, name, unit
                FROM items
                WHERE active = TRUE
                ORDER BY item_code ASC;
                """
            )
            all_items = cur.fetchall()

            # Task D3: Fetch incoming donations assigned to this hub
            cur.execute(
                """
                SELECT d.donation_id, d.donor_id, d.status, d.created_at,
                       u.full_name AS donor_name, u.district AS donor_district,
                       COALESCE(
                           json_agg(
                               json_build_object(
                                   'item_name', i.name,
                                   'item_code', i.item_code,
                                   'unit', i.unit,
                                   'qty', di.qty
                               )
                           ) FILTER (WHERE di.donation_item_id IS NOT NULL), '[]'::json
                       ) AS items
                FROM donations d
                JOIN users u ON d.donor_id = u.user_id
                LEFT JOIN donation_items di ON d.donation_id = di.donation_id
                LEFT JOIN items i ON di.item_id = i.item_id
                WHERE d.assigned_hub_id = %s AND d.status = 'hub_assigned'
                GROUP BY d.donation_id, d.donor_id, d.status, d.created_at, u.full_name, u.district
                ORDER BY d.created_at ASC;
                """,
                (effective_hub_id,)
            )
            incoming_donations = cur.fetchall()

            # Task D4: Fetch planned outgoing allocations from this hub awaiting dispatch
            cur.execute(
                """
                SELECT a.allocation_id, a.run_id, a.camp_id, a.item_id, a.qty,
                       a.status, a.created_at,
                       c.name AS camp_name, c.district AS camp_district,
                       i.name AS item_name, i.item_code, i.unit
                FROM allocations a
                JOIN camps c ON a.camp_id = c.camp_id
                JOIN items i ON a.item_id = i.item_id
                WHERE a.hub_id = %s AND a.status = 'planned'
                ORDER BY a.created_at ASC, a.allocation_id ASC;
                """,
                (effective_hub_id,)
            )
            planned_allocations = cur.fetchall()

            # Fetch recent stock movements logbook (audit trail)
            cur.execute(
                """
                SELECT sm.movement_id, sm.hub_id, sm.item_id, sm.change_qty,
                       sm.reason, sm.ref_id, sm.created_at,
                       i.name AS item_name, i.item_code, i.unit,
                       COALESCE(u.username, 'System') AS user_name
                FROM stock_movements sm
                JOIN items i ON sm.item_id = i.item_id
                LEFT JOIN users u ON sm.created_by = u.user_id
                WHERE sm.hub_id = %s
                ORDER BY sm.created_at DESC
                LIMIT 20;
                """,
                (effective_hub_id,)
            )
            recent_movements = cur.fetchall()

    finally:
        conn.close()

    if format == "json":
        return JSONResponse(content=jsonable_encoder(stock_items))

    return templates.TemplateResponse(
        "hub_dashboard.html",
        {
            "request": request,
            "hub": current_hub,
            "all_hubs": all_hubs,
            "stock_items": stock_items,
            "all_items": all_items,
            "incoming_donations": incoming_donations,
            "planned_allocations": planned_allocations,
            "recent_movements": recent_movements,
            "user": user,
            "current_user": user,
            "is_admin": role == "admin",
            "effective_hub_id": effective_hub_id,
        },
    )


@router.post("/stock/adjust")
async def adjust_stock(
    request: Request,
    hub_id: int = Form(...),
    item_id: int = Form(...),
    change_qty: int = Form(...),
    reason: str = Form(...),
    user: Dict[str, Any] = Depends(require_role("admin", "hub_coordinator")),
):
    """
    Manually adjust stock quantity with a mandatory explanation reason.
    ACID rule: Updates stock table and logs stock_movements entry within ONE transaction.
    Stock can never go negative.
    """
    role = user.get("role")
    user_hub_id = user.get("hub_id")
    user_id = user.get("user_id")

    if role == "hub_coordinator" and user_hub_id != hub_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Hub coordinators can only modify inventory for their own hub.",
        )

    cleaned_reason = reason.strip()
    if not cleaned_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A descriptive reason is mandatory for manual stock adjustments.",
        )

    if change_qty == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="change_qty cannot be zero.",
        )

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Lock the stock row to prevent race conditions
            cur.execute(
                """
                SELECT qty_available
                FROM stock
                WHERE hub_id = %s AND item_id = %s
                FOR UPDATE;
                """,
                (hub_id, item_id)
            )
            row = cur.fetchone()

            current_qty = row["qty_available"] if row else 0
            new_qty = current_qty + change_qty

            if new_qty < 0:
                conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Adjustment refused: stock cannot become negative. "
                        f"Current available: {current_qty}, requested change: {change_qty}."
                    ),
                )

            # Update or insert into stock table
            cur.execute(
                """
                INSERT INTO stock (hub_id, item_id, qty_available, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (hub_id, item_id)
                DO UPDATE SET qty_available = %s, updated_at = now();
                """,
                (hub_id, item_id, new_qty, new_qty)
            )

            # Record audit row in stock_movements
            cur.execute(
                """
                INSERT INTO stock_movements (hub_id, item_id, change_qty, reason, ref_id, created_by, created_at)
                VALUES (%s, %s, %s, 'manual_adjustment', NULL, %s, now());
                """,
                (hub_id, item_id, change_qty, user_id)
            )

        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record stock adjustment: {exc}",
        )
    finally:
        conn.close()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "hub_id": hub_id, "item_id": item_id, "new_qty": new_qty},
        )

    return RedirectResponse(url=f"/stock?hub_id={hub_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/hub/donations/{id}/receive")
async def receive_donation(
    id: int,
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin", "hub_coordinator")),
):
    """
    Task D3: Hub Coordinator confirms arrival of a donation.
    - Only the coordinator of the assigned hub (or admin) can receive.
    - Donation status must be 'hub_assigned'.
    - In ONE transaction:
        1. Add item quantities to hub stock.
        2. Write stock_movements audit records (reason 'donation_received').
        3. Set donation status to 'received' and received_at = now().
    - Idempotent: A second click on an already received donation does not double-add.
    """
    donation_id = id
    role = user.get("role")
    user_hub_id = user.get("hub_id")
    user_id = user.get("user_id")

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Lock donation row
            cur.execute(
                """
                SELECT donation_id, status, assigned_hub_id
                FROM donations
                WHERE donation_id = %s
                FOR UPDATE;
                """,
                (donation_id,)
            )
            donation = cur.fetchone()

            if not donation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Donation #{donation_id} not found.",
                )

            assigned_hub_id = donation["assigned_hub_id"]

            # Role verification
            if role == "hub_coordinator" and user_hub_id != assigned_hub_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: You can only receive donations assigned to Hub #{user_hub_id}.",
                )

            # Idempotency check: if already received, return gracefully without adding stock
            if donation["status"] == "received":
                conn.rollback()
                return RedirectResponse(
                    url=f"/stock?hub_id={assigned_hub_id}",
                    status_code=status.HTTP_303_SEE_OTHER,
                )

            if donation["status"] != "hub_assigned":
                conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Donation #{donation_id} cannot be received: "
                        f"status must be 'hub_assigned', but current status is '{donation['status']}'."
                    ),
                )

            # Fetch donation item lines
            cur.execute(
                """
                SELECT item_id, qty
                FROM donation_items
                WHERE donation_id = %s;
                """,
                (donation_id,)
            )
            items = cur.fetchall()

            # Atomic updates for all items
            for it in items:
                item_id = it["item_id"]
                qty = it["qty"]

                # 1. Increment hub stock
                cur.execute(
                    """
                    INSERT INTO stock (hub_id, item_id, qty_available, updated_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (hub_id, item_id)
                    DO UPDATE SET qty_available = stock.qty_available + %s, updated_at = now();
                    """,
                    (assigned_hub_id, item_id, qty, qty)
                )

                # 2. Add stock_movement audit row
                cur.execute(
                    """
                    INSERT INTO stock_movements (hub_id, item_id, change_qty, reason, ref_id, created_by, created_at)
                    VALUES (%s, %s, %s, 'donation_received', %s, %s, now());
                    """,
                    (assigned_hub_id, item_id, qty, donation_id, user_id)
                )

            # 3. Mark donation received
            cur.execute(
                """
                UPDATE donations
                SET status = 'received', received_at = now()
                WHERE donation_id = %s;
                """,
                (donation_id,)
            )

        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error receiving donation #{donation_id}: {exc}",
        )
    finally:
        conn.close()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "received", "donation_id": donation_id, "hub_id": assigned_hub_id},
        )

    return RedirectResponse(
        url=f"/stock?hub_id={assigned_hub_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
