"""
Requests Router – handles creating, viewing, escalating, and cancelling relief requests.

Implements Task B3 (Camps & Requests: Request entry, validation, escalation, detail).
Follows contracts defined in DisasterRelief Team Guide Sections 6.2, 10, and 11.
"""

import csv
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg2.extras

from database import get_conn
from deps import get_current_user, require_role

router = APIRouter()

# Resolve path to templates and seed data relative to the project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))
_CSV_PATH = _PROJECT_ROOT / "seed" / "seed_items.csv"

# ── Catalog helper for Request Form ────────────────────────────────────────

CORE_GROUP_CODES = ["FW", "CB", "SH", "MF", "KU", "SU"]
EXTENDED_GROUP_CODES = ["SG", "CA", "SS", "WI", "PR", "LV", "RC", "TL"]
ALL_GROUP_CODES = CORE_GROUP_CODES + EXTENDED_GROUP_CODES

GROUP_FULL_NAMES = {
    "FW": "Food & Water",
    "CB": "Clothing & Bedding",
    "SH": "Sanitation & Hygiene",
    "MF": "Medical / First Aid",
    "KU": "Kitchen & Utensils",
    "SU": "Shelter & Utility",
    "SG": "Special Groups",
    "CA": "Communication & Administration",
    "SS": "Safety & Security",
    "WI": "Waste & WASH Infrastructure",
    "PR": "Psychosocial & Recreation",
    "LV": "Livestock & Pets",
    "RC": "Recovery & Cleaning",
    "TL": "Transport & Logistics",
}


def _group_order_key(item: dict) -> int:
    code = item.get("group_code", "")
    try:
        return ALL_GROUP_CODES.index(code)
    except ValueError:
        return len(ALL_GROUP_CODES)


