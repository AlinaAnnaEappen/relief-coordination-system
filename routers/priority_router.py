"""
priority_router.py (Owner: Member C)
=====================================
FastAPI router for Camp Priority Ranking operations.

Endpoints:
  - POST /priority/run     : Runs the SAW priority engine for active camps and stores results.
  - GET  /priority/latest  : Fetches or displays the newest ranking with criteria breakdowns.

Permissions: admin role required.
Reference: DisasterRelief Team Guide - Sections 8, 10, 11 (Task C3)
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from psycopg2.extras import execute_values, RealDictCursor

# Direct contract imports from project modules (no fallbacks)
from deps import require_role
from database import get_conn
from config import SAW_WEIGHTS, TIME_CAP_HOURS
from engines.priority_engine import compute_priority

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))

router = APIRouter(prefix="/priority", tags=["priority"])


@router.post("/run")
def run_priority_calculation(
    request: Request,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    POST /priority/run:
    1. Loads active camps plus has_escalation (BOOL_OR over open requests: pending and partially_allocated)
       and oldest_open_request_at (MIN) with a LEFT JOIN.
    2. Calls compute_priority with datetime.now(timezone.utc) and config weights.
    3. Saves priority_runs (with weights_json) and all priority_scores in ONE transaction
       using execute_values, rolling back on any error.
    4. Browser form posts get a 303 redirect to /priority/latest; other clients get JSON.
    """
    conn = get_conn()
    now = datetime.now(timezone.utc)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.camp_id,
                    c.name,
                    c.district,
                    c.occupancy,
                    c.children_count,
                    c.elderly_count,
                    c.pregnant_count,
                    c.disabled_count,
                    c.damage_level,
                    c.access_difficulty,
                    c.last_supply_at,
                    c.created_at,
                    COALESCE(BOOL_OR(r.escalated), FALSE) AS has_escalation,
                    MIN(r.created_at) AS oldest_open_request_at
                FROM camps c
                LEFT JOIN requests r 
                    ON c.camp_id = r.camp_id 
                    AND r.status IN ('pending', 'partially_allocated')
                WHERE c.status = 'active'
                GROUP BY 
                    c.camp_id, c.name, c.district, c.occupancy, c.children_count, c.elderly_count,
                    c.pregnant_count, c.disabled_count, c.damage_level, c.access_difficulty,
                    c.last_supply_at, c.created_at
                ORDER BY c.camp_id;
            """)
            rows = cur.fetchall()

            if not rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active camps found to rank."
                )

            camp_dicts = []
            for r in rows:
                camp_dicts.append({
                    "camp_id": r[0],
                    "name": r[1],
                    "district": r[2],
                    "occupancy": r[3],
                    "children_count": r[4],
                    "elderly_count": r[5],
                    "pregnant_count": r[6],
                    "disabled_count": r[7],
                    "damage_level": r[8],
                    "access_difficulty": r[9],
                    "last_supply_at": r[10],
                    "created_at": r[11],
                    "has_escalation": r[12],
                    "oldest_open_request_at": r[13],
                })

            # Pure mathematical SAW calculation
            ranked = compute_priority(
                camp_dicts,
                weights=SAW_WEIGHTS,
                now=now,
                time_cap_hours=TIME_CAP_HOURS
            )

            # Save in ONE transaction: priority_runs and all priority_scores
            run_by_id = user.get("user_id") if isinstance(user, dict) else 1
            cur.execute("""
                INSERT INTO priority_runs (run_at, run_by, weights_json)
                VALUES (%s, %s, %s)
                RETURNING run_id;
            """, (now, run_by_id, json.dumps(SAW_WEIGHTS)))
            run_id = cur.fetchone()[0]

            score_values = [
                (run_id, item["camp_id"], item["score"], item["rank"], json.dumps(item["breakdown"]))
                for item in ranked
            ]
            execute_values(
                cur,
                """
                INSERT INTO priority_scores (run_id, camp_id, score, rank, breakdown)
                VALUES %s;
                """,
                score_values
            )

        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate and store priority ranking: {e}"
        )
    finally:
        conn.close()

    # Browser form posts get a 303 redirect to /priority/latest; other clients get JSON
    accept_header = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or ("text/html" in accept_header and "application/json" not in accept_header):
        return RedirectResponse(url="/priority/latest", status_code=status.HTTP_303_SEE_OTHER)

    return {
        "status": "ok",
        "run_id": run_id,
        "run_at": now.isoformat(),
        "camps_ranked": len(ranked),
        "rankings": ranked
    }


@router.get("/latest")
def get_latest_priority(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    district: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    GET /priority/latest:
    - HTML only when Accept contains text/html (and format != json)
    - JSON for Accept: application/json, ?format=json and any other client
    - Parameters: limit (default 50, max 500), offset, district
    - JSON shape: {run, ranking, total, limit, offset}
    - Escalation flag read from stored breakdown so the page shows what the run used.
    """
    conn = get_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch latest priority run
            cur.execute("""
                SELECT pr.run_id, pr.run_at, pr.run_by, pr.weights_json, u.username AS run_by_username
                FROM priority_runs pr
                LEFT JOIN users u ON pr.run_by = u.user_id
                ORDER BY pr.run_at DESC
                LIMIT 1;
            """)
            run_meta = cur.fetchone()

            if not run_meta:
                # No run exists yet
                accept_header = request.headers.get("accept", "")
                if "text/html" in accept_header and format != "json":
                    return templates.TemplateResponse(
                        request=request,
                        name="admin_priority.html",
                        context={
                            "run": None,
                            "ranking": [],
                            "total": 0,
                            "limit": limit,
                            "offset": offset,
                            "district": district,
                            "districts": [],
                            "user": user,
                            "weights": SAW_WEIGHTS,
                        }
                    )
                return {
                    "run": None,
                    "ranking": [],
                    "total": 0,
                    "limit": limit,
                    "offset": offset
                }

            run_id = run_meta["run_id"]

            # Parse weights_json if string
            if isinstance(run_meta["weights_json"], str):
                run_meta["weights_json"] = json.loads(run_meta["weights_json"])

            # 2. Get distinct districts for dropdown filter
            cur.execute("SELECT DISTINCT district FROM camps ORDER BY district;")
            all_districts = [r["district"] for r in cur.fetchall()]

            # 3. Base count query
            count_sql = """
                SELECT COUNT(*) AS total
                FROM priority_scores ps
                JOIN camps c ON ps.camp_id = c.camp_id
                WHERE ps.run_id = %s
            """
            params = [run_id]
            if district:
                count_sql += " AND c.district = %s"
                params.append(district)

            cur.execute(count_sql, params)
            total = cur.fetchone()["total"]

            # 4. Fetch ranked camps joined with camps metadata
            data_sql = """
                SELECT 
                    ps.score_id,
                    ps.run_id,
                    ps.camp_id,
                    ps.score,
                    ps.rank,
                    ps.breakdown,
                    c.name AS camp_name,
                    c.district,
                    c.occupancy,
                    c.capacity,
                    c.damage_level,
                    c.access_difficulty,
                    c.last_supply_at
                FROM priority_scores ps
                JOIN camps c ON ps.camp_id = c.camp_id
                WHERE ps.run_id = %s
            """
            data_params = [run_id]
            if district:
                data_sql += " AND c.district = %s"
                data_params.append(district)

            data_sql += " ORDER BY ps.rank ASC LIMIT %s OFFSET %s;"
            data_params.extend([limit, offset])

            cur.execute(data_sql, data_params)
            rows = cur.fetchall()

            # Process breakdown and escalation flag
            ranking_list = []
            for r in rows:
                bd = r["breakdown"]
                if isinstance(bd, str):
                    bd = json.loads(bd)
                
                # Escalation flag from stored breakdown (1.0 = escalated)
                has_esc = float(bd.get("escalation", 0.0)) > 0.0

                ranking_list.append({
                    "score_id": r["score_id"],
                    "camp_id": r["camp_id"],
                    "camp_name": r["camp_name"],
                    "district": r["district"],
                    "score": float(r["score"]),
                    "rank": r["rank"],
                    "breakdown": bd,
                    "has_escalation": has_esc,
                    "occupancy": r["occupancy"],
                    "capacity": r["capacity"],
                    "damage_level": r["damage_level"],
                    "access_difficulty": r["access_difficulty"],
                    "last_supply_at": r["last_supply_at"].isoformat() if r["last_supply_at"] else None,
                })

    finally:
        conn.close()

    # Determine response format
    accept_header = request.headers.get("accept", "")
    is_html = ("text/html" in accept_header) and (format != "json")

    if is_html:
        context = {
            "run": {
                "run_id": run_meta["run_id"],
                "run_at": run_meta["run_at"],
                "run_by": run_meta["run_by_username"] or "admin1",
                "weights": run_meta["weights_json"],
            },
            "ranking": ranking_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "district": district,
            "districts": all_districts,
            "user": user,
            "prev_offset": max(0, offset - limit) if offset > 0 else None,
            "next_offset": offset + limit if (offset + limit) < total else None,
            "page_start": offset + 1 if total > 0 else 0,
            "page_end": min(offset + limit, total),
        }
        return templates.TemplateResponse(
            request=request,
            name="admin_priority.html",
            context=context
        )

    return {
        "run": {
            "run_id": run_meta["run_id"],
            "run_at": run_meta["run_at"].isoformat(),
            "run_by": run_meta["run_by_username"] or "admin1",
            "weights": run_meta["weights_json"],
        },
        "ranking": ranking_list,
        "total": total,
        "limit": limit,
        "offset": offset
    }
