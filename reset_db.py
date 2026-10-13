# reset_db.py (Owner: Member A)
# Re-creates all database tables by running schema.sql

import os
from database import get_conn

def reset_database():
    """
    Executes schema.sql to drop existing tables and re-create all 14 tables cleanly.
    """
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("Database reset successful: all 14 tables created from schema.sql.")
    except Exception as e:
        conn.rollback()
        print(f"Error resetting database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    reset_database()