def get_catalog_items() -> list[dict]:
    """
    Fetch active items for request entry.
    Queries the database first. If database is unreachable or empty,
    falls back to seed/seed_items.csv with synthetic item_id.
    """
    items: list[dict] = []
    if get_conn is not None:
        try:
            conn = get_conn()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT item_id, item_code, name, group_code, group_kind,
                               unit, item_type, perishable, requires_approval,
                               emergency_eligible, notes
                        FROM items
                        WHERE active = true
                        ORDER BY item_id ASC;
                        """
                    )
                    items = cur.fetchall()
            finally:
                conn.close()
        except Exception:
            items = []

    if not items and _CSV_PATH.is_file():
        with open(_CSV_PATH, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for idx, row in enumerate(reader, start=1):
                if not row.get("item_code", "").strip():
                    continue
                items.append({
                    "item_id": idx,
                    "item_code": row.get("item_code", ""),
                    "name": row.get("name", ""),
                    "group_code": row.get("group_code", "FW"),
                    "group_kind": row.get("group_kind", "core"),
                    "unit": row.get("unit", "piece"),
                    "item_type": row.get("item_type", "Consumable"),
                    "perishable": row.get("perishable", "No"),
                    "requires_approval": row.get("requires_approval", "No"),
                    "emergency_eligible": row.get("emergency_eligible", "no").strip().lower() in ("yes", "true"),
                    "notes": row.get("notes", ""),
                })

    return items


# ── Shared Validation and Save Logic for Requests ──────────────────────────

def _validate_and_save_request(
    user: dict,
    input_data: dict,
) -> tuple[Optional[dict], dict, list[str]]:
    """
    Validate and save a new relief request.
    Shared between HTML form submissions and JSON API calls.

    Rules:
    1. Role: camp_officer (for own camp) or admin.
    2. Camp must exist and be 'active'.
    3. At least one item requested.
    4. Each item quantity must be > 0.
    5. No duplicate items in the request.
    6. Comment max 500 characters (not scored, not analysed).
    7. Escalate flag is boolean.

    Returns:
        (created_request_dict_or_none, form_state_dict, list_of_errors)
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")
    errors: list[str] = []

    # 1. Authorization & Target Camp
    target_camp_id_raw = input_data.get("camp_id")
    if role == "camp_officer":
        if user_camp_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Camp officer is not assigned to any camp.",
            )
        target_camp_id = int(user_camp_id)
        if target_camp_id_raw is not None and str(target_camp_id_raw).strip():
            try:
                if int(target_camp_id_raw) != target_camp_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: You can only submit requests for your own assigned camp.",
                    )
            except ValueError:
                pass
    elif role == "admin":
        if not target_camp_id_raw:
            errors.append("Target camp is required.")
            target_camp_id = None
        else:
            try:
                target_camp_id = int(target_camp_id_raw)
            except (ValueError, TypeError):
                errors.append("Invalid camp ID.")
                target_camp_id = None
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only camp officers and administrators can submit requests.",
        )

    # 2. Verify Camp is Active
    camp_record = None
    if target_camp_id is not None:
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT camp_id, name, district, status FROM camps WHERE camp_id = %s;",
                    (target_camp_id,),
                )
                camp_record = cur.fetchone()
        finally:
            conn.close()

        if not camp_record:
            errors.append(f"Camp with ID {target_camp_id} was not found.")
        elif camp_record.get("status") != "active":
            errors.append(f"Camp '{camp_record.get('name')}' is closed. Requests can only be submitted for active camps.")

    # 3. Comment validation (max 500 characters, unanalysed plain text)
    raw_comment = input_data.get("comment", "")
    comment_text = str(raw_comment).strip() if raw_comment is not None else ""
    if len(comment_text) > 500:
        errors.append("Comment cannot exceed 500 characters.")
    final_comment = comment_text if comment_text else None

    # 4. Escalation flag
    raw_escalated = input_data.get("escalated", False)
    if isinstance(raw_escalated, str):
        escalated_val = raw_escalated.strip().lower() in ("true", "1", "yes", "on")
    else:
        escalated_val = bool(raw_escalated)

    # 5. Items parsing & validation
    # Supports list of dicts: [{"item_id": 1, "qty": 10}],
    # or parallel lists: item_id[] and qty[], or qty_{item_id}
    raw_items = input_data.get("items")
    parsed_items: list[dict] = []

    if isinstance(raw_items, list):
        for entry in raw_items:
            if isinstance(entry, dict):
                i_id = entry.get("item_id")
                q_val = entry.get("qty") or entry.get("quantity") or entry.get("qty_requested")
                if i_id is not None:
                    parsed_items.append({"item_id": i_id, "qty": q_val})
    else:
        # Check for item_id / qty parallel lists or qty_{item_id} format from HTML forms
        item_ids = input_data.get("item_id")
        qtys = input_data.get("quantity") or input_data.get("qty")
        if item_ids and qtys:
            if not isinstance(item_ids, list):
                item_ids = [item_ids]
            if not isinstance(qtys, list):
                qtys = [qtys]
            for i_id, q_val in zip(item_ids, qtys):
                if str(q_val).strip() != "":
                    parsed_items.append({"item_id": i_id, "qty": q_val})
        else:
            # Check for keys starting with qty_
            for k, v in input_data.items():
                if k.startswith("qty_") and str(v).strip():
                    item_id_str = k[4:]
                    if item_id_str.isdigit():
                        parsed_items.append({"item_id": int(item_id_str), "qty": v})

    # Validate items
    if not parsed_items:
        errors.append("At least one item must be requested.")

    validated_items: list[dict] = []
    seen_item_ids: set[int] = set()

    for item in parsed_items:
        try:
            item_id = int(item["item_id"])
        except (ValueError, TypeError):
            errors.append(f"Invalid item ID: {item.get('item_id')}")
            continue

        if item_id in seen_item_ids:
            errors.append(f"Duplicate item found (Item ID {item_id}). Each item may only appear once in a request.")
            continue
        seen_item_ids.add(item_id)

        try:
            qty = int(item["qty"])
            if qty <= 0:
                errors.append(f"Requested quantity for Item ID {item_id} must be greater than 0.")
                continue
        except (ValueError, TypeError):
            errors.append(f"Quantity for Item ID {item_id} must be a valid positive whole number.")
            continue

        validated_items.append({"item_id": item_id, "qty": qty})

    form_state = {
        "camp_id": target_camp_id,
        "escalated": escalated_val,
        "comment": comment_text,
        "items": parsed_items,
    }

    if errors:
        return None, form_state, errors

    # 6. Database Transaction: Insert request and request_items
    submitted_by_id = user.get("user_id")
    # Fallback to 1 if user_id is None in mock dev
    if submitted_by_id is None:
        submitted_by_id = 1

    created_request = None
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO requests (camp_id, submitted_by, status, escalated, comment, created_at)
                VALUES (%s, %s, 'pending', %s, %s, now())
                RETURNING request_id, camp_id, submitted_by, status, escalated, comment, created_at;
                """,
                (target_camp_id, submitted_by_id, escalated_val, final_comment),
            )
            created_request = cur.fetchone()
            req_id = created_request["request_id"]

            for itm in validated_items:
                cur.execute(
                    """
                    INSERT INTO request_items (request_id, item_id, qty_requested, qty_allocated)
                    VALUES (%s, %s, %s, 0);
                    """,
                    (req_id, itm["item_id"], itm["qty"]),
                )
        conn.commit()
    finally:
        conn.close()

    created_request["items"] = validated_items
    return created_request, form_state, []


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/requests/new", response_class=HTMLResponse)
async def get_request_form_page(
    request: Request,
    camp_id: Optional[int] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    Render request entry form (request_form.html).
    - Camp officer submits for their own assigned camp.
    - Admin can specify camp_id or select an active camp.
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    if role == "camp_officer":
        target_camp_id = user_camp_id
    elif role == "admin":
        target_camp_id = camp_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only camp officers and administrators can submit relief requests.",
        )

    # Fetch active camps if admin
    camps_list = []
    selected_camp = None
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if role == "admin":
                cur.execute(
                    "SELECT camp_id, name, district, status FROM camps WHERE status = 'active' ORDER BY name ASC;"
                )
                camps_list = cur.fetchall()
            if target_camp_id:
                cur.execute(
                    "SELECT camp_id, name, district, status FROM camps WHERE camp_id = %s;",
                    (target_camp_id,),
                )
                selected_camp = cur.fetchone()
    finally:
        conn.close()

    catalog_items = get_catalog_items()
    # Group items by canonical group code
    sorted_items = sorted(catalog_items, key=_group_order_key)
    grouped_items: dict[str, list[dict]] = {}
    for item in sorted_items:
        gcode = item.get("group_code", "FW")
        grouped_items.setdefault(gcode, []).append(item)

    return templates.TemplateResponse(
        request=request,
        name="request_form.html",
        context={
            "request": request,
            "user": user,
            "camps": camps_list,
            "selected_camp": selected_camp,
            "grouped_items": grouped_items,
            "core_codes": CORE_GROUP_CODES,
            "extended_codes": EXTENDED_GROUP_CODES,
            "group_names": GROUP_FULL_NAMES,
            "errors": [],
            "form_state": {},
        },
    )


@router.post("/requests", response_class=HTMLResponse)
async def create_request(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Create a new relief request.
    Supports both HTML form submission and JSON payload.
    """
    content_type = request.headers.get("content-type", "")
    is_json = "application/json" in content_type

    if is_json:
        try:
            input_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload.",
            )
    else:
        form = await request.form()
        # Parse form data into a dict, handling multiple item_id and quantity fields
        input_data = {}
        for k in form.keys():
            val_list = form.getlist(k)
            if len(val_list) > 1:
                input_data[k] = val_list
            else:
                input_data[k] = val_list[0] if val_list else ""

    created_request, form_state, errors = _validate_and_save_request(user, input_data)

    if errors:
        if is_json:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"errors": errors, "detail": errors},
            )
        # Re-render request_form.html with errors
        catalog_items = get_catalog_items()
        sorted_items = sorted(catalog_items, key=_group_order_key)
        grouped_items: dict[str, list[dict]] = {}
        for item in sorted_items:
            gcode = item.get("group_code", "FW")
            grouped_items.setdefault(gcode, []).append(item)

        selected_camp = None
        camps_list = []
        target_camp_id = form_state.get("camp_id") or user.get("camp_id")
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if user.get("role") == "admin":
                    cur.execute(
                        "SELECT camp_id, name, district, status FROM camps WHERE status = 'active' ORDER BY name ASC;"
                    )
                    camps_list = cur.fetchall()
                if target_camp_id:
                    cur.execute(
                        "SELECT camp_id, name, district, status FROM camps WHERE camp_id = %s;",
                        (target_camp_id,),
                    )
                    selected_camp = cur.fetchone()
        finally:
            conn.close()

        return templates.TemplateResponse(
            request=request,
            name="request_form.html",
            context={
                "request": request,
                "user": user,
                "camps": camps_list,
                "selected_camp": selected_camp,
                "grouped_items": grouped_items,
                "core_codes": CORE_GROUP_CODES,
                "extended_codes": EXTENDED_GROUP_CODES,
                "group_names": GROUP_FULL_NAMES,
                "errors": errors,
                "form_state": form_state,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if is_json:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder(created_request),
        )

    # HTML redirect to the new request detail page
    new_req_id = created_request["request_id"]
    return RedirectResponse(
        url=f"/requests/{new_req_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/requests", response_class=HTMLResponse)
async def list_requests(
    request: Request,
    camp_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    user: dict = Depends(get_current_user),
):
    """
    List relief requests.
    - Admin sees all camps, filterable by ?camp_id= and ?status=.
    - Camp officer sees only their own camp's requests.
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    if role == "camp_officer":
        if user_camp_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Camp officer has no assigned camp.",
            )
        if camp_id is not None and int(camp_id) != int(user_camp_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only view requests for your own camp.",
            )
        effective_camp_id = int(user_camp_id)
    elif role == "admin":
        effective_camp_id = camp_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to list requests.",
        )

    # Build SQL query with optional filters
    query_parts = [
        """
        SELECT r.request_id, r.camp_id, c.name AS camp_name, c.district,
               r.submitted_by, u.full_name AS submitted_by_name,
               r.status, r.escalated, r.comment, r.created_at,
               COUNT(ri.request_item_id) AS total_items,
               COALESCE(SUM(ri.qty_requested), 0) AS total_qty_requested,
               COALESCE(SUM(ri.qty_allocated), 0) AS total_qty_allocated
        FROM requests r
        JOIN camps c ON r.camp_id = c.camp_id
        LEFT JOIN users u ON r.submitted_by = u.user_id
        LEFT JOIN request_items ri ON r.request_id = ri.request_id
        """
    ]
    where_clauses = []
    params: list[Any] = []

    if effective_camp_id is not None:
        where_clauses.append("r.camp_id = %s")
        params.append(effective_camp_id)

    if status_filter:
        where_clauses.append("r.status = %s")
        params.append(status_filter.strip())

    if where_clauses:
        query_parts.append("WHERE " + " AND ".join(where_clauses))

    query_parts.append(
        """
        GROUP BY r.request_id, c.name, c.district, u.full_name
        ORDER BY r.created_at DESC;
        """
    )
    final_query = "\n".join(query_parts)

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(final_query, tuple(params))
            requests_list = cur.fetchall()
    finally:
        conn.close()

    # If client prefers JSON
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return JSONResponse(content=jsonable_encoder(requests_list))

    return templates.TemplateResponse(
        request=request,
        name="request_list.html",
        context={
            "request": request,
            "requests": requests_list,
            "user": user,
            "selected_status": status_filter or "",
            "selected_camp_id": effective_camp_id,
        },
    )


@router.get("/requests/{request_id}", response_class=HTMLResponse)
async def get_request_detail(
    request_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    View detail of a single relief request, including requested vs allocated counts.
    - Admin can view any request.
    - Camp officer can only view requests belonging to their camp.
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT r.request_id, r.camp_id, c.name AS camp_name, c.district, c.status AS camp_status,
                       r.submitted_by, u.full_name AS submitted_by_name,
                       r.status, r.escalated, r.comment, r.created_at
                FROM requests r
                JOIN camps c ON r.camp_id = c.camp_id
                LEFT JOIN users u ON r.submitted_by = u.user_id
                WHERE r.request_id = %s;
                """,
                (request_id,),
            )
            req_record = cur.fetchone()

            if not req_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Request {request_id} not found.",
                )

            # Role verification
            if role == "camp_officer":
                if user_camp_id is None or int(user_camp_id) != req_record["camp_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: You can only view requests for your own camp.",
                    )
            elif role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have permission to view request details.",
                )

            # Fetch line items
            cur.execute(
                """
                SELECT ri.request_item_id, ri.request_id, ri.item_id,
                       i.item_code, i.name AS item_name, i.unit, i.group_code,
                       i.emergency_eligible,
                       ri.qty_requested, ri.qty_allocated,
                       (ri.qty_requested - ri.qty_allocated) AS qty_pending
                FROM request_items ri
                JOIN items i ON ri.item_id = i.item_id
                WHERE ri.request_id = %s
                ORDER BY i.group_code, i.item_code;
                """,
                (request_id,),
            )
            items = cur.fetchall()
    finally:
        conn.close()

    req_record["items"] = items

    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return JSONResponse(content=jsonable_encoder(req_record))

    return templates.TemplateResponse(
        request=request,
        name="request_detail.html",
        context={
            "request": request,
            "req": req_record,
            "items": items,
            "user": user,
            "group_names": GROUP_FULL_NAMES,
        },
    )


