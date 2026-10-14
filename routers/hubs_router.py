"""
hubs_router.py (Owner: Member D)
================================
FastAPI router for Distribution Hub management.

Endpoints:
  - POST /hubs          : Create a relief hub (admin only)
  - GET  /hubs          : List all distribution hubs (admin, hub_coordinator)
  - GET  /hubs/{hub_id} : View details for a single hub

Contract Reference: DisasterRelief Team Guide - Sections 6.2, 10, 11 (Task D1)
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg2.extras

from database import get_conn
from deps import get_current_user, require_role

router = APIRouter(tags=["hubs"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))


@router.get("/hubs", response_class=HTMLResponse)
async def list_hubs(
    request: Request,
    format: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role("admin", "hub_coordinator")),
):
    """
    List relief distribution hubs.
    - Admins see all hubs.
    - Hub coordinators see all hubs with their own hub highlighted.
    - format=json returns raw JSON payload.
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT h.hub_id, h.name, h.district, h.address,
                       h.latitude, h.longitude, h.active, h.created_at,
                       COALESCE(COUNT(DISTINCT s.item_id), 0) AS distinct_items_stocked,
                       COALESCE(SUM(s.qty_available), 0) AS total_units_available
                FROM hubs h
                LEFT JOIN stock s ON h.hub_id = s.hub_id AND s.qty_available > 0
                GROUP BY h.hub_id, h.name, h.district, h.address, h.latitude, h.longitude, h.active, h.created_at
                ORDER BY h.hub_id ASC;
                """
            )
            hubs = cur.fetchall()
    finally:
        conn.close()

    # Convert Decimal values for JSON serialization
    serialized_hubs = []
    for h in hubs:
        item = dict(h)
        for k, v in item.items():
            if isinstance(v, Decimal):
                item[k] = float(v)
        serialized_hubs.append(item)

    if format == "json":
        return JSONResponse(content=jsonable_encoder(serialized_hubs))

    return templates.TemplateResponse(
        "hub_list.html",
        {
            "request": request,
            "hubs": serialized_hubs,
            "user": user,
            "current_user": user,
            "is_admin": user.get("role") == "admin",
            "user_hub_id": user.get("hub_id"),
        },
    )


@router.post("/hubs", response_class=HTMLResponse)
async def create_hub(
    request: Request,
    name: str = Form(...),
    district: str = Form(...),
    address: Optional[str] = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    active: bool = Form(True),
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Create a new relief distribution hub (admin only).
    Validates geographic coordinates and ensures name uniqueness.
    """
    errors = []
    cleaned_name = name.strip()
    cleaned_district = district.strip()
    cleaned_address = address.strip() if address else None

    if not cleaned_name:
        errors.append("Hub name is required.")
    if not cleaned_district:
        errors.append("District is required.")
    if not (-90.0 <= latitude <= 90.0):
        errors.append("Latitude must be between -90.0 and 90.0 degrees.")
    if not (-180.0 <= longitude <= 180.0):
        errors.append("Longitude must be between -180.0 and 180.0 degrees.")

    if errors:
        return templates.TemplateResponse(
            "hub_list.html",
            {
                "request": request,
                "hubs": [],
                "user": user,
                "current_user": user,
                "is_admin": True,
                "errors": errors,
                "form_data": {
                    "name": name,
                    "district": district,
                    "address": address,
                    "latitude": latitude,
                    "longitude": longitude,
                    "active": active,
                },
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hubs (name, district, address, latitude, longitude, active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                RETURNING hub_id;
                """,
                (cleaned_name, cleaned_district, cleaned_address, latitude, longitude, active)
            )
            hub_id = cur.fetchone()[0]
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while creating hub: {exc}",
        )
    finally:
        conn.close()

    # If client accepts JSON, return JSON
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": "created", "hub_id": hub_id, "name": cleaned_name},
        )

    return RedirectResponse(url="/hubs", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/hubs/{hub_id}")
async def get_hub_details(
    hub_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role("admin", "hub_coordinator")),
):
    """
    Returns single hub metadata and redirects to /stock?hub_id=... for inventory.
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM hubs WHERE hub_id = %s;", (hub_id,))
            hub = cur.fetchone()
    finally:
        conn.close()

    if not hub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hub #{hub_id} not found.")

    item = dict(hub)
    for k, v in item.items():
        if isinstance(v, Decimal):
            item[k] = float(v)

    if format == "json":
        return JSONResponse(content=jsonable_encoder(item))

    return RedirectResponse(url=f"/stock?hub_id={hub_id}", status_code=status.HTTP_303_SEE_OTHER)
