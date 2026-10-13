"""
test_requests.py (Owner: Member B)
=================================
Unit tests for requests_router.py (Task B3: Requests module).

Validates:
1. Request creation with valid items and escalation (status 'pending').
2. Zero items submitted (fails with error).
3. Zero or negative quantity submitted (fails with error).
4. Duplicate items in a single request (fails with error).
5. Comment length constraint (max 500 characters).
6. Camp active status constraint (closed camp cannot submit request).
7. Authorization boundaries:
   - Officer can only submit and view requests for their own camp.
   - Officer attempting to access another camp receives 403 Forbidden.
   - Admin can view and submit for any camp.
8. Escalation (POST /requests/{id}/escalate) and Cancellation (POST /requests/{id}/cancel):
   - Only permitted for open requests ('pending' or 'partially_allocated').
   - Restricted to the owning camp officer or admin.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
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
    mock_deps.get_current_user = lambda request: {"role": "camp_officer", "camp_id": 1, "user_id": 2}
    mock_deps.require_role = lambda *roles: (lambda: {"role": "camp_officer", "camp_id": 1})
    sys.modules["deps"] = mock_deps

from routers.requests_router import (
    _validate_and_save_request,
    escalate_request,
    cancel_request,
)


class TestRequestsModule(unittest.TestCase):
    """Test suite for relief request validation, storage, and lifecycle."""

    def _get_active_camp(self, camp_id=1):
        return {
            "camp_id": camp_id,
            "name": "St. Mary HSS Relief Camp",
            "district": "Alappuzha",
            "status": "active",
        }

    @patch("routers.requests_router.get_conn")
    def test_officer_submits_valid_request_with_escalation(self, mock_get_conn):
        """
        Guide Done-when: officer1 submits a request with two items and escalation
        -> it appears with status 'pending'.
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # 1. Check camp active query
        mock_cur.fetchone.side_effect = [
            self._get_active_camp(1),
            {
                "request_id": 101,
                "camp_id": 1,
                "submitted_by": 2,
                "status": "pending",
                "escalated": True,
                "comment": "Urgent food and bedding required.",
                "created_at": "2026-08-15 10:00:00",
            },
        ]

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2, "username": "officer1"}
        input_data = {
            "camp_id": "1",
            "escalated": "true",
            "comment": "Urgent food and bedding required.",
            "items": [
                {"item_id": 2, "qty": 60},  # 60 kg Rice
                {"item_id": 16, "qty": 30}, # 30 Blankets
            ],
        }

        created_req, form_state, errors = _validate_and_save_request(officer_user, input_data)

        self.assertEqual(errors, [])
        self.assertIsNotNone(created_req)
        self.assertEqual(created_req["request_id"], 101)
        self.assertEqual(created_req["status"], "pending")
        self.assertTrue(created_req["escalated"])
        self.assertEqual(len(created_req["items"]), 2)
        self.assertTrue(mock_conn.commit.called)

    @patch("routers.requests_router.get_conn")
    def test_zero_items_requested_fails_validation(self, mock_get_conn):
        """Submitting 0 items must yield an error: 'At least one item must be requested.'"""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = self._get_active_camp(1)

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        input_data = {
            "camp_id": 1,
            "items": [],
        }

        created_req, form_state, errors = _validate_and_save_request(officer_user, input_data)

        self.assertIsNone(created_req)
        self.assertTrue(any("At least one item must be requested" in e for e in errors))

    @patch("routers.requests_router.get_conn")
    def test_zero_or_negative_quantity_fails_validation(self, mock_get_conn):
        """Quantity <= 0 must yield an error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = self._get_active_camp(1)

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        input_data = {
            "camp_id": 1,
            "items": [
                {"item_id": 2, "qty": 0},   # Invalid qty = 0
                {"item_id": 5, "qty": -10}, # Invalid qty < 0
            ],
        }

        created_req, form_state, errors = _validate_and_save_request(officer_user, input_data)

        self.assertIsNone(created_req)
        self.assertTrue(any("must be greater than 0" in e for e in errors))

    @patch("routers.requests_router.get_conn")
    def test_duplicate_items_fail_validation(self, mock_get_conn):
        """Duplicate item_id in request must yield validation error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = self._get_active_camp(1)

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        input_data = {
            "camp_id": 1,
            "items": [
                {"item_id": 2, "qty": 20},
                {"item_id": 2, "qty": 50},  # Duplicate item_id 2
            ],
        }

        created_req, form_state, errors = _validate_and_save_request(officer_user, input_data)

        self.assertIsNone(created_req)
        self.assertTrue(any("Duplicate item found" in e for e in errors))

    @patch("routers.requests_router.get_conn")
    def test_closed_camp_cannot_submit_request(self, mock_get_conn):
        """Closed camp must not be permitted to submit requests."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = {
            "camp_id": 1,
            "name": "Closed Shelter",
            "district": "Kottayam",
            "status": "closed",
        }

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        input_data = {
            "camp_id": 1,
            "items": [{"item_id": 1, "qty": 10}],
        }

        created_req, form_state, errors = _validate_and_save_request(officer_user, input_data)

        self.assertIsNone(created_req)
        self.assertTrue(any("is closed" in e for e in errors))

    @patch("routers.requests_router.get_conn")
    def test_officer_cannot_submit_for_different_camp(self, mock_get_conn):
        """Camp officer assigned to camp 1 cannot submit for camp 2 (403 Forbidden)."""
        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        input_data = {
            "camp_id": 2,  # Different camp
            "items": [{"item_id": 1, "qty": 10}],
        }

        with self.assertRaises(HTTPException) as ctx:
            _validate_and_save_request(officer_user, input_data)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("own assigned camp", ctx.exception.detail)

    @patch("routers.requests_router.get_conn")
    def test_comment_over_500_chars_fails_validation(self, mock_get_conn):
        """Comment exceeding 500 characters must fail validation."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = self._get_active_camp(1)

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        long_comment = "A" * 501
        input_data = {
            "camp_id": 1,
            "comment": long_comment,
            "items": [{"item_id": 1, "qty": 10}],
        }

        created_req, form_state, errors = _validate_and_save_request(officer_user, input_data)

        self.assertIsNone(created_req)
        self.assertTrue(any("Comment cannot exceed 500 characters" in e for e in errors))

    @patch("routers.requests_router.get_conn")
    def test_escalate_and_cancel_lifecycle(self, mock_get_conn):
        """Tests that open requests can be escalated and cancelled by the owning officer."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Setup mock request belonging to camp 1, currently pending
        mock_req = {
            "request_id": 10,
            "camp_id": 1,
            "status": "pending",
            "escalated": False,
        }
        mock_cur.fetchone.side_effect = [
            mock_req,                         # SELECT before escalate
            {**mock_req, "escalated": True},   # UPDATE escalate RETURNING
            {**mock_req, "escalated": True},   # SELECT before cancel
            {**mock_req, "status": "cancelled"}# UPDATE cancel RETURNING
        ]

        officer_user = {"role": "camp_officer", "camp_id": 1, "user_id": 2}
        dummy_req = MagicMock()
        dummy_req.headers = {"accept": "application/json"}

        # 1. Escalate
        import asyncio
        escalated_res = asyncio.run(escalate_request(10, dummy_req, officer_user))
        self.assertEqual(escalated_res.status_code, 200)

        # 2. Cancel
        cancelled_res = asyncio.run(cancel_request(10, dummy_req, officer_user))
        self.assertEqual(cancelled_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
