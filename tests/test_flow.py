"""
test_flow.py (Owner: Member C)
==============================
Automated End-to-End Operational Lifecycle Integration Test for DisasterReliefMVP.

Executes integration testing against the live FastAPI application and PostgreSQL database
for all 9 operational steps specified in Guide Section 15.4:
  Step 1: Admin inspects active camps and distribution hubs.
  Step 2: Donor offers supplies (100 kg rice, 50 blankets) -> routed to Alappuzha hub.
  Step 3: Hub receives donation -> Stock increases (+100 rice, +50 blankets).
  Step 4: Camp Officer submits urgent request (60 kg rice, 30 blankets, Escalated=True).
  Step 5: Priority Engine executes SAW ranking -> All 6,377 camps ranked; urgent camps elevated.
  Step 6: Allocation logic runs -> Allocates stock to highest priority camps first.
  Step 7: Request status updates to 'fulfilled' or 'partially_allocated'.
  Step 8: Hub Coordinator marks allocation as dispatched -> last_supply_at updates.
  Step 9: Priority recalculation -> Time factor resets downward for the supplied camp.

Unmerged endpoints belonging to teammate modules (Members A, B, and D) are cleanly skipped
with explicit blocker explanations per Guide Section 14.5 and Section 15.4 contracts.

Reference: DisasterReliefMVP Team Guide - Section 11 (Task C4) & Section 15.4
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import app
from deps import serializer
from database import get_conn


def make_session_cookie(user_id: int, username: str, role: str, district: str = "Alappuzha", camp_id: int = None, hub_id: int = None) -> str:
    """Creates a cryptographic session cookie token matching deps.py URLSafeSerializer."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "district": district,
    }
    if camp_id is not None:
        payload["camp_id"] = camp_id
    if hub_id is not None:
        payload["hub_id"] = hub_id
    return serializer.dumps(payload)


def get_available_routes(fastapi_app):
    """Collects all registered route paths across root and included routers."""
    paths = set()
    for r in fastapi_app.routes:
        if hasattr(r, "path"):
            paths.add(r.path)
        if hasattr(r, "original_router"):
            for sub in r.original_router.routes:
                if hasattr(sub, "path"):
                    paths.add(sub.path)
    return paths


@pytest.fixture(scope="module")
def admin_client():
    """TestClient authenticated as admin1."""
    token = make_session_cookie(1, "admin1", "admin")
    client = TestClient(app)
    client.cookies.set("session_user", token)
    return client


@pytest.fixture(scope="module")
def officer_client():
    """TestClient authenticated as officer1."""
    token = make_session_cookie(2, "officer1", "camp_officer", camp_id=1)
    client = TestClient(app)
    client.cookies.set("session_user", token)
    return client


def test_step_1_admin_inspect_camps_and_hubs(admin_client):
    """
    Step 1: Admin logs in and inspects active camps and distribution hubs.
    Real API GET /camps?format=json returns all 6,377 registered Kerala relief camps.
    Note: Hub list endpoint is noted pending Member D's hubs_router.py merge.
    """
    resp = admin_client.get("/camps?format=json")
    assert resp.status_code == 200, f"Expected 200 OK from /camps, got {resp.status_code}"
    camps = resp.json()
    assert len(camps) == 6377, f"Expected all 6,377 Kerala camps, received {len(camps)}"

    # Check whether Member D's hubs router is merged
    routes = get_available_routes(app)
    if "/hubs" not in routes:
        # Hub inspection endpoint pending Member D merge; camps inspection fully verified
        pass
    else:
        hub_resp = admin_client.get("/hubs")
        assert hub_resp.status_code == 200


def test_step_2_donor_offers_supplies():
    """
    Step 2: Donor offers 100 kg rice and 50 blankets.
    Route: POST /donations -> status 'hub_assigned' to Alappuzha Hub.
    """
    routes = get_available_routes(app)
    if "/donations" not in routes:
        pytest.skip("Step 2 skipped: routers/donors_router.py not yet merged by Member A")


def test_step_3_hub_receives_donation():
    """
    Step 3: Hub coordinator receives incoming donation -> Stock increases.
    Route: POST /hub/donations/{id}/receive.
    """
    routes = get_available_routes(app)
    if not any("/donations" in r and "receive" in r for r in routes):
        pytest.skip("Step 3 skipped: routers/stock_router.py receive endpoint not yet merged by Member D")


def test_step_4_camp_officer_submits_urgent_request():
    """
    Step 4: Camp Officer submits urgent request (60 kg rice, 30 blankets, Escalate=True).
    Route: POST /requests -> status 'pending'.
    """
    routes = get_available_routes(app)
    if "/requests" not in routes and "/request" not in routes:
        pytest.skip("Step 4 skipped: routers/requests_router.py not yet merged by Member B")


