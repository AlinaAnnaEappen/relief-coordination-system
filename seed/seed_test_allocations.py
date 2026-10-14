import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database

def seed_sample_allocations():
    conn = database.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT run_id FROM allocation_runs LIMIT 1;")
            run = cur.fetchone()
            if not run:
                cur.execute("""
                    INSERT INTO allocation_runs (note)
                    VALUES ('Manual test run for Task B4 supplies verification')
                    RETURNING run_id;
                """)
                run_id = cur.fetchone()[0]
            else:
                run_id = run[0]

            cur.execute("SELECT count(*) FROM allocations WHERE camp_id = 1;")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("SELECT item_id, item_code FROM items WHERE item_code IN ('FW01', 'CB01', 'MF01');")
                item_map = {row[1]: row[0] for row in cur.fetchall()}

                cur.execute("SELECT hub_id FROM hubs ORDER BY hub_id LIMIT 2;")
                hubs = [row[0] for row in cur.fetchall()]
                hub1 = hubs[0]
                hub2 = hubs[1] if len(hubs) > 1 else hub1

                if "FW01" in item_map:
                    cur.execute(
                        "INSERT INTO allocations (run_id, camp_id, hub_id, item_id, qty, status) VALUES (%s, 1, %s, %s, 50, 'dispatched');",
                        (run_id, hub1, item_map["FW01"])
                    )
                if "CB01" in item_map:
                    cur.execute(
                        "INSERT INTO allocations (run_id, camp_id, hub_id, item_id, qty, status) VALUES (%s, 1, %s, %s, 25, 'planned');",
                        (run_id, hub2, item_map["CB01"])
                    )
                if "MF01" in item_map:
                    cur.execute(
                        "INSERT INTO allocations (run_id, camp_id, hub_id, item_id, qty, status) VALUES (%s, 1, %s, %s, 15, 'delivered');",
                        (run_id, hub1, item_map["MF01"])
                    )
                conn.commit()
                print("Successfully seeded 3 sample allocations for Camp 1!")
            else:
                print(f"Camp 1 already has {count} allocations.")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_sample_allocations()