@router.post("/requests/{request_id}/escalate")
async def escalate_request(
    request_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Mark an open request as urgent (escalated = TRUE).
    - Can only be done by owning camp officer or admin.
    - Only allowed when request is open ('pending' or 'partially_allocated').
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT request_id, camp_id, status, escalated FROM requests WHERE request_id = %s;",
                (request_id,),
            )
            req = cur.fetchone()

            if not req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Request {request_id} not found.",
                )

            if role == "camp_officer":
                if user_camp_id is None or int(user_camp_id) != req["camp_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: You can only escalate requests for your own camp.",
                    )
            elif role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have permission to escalate requests.",
                )

            if req["status"] not in ("pending", "partially_allocated"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot escalate request with status '{req['status']}'. Only open requests can be escalated.",
                )

            cur.execute(
                "UPDATE requests SET escalated = TRUE WHERE request_id = %s RETURNING *;",
                (request_id,),
            )
            updated = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return JSONResponse(content=jsonable_encoder(updated))

    return RedirectResponse(
        url=f"/requests/{request_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/requests/{request_id}/cancel")
async def cancel_request(
    request_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Cancel an open request (status = 'cancelled').
    - Can only be done by owning camp officer or admin.
    - Only allowed when request is open ('pending' or 'partially_allocated').
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT request_id, camp_id, status FROM requests WHERE request_id = %s;",
                (request_id,),
            )
            req = cur.fetchone()

            if not req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Request {request_id} not found.",
                )

            if role == "camp_officer":
                if user_camp_id is None or int(user_camp_id) != req["camp_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: You can only cancel requests for your own camp.",
                    )
            elif role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have permission to cancel requests.",
                )

            if req["status"] not in ("pending", "partially_allocated"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel request with status '{req['status']}'. Only open requests can be cancelled.",
                )

            cur.execute(
                "UPDATE requests SET status = 'cancelled' WHERE request_id = %s RETURNING *;",
                (request_id,),
            )
            updated = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return JSONResponse(content=jsonable_encoder(updated))

    return RedirectResponse(
        url=f"/requests/{request_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