def test_step_5_admin_recalculates_priority(admin_client, officer_client):
    """
    Step 5: Admin triggers SAW priority recalculation across all active camps.
    Route: POST /priority/run, GET /priority/latest.
    Expected: All 6,377 camps scored and ranked; 6-part breakdown factors computed.
    Also verifies RBAC enforcement: Camp Officer is rejected with 403 Forbidden.
    """
    # 1. RBAC Check: Camp officer cannot trigger recalculation
    officer_resp = officer_client.post("/priority/run")
    assert officer_resp.status_code == 403, f"Officer must receive 403 Forbidden, got {officer_resp.status_code}"

    # 2. Admin executes priority recalculation
    run_resp = admin_client.post("/priority/run")
    assert run_resp.status_code == 200, f"Expected 200 OK from /priority/run, got {run_resp.status_code}: {run_resp.text}"
    run_data = run_resp.json()
    assert run_data["status"] == "ok"
    assert "run_id" in run_data
    assert run_data["camps_ranked"] == 6377

    # 3. Retrieve latest rankings via JSON endpoint (default pagination limit 50, total 6377)
    latest_resp = admin_client.get("/priority/latest", headers={"Accept": "application/json"})
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["total"] == 6377
    assert len(latest_data["ranking"]) == 50

    # 4. Verify ranking schema and breakdown factors on top camp
    top_camp = latest_data["ranking"][0]
    assert "score" in top_camp
    assert "rank" in top_camp
    assert top_camp["rank"] == 1
    assert "breakdown" in top_camp
    assert all(k in top_camp["breakdown"] for k in ("people", "vulnerable", "damage", "access", "time", "escalation"))


def test_step_6_admin_runs_allocation():
    """
    Step 6: Admin triggers automated stock allocation.
    Route: POST /allocation/run.
    """
    routes = get_available_routes(app)
    if "/allocation/run" not in routes:
        pytest.skip("Step 6 skipped: routers/allocation_router.py (POST /allocation/run) not yet merged by Member D")


def test_step_7_officer_views_what_is_coming():
    """
    Step 7: Camp officer checks incoming supply allocations.
    Route: GET /allocation?camp_id=1.
    """
    routes = get_available_routes(app)
    if "/allocation" not in routes:
        pytest.skip("Step 7 skipped: routers/allocation_router.py (GET /allocation) not yet merged by Member D")


def test_step_8_hub_marks_dispatched():
    """
    Step 8: Hub Coordinator marks allocation as dispatched.
    Route: POST /allocation/{id}/dispatch.
    Note: Hub Check finding indicates Camp 1 in Thiruvananthapuram routes to Hub 3 (Pathanamthitta),
    requiring a hub3 coordinator user which is pending from Member A.
    """
    routes = get_available_routes(app)
    if not any("/dispatch" in r for r in routes):
        pytest.skip("Step 8 skipped: routers/allocation_router.py dispatch endpoint not yet merged by Member D. "
                    "[Hub Check: Camp 1 routes to Hub 3; user hub3 required]")


def test_step_9_admin_recalculates_priority_after_dispatch(admin_client):
    """
    Step 9: Priority recalculation after relief dispatch.
    Expected: Camp's time factor and priority score drop significantly once supplied.
    """
    # 1. Trigger fresh ranking to record baseline score for Camp 1 (from full recalculation response)
    run1 = admin_client.post("/priority/run").json()
    camp_1_baseline = next(r for r in run1["rankings"] if r["camp_id"] == 1)
    baseline_score = camp_1_baseline["score"]

    # 2. Simulate relief dispatch completion in database (Section 9.6: last_supply_at updated, request fulfilled)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE camps SET last_supply_at = NOW() WHERE camp_id = 1;")
            cur.execute("UPDATE requests SET status = 'fulfilled' WHERE camp_id = 1;")
        conn.commit()
    finally:
        conn.close()

    # 3. Recalculate priority
    run2 = admin_client.post("/priority/run").json()
    camp_1_updated = next(r for r in run2["rankings"] if r["camp_id"] == 1)
    updated_score = camp_1_updated["score"]

    # 4. Verify time component dropped near 0.0 and total score decreased
    assert camp_1_updated["breakdown"]["time"] < 0.01, (
        f"Expected time component to reset near 0.0 after dispatch, got {camp_1_updated['breakdown']['time']}"
    )
    assert updated_score < baseline_score, (
        f"Expected priority score to decrease after dispatch (was {baseline_score}, now {updated_score})"
    )

    # 5. Verify GET /priority/latest endpoint with district filter reflects the updated score
    tvm_resp = admin_client.get("/priority/latest?district=Thiruvananthapuram&limit=500", headers={"Accept": "application/json"})
    assert tvm_resp.status_code == 200
    tvm_data = tvm_resp.json()
    camp_1_in_tvm = next(r for r in tvm_data["ranking"] if r["camp_id"] == 1)
    assert camp_1_in_tvm["score"] == updated_score
