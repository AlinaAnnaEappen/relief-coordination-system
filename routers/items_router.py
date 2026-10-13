"""
Item Catalog router – GET /items (HTML and JSON).

Data source: reads seed/seed_items.csv through get_items().
When the database exists, only get_items() needs to change.
"""

import csv
import os
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Resolve paths relative to the project root (one level up from routers/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CSV_PATH = _PROJECT_ROOT / "seed" / "seed_items.csv"

templates = Jinja2Templates(directory=str(_PROJECT_ROOT / "templates"))

# ── Group ordering and display names ─────────────────────────────────────

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


# ── Data access ──────────────────────────────────────────────────────────

def _parse_bool(value: str) -> bool:
    """Accept yes/no/true/false in any capitalisation → Python bool."""
    return value.strip().lower() in ("yes", "true")


def get_items() -> list[dict]:
    """
    Read the item catalog from the seed CSV.

    Returns a list of dicts with keys matching the CSV columns.
    `emergency_eligible` is normalised to a Python bool.

    TODO: swap this to read from the database once Member A's models exist.
    """
    items: list[dict] = []
    with open(_CSV_PATH, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Skip blank trailing rows
            if not row.get("item_code", "").strip():
                continue
            row["emergency_eligible"] = _parse_bool(row.get("emergency_eligible", "no"))
            items.append(row)
    return items


# ── Helpers ──────────────────────────────────────────────────────────────

def _group_order_key(item: dict) -> int:
    """Return a sort key so core groups come first, then extended, in the
    canonical order defined by ALL_GROUP_CODES."""
    code = item.get("group_code", "")
    try:
        return ALL_GROUP_CODES.index(code)
    except ValueError:
        return len(ALL_GROUP_CODES)  # unknown codes go last


def _group_items(items: list[dict]) -> OrderedDict:
    """Group items by group_code, preserving canonical ordering."""
    sorted_items = sorted(items, key=_group_order_key)
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for item in sorted_items:
        code = item["group_code"]
        grouped.setdefault(code, []).append(item)
    return grouped


# ── Route ────────────────────────────────────────────────────────────────

# admin add/edit comes after the database and login exist


@router.get("/items", response_class=HTMLResponse)
async def list_items(
    request: Request,
    group_code: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    group_kind: Optional[str] = Query(None),
    emergency_only: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
):
    """
    Show the item catalog.

    Filters (all optional, via query string):
        group_code / category  – e.g. FW, CB  (category is an alias)
        group_kind             – "core" or "extended"
        emergency_only         – "true" to show only emergency-eligible items

    Add ?format=json to get the filtered result as JSON instead of HTML.
    """
    items = get_items()

    # ── Apply filters ────────────────────────────────────────────────
    effective_group = group_code or category
    if effective_group:
        gc = effective_group.upper()
        items = [i for i in items if i["group_code"] == gc]

    if group_kind:
        gk = group_kind.lower()
        items = [i for i in items if i.get("group_kind", "").lower() == gk]

    if emergency_only and emergency_only.lower() in ("true", "yes", "1"):
        items = [i for i in items if i["emergency_eligible"] is True]

    # ── JSON response ────────────────────────────────────────────────
    if format and format.lower() == "json":
        return JSONResponse(content=items)

    # ── Prepare template context ─────────────────────────────────────
    grouped = _group_items(items)

    total = len(items)
    emergency_count = sum(1 for i in items if i["emergency_eligible"] is True)
    approval_count = sum(
        1 for i in items if i.get("requires_approval", "").lower() in ("yes", "true")
    )

    return templates.TemplateResponse(
        request=request,
        name="items.html",
        context={
            "grouped": grouped,
            "total": total,
            "emergency_count": emergency_count,
            "approval_count": approval_count,
            "group_names": GROUP_FULL_NAMES,
            "core_codes": CORE_GROUP_CODES,
            "extended_codes": EXTENDED_GROUP_CODES,
            "all_codes": ALL_GROUP_CODES,
            # Echo current filter values back to the form
            "sel_group": effective_group or "",
            "sel_kind": group_kind or "",
            "sel_emergency": emergency_only or "",
        },
    )