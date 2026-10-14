"""
allocation_router.py (Owner: Member D)
=====================================
FastAPI router for Relief Supply Allocation Runs, Dispatch Confirmation, and Tracking.

Endpoints:
  - POST /allocation/run              : Execute allocation run on latest priority ranking (admin only)
  - GET  /allocation/latest           : View details & shortage report for newest allocation run (admin)
  - GET  /allocation                  : List allocations (filtered by ?camp_id= or ?hub_id=)
  - POST /allocation/{id}/dispatch    : Mark allocation dispatched -> updates camp.last_supply_at (Task D4/9.6)

Contract Reference: DisasterRelief Team Guide - Sections 6.2, 9.2, 9.6, 10, 11 (Task D4)
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
from engines.allocation_engine import run_allocation

router = APIRouter(tags=["allocation"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))


@router.post("/allocation/run")
async def execute_allocation_run(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Triggers deterministic resource allocation from nearest hubs to camps in priority order.
    Uses the latest priority ranking run.
    """
    user_id = user.get("user_id")
    conn = get_conn()
    try:
        summary = run_allocation(conn, user_id=user_id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Allocation execution failed: {exc}",
        )
    finally:
        conn.close()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(status_code=status.HTTP_200_OK, content=summary)

    return RedirectResponse(url="/allocation/latest", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/allocation/latest", response_class=HTMLResponse)
async def get_latest_allocation(
    request: Request,
    format: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Detailed results dashboard of the most recent allocation execution:
    - Overall summary metrics (batches planned, distinct camps, distinct hubs)
    - Item allocation ledger
    - Shortages table (remaining unmet requests across active camps)
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Fetch latest allocation run
            cur.execute(
                """
                SELECT ar.run_id, ar.priority_run_id, ar.run_at, ar.note,
                       u.full_name AS run_by_name
                FROM allocation_runs ar
                LEFT JOIN users u ON ar.run_by = u.user_id
                ORDER BY ar.run_at DESC, ar.run_id DESC
                LIMIT 1;
                """
            )
            run = cur.fetchone()

            if not run:
                return templates.TemplateResponse(
                    request=request,
                    name="allocation_results.html",
                    context={
                        "request": request,
                        "run": None,
                        "allocations": [],
                        "shortages": [],
                        "camps_summary": [],
                        "user": user,
                        "current_user": user,
                    },
                )

            run_id = run["run_id"]

            # 2. Fetch allocations in this run
            cur.execute(
                """
                SELECT a.allocation_id, a.run_id, a.camp_id, a.hub_id, a.item_id,
                       a.qty, a.status, a.created_at,
                       c.name AS camp_name, c.district AS camp_district,
                       h.name AS hub_name, h.district AS hub_district,
                       i.name AS item_name, i.item_code, i.unit,
                       COALESCE(i.group_code, i.category, 'General') AS category_code
                FROM allocations a
                JOIN camps c ON a.camp_id = c.camp_id
                JOIN hubs h ON a.hub_id = h.hub_id
                JOIN items i ON a.item_id = i.item_id
                WHERE a.run_id = %s
                ORDER BY c.camp_id ASC, i.item_code ASC;
                """,
                (run_id,)
            )
            allocations = cur.fetchall()

            # 3. Aggregate allocations per camp
            camp_summary_dict: Dict[int, Dict[str, Any]] = {}
            for row in allocations:
                cid = row["camp_id"]
                if cid not in camp_summary_dict:
                    camp_summary_dict[cid] = {
                        "camp_id": cid,
                        "camp_name": row["camp_name"],
                        "camp_district": row["camp_district"],
                        "total_units": 0,
                        "items_list": [],
                    }
                camp_summary_dict[cid]["total_units"] += row["qty"]
                camp_summary_dict[cid]["items_list"].append({
                    "item_name": row["item_name"],
                    "item_code": row["item_code"],
                    "qty": row["qty"],
                    "unit": row["unit"],
                    "hub_name": row["hub_name"],
                    "status": row["status"],
                })

            camps_summary = list(camp_summary_dict.values())

            # 4. Compute remaining shortages across all active camps
            cur.execute(
                """
                SELECT c.camp_id, c.name AS camp_name, c.district AS camp_district,
                       i.item_id, i.name AS item_name, i.item_code, i.unit,
                       SUM(ri.qty_requested) AS total_requested,
                       SUM(ri.qty_allocated) AS total_allocated,
                       SUM(ri.qty_requested - ri.qty_allocated) AS shortage_qty
                FROM requests r
                JOIN request_items ri ON r.request_id = ri.request_id
                JOIN camps c ON r.camp_id = c.camp_id
                JOIN items i ON ri.item_id = i.item_id
                WHERE c.status = 'active'
                  AND r.status IN ('pending', 'partially_allocated')
                  AND (ri.qty_requested - ri.qty_allocated) > 0
                GROUP BY c.camp_id, c.name, c.district, i.item_id, i.name, i.item_code, i.unit
                ORDER BY c.camp_id ASC, shortage_qty DESC;
                """
            )
            shortages = cur.fetchall()

    finally:
        conn.close()

    if format == "json":
        return JSONResponse(
            content=jsonable_encoder({
                "run": run,
                "allocations": allocations,
                "shortages": shortages,
            })
        )

    return templates.TemplateResponse(
        request=request,
        name="allocation_results.html",
        context={
            "request": request,
            "run": run,
            "allocations": allocations,
            "camps_summary": camps_summary,
            "shortages": shortages,
            "user": user,
            "current_user": user,
        },
    )


@router.get("/allocation")
async def list_allocations(
    request: Request,
    camp_id: Optional[int] = Query(None),
    hub_id: Optional[int] = Query(None),
    format: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role("admin", "camp_officer", "hub_coordinator")),
):
    """
    List allocations with role-based filtering:
    - Admin: can see all, or filter by ?camp_id= or ?hub_id=.
    - Camp Officer: can only see own camp (enforced). Supports Member B Task B4 ("what is coming").
    - Hub Coordinator: can only see allocations originating from own hub (enforced).
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")
    user_hub_id = user.get("hub_id")

    query_params = []
    where_clauses = []

    if role == "camp_officer":
        where_clauses.append("a.camp_id = %s")
        query_params.append(user_camp_id)
    elif role == "hub_coordinator":
        where_clauses.append("a.hub_id = %s")
        query_params.append(user_hub_id)
    else:
        # Admin filtering
        if camp_id:
            where_clauses.append("a.camp_id = %s")
            query_params.append(camp_id)
        if hub_id:
            where_clauses.append("a.hub_id = %s")
            query_params.append(hub_id)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT a.allocation_id, a.run_id, a.camp_id, a.hub_id, a.item_id,
                       a.qty, a.status, a.created_at,
                       c.name AS camp_name, c.district AS camp_district,
                       h.name AS hub_name, h.district AS hub_district,
                       i.name AS item_name, i.item_code, i.unit
                FROM allocations a
                JOIN camps c ON a.camp_id = c.camp_id
                JOIN hubs h ON a.hub_id = h.hub_id
                JOIN items i ON a.item_id = i.item_id
                {where_sql}
                ORDER BY a.created_at DESC, a.allocation_id DESC;
                """,
                tuple(query_params)
            )
            allocations = cur.fetchall()
    finally:
        conn.close()

    # Always return JSON if requested, or if format=json
    if format == "json" or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content=jsonable_encoder(allocations))

    # Otherwise render allocation table template
    return templates.TemplateResponse(
        request=request,
        name="allocation_results.html",
        context={
            "request": request,
            "run": None,
            "allocations": allocations,
            "camps_summary": [],
            "shortages": [],
            "user": user,
            "current_user": user,
            "filter_camp_id": camp_id or user_camp_id,
            "filter_hub_id": hub_id or user_hub_id,
        },
    )


