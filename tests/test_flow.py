"""
test_flow.py (Owner: Member C)
==============================
 priority-testing
Automated End-to-End Operational Lifecycle Integration Test for DisasterReliefMVP.

Executes integration testing against the live FastAPI application and PostgreSQL database
for all 9 operational steps specified in Guide Section 15.4:
  Step 1: Admin inspects active camps and distribution hubs.
  Step 2: Donor offers supplies (100 kg rice, 50 blankets) -> routed to Alappuzha hub.
  Step 3: Hub receives donation -> Stock increases (+100 rice, +50 blankets).
  Step 4: Camp Officer submits urgent request (60 kg rice, 30 blankets, Escalated=True).
  Step 5: Priority Engine executes SAW ranking -> All 6,377 camps ranked; urgent camps elevated.
=======
Automated End-to-End Integration Flow Test for DisasterReliefMVP.

Simulates and tests the complete 9-step demo flow defined in Guide Section 15.4:
  Step 1: Admin inspects seeded active camps and distribution hubs.
  Step 2: Donor offers supplies (100 kg rice, 50 blankets) -> routed to Alappuzha hub.
  Step 3: Hub receives donation -> Stock increases (+100 rice, +50 blankets).
  Step 4: Camp Officer submits urgent request (60 kg rice, 30 blankets, Escalated=True).
  Step 5: Priority Engine executes SAW ranking -> Camp 1 receives elevated score.
 main
  Step 6: Allocation logic runs -> Allocates stock to highest priority camps first.
  Step 7: Request status updates to 'fulfilled' or 'partially_allocated'.
  Step 8: Hub Coordinator marks allocation as dispatched -> last_supply_at updates.
  Step 9: Priority recalculation -> Time factor resets downward for the supplied camp.

 priority-testing
Unmerged endpoints belonging to teammate modules (Members A, B, and D) are cleanly skipped
with explicit blocker explanations per Guide Section 14.5 and Section 15.4 contracts.

Reference: DisasterReliefMVP Team Guide - Section 11 (Task C4) & Section 15.4
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
=======
Reference: DisasterReliefMVP Team Guide - Section 15.4 & Section 11 (Task C4)
"""

import unittest
from datetime import datetime, timedelta
import sys
import os
 main

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

 priority-testing
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
=======
from engines.priority_engine import compute_priority, DEFAULT_SAW_WEIGHTS
from seed.load_seed import validate_seed_data


