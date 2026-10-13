# database.py (Owner: Member A)
# Provides database connection helper to PostgreSQL

import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

def get_conn():
    """
    Creates and returns a connection to the PostgreSQL database.
    Callers are responsible for closing the connection or using it as a context manager.
    """
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_dict_conn():
    """
    Helper function to get a connection where cursors return dictionaries by default.
    """
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn
