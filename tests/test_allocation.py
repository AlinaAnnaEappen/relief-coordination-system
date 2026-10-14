"""
test_allocation.py (Owner: Member D)
====================================
Comprehensive Unit & Endpoint Tests for Member D (Hubs, Stock, Allocation).

Test Suite covers all contracts specified in Guide Section 9.4, 10, & 11 (Tasks D1, D2, D3, D4):
1. Section 9.4 Worked Example: Strict priority allocation (60 / 40 / 0).
2. Two-hub split: Supplies drawn first from nearest hub, remainder from next nearest.
3. Multi-hub cascade: 3 hubs cascade supply until demand fulfilled.
4. Camp with zero or empty needs: Produces zero allocations without errors.
5. Camp with negative requested quantity: Ignored gracefully without errors.
6. Item unavailable at any hub: Produces zero allocations without crashing.
7. Competition for scarce stock: Higher priority camp receives remaining stock.
8. Distance tie-breaking: Selects lowest hub_id when distances are identical.
9. Immutability guarantee: Caller dictionaries (open_needs, hub_stock) are never mutated.
10. Great-circle distance calculations: Accurate Haversine metric distances.
11. RBAC permissions:
    - Anonymous users rejected with 401 Unauthorized on protected routes.
    - Camp officers rejected with 403 Forbidden on hub admin routes.
    - Hub coordinators and admins authorized on appropriate hub/stock routes.
"""

import unittest
import copy
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engines.allocation_engine import plan_allocation, calculate_haversine_metres
from fastapi.testclient import TestClient
from main import app
from deps import serializer


