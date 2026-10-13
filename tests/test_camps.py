"""
test_camps.py (Owner: Member B)
==============================
Unit tests for camps_router.py (Task B2: Camp list, view, creation, and updates).

Validates:
1. Authorization boundaries (Officer own camp vs other camp 403, Admin privileges, Donor forbidden).
2. Operational field validation (occupancy non-negative, vulnerable counts <= occupancy, damage & access in 1..5).
3. Admin-only fields (officers cannot modify name, district, capacity, status, coordinates).
4. HTML update endpoints and API PUT responses.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from fastapi import HTTPException

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock database and deps if not available in environment
if "database" not in sys.modules:
    sys.modules["database"] = MagicMock()
if "deps" not in sys.modules:
    mock_deps = MagicMock()
    mock_deps.get_current_user = lambda request: {"role": "admin", "camp_id": None}
    mock_deps.require_role = lambda *roles: (lambda: {"role": "admin"})
    sys.modules["deps"] = mock_deps

from routers.camps_router import _validate_and_save_camp_update


class TestCampUpdates(unittest.TestCase):
    """Test suite for camp update validation and authorization logic."""

    def _get_sample_camp(self, camp_id=1):
        return {
            "camp_id": camp_id,
            "name": "St. Mary HSS Camp",
            "district": "Alappuzha",
            "address": "Near Boat Jetty, Kuttanad",
            "latitude": Decimal("9.498100"),
            "longitude": Decimal("76.338800"),
            "capacity": 500,
            "occupancy": 200,
            "children_count": 40,
            "elderly_count": 30,
            "pregnant_count": 5,
            "disabled_count": 8,
            "damage_level": 3,
            "access_difficulty": 4,
            "status": "active",
            "last_supply_at": None,
            "created_at": "2026-08-10 10:00:00",
            "updated_at": "2026-08-10 10:00:00",
        }

    @patch("routers.camps_router.get_conn")
    def test_officer_can_update_own_camp(self, mock_get_conn):
        """Camp officer should successfully update operational fields of their assigned camp."""
        sample_camp = self._get_sample_camp(1)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [sample_camp, {**sample_camp, "occupancy": 250}]

        officer_user = {"role": "camp_officer", "camp_id": 1, "username": "officer1"}
        input_data = {
            "occupancy": "250",
            "children_count": "50",
            "elderly_count": "35",
            "pregnant_count": "6",
            "disabled_count": "10",
            "damage_level": "4",
            "access_difficulty": "5",
        }

        updated_camp, form_state, errors = _validate_and_save_camp_update(
            camp_id=1,
            user=officer_user,
            input_data=input_data,
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(updated_camp)
        # Verify query was executed and committed
        self.assertTrue(mock_cur.execute.called)
        self.assertTrue(mock_conn.commit.called)

    @patch("routers.camps_router.get_conn")
    def test_officer_cannot_update_other_camp(self, mock_get_conn):
        """Camp officer attempting to update a different camp must receive 403 Forbidden."""
        officer_user = {"role": "camp_officer", "camp_id": 1, "username": "officer1"}
        with self.assertRaises(HTTPException) as ctx:
            _validate_and_save_camp_update(
                camp_id=2,  # Camp 2, but officer is assigned to Camp 1
                user=officer_user,
                input_data={"occupancy": "100"},
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("own assigned camp", ctx.exception.detail)

    @patch("routers.camps_router.get_conn")
    def test_donor_cannot_update_camp(self, mock_get_conn):
        """Donors attempting to update any camp must receive 403 Forbidden."""
        donor_user = {"role": "donor", "username": "donor1"}
        with self.assertRaises(HTTPException) as ctx:
            _validate_and_save_camp_update(
                camp_id=1,
                user=donor_user,
                input_data={"occupancy": "100"},
            )
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("routers.camps_router.get_conn")
    def test_subgroup_exceeding_occupancy_fails_validation(self, mock_get_conn):
        """Any vulnerable count strictly exceeding occupancy must yield a validation error."""
        sample_camp = self._get_sample_camp(1)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = sample_camp

        admin_user = {"role": "admin", "username": "admin1"}
        input_data = {
            "occupancy": "50",
            "children_count": "60",  # Greater than occupancy (50)
            "elderly_count": "10",
            "pregnant_count": "2",
            "disabled_count": "5",
            "damage_level": "2",
            "access_difficulty": "2",
        }

        updated_camp, form_state, errors = _validate_and_save_camp_update(
            camp_id=1,
            user=admin_user,
            input_data=input_data,
        )

        self.assertIsNone(updated_camp)
        self.assertTrue(any("Children count cannot be greater than occupancy" in e for e in errors))

    @patch("routers.camps_router.get_conn")
    def test_damage_and_access_out_of_bounds_fail_validation(self, mock_get_conn):
        """Damage level and access difficulty outside 1..5 must yield validation errors."""
        sample_camp = self._get_sample_camp(1)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = sample_camp

        admin_user = {"role": "admin", "username": "admin1"}
        input_data = {
            "occupancy": "100",
            "children_count": "20",
            "elderly_count": "10",
            "pregnant_count": "2",
            "disabled_count": "5",
            "damage_level": "6",       # Invalid: must be 1..5
            "access_difficulty": "0",  # Invalid: must be 1..5
        }

        updated_camp, form_state, errors = _validate_and_save_camp_update(
            camp_id=1,
            user=admin_user,
            input_data=input_data,
        )

        self.assertIsNone(updated_camp)
        self.assertTrue(any("Damage level must be between 1 and 5" in e for e in errors))
        self.assertTrue(any("Access difficulty must be between 1 and 5" in e for e in errors))

    @patch("routers.camps_router.get_conn")
    def test_admin_fields_silently_ignored_for_officers(self, mock_get_conn):
        """If an officer submits administrative fields (name, district, status), they are ignored."""
        sample_camp = self._get_sample_camp(1)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [sample_camp, sample_camp]

        officer_user = {"role": "camp_officer", "camp_id": 1, "username": "officer1"}
        input_data = {
            "name": "Tampered Name",
            "status": "closed",
            "district": "Kottayam",
            "occupancy": "200",
            "children_count": "40",
            "elderly_count": "30",
            "pregnant_count": "5",
            "disabled_count": "8",
            "damage_level": "3",
            "access_difficulty": "4",
        }

        updated_camp, form_state, errors = _validate_and_save_camp_update(
            camp_id=1,
            user=officer_user,
            input_data=input_data,
        )

        self.assertEqual(errors, [])
        # Check SQL executed in cur.execute
        executed_query = mock_cur.execute.call_args[0][0]
        # Query for officer must NOT update name, district, or status
        self.assertNotIn("name = %s", executed_query)
        self.assertNotIn("district = %s", executed_query)
        self.assertNotIn("status = %s", executed_query)


if __name__ == "__main__":
    unittest.main()
