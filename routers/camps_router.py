"""
Camps Router – handles listing, viewing, creating, and updating relief camps.

Implements Task B2a (Admin side: camp list and creation) and Task B2b (Camp updates).
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


# ── Shared Validation and Save Helper for Updates ──────────────────────────

def _validate_and_save_camp_update(
    camp_id: int,
    user: dict,
    input_data: dict,
) -> tuple[Optional[dict], dict, list[str]]:
    """
    Validate and save updates to a relief camp.

    Shared between POST /camps/{camp_id}/update (HTML form) and PUT /camps/{camp_id} (JSON).
    - Checks role authorization: admins can update any camp; camp officers can update only their own camp.
    - Officers may only update operational fields: occupancy, children_count, elderly_count,
      pregnant_count, disabled_count, damage_level, access_difficulty.
    - Admin-only fields sent by officers are silently ignored.
    - Validates bounds and ensures no vulnerable subgroup count exceeds occupancy.
    - Sets updated_at = now() and preserves last_supply_at.

    Returns:
        (updated_camp_or_none, merged_form_state, list_of_error_messages)
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    # Permission check: officer can only update their own assigned camp
    if role == "camp_officer":
        if user_camp_id is None or int(user_camp_id) != camp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only update your own assigned camp.",
            )
    elif role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to update relief camps.",
        )

    # Fetch current camp record from database
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
            current_camp = cur.fetchone()
    finally:
        conn.close()

    if not current_camp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camp {camp_id} not found.",
        )

    errors: list[str] = []

    # Start with current camp data, overlaying incoming inputs for re-rendering form state
    merged_state = dict(current_camp)

    # 1. Operational fields (both officer and admin can change)
    raw_occupancy = input_data.get("occupancy", current_camp["occupancy"])
    raw_children = input_data.get("children_count", current_camp["children_count"])
    raw_elderly = input_data.get("elderly_count", current_camp["elderly_count"])
    raw_pregnant = input_data.get("pregnant_count", current_camp["pregnant_count"])
    raw_disabled = input_data.get("disabled_count", current_camp["disabled_count"])
    raw_damage = input_data.get("damage_level", current_camp["damage_level"])
    raw_access = input_data.get("access_difficulty", current_camp["access_difficulty"])

    # Keep typed values in merged_state for template re-display
    merged_state["occupancy"] = raw_occupancy
    merged_state["children_count"] = raw_children
    merged_state["elderly_count"] = raw_elderly
    merged_state["pregnant_count"] = raw_pregnant
    merged_state["disabled_count"] = raw_disabled
    merged_state["damage_level"] = raw_damage
    merged_state["access_difficulty"] = raw_access

    # Validate occupancy
    occupancy_val: Optional[int] = None
    try:
        if raw_occupancy is None or str(raw_occupancy).strip() == "":
            errors.append("Occupancy is required.")
        else:
            occupancy_val = int(raw_occupancy)
            if occupancy_val < 0:
                errors.append("Occupancy cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Occupancy must be a non-negative whole number.")

    # Validate vulnerable subgroup counts
    def parse_count(label: str, raw_val: any) -> Optional[int]:
        if raw_val is None or str(raw_val).strip() == "":
            return 0
        try:
            val = int(raw_val)
            if val < 0:
                errors.append(f"{label} cannot be negative.")
                return None
            return val
        except (ValueError, TypeError):
            errors.append(f"{label} must be a non-negative whole number.")
            return None

    children_val = parse_count("Children count", raw_children)
    elderly_val = parse_count("Elderly count", raw_elderly)
    pregnant_val = parse_count("Pregnant women count", raw_pregnant)
    disabled_val = parse_count("Persons with disabilities count", raw_disabled)

    # Validate subgroup counts do not exceed occupancy
    if occupancy_val is not None and occupancy_val >= 0:
        if children_val is not None and children_val > occupancy_val:
            errors.append("Children count cannot be greater than occupancy.")
        if elderly_val is not None and elderly_val > occupancy_val:
            errors.append("Elderly count cannot be greater than occupancy.")
        if pregnant_val is not None and pregnant_val > occupancy_val:
            errors.append("Pregnant count cannot be greater than occupancy.")
        if disabled_val is not None and disabled_val > occupancy_val:
            errors.append("Disabled count cannot be greater than occupancy.")

    # Validate damage level (1 to 5)
    damage_val: Optional[int] = None
    try:
        damage_val = int(raw_damage)
        if damage_val < 1 or damage_val > 5:
            errors.append("Damage level must be between 1 and 5.")
    except (ValueError, TypeError):
        errors.append("Damage level must be a whole number between 1 and 5.")

    # Validate access difficulty (1 to 5)
    access_val: Optional[int] = None
    try:
        access_val = int(raw_access)
        if access_val < 1 or access_val > 5:
            errors.append("Access difficulty must be between 1 and 5.")
    except (ValueError, TypeError):
        errors.append("Access difficulty must be a whole number between 1 and 5.")

    # 2. Administrative fields (only admin can change; silently ignore if submitted by officer)
    name_val = current_camp["name"]
    district_val = current_camp["district"]
    address_val = current_camp["address"]
    lat_val = current_camp["latitude"]
    lon_val = current_camp["longitude"]
    cap_val = current_camp["capacity"]
    status_val = current_camp["status"]

    if role == "admin":
        if "name" in input_data:
            raw_name = input_data["name"]
            merged_state["name"] = raw_name
            clean_name = str(raw_name).strip() if raw_name else ""
            if not clean_name:
                errors.append("Camp name is required.")
            else:
                name_val = clean_name

        if "district" in input_data:
            raw_district = input_data["district"]
            merged_state["district"] = raw_district
            clean_district = str(raw_district).strip() if raw_district else ""
            if not clean_district:
                errors.append("District is required.")
            else:
                district_val = clean_district

        if "address" in input_data:
            raw_address = input_data["address"]
            merged_state["address"] = raw_address
            address_val = str(raw_address).strip() if raw_address and str(raw_address).strip() else None

        if "latitude" in input_data:
            raw_lat = input_data["latitude"]
            merged_state["latitude"] = raw_lat
            try:
                parsed_lat = Decimal(str(raw_lat).strip())
                if parsed_lat < Decimal("-90") or parsed_lat > Decimal("90"):
                    errors.append("Latitude must be between -90.0 and 90.0 degrees.")
                else:
                    lat_val = parsed_lat
            except Exception:
                errors.append("Latitude must be a valid number.")

        if "longitude" in input_data:
            raw_lon = input_data["longitude"]
            merged_state["longitude"] = raw_lon
            try:
                parsed_lon = Decimal(str(raw_lon).strip())
                if parsed_lon < Decimal("-180") or parsed_lon > Decimal("180"):
                    errors.append("Longitude must be between -180.0 and 180.0 degrees.")
                else:
                    lon_val = parsed_lon
            except Exception:
                errors.append("Longitude must be a valid number.")

        if "capacity" in input_data:
            raw_cap = input_data["capacity"]
            merged_state["capacity"] = raw_cap
            if raw_cap is None or str(raw_cap).strip() == "":
                cap_val = None
            else:
                try:
                    parsed_cap = int(raw_cap)
                    if parsed_cap < 0:
                        errors.append("Capacity cannot be negative.")
                    else:
                        cap_val = parsed_cap
                except (ValueError, TypeError):
                    errors.append("Capacity must be a non-negative whole number (or left empty).")

        if "status" in input_data:
            raw_status = input_data["status"]
            merged_state["status"] = raw_status
            clean_status = str(raw_status).strip().lower() if raw_status else ""
            if clean_status not in ("active", "closed"):
                errors.append("Status must be either 'active' or 'closed'.")
            else:
                status_val = clean_status

    # If any validation errors occurred, abort save and return errors
    if errors:
        return None, merged_state, errors

    # Save changes to database; sets updated_at = now() and leaves last_supply_at intact
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if role == "admin":
                cur.execute(
                    """
                    UPDATE camps
                    SET name = %s,
                        district = %s,
                        address = %s,
                        latitude = %s,
                        longitude = %s,
                        capacity = %s,
                        status = %s,
                        occupancy = %s,
                        children_count = %s,
                        elderly_count = %s,
                        pregnant_count = %s,
                        disabled_count = %s,
                        damage_level = %s,
                        access_difficulty = %s,
                        updated_at = now()
                    WHERE camp_id = %s
                    RETURNING *;
                    """,
                    (
                        name_val,
                        district_val,
                        address_val,
                        lat_val,
                        lon_val,
                        cap_val,
                        status_val,
                        occupancy_val,
                        children_val or 0,
                        elderly_val or 0,
                        pregnant_val or 0,
                        disabled_val or 0,
                        damage_val,
                        access_val,
                        camp_id,
                    ),
                )
            else:
                # Camp officer update: only operational fields
                cur.execute(
                    """
                    UPDATE camps
                    SET occupancy = %s,
                        children_count = %s,
                        elderly_count = %s,
                        pregnant_count = %s,
                        disabled_count = %s,
                        damage_level = %s,
                        access_difficulty = %s,
                        updated_at = now()
                    WHERE camp_id = %s
                    RETURNING *;
                    """,
                    (
                        occupancy_val,
                        children_val or 0,
                        elderly_val or 0,
                        pregnant_val or 0,
                        disabled_val or 0,
                        damage_val,
                        access_val,
                        camp_id,
                    ),
                )
            updated_camp = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    return updated_camp, merged_state, []


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