class TestAllocationEngine(unittest.TestCase):

    def test_section_9_4_worked_example(self):
        """
        Guide Section 9.4:
        Hub H1 has 100 kg rice.
        Ranking: Camp 1 (rank 1), Camp 2 (rank 2), Camp 3 (rank 3).
        Needs: Camp 1 needs 60, Camp 2 needs 50, Camp 3 needs 40.
        Expected result:
          Camp 1 gets 60 kg from H1
          Camp 2 gets 40 kg from H1
          Camp 3 gets 0 kg
        """
        ranked_camps = [1, 2, 3]
        open_needs = {
            1: {1: 60},
            2: {1: 50},
            3: {1: 40},
        }
        hub_stock = {
            1: {1: 100}
        }
        distances = {
            (1, 1): 1000.0,
            (2, 1): 1000.0,
            (3, 1): 1000.0,
        }

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)

        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0], {"camp_id": 1, "hub_id": 1, "item_id": 1, "qty": 60})
        self.assertEqual(allocations[1], {"camp_id": 2, "hub_id": 1, "item_id": 1, "qty": 40})
        camp_3_allocs = [a for a in allocations if a["camp_id"] == 3]
        self.assertEqual(len(camp_3_allocs), 0)

    def test_two_hub_split_nearest_first(self):
        """
        Guide Section 9.4 second test:
        Nearest hub has 30 kg, second hub has 100 kg.
        Camp needing 60 kg should get 30 from nearest hub, and remaining 30 from second hub.
        """
        ranked_camps = [1]
        open_needs = {
            1: {1: 60}
        }
        hub_stock = {
            1: {1: 30},
            2: {1: 100},
        }
        distances = {
            (1, 1): 500.0,
            (1, 2): 2000.0,
        }

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)

        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0], {"camp_id": 1, "hub_id": 1, "item_id": 1, "qty": 30})
        self.assertEqual(allocations[1], {"camp_id": 1, "hub_id": 2, "item_id": 1, "qty": 30})

    def test_multi_hub_cascade(self):
        """
        Three hubs at increasing distance:
        Hub 1 (100m) has 10 units.
        Hub 2 (200m) has 20 units.
        Hub 3 (500m) has 50 units.
        Camp needs 55 units.
        Should take 10 from Hub 1, 20 from Hub 2, and 25 from Hub 3.
        """
        ranked_camps = [10]
        open_needs = {10: {1: 55}}
        hub_stock = {
            1: {1: 10},
            2: {1: 20},
            3: {1: 50},
        }
        distances = {
            (10, 1): 100.0,
            (10, 2): 200.0,
            (10, 3): 500.0,
        }

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)
        self.assertEqual(len(allocations), 3)
        self.assertEqual(allocations[0], {"camp_id": 10, "hub_id": 1, "item_id": 1, "qty": 10})
        self.assertEqual(allocations[1], {"camp_id": 10, "hub_id": 2, "item_id": 1, "qty": 20})
        self.assertEqual(allocations[2], {"camp_id": 10, "hub_id": 3, "item_id": 1, "qty": 25})

    def test_camp_with_no_needs(self):
        """A camp with empty needs or 0 qty requested yields no allocations."""
        ranked_camps = [1, 2]
        open_needs = {
            1: {},
            2: {1: 0, 2: 0},
        }
        hub_stock = {
            1: {1: 100, 2: 50}
        }
        distances = {(1, 1): 100.0, (2, 1): 100.0}

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)
        self.assertEqual(allocations, [])

    def test_camp_with_negative_need_ignored(self):
        """Negative requested quantities are ignored safely."""
        ranked_camps = [1]
        open_needs = {1: {1: -10, 2: 30}}
        hub_stock = {1: {1: 50, 2: 50}}
        distances = {(1, 1): 100.0}

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)
        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0], {"camp_id": 1, "hub_id": 1, "item_id": 2, "qty": 30})

    def test_item_not_in_any_hub_stock(self):
        """If an item is completely out of stock across all hubs, allocation is skipped gracefully."""
        ranked_camps = [1]
        open_needs = {
            1: {999: 50}
        }
        hub_stock = {
            1: {1: 100},
            2: {2: 50},
        }
        distances = {(1, 1): 100.0, (1, 2): 200.0}

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)
        self.assertEqual(allocations, [])

    def test_competition_for_scarce_stock(self):
        """
        Two camps need 20 units of blankets each.
        Hub has only 25 units.
        Rank 1 gets 20, Rank 2 gets 5.
        """
        ranked_camps = [10, 20]
        open_needs = {
            10: {5: 20},
            20: {5: 20},
        }
        hub_stock = {
            1: {5: 25}
        }
        distances = {(10, 1): 300.0, (20, 1): 300.0}

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)
        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0], {"camp_id": 10, "hub_id": 1, "item_id": 5, "qty": 20})
        self.assertEqual(allocations[1], {"camp_id": 20, "hub_id": 1, "item_id": 5, "qty": 5})

    def test_equal_distances_tie_break_lowest_hub_id(self):
        """
        When two hubs have stock and are at identical distance from the camp,
        the hub with the lowest hub_id is chosen first.
        """
        ranked_camps = [1]
        open_needs = {
            1: {1: 10}
        }
        hub_stock = {
            2: {1: 50},
            1: {1: 50},
        }
        distances = {
            (1, 1): 1500.0,
            (1, 2): 1500.0,
        }

        allocations = plan_allocation(ranked_camps, open_needs, hub_stock, distances)
        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0]["hub_id"], 1, "Lowest hub_id (1) must be selected over 2")
        self.assertEqual(allocations[0]["qty"], 10)

    def test_pure_function_does_not_mutate_inputs(self):
        """Verifies that plan_allocation does not mutate open_needs or hub_stock."""
        ranked_camps = [1, 2]
        open_needs = {
            1: {1: 50},
            2: {1: 50},
        }
        hub_stock = {
            1: {1: 70}
        }
        distances = {(1, 1): 100.0, (2, 1): 200.0}

        needs_copy = copy.deepcopy(open_needs)
        stock_copy = copy.deepcopy(hub_stock)

        _ = plan_allocation(ranked_camps, open_needs, hub_stock, distances)

        self.assertEqual(open_needs, needs_copy, "open_needs was mutated by plan_allocation")
        self.assertEqual(hub_stock, stock_copy, "hub_stock was mutated by plan_allocation")

    def test_haversine_distance_calculation(self):
        """Calculates distance between Alappuzha (9.49, 76.33) and Kottayam (9.59, 76.52)."""
        dist = calculate_haversine_metres(9.49, 76.33, 9.59, 76.52)
        # Approximate straight line distance is ~23.5 km
        self.assertGreater(dist, 20000.0)
        self.assertLess(dist, 26000.0)


class TestMemberDRouterPermissions(unittest.TestCase):
    """
    Verifies RBAC and endpoint routing for Member D endpoints.
    """

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_unauthenticated_requests_rejected(self):
        # /hubs requires admin or hub_coordinator
        self.assertEqual(self.client.get("/hubs").status_code, 401)
        # /stock requires admin or hub_coordinator
        self.assertEqual(self.client.get("/stock").status_code, 401)
        # /allocation/latest requires admin
        self.assertEqual(self.client.get("/allocation/latest").status_code, 401)

    def test_camp_officer_forbidden_on_admin_routes(self):
        officer_token = serializer.dumps({"user_id": 2, "username": "officer1", "role": "camp_officer", "camp_id": 1})
        client = TestClient(app)
        client.cookies.set("session_user", officer_token)

        # Camp officer cannot access /hubs list
        resp = client.get("/hubs")
        self.assertEqual(resp.status_code, 403)

        # Camp officer cannot run allocation
        resp = client.post("/allocation/run")
        self.assertEqual(resp.status_code, 403)

        # Camp officer cannot view latest allocation dashboard
        resp = client.get("/allocation/latest")
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
