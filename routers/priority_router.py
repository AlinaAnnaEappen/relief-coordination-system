"""
priority_router.py (Owner: Member C)
=====================================
FastAPI router for Camp Priority Ranking operations.

Endpoints (Guide Section 10):
  - POST /priority/run     : Runs the SAW priority engine for active camps and stores results.
  - GET  /priority/latest  : Fetches or displays the newest ranking with criteria breakdowns.

Permissions: admin role required.
Reference: DisasterReliefMVP Team Guide - Section 8, 10, 11 (Task C3)
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Ensure project root is accessible
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engines.priority_engine import compute_priority, DEFAULT_SAW_WEIGHTS, DEFAULT_TIME_CAP_HOURS

# Setup Jinja2 templates directory
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))

router = APIRouter(prefix="/priority", tags=["priority"])


# --- Safe Dependency Fallbacks (Integration with Member A) ---
def get_db():
    """Acquires a PostgreSQL database connection."""
    try:
        from database import get_conn
        return get_conn()
    except ImportError:
        pass

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not configured (DATABASE_URL missing)."
        )
    return psycopg2.connect(db_url)


def get_weights_and_time_cap():
    """Loads configured SAW weights and time cap from config.py or default."""
    try:
        from config import SAW_WEIGHTS, TIME_CAP_HOURS
        return SAW_WEIGHTS, TIME_CAP_HOURS
    except ImportError:
        return DEFAULT_SAW_WEIGHTS, DEFAULT_TIME_CAP_HOURS


def get_current_admin_user():
    """Authenticates admin user (integrates with Member A's deps.py with dev bypass)."""
    try:
        from deps import require_role
        return require_role("admin")
    except ImportError:
        # Development fallback (matches Guide Section 10 fake-login switch)
        def fallback_auth():
            return {"user_id": 1, "username": "admin1", "role": "admin"}
        return fallback_auth


# --- Router Endpoints ---

@router.post("/run")
def run_priority_calculation(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin_user())
):
    """
    Executes a new priority ranking run:
    1. Loads active camps and open requests (SQL join).
    2. Runs the pure SAW calculation engine (compute_priority).
    3. Saves priority_runs and priority_scores in ONE ACID transaction.
    4. Redirects to /priority/latest for HTML clients, or returns JSON.
    """
    conn = get_db()
    weights, time_cap = get_weights_and_time_cap()
    now = datetime.now()

    try:
        with conn.cursor() as cur:
            # Guide Section 8.6 & 11 C3: SQL join with open requests (pending/partially_allocated)
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
                    detail="No active camps found to rank. Please seed camp data first."
                )

            # Map SQL rows into dicts for pure engine
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

            # Pure SAW calculation
            ranked = compute_priority(camp_dicts, weights=weights, now=now, time_cap_hours=time_cap)

            # Save in ONE transaction: priority_runs and priority_scores
            run_by_id = user.get("user_id") if isinstance(user, dict) else 1
            cur.execute("""
                INSERT INTO priority_runs (run_at, run_by, weights_json)
                VALUES (%s, %s, %s)
                RETURNING run_id;
            """, (now, run_by_id, json.dumps(weights)))
            run_id = cur.fetchone()[0]

            for item in ranked:
                cur.execute("""
                    INSERT INTO priority_scores (run_id, camp_id, score, rank, breakdown)
                    VALUES (%s, %s, %s, %s, %s);
                """, (
                    run_id,
                    item["camp_id"],
                    item["score"],
                    item["rank"],
                    json.dumps(item["breakdown"])
                ))

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

    # If requested by browser form, redirect to latest ranking view
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
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
    user: Dict[str, Any] = Depends(get_current_admin_user())
):
    """
    Retrieves the newest priority ranking results.
    Renders admin_priority.html for browser users, or returns JSON for API clients.
    """
    conn = get_db()
    run_meta = None
    scores_list = []

    try:
        with conn.cursor() as cur:
            # Fetch latest priority_run
            cur.execute("""
                SELECT pr.run_id, pr.run_at, pr.weights_json, u.full_name, u.username
                FROM priority_runs pr
                LEFT JOIN users u ON pr.run_by = u.user_id
                ORDER BY pr.run_id DESC
                LIMIT 1;
            """)
            run_row = cur.fetchone()

            if run_row:
                weights = run_row[2] if isinstance(run_row[2], dict) else json.loads(run_row[2])
                run_meta = {
                    "run_id": run_row[0],
                    "run_at": run_row[1],
                    "weights": weights,
                    "run_by": run_row[3] or run_row[4] or "Admin Control Room"
                }

                # Fetch scores for this run joined with camps and escalation status
                cur.execute("""
                    SELECT 
                        ps.rank,
                        ps.score,
                        ps.breakdown,
                        c.camp_id,
                        c.name,
                        c.district,
                        c.occupancy,
                        COALESCE(BOOL_OR(r.escalated), FALSE) AS has_escalation
                    FROM priority_scores ps
                    JOIN camps c ON ps.camp_id = c.camp_id
                    LEFT JOIN requests r 
                        ON c.camp_id = r.camp_id 
                        AND r.status IN ('pending', 'partially_allocated')
                    WHERE ps.run_id = %s
                    GROUP BY ps.rank, ps.score, ps.breakdown, c.camp_id, c.name, c.district, c.occupancy
                    ORDER BY ps.rank ASC;
                """, (run_meta["run_id"],))
                
                for r in cur.fetchall():
                    breakdown = r[2] if isinstance(r[2], dict) else json.loads(r[2])
                    scores_list.append({
                        "rank": r[0],
                        "score": float(r[1]),
                        "breakdown": breakdown,
                        "camp_id": r[3],
                        "name": r[4],
                        "district": r[5],
                        "occupancy": r[6],
                        "has_escalation": r[7]
                    })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading latest priority scores: {e}"
        )
    finally:
        conn.close()

    # Browser HTML view
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header or "text/*" in accept_header or "*/*" in accept_header:
        configured_weights, time_cap = get_weights_and_time_cap()
        return templates.TemplateResponse(
            "admin_priority.html",
            {
                "request": request,
                "user": user,
                "run": run_meta,
                "scores": scores_list,
                "configured_weights": configured_weights,
                "time_cap": time_cap,
            }
        )

    # API JSON response
    return {
        "run": run_meta,
        "ranking": scores_list
    }


# Convenience redirect
@router.get("", include_in_schema=False)
def priority_index():
    return RedirectResponse(url="/priority/latest")
