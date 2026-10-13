"""
test_priority.py (Owner: Member C)
==================================
Unit tests for the SAW Priority Engine (engines/priority_engine.py).

Checks all mathematical contracts and edge cases defined in Section 8 of the Guide:
1. Section 8.4 Worked Example (Benchmark: score ≈ 73.92)
2. Zero occupancy (no division by zero)
3. Single camp normalization (people = 1.0)
4. Missing last_supply_at (falls back to created_at)
5. Time capping (elapsed hours capped at 72 hours)
6. Tie-breaking rules (oldest open request date, then lower camp_id)
7. Weight validation (raises ValueError if weights don't sum to 1.0)
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.priority_engine import compute_priority, validate_weights, DEFAULT_SAW_WEIGHTS


class TestPriorityEngine(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 8, 15, 12, 0, 0)

    def test_worked_example_section_8_4(self):
        """
        Verify the exact worked example from Guide Section 8.4:
        Camp X with occupancy 400 (max in district 500), 180 vulnerable,
        damage 4, access 5, last supplied 48h ago, escalated request.
        Expected composite score is ~73.92.
        """
        camps = [
            # Camp X
            {
                "camp_id": 1,
                "occupancy": 400,
                "children_count": 90,
                "elderly_count": 60,
                "pregnant_count": 10,
                "disabled_count": 20,
                "damage_level": 4,
                "access_difficulty": 5,
                "last_supply_at": self.now - timedelta(hours=48),
                "created_at": self.now - timedelta(hours=96),
                "has_escalation": True,
                "oldest_open_request_at": self.now - timedelta(hours=10),
            },
            # Dummy Camp Y with max occupancy 500 to establish the denominator
            {
                "camp_id": 2,
                "occupancy": 500,
                "children_count": 50,
                "elderly_count": 20,
                "pregnant_count": 5,
                "disabled_count": 5,
                "damage_level": 1,
                "access_difficulty": 1,
                "last_supply_at": self.now - timedelta(hours=2),
                "created_at": self.now - timedelta(hours=24),
                "has_escalation": False,
                "oldest_open_request_at": None,
            },
        ]

        results = compute_priority(camps, weights=DEFAULT_SAW_WEIGHTS, now=self.now, time_cap_hours=72)
        camp_x_res = next(r for r in results if r["camp_id"] == 1)

        # Expected score is 73.92 (within 0.05 tolerance for rounding differences)
        self.assertAlmostEqual(camp_x_res["score"], 73.92, delta=0.05)

        # Verify criterion breakdown values
        breakdown = camp_x_res["breakdown"]
        self.assertAlmostEqual(breakdown["people"], 0.80, delta=0.01)       # 400 / 500
        self.assertAlmostEqual(breakdown["vulnerable"], 0.45, delta=0.01)   # 180 / 400
        self.assertAlmostEqual(breakdown["damage"], 0.75, delta=0.01)       # (4 - 1) / 4
        self.assertAlmostEqual(breakdown["access"], 1.00, delta=0.01)       # (5 - 1) / 4
        self.assertAlmostEqual(breakdown["time"], 48.0 / 72.0, delta=0.01)  # 48 / 72
        self.assertEqual(breakdown["escalation"], 1.0)                      # True -> 1.0

    def test_zero_occupancy_no_division_by_zero(self):
        """Verify camp with 0 occupancy gracefully returns 0 for people and vulnerable."""
        camps = [
            {
                "camp_id": 1,
                "occupancy": 0,
                "children_count": 0,
                "elderly_count": 0,
                "pregnant_count": 0,
                "disabled_count": 0,
                "damage_level": 3,
                "access_difficulty": 3,
                "last_supply_at": self.now,
                "created_at": self.now,
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=DEFAULT_SAW_WEIGHTS, now=self.now)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["breakdown"]["people"], 0.0)
        self.assertEqual(results[0]["breakdown"]["vulnerable"], 0.0)

    def test_single_camp_normalization(self):
        """Guide Section 8.5: If only one camp exists, people = 1.0 if occupancy > 0."""
        camps = [
            {
                "camp_id": 5,
                "occupancy": 75,
                "children_count": 10,
                "elderly_count": 5,
                "pregnant_count": 2,
                "disabled_count": 1,
                "damage_level": 2,
                "access_difficulty": 2,
                "last_supply_at": self.now,
                "created_at": self.now,
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=DEFAULT_SAW_WEIGHTS, now=self.now)
        self.assertEqual(results[0]["breakdown"]["people"], 1.0)

    def test_missing_last_supply_at_uses_created_at(self):
        """Guide Section 8.1: If last_supply_at is empty/None, use created_at."""
        camps = [
            {
                "camp_id": 1,
                "occupancy": 100,
                "children_count": 0,
                "elderly_count": 0,
                "pregnant_count": 0,
                "disabled_count": 0,
                "damage_level": 1,
                "access_difficulty": 1,
                "last_supply_at": None,
                "created_at": self.now - timedelta(hours=36),
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=DEFAULT_SAW_WEIGHTS, now=self.now, time_cap_hours=72)
        # 36 hours elapsed / 72 hours cap = 0.5
        self.assertAlmostEqual(results[0]["breakdown"]["time"], 0.5, delta=0.01)

    def test_time_capping(self):
        """Guide Section 8.1: Elapsed time beyond 72 hours must cap at 1.0."""
        camps = [
            {
                "camp_id": 1,
                "occupancy": 100,
                "children_count": 0,
                "elderly_count": 0,
                "pregnant_count": 0,
                "disabled_count": 0,
                "damage_level": 1,
                "access_difficulty": 1,
                "last_supply_at": self.now - timedelta(hours=120),  # 120h > 72h
                "created_at": self.now - timedelta(hours=200),
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=DEFAULT_SAW_WEIGHTS, now=self.now, time_cap_hours=72)
        self.assertEqual(results[0]["breakdown"]["time"], 1.0)

    def test_tie_breaking(self):
        """
        Guide Section 8.5: When scores are tied:
        1. Camp with older oldest_open_request_at ranks higher.
        2. If still tied, lower camp_id ranks higher.
        """
        camp_a = {
            "camp_id": 10,
            "occupancy": 100,
            "children_count": 0,
            "elderly_count": 0,
            "pregnant_count": 0,
            "disabled_count": 0,
            "damage_level": 1,
            "access_difficulty": 1,
            "last_supply_at": self.now,
            "created_at": self.now,
            "has_escalation": False,
            "oldest_open_request_at": self.now - timedelta(hours=5),  # newer request
        }
        camp_b = {
            "camp_id": 20,
            "occupancy": 100,
            "children_count": 0,
            "elderly_count": 0,
            "pregnant_count": 0,
            "disabled_count": 0,
            "damage_level": 1,
            "access_difficulty": 1,
            "last_supply_at": self.now,
            "created_at": self.now,
            "has_escalation": False,
            "oldest_open_request_at": self.now - timedelta(hours=20),  # older request -> wins
        }

        results = compute_priority([camp_a, camp_b], weights=DEFAULT_SAW_WEIGHTS, now=self.now)
        # Scores are identical, so Camp B (older request) should be Rank 1
        self.assertEqual(results[0]["camp_id"], 20)
        self.assertEqual(results[0]["rank"], 1)
        self.assertEqual(results[1]["camp_id"], 10)
        self.assertEqual(results[1]["rank"], 2)

    def test_weights_validation_error(self):
        """Weights must sum to 1.00; invalid weights must raise ValueError."""
        invalid_weights = {
            "people": 0.30,
            "vulnerable": 0.30,
            "damage": 0.20,
            "access": 0.15,
            "time": 0.10,
            "escalation": 0.10,  # Total = 1.15
        }
        with self.assertRaises(ValueError):
            validate_weights(invalid_weights)


if __name__ == "__main__":
    unittest.main()