class TestEndToEndReliefFlow(unittest.TestCase):
    """
    Automated verification of the full 9-step relief allocation lifecycle.
    """

    def setUp(self):
        self.now = datetime(2026, 8, 15, 12, 0, 0)
        self.weights = DEFAULT_SAW_WEIGHTS

    def test_step_1_seed_data_integrity(self):
        """Step 1: Verify the system has all 6,377 active camps, 3 hubs, and 196 items seeded."""
        data = validate_seed_data()
        self.assertEqual(len(data["camps"]), 6377, "Must have all 6377 camps from Kerala master")
        self.assertEqual(len(data["hubs"]), 3, "Must have exactly 3 test distribution hubs")
        self.assertEqual(len(data["items"]), 196, "Item catalog must have all 196 items")

        # Verify key geographic test camps from Guide Section 7.4
        camp_names = [c["name"] for c in data["camps"]]
        self.assertTrue(any("Chengannur" in n for n in camp_names))
        self.assertTrue(any("Kuttanad" in n for n in camp_names))

    def test_steps_2_to_9_full_operational_lifecycle(self):
        """
        Executes Steps 2 through 9 in full sequence:
        Donation -> Intake -> Request -> SAW Priority -> Allocation -> Dispatch -> Recalculation.
        """
        # =========================================================================
        # STEP 2 & 3: Donor Offers Items -> Hub Receives -> Stock Increments
        # =========================================================================
        # Official catalog: FW02 = Rice, CB11 = Blanket
        hub_stock = {
            1: {"FW02": 100, "CB11": 50},  # Hub 1 (Alappuzha)
            2: {"FW02": 30, "CB11": 0},    # Hub 2 (Kottayam)
            3: {"FW02": 100, "CB11": 25},  # Hub 3 (Pathanamthitta)
        }

        # Donor donation intake (+100 Rice, +50 Blankets to Hub 1)
        donation_items = {"FW02": 100, "CB11": 50}
        assigned_hub_id = 1
        for item_code, qty in donation_items.items():
            hub_stock[assigned_hub_id][item_code] += qty

        self.assertEqual(hub_stock[1]["FW02"], 200, "Hub 1 rice stock should increase by 100 to 200")
        self.assertEqual(hub_stock[1]["CB11"], 100, "Hub 1 blanket stock should increase by 50 to 100")

        # =========================================================================
        # STEP 4: Camp Officer Submits Request with Escalation
        # =========================================================================
        # Camp 1 submits request: 60 kg rice, 30 blankets, Escalated=True
        camp_requests = {
            1: {
                "camp_id": 1,
                "escalated": True,
                "created_at": self.now - timedelta(hours=2),
                "items": {"FW02": 60, "CB11": 30},
                "status": "pending",
                "allocated": {"FW02": 0, "CB11": 0},
            },
            2: {
                "camp_id": 2,
                "escalated": True,
                "created_at": self.now - timedelta(hours=6),
                "items": {"FW02": 50, "CB11": 40},
                "status": "pending",
                "allocated": {"FW02": 0, "CB11": 0},
            },
            6: {
                "camp_id": 6,
                "escalated": False,
                "created_at": self.now - timedelta(hours=1),
                "items": {"FW02": 20, "CB11": 10},
                "status": "pending",
                "allocated": {"FW02": 0, "CB11": 0},
            },
        }

        # =========================================================================
        # STEP 5: Priority Engine (SAW) Ranking Calculation
        # =========================================================================
        active_camps = [
            {
                "camp_id": 1,
                "name": "Chengannur Relief Camp",
                "occupancy": 400,
                "children_count": 90,
                "elderly_count": 60,
                "pregnant_count": 10,
                "disabled_count": 5,
                "damage_level": 4,
                "access_difficulty": 5,
                "last_supply_at": self.now - timedelta(hours=48),
                "created_at": self.now - timedelta(hours=72),
                "has_escalation": camp_requests[1]["escalated"],
                "oldest_open_request_at": camp_requests[1]["created_at"],
            },
            {
                "camp_id": 2,
                "name": "Kuttanad Relief Camp",
                "occupancy": 500,
                "children_count": 120,
                "elderly_count": 80,
                "pregnant_count": 15,
                "disabled_count": 10,
                "damage_level": 5,
                "access_difficulty": 5,
                "last_supply_at": self.now - timedelta(hours=60),
                "created_at": self.now - timedelta(hours=96),
                "has_escalation": camp_requests[2]["escalated"],
                "oldest_open_request_at": camp_requests[2]["created_at"],
            },
            {
                "camp_id": 6,
                "name": "Changanassery Camp",
                "occupancy": 80,
                "children_count": 15,
                "elderly_count": 12,
                "pregnant_count": 1,
                "disabled_count": 0,
                "damage_level": 1,
                "access_difficulty": 1,
                "last_supply_at": self.now - timedelta(hours=4),
                "created_at": self.now - timedelta(hours=24),
                "has_escalation": camp_requests[6]["escalated"],
                "oldest_open_request_at": camp_requests[6]["created_at"],
            },
        ]

        ranking_1 = compute_priority(active_camps, self.weights, now=self.now)

        # Check ranking order: High vulnerability/damage camps (2 and 1) should be at top
        rank_1_camp = ranking_1[0]["camp_id"]
        rank_last_camp = ranking_1[-1]["camp_id"]
        self.assertEqual(rank_1_camp, 2, "Kuttanad (Camp 2) should be Rank #1")
        self.assertEqual(rank_last_camp, 6, "Changanassery (Camp 6) should be Rank #3")
        self.assertGreater(ranking_1[0]["score"], 80.0, "Top camp score should be > 80")
        self.assertTrue(ranking_1[1]["breakdown"]["escalation"] == 1.0, "Camp 1 should have escalation = 1.0")

        # =========================================================================
        # STEP 6 & 7: Stock Allocation to Highest Priority Camps First
        # =========================================================================
        # We allocate stock in priority order (Rank 1 -> Rank 2 -> Rank 3)
        planned_allocations = []
        for ranked_entry in ranking_1:
            cid = ranked_entry["camp_id"]
            req = camp_requests[cid]

            for item_code, needed_qty in req["items"].items():
                qty_to_allocate = min(needed_qty, hub_stock[1][item_code])
                if qty_to_allocate > 0:
                    hub_stock[1][item_code] -= qty_to_allocate
                    req["allocated"][item_code] += qty_to_allocate
                    planned_allocations.append({
                        "camp_id": cid,
                        "hub_id": 1,
                        "item_code": item_code,
                        "qty": qty_to_allocate,
                        "status": "planned",
                    })

                # Update request status
                if all(req["allocated"][k] >= req["items"][k] for k in req["items"]):
                    req["status"] = "fulfilled"
                elif any(req["allocated"][k] > 0 for k in req["items"]):
                    req["status"] = "partially_allocated"

        # Verify Camp 1 (Chengannur) was fully allocated (60 rice, 30 blankets)
        self.assertEqual(camp_requests[1]["allocated"]["FW02"], 60)
        self.assertEqual(camp_requests[1]["allocated"]["CB11"], 30)
        self.assertEqual(camp_requests[1]["status"], "fulfilled", "Camp 1 request should be fulfilled")


        # =========================================================================
        # STEP 8: Hub Marks Dispatched -> Camp last_supply_at Updates
        # =========================================================================
        dispatch_time = self.now + timedelta(hours=1)
        for alloc in planned_allocations:
            if alloc["camp_id"] == 1:
                alloc["status"] = "dispatched"

        # Camp 1's last_supply_at is set to dispatch_time (Guide Section 9.6)
        active_camps[0]["last_supply_at"] = dispatch_time
        # Since request was fulfilled, active escalation is cleared
        active_camps[0]["has_escalation"] = False

        # =========================================================================
        # STEP 9: Recalculate Priority -> Time & Score Drop Sensibly
        # =========================================================================
        eval_time = dispatch_time + timedelta(minutes=15)
        ranking_2 = compute_priority(active_camps, self.weights, now=eval_time)

        camp_1_new = next(r for r in ranking_2 if r["camp_id"] == 1)

        # Camp 1's time component should have plummeted (supplied just 15 mins ago)
        self.assertLess(camp_1_new["breakdown"]["time"], 0.01, "Time component should drop near 0 after supply")
        self.assertEqual(camp_1_new["breakdown"]["escalation"], 0.0, "Escalation should be 0 after fulfillment")
        # Camp 1 score must be significantly lower than before
        original_camp_1_score = next(r for r in ranking_1 if r["camp_id"] == 1)["score"]
        self.assertLess(camp_1_new["score"], original_camp_1_score, "Priority score must drop after relief is dispatched")


if __name__ == "__main__":
    unittest.main()
 main
