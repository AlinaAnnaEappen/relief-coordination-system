"""
test_priority.py (Owner: Member C)
==================================
Comprehensive Unit Tests for the SAW Priority Engine (engines/priority_engine.py).

Checks all mathematical contracts, edge cases, timezone safety, and performance:
1. Section 8.4 Worked Example (Benchmark: score ≈ 73.92)
2. Zero occupancy (no division by zero)
3. Single camp normalization (people = 1.0)
4. Missing last_supply_at (falls back to created_at)
5. Time capping (elapsed hours capped at 72 hours)
6. Tie-breaking rules (oldest open request date, then lower camp_id)
7. Weight validation (raises ValueError if weights don't sum to 1.0)
8. Missing weight key (raises ValueError explaining missing keys)
9. Timezone handling: aware and naive inputs produce identical scores
10. Mixed aware and naive timestamps do not crash
11. None values for occupancy, damage_level, access_difficulty handled safely
12. Performance benchmark: all 6,377 camps ranked in under 2 seconds
"""

import unittest
import csv
import time
from datetime import datetime, timedelta, timezone
import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engines.priority_engine import compute_priority, validate_weights, DEFAULT_SAW_WEIGHTS


class TestPriorityEngine(unittest.TestCase):

    def setUp(self):
        self.now_naive = datetime(2026, 8, 15, 12, 0, 0)
        self.now_aware = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.weights = DEFAULT_SAW_WEIGHTS

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
                "last_supply_at": self.now_aware - timedelta(hours=48),
                "created_at": self.now_aware - timedelta(hours=96),
                "has_escalation": True,
                "oldest_open_request_at": self.now_aware - timedelta(hours=10),
            },
            # Camp Y with max occupancy 500 to establish the denominator
            {
                "camp_id": 2,
                "occupancy": 500,
                "children_count": 50,
                "elderly_count": 20,
                "pregnant_count": 5,
                "disabled_count": 5,
                "damage_level": 1,
                "access_difficulty": 1,
                "last_supply_at": self.now_aware - timedelta(hours=2),
                "created_at": self.now_aware - timedelta(hours=24),
                "has_escalation": False,
                "oldest_open_request_at": None,
            },
        ]

        results = compute_priority(camps, weights=self.weights, now=self.now_aware, time_cap_hours=72)
        camp_x_res = next(r for r in results if r["camp_id"] == 1)

        self.assertAlmostEqual(camp_x_res["score"], 73.92, delta=0.05)

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
                "last_supply_at": self.now_aware,
                "created_at": self.now_aware,
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=self.weights, now=self.now_aware)
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
                "last_supply_at": self.now_aware,
                "created_at": self.now_aware,
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=self.weights, now=self.now_aware)
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
                "created_at": self.now_aware - timedelta(hours=36),
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=self.weights, now=self.now_aware, time_cap_hours=72)
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
                "last_supply_at": self.now_aware - timedelta(hours=120),  # 120h > 72h
                "created_at": self.now_aware - timedelta(hours=200),
                "has_escalation": False,
                "oldest_open_request_at": None,
            }
        ]
        results = compute_priority(camps, weights=self.weights, now=self.now_aware, time_cap_hours=72)
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
            "last_supply_at": self.now_aware,
            "created_at": self.now_aware,
            "has_escalation": False,
            "oldest_open_request_at": self.now_aware - timedelta(hours=5),  # newer
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
            "last_supply_at": self.now_aware,
            "created_at": self.now_aware,
            "has_escalation": False,
            "oldest_open_request_at": self.now_aware - timedelta(hours=20),  # older -> wins
        }

        results = compute_priority([camp_a, camp_b], weights=self.weights, now=self.now_aware)
        self.assertEqual(results[0]["camp_id"], 20)
        self.assertEqual(results[0]["rank"], 1)
        self.assertEqual(results[1]["camp_id"], 10)
        self.assertEqual(results[1]["rank"], 2)

    def test_weights_validation_error(self):
        """Weights must sum to 1.00; invalid sum must raise ValueError."""
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

    def test_missing_weight_key(self):
        """Missing any required weight key must raise ValueError."""
        incomplete_weights = {
            "people": 0.20,
            "vulnerable": 0.25,
            "damage": 0.20,
            "access": 0.15,
            "time": 0.20,
            # 'escalation' is missing
        }
        with self.assertRaises(ValueError) as ctx:
            validate_weights(incomplete_weights)
        self.assertIn("escalation", str(ctx.exception))

    def test_aware_and_naive_inputs_give_same_score(self):
        """Timezone-aware and naive inputs with same wall-clock time yield identical scores."""
        camp_naive = {
            "camp_id": 1,
            "occupancy": 200,
            "children_count": 30,
            "elderly_count": 20,
            "pregnant_count": 5,
            "disabled_count": 5,
            "damage_level": 3,
            "access_difficulty": 3,
            "last_supply_at": self.now_naive - timedelta(hours=24),
            "created_at": self.now_naive - timedelta(hours=48),
            "has_escalation": True,
            "oldest_open_request_at": self.now_naive - timedelta(hours=6),
        }
        camp_aware = {
            "camp_id": 1,
            "occupancy": 200,
            "children_count": 30,
            "elderly_count": 20,
            "pregnant_count": 5,
            "disabled_count": 5,
            "damage_level": 3,
            "access_difficulty": 3,
            "last_supply_at": self.now_aware - timedelta(hours=24),
            "created_at": self.now_aware - timedelta(hours=48),
            "has_escalation": True,
            "oldest_open_request_at": self.now_aware - timedelta(hours=6),
        }

        res_naive = compute_priority([camp_naive], weights=self.weights, now=self.now_naive)
        res_aware = compute_priority([camp_aware], weights=self.weights, now=self.now_aware)

        self.assertEqual(res_naive[0]["score"], res_aware[0]["score"])
        self.assertEqual(res_naive[0]["breakdown"], res_aware[0]["breakdown"])

    def test_mixed_aware_and_naive_does_not_crash(self):
        """Mixed naive now and aware camp timestamps do not raise TypeError."""
        camp_aware = {
            "camp_id": 1,
            "occupancy": 150,
            "children_count": 20,
            "elderly_count": 10,
            "pregnant_count": 2,
            "disabled_count": 1,
            "damage_level": 2,
            "access_difficulty": 2,
            "last_supply_at": self.now_aware - timedelta(hours=12),
            "created_at": self.now_aware - timedelta(hours=24),
            "has_escalation": False,
            "oldest_open_request_at": None,
        }
        # Run with naive now
        results = compute_priority([camp_aware], weights=self.weights, now=self.now_naive)
        self.assertEqual(len(results), 1)
        self.assertGreater(results[0]["score"], 0)

    def test_occupancy_none_does_not_crash(self):
        """None values for occupancy, damage_level, access_difficulty are handled safely."""
        camp_none = {
            "camp_id": 99,
            "occupancy": None,
            "children_count": None,
            "elderly_count": None,
            "pregnant_count": None,
            "disabled_count": None,
            "damage_level": None,
            "access_difficulty": None,
            "last_supply_at": None,
            "created_at": None,
            "has_escalation": False,
            "oldest_open_request_at": None,
        }
        results = compute_priority([camp_none], weights=self.weights, now=self.now_aware)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["breakdown"]["people"], 0.0)
        self.assertEqual(results[0]["breakdown"]["vulnerable"], 0.0)

    def test_performance_6377_camps(self):
        """
        Performance benchmark: compute priority scores for all 6,377 real camps in seed_camps.csv.
        Must complete in under 2.0 seconds.
        """
        camps_path = os.path.join(PROJECT_ROOT, "seed", "seed_camps.csv")
        self.assertTrue(os.path.exists(camps_path), "seed_camps.csv must exist")

        with open(camps_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            camps = []
            for r in reader:
                last_sup = r.get("last_supply_at", "").strip()
                last_dt = None
                if last_sup:
                    try:
                        clean = last_sup.replace("+00:00", "+0000").replace("+00", "+0000").replace("Z", "+0000")
                        last_dt = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S%z")
                    except Exception:
                        pass
                camps.append({
                    "camp_id": int(r["camp_id"]),
                    "occupancy": int(r.get("occupancy") or 0),
                    "children_count": int(r.get("children_count") or 0),
                    "elderly_count": int(r.get("elderly_count") or 0),
                    "pregnant_count": int(r.get("pregnant_count") or 0),
                    "disabled_count": int(r.get("disabled_count") or 0),
                    "damage_level": int(r.get("damage_level") or 1),
                    "access_difficulty": int(r.get("access_difficulty") or 1),
                    "last_supply_at": last_dt,
                    "created_at": self.now_aware - timedelta(hours=72),
                    "has_escalation": False,
                    "oldest_open_request_at": None,
                })

        self.assertEqual(len(camps), 6377, "Must load exactly 6,377 camps")

        start = time.time()
        results = compute_priority(camps, weights=self.weights, now=self.now_aware)
        elapsed = time.time() - start

        self.assertEqual(len(results), 6377)
        self.assertEqual(results[0]["rank"], 1)
        self.assertEqual(results[-1]["rank"], 6377)

        # Must rank in under 2 seconds
        self.assertLess(elapsed, 2.0, f"Ranking 6,377 camps took {elapsed:.3f}s, expected < 2.0s")
        print(f"\n[PERFORMANCE BENCHMARK] Ranked all 6,377 camps in {elapsed:.4f} seconds.")


if __name__ == "__main__":
    unittest.main()