@router.post("/allocation/{id}/dispatch")
async def dispatch_allocation(
    id: int,
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin", "hub_coordinator")),
):
    """
    Task D4 & Guide Section 9.6:
    Hub coordinator presses 'Mark dispatched' on a planned allocation.
    - Sets allocation status to 'dispatched'.
    - Updates camps.last_supply_at = now() for the recipient camp.
    - This updates the camp's time-since-last-supply factor in subsequent SAW ranking runs.
    """
    allocation_id = id
    role = user.get("role")
    user_hub_id = user.get("hub_id")

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT a.allocation_id, a.camp_id, a.hub_id, a.status
                FROM allocations a
                WHERE a.allocation_id = %s
                FOR UPDATE;
                """,
                (allocation_id,)
            )
            alloc = cur.fetchone()

            if not alloc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Allocation #{allocation_id} not found.",
                )

            # Role verification
            if role == "hub_coordinator" and user_hub_id != alloc["hub_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You can only dispatch allocations originating from your assigned hub.",
                )

            # Idempotency check: if already dispatched, proceed safely
            if alloc["status"] == "dispatched":
                conn.rollback()
                return RedirectResponse(url=f"/stock?hub_id={alloc['hub_id']}", status_code=status.HTTP_303_SEE_OTHER)

            if alloc["status"] != "planned":
                conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Only 'planned' allocations can be marked dispatched. Current status is '{alloc['status']}'.",
                )

            # Update allocation status
            cur.execute(
                "UPDATE allocations SET status = 'dispatched' WHERE allocation_id = %s;",
                (allocation_id,)
            )

            # Update camp last supply timestamp
            cur.execute(
                "UPDATE camps SET last_supply_at = now(), updated_at = now() WHERE camp_id = %s;",
                (alloc["camp_id"],)
            )

        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch allocation #{allocation_id}: {exc}",
        )
    finally:
        conn.close()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "dispatched", "allocation_id": allocation_id},
        )

    return RedirectResponse(
        url=f"/stock?hub_id={alloc['hub_id']}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
