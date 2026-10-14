"""
conftest.py (Owner: Member C)
=============================
Pytest configuration and fixtures for DisasterReliefMVP integration test suite.
Provides clean, deterministic database state by executing schema reset and
loading the full production seed datasets (6,377 camps, 3 hubs, 196 items, stock, requests).

Reference: DisasterReliefMVP Team Guide - Section 11 & Section 15
"""

import sys
import os
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import get_conn
from seed.load_seed import load_all_seeds


@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """
    Session-scoped autouse fixture that guarantees the database is reset
    and populated with all 6,377 camps, 3 hubs, 196 items, stock, and requests.
    """
    conn = get_conn()
    try:
        load_all_seeds(conn=conn, reset=True)
    finally:
        conn.close()
    yield


@pytest.fixture
def reset_db_state():
    """
    Function-scoped fixture to reset and re-seed the database for tests
    that perform data mutations.
    """
    conn = get_conn()
    try:
        load_all_seeds(conn=conn, reset=True)
    finally:
        conn.close()
    yield
