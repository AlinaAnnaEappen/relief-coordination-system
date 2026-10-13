"""
Camps Router – handles listing, viewing, and creating relief camps.

Implements Task B2a (Admin side: camp list and camp creation).
Follows contracts defined in DisasterRelief Team Guide Sections 6.2, 10, and 11.
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg2.extras

from database import get_conn
from deps import get_current_user, require_role

router = APIRouter()

# Resolve path to templates relative to the project root (same as items_router.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))


# ── Camp List ─────────────────────────────────────────────────────────────

@router.get("/camps", response_class=HTMLResponse)
async def list_camps(
    request: Request,
    format: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    List relief camps.
    - Admins see all camps.
    - A camp officer sees only their own camp (matching user['camp_id']).
    - Add ?format=json to get the list as JSON using Section 6.2 column names.
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    if role not in ("admin", "camp_officer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view relief camps.",
        )

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if role == "admin":
                cur.execute(
                    """
                    SELECT camp_id, name, district, address, latitude, longitude,
                           capacity, occupancy, children_count, elderly_count,
                           pregnant_count, disabled_count, damage_level,
                           access_difficulty, status, last_supply_at, created_at, updated_at
                    FROM camps
                    ORDER BY camp_id ASC;
                    """
                )
                camps = cur.fetchall()
            else:
                # Camp officer view: only their assigned camp
                if not user_camp_id:
                    camps = []
                else:
                    cur.execute(
                        """
                        SELECT camp_id, name, district, address, latitude, longitude,
                               capacity, occupancy, children_count, elderly_count,
                               pregnant_count, disabled_count, damage_level,
                               access_difficulty, status, last_supply_at, created_at, updated_at
                        FROM camps
                        WHERE camp_id = %s
                        ORDER BY camp_id ASC;
                        """,
                        (user_camp_id,),
                    )
                    camps = cur.fetchall()
    finally:
        conn.close()

    # Return JSON when requested
    if format and format.lower() == "json":
        return JSONResponse(content=jsonable_encoder(camps))

    # Default to rendering the HTML table
    return templates.TemplateResponse(
        request=request,
        name="camp_list.html",
        context={
            "request": request,
            "camps": camps,
            "user": user,
        },
    )


# ── Create Camp Form (Admin Only) ─────────────────────────────────────────

@router.get("/camps/new", response_class=HTMLResponse)
async def new_camp_form(
    request: Request,
    user: dict = Depends(require_role("admin")),
):
    """
    Display the empty camp creation form.
    Placed BEFORE /camps/{camp_id} so 'new' is not treated as a camp ID.
    """
    empty_form = {
        "name": "",
        "district": "",
        "address": "",
        "latitude": "",
        "longitude": "",
        "capacity": "",
        "status": "active",
    }
    return templates.TemplateResponse(
        request=request,
        name="camp_form.html",
        context={
            "request": request,
            "camp": empty_form,
            "errors": [],
            "user": user,
            "is_new": True,
        },
    )


# ── Create Camp Submission (Admin Only) ───────────────────────────────────

@router.post("/camps", response_class=HTMLResponse)
async def create_camp(
    request: Request,
    name: str = Form(""),
    district: str = Form(""),
    address: Optional[str] = Form(None),
    latitude: str = Form(""),
    longitude: str = Form(""),
    capacity: Optional[str] = Form(None),
    camp_status: str = Form("active", alias="status"),
    user: dict = Depends(require_role("admin")),
):
    """
    Create a new camp from form inputs.
    Validates required fields, coordinate boundaries, capacity, and status.
    If validation fails, re-renders the form with typed values and clear messages.
    """
    errors: list[str] = []

    # Preserve typed values to re-fill form on error
    form_data = {
        "name": name,
        "district": district,
        "address": address or "",
        "latitude": latitude,
        "longitude": longitude,
        "capacity": capacity or "",
        "status": camp_status,
    }

    # Validate name
    clean_name = name.strip()
    if not clean_name:
        errors.append("Camp name is required.")

    # Validate district
    clean_district = district.strip()
    if not clean_district:
        errors.append("District is required.")

    # Validate latitude (-90 to 90)
    lat_val: Optional[Decimal] = None
    if not latitude.strip():
        errors.append("Latitude is required.")
    else:
        try:
            lat_val = Decimal(latitude.strip())
            if lat_val < Decimal("-90") or lat_val > Decimal("90"):
                errors.append("Latitude must be between -90.0 and 90.0 degrees.")
        except Exception:
            errors.append("Latitude must be a valid number.")

    # Validate longitude (-180 to 180)
    lon_val: Optional[Decimal] = None
    if not longitude.strip():
        errors.append("Longitude is required.")
    else:
        try:
            lon_val = Decimal(longitude.strip())
            if lon_val < Decimal("-180") or lon_val > Decimal("180"):
                errors.append("Longitude must be between -180.0 and 180.0 degrees.")
        except Exception:
            errors.append("Longitude must be a valid number.")

    # Validate capacity (empty or >= 0)
    cap_val: Optional[int] = None
    if capacity is not None and capacity.strip():
        try:
            cap_val = int(capacity.strip())
            if cap_val < 0:
                errors.append("Capacity cannot be negative.")
        except ValueError:
            errors.append("Capacity must be a non-negative whole number (or left empty).")

    # Validate status ('active' or 'closed')
    clean_status = camp_status.strip().lower()
    if clean_status not in ("active", "closed"):
        errors.append("Status must be either 'active' or 'closed'.")

    # If any validation errors occurred, re-display form with user inputs preserved
    if errors:
        return templates.TemplateResponse(
            request=request,
            name="camp_form.html",
            context={
                "request": request,
                "camp": form_data,
                "errors": errors,
                "user": user,
                "is_new": True,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Insert into PostgreSQL; remaining columns use Section 6.2 defaults
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO camps (name, district, address, latitude, longitude, capacity, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING camp_id;
                """,
                (
                    clean_name,
                    clean_district,
                    address.strip() if address and address.strip() else None,
                    lat_val,
                    lon_val,
                    cap_val,
                    clean_status,
                ),
            )
            cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    # Redirect to camp list upon successful creation
    return RedirectResponse(url="/camps", status_code=status.HTTP_303_SEE_OTHER)


# ── Single Camp Detail / View ─────────────────────────────────────────────

@router.get("/camps/{camp_id}", response_class=HTMLResponse)
async def get_camp(
    camp_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    Retrieve one camp by ID.
    - An officer asking for another camp gets 403.
    - Unknown ID gives 404.
    - Output can be HTML page or JSON (?format=json).
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    # Permission check: officer can only view their own camp
    if role == "camp_officer":
        if user_camp_id is None or int(user_camp_id) != camp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only view your own assigned camp.",
            )
    elif role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view camp details.",
        )

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT camp_id, name, district, address, latitude, longitude,
                       capacity, occupancy, children_count, elderly_count,
                       pregnant_count, disabled_count, damage_level,
                       access_difficulty, status, last_supply_at, created_at, updated_at
                FROM camps
                WHERE camp_id = %s;
                """,
                (camp_id,),
            )
            camp = cur.fetchone()
    finally:
        conn.close()

    if not camp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camp {camp_id} not found.",
        )

    if format and format.lower() == "json":
        return JSONResponse(content=jsonable_encoder(camp))

    return templates.TemplateResponse(
        request=request,
        name="camp_form.html",
        context={
            "request": request,
            "camp": camp,
            "errors": [],
            "user": user,
            "is_new": False,
        },
    )