# ── Camp Update Form Page (Officer own camp, or Admin) ────────────────────

@router.get("/camps/{camp_id}/update", response_class=HTMLResponse)
async def get_camp_update_page(
    camp_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Display the camp update form.
    - Admins can update any camp.
    - Camp officers can only update their own assigned camp (403 otherwise).
    - Unknown camp ID returns 404.
    Declared before /camps/{camp_id} to avoid any route ambiguity.
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    if role == "camp_officer":
        if user_camp_id is None or int(user_camp_id) != camp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only update your own assigned camp.",
            )
    elif role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to update relief camps.",
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

    return templates.TemplateResponse(
        request=request,
        name="camp_update.html",
        context={
            "request": request,
            "camp": camp,
            "errors": [],
            "user": user,
        },
    )


# ── Camp Update Form Submission (HTML) ────────────────────────────────────

@router.post("/camps/{camp_id}/update", response_class=HTMLResponse)
async def post_camp_update(
    camp_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Process camp update form submission from camp_update.html.
    Uses shared validation and save logic.
    On success: redirects (303) to /camps.
    On failure: re-renders camp_update.html with status 422 and friendly errors.
    """
    form_data = await request.form()
    input_dict = dict(form_data)

    updated_camp, form_state, errors = _validate_and_save_camp_update(camp_id, user, input_dict)

    if errors:
        return templates.TemplateResponse(
            request=request,
            name="camp_update.html",
            context={
                "request": request,
                "camp": form_state,
                "errors": errors,
                "user": user,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return RedirectResponse(url="/camps", status_code=status.HTTP_303_SEE_OTHER)


# ── Camp Update API Endpoint (PUT JSON, Guide Section 10) ──────────────────

@router.put("/camps/{camp_id}")
async def put_camp(
    camp_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Update camp details via JSON (Guide Section 10).
    Uses the exact same validation and save logic as POST /camps/{camp_id}/update.
    On success: returns updated camp record as JSON.
    On validation failure: returns status 422 with list of errors.
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            input_dict = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload.",
            )
    else:
        # Fallback if form-encoded data is sent to PUT
        form_data = await request.form()
        input_dict = dict(form_data)

    updated_camp, form_state, errors = _validate_and_save_camp_update(camp_id, user, input_dict)

    if errors:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"errors": errors, "detail": errors},
        )

    return JSONResponse(content=jsonable_encoder(updated_camp))


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


# ── Camp Allocations / "What is Coming" (Task B4) ──────────────────────────

@router.get("/camps/{camp_id}/allocations", response_class=HTMLResponse)
async def get_camp_allocations(
    camp_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    Retrieve incoming supplies and allocations for a camp (Task B4).
    - Admins can view allocations for any camp.
    - Camp officers can view allocations only for their own camp (403 otherwise).
    - Supports ?format=json to return allocations list as JSON.
    """
    role = user.get("role")
    user_camp_id = user.get("camp_id")

    if role == "camp_officer":
        if user_camp_id is None or int(user_camp_id) != camp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only view allocations for your own assigned camp.",
            )
    elif role not in ("admin", "hub_coordinator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view camp allocations.",
        )

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Fetch camp info
            cur.execute(
                """
                SELECT camp_id, name, district, status, last_supply_at
                FROM camps
                WHERE camp_id = %s;
                """,
                (camp_id,),
            )
            camp = cur.fetchone()
            if not camp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Camp {camp_id} not found.",
                )

            # 2. Fetch allocations with item, hub, and request metadata
            cur.execute(
                """
                SELECT 
                    a.allocation_id,
                    a.run_id,
                    a.camp_id,
                    a.hub_id,
                    a.item_id,
                    a.request_item_id,
                    a.qty,
                    a.status AS allocation_status,
                    a.created_at AS allocated_at,
                    i.item_code,
                    i.name AS item_name,
                    i.group_code,
                    i.unit,
                    i.emergency_eligible,
                    h.name AS hub_name,
                    h.district AS hub_district,
                    r.request_id,
                    r.status AS request_status
                FROM allocations a
                JOIN items i ON a.item_id = i.item_id
                JOIN hubs h ON a.hub_id = h.hub_id
                LEFT JOIN request_items ri ON a.request_item_id = ri.request_item_id
                LEFT JOIN requests r ON ri.request_id = r.request_id
                WHERE a.camp_id = %s
                ORDER BY a.created_at DESC, a.allocation_id DESC;
                """,
                (camp_id,),
            )
            allocations = cur.fetchall()
    finally:
        conn.close()

    if format and format.lower() == "json":
        return JSONResponse(content=jsonable_encoder(allocations))

    return templates.TemplateResponse(
        request=request,
        name="camp_allocations.html",
        context={
            "request": request,
            "camp": camp,
            "allocations": allocations,
            "user": user,
        },
    )


@router.get("/allocation")
async def get_allocations_query(
    request: Request,
    camp_id: Optional[int] = Query(None),
    format: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    Query allocations matching Guide Section 10 contract: GET /allocation?camp_id=
    Delegates to get_camp_allocations for the specified camp.
    """
    target_camp_id = camp_id
    if target_camp_id is None and user.get("role") == "camp_officer" and user.get("camp_id"):
        target_camp_id = int(user["camp_id"])

    if target_camp_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="camp_id parameter is required.",
        )

    return await get_camp_allocations(
        camp_id=target_camp_id,
        request=request,
        format=format,
        user=user,
    )

