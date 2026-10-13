"""
load_seed.py (Owner: Member C)
==============================
Production Database Seed Data Loader for relief-coordination-system.

Loads seed datasets into PostgreSQL in the exact required foreign-key sequence:
    1. Items (seed_items.csv)
    2. Camps (seed_camps.csv)
    3. Hubs (seed_hubs.csv)
    4. Users (seed/seed_users.py or standard system users)
    5. Stock (seed_stock.csv)
    6. Requests & Request Items (seed_requests.csv)

Supports:
    --no-reset : Skips database reset (default is to run clean reset)
    --only items : Loads ONLY the item catalog (for Member B)
    --validate : Checks all CSVs and foreign keys without connecting to DB

Reference: DisasterRelief Team Guide - Sections 6.2, 7, 11 (Task C1)
"""

import sys
import os
import csv
import argparse
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from dotenv import load_dotenv

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SEED_DIR = os.path.dirname(__file__)


def get_db_connection():
    """
    Acquires database connection from DATABASE_URL in .env or os.environ.
    Falls back to database.py if available.
    """
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)

    try:
        from database import get_conn
        return get_conn()
    except Exception as e:
        raise ConnectionError(f"Cannot connect to database: DATABASE_URL not set and database.py failed: {e}")


def read_csv(filename: str) -> List[Dict[str, str]]:
    """Reads a CSV file from seed directory into a list of row dictionaries."""
    filepath = os.path.join(SEED_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Seed file not found: {filepath}")
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def reset_database(conn):
    """
    Executes schema.sql to cleanly drop and recreate all tables.
    """
    schema_path = os.path.join(PROJECT_ROOT, "relief-coordination-system", "schema.sql")
    if not os.path.exists(schema_path):
        schema_path = os.path.join(PROJECT_ROOT, "schema.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError("schema.sql not found at project root or relief-coordination-system/")

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def validate_seed_data() -> Dict[str, Any]:
    """
    Validates CSV formats, headers, and foreign-key references across all seed files.
    Returns a dictionary of loaded rows.
    """
    items = read_csv("seed_items.csv")
    camps = read_csv("seed_camps.csv")
    hubs = read_csv("seed_hubs.csv")
    stock = read_csv("seed_stock.csv")
    requests = read_csv("seed_requests.csv")

    item_codes = {r["item_code"] for r in items}
    camp_ids = {int(r["camp_id"]) for r in camps}
    hub_ids = {int(r["hub_id"]) for r in hubs}

    # Verify stock foreign keys
    for row in stock:
        hid = int(row["hub_id"])
        icode = row["item_code"]
        if hid not in hub_ids:
            raise ValueError(f"Stock references unknown hub_id: {hid}")
        if icode not in item_codes:
            raise ValueError(f"Stock references unknown item_code: {icode}")

    # Verify request foreign keys
    unique_requests = set()
    for row in requests:
        cid = int(row["camp_id"])
        icode = row["item_code"]
        rid = int(row["request_id"])
        unique_requests.add(rid)
        if cid not in camp_ids:
            raise ValueError(f"Request references unknown camp_id: {cid}")
        if icode not in item_codes:
            raise ValueError(f"Request references unknown item_code: {icode}")

    return {
        "items": items,
        "camps": camps,
        "hubs": hubs,
        "stock": stock,
        "requests": requests,
        "unique_requests_count": len(unique_requests),
    }


def seed_items_table(conn, items: List[Dict[str, str]]) -> int:
    """
    Inserts item records into the items table.
    Adapts seamlessly whether schema has 14-group columns (group_code)
    or legacy 7-category columns (category).
    """
    with conn.cursor() as cur:
        # Inspect columns in table items
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'items';")
        cols = {r[0] for r in cur.fetchall()}

        if "group_code" in cols:
            sql = """
                INSERT INTO items (
                    item_code, name, group_code, group_kind, unit,
                    item_type, perishable, requires_approval, emergency_eligible,
                    notes, active
                ) VALUES %s
                ON CONFLICT (item_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    group_code = EXCLUDED.group_code,
                    group_kind = EXCLUDED.group_kind,
                    unit = EXCLUDED.unit,
                    item_type = EXCLUDED.item_type,
                    perishable = EXCLUDED.perishable,
                    requires_approval = EXCLUDED.requires_approval,
                    emergency_eligible = EXCLUDED.emergency_eligible,
                    notes = EXCLUDED.notes;
            """
            values = []
            for r in items:
                ee = r.get("emergency_eligible", "no").strip().lower() in ("true", "1", "yes")
                values.append((
                    r["item_code"],
                    r["name"],
                    r["group_code"],
                    r.get("group_kind", "core"),
                    r["unit"],
                    r.get("item_type", "Consumable"),
                    r.get("perishable", "No"),
                    r.get("requires_approval", "No"),
                    ee,
                    r.get("notes") or None,
                ))
            execute_values(cur, sql, values)
        else:
            # Legacy 7-category schema from Member A's initial schema.sql
            sql = """
                INSERT INTO items (
                    item_code, name, category, unit,
                    perishable, requires_approval, emergency_eligible,
                    acceptance_rule, norm_note, active
                ) VALUES %s
                ON CONFLICT (item_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    unit = EXCLUDED.unit,
                    perishable = EXCLUDED.perishable,
                    requires_approval = EXCLUDED.requires_approval,
                    emergency_eligible = EXCLUDED.emergency_eligible;
            """
            values = []
            for r in items:
                ee = r.get("emergency_eligible", "no").strip().lower() in ("true", "1", "yes")
                perish_bool = r.get("perishable", "No").strip().lower() in ("yes", "true", "semi")
                req_app_bool = r.get("requires_approval", "No").strip().lower() in ("yes", "true")
                # Map 14-group code to 7 categories if necessary
                cat = r["group_code"]
                if cat not in ('FW', 'CB', 'SH', 'MF', 'KU', 'SU', 'SG'):
                    cat = 'SG'
                values.append((
                    r["item_code"],
                    r["name"],
                    cat,
                    r["unit"],
                    perish_bool,
                    req_app_bool,
                    ee,
                    r.get("notes") or None,
                    r.get("notes") or None,
                    True,
                ))
            execute_values(cur, sql, values)

        cur.execute("SELECT setval('items_item_id_seq', (SELECT COALESCE(MAX(item_id), 1) FROM items));")
    return len(items)


def seed_camps_table(conn, camps: List[Dict[str, str]]) -> int:
    """
    Bulk-loads all camps using execute_values and resets serial sequence.
    """
    sql = """
        INSERT INTO camps (
            camp_id, name, district, address, latitude, longitude,
            capacity, occupancy, children_count, elderly_count,
            pregnant_count, disabled_count, damage_level, access_difficulty,
            status, last_supply_at
        ) VALUES %s
        ON CONFLICT (camp_id) DO UPDATE SET
            name = EXCLUDED.name,
            district = EXCLUDED.district,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            capacity = EXCLUDED.capacity,
            occupancy = EXCLUDED.occupancy,
            children_count = EXCLUDED.children_count,
            elderly_count = EXCLUDED.elderly_count,
            pregnant_count = EXCLUDED.pregnant_count,
            disabled_count = EXCLUDED.disabled_count,
            damage_level = EXCLUDED.damage_level,
            access_difficulty = EXCLUDED.access_difficulty,
            status = EXCLUDED.status,
            last_supply_at = EXCLUDED.last_supply_at;
    """
    values = []
    for r in camps:
        last_supply = r.get("last_supply_at", "").strip() or None
        cap = r.get("capacity", "").strip()
        capacity_val = int(cap) if cap and cap.isdigit() else 0
        occ = r.get("occupancy", "").strip()
        occupancy_val = int(occ) if occ and occ.isdigit() else 0
        ch = r.get("children_count", "").strip()
        children_val = int(ch) if ch and ch.isdigit() else 0
        el = r.get("elderly_count", "").strip()
        elderly_val = int(el) if el and el.isdigit() else 0
        pr = r.get("pregnant_count", "").strip()
        pregnant_val = int(pr) if pr and pr.isdigit() else 0
        dis = r.get("disabled_count", "").strip()
        disabled_val = int(dis) if dis and dis.isdigit() else 0
        dmg = r.get("damage_level", "").strip()
        damage_val = int(dmg) if dmg and dmg.isdigit() else 1
        acc = r.get("access_difficulty", "").strip()
        access_val = int(acc) if acc and acc.isdigit() else 1

        values.append((
            int(r["camp_id"]),
            r["name"],
            r["district"],
            r.get("address"),
            float(r["latitude"]),
            float(r["longitude"]),
            capacity_val,
            occupancy_val,
            children_val,
            elderly_val,
            pregnant_val,
            disabled_val,
            damage_val,
            access_val,
            r.get("status", "active") or "active",
            last_supply,
        ))

    with conn.cursor() as cur:
        execute_values(cur, sql, values)
        cur.execute("SELECT setval('camps_camp_id_seq', (SELECT COALESCE(MAX(camp_id), 1) FROM camps));")
    return len(camps)


def seed_hubs_table(conn, hubs: List[Dict[str, str]]) -> int:
    """Inserts hubs into hubs table and updates auto-increment sequence."""
    sql = """
        INSERT INTO hubs (
            hub_id, name, district, address, latitude, longitude, active
        ) VALUES %s
        ON CONFLICT (hub_id) DO UPDATE SET
            name = EXCLUDED.name,
            district = EXCLUDED.district,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            active = EXCLUDED.active;
    """
    values = []
    for r in hubs:
        act = r.get("active", "true").strip().lower() in ("true", "1", "yes")
        values.append((
            int(r["hub_id"]),
            r["name"],
            r["district"],
            r.get("address"),
            float(r["latitude"]),
            float(r["longitude"]),
            act,
        ))

    with conn.cursor() as cur:
        execute_values(cur, sql, values)
        cur.execute("SELECT setval('hubs_hub_id_seq', (SELECT COALESCE(MAX(hub_id), 1) FROM hubs));")
    return len(hubs)


def seed_users_table(conn) -> int:
    """
    Loads users by calling Member A's seed_users.py if present,
    or inserting the 4 required standard test accounts.
    """
    try:
        import seed.seed_users as su
        if hasattr(su, "seed_users"):
            return su.seed_users(conn)
    except Exception:
        pass

    test_users = [
        ("admin1", "District Admin Control Room", "admin", None, None, None),
        ("officer1", "Chengannur Camp Officer", "camp_officer", 1, None, None),
        ("hub1", "Alappuzha Hub Coordinator", "hub_coordinator", None, 1, None),
        ("donor1", "Test Relief Donor", "donor", None, None, "Alappuzha"),
    ]
    test_hash = "$2b$12$e80MvQ0108u7c8FqTq8Q4eL3sB1Dk9P1A0X9M2W7F4G6H8J0K2L4"

    sql = """
        INSERT INTO users (username, full_name, password_hash, role, camp_id, hub_id, district, active)
        VALUES %s
        ON CONFLICT (username) DO UPDATE SET
            role = EXCLUDED.role,
            camp_id = EXCLUDED.camp_id,
            hub_id = EXCLUDED.hub_id,
            district = EXCLUDED.district;
    """
    values = [(u, fn, test_hash, r, cid, hid, dist, True) for u, fn, r, cid, hid, dist in test_users]

    with conn.cursor() as cur:
        execute_values(cur, sql, values)
        cur.execute("SELECT setval('users_user_id_seq', (SELECT COALESCE(MAX(user_id), 1) FROM users));")
    return len(test_users)


def seed_stock_table(conn, stock: List[Dict[str, str]]) -> int:
    """Inserts initial inventory records into the stock table."""
    with conn.cursor() as cur:
        cur.execute("SELECT item_code, item_id FROM items;")
        code_to_id = {row[0]: row[1] for row in cur.fetchall()}

        values = []
        for r in stock:
            hid = int(r["hub_id"])
            item_code = r["item_code"]
            qty = int(r["qty_available"])
            item_id = code_to_id.get(item_code)
            if not item_id:
                raise ValueError(f"Unknown item_code in seed_stock: {item_code}")
            values.append((hid, item_id, qty))

        sql = """
            INSERT INTO stock (hub_id, item_id, qty_available)
            VALUES %s
            ON CONFLICT (hub_id, item_id) DO UPDATE SET
                qty_available = EXCLUDED.qty_available,
                updated_at = NOW();
        """
        execute_values(cur, sql, values)
    return len(stock)


def seed_requests_tables(conn, request_rows: List[Dict[str, str]]) -> tuple[int, int]:
    """
    Inserts requests and request_items into the database.
    Looks up submitted_by by username ('officer1') or validates user_id.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT item_code, item_id FROM items;")
        code_to_id = {row[0]: row[1] for row in cur.fetchall()}

        # Look up officer1 user_id dynamically
        cur.execute("SELECT user_id FROM users WHERE username = 'officer1';")
        user_row = cur.fetchone()
        default_officer_id = user_row[0] if user_row else 2

        grouped = {}
        for r in request_rows:
            rid = int(r["request_id"])
            if rid not in grouped:
                # determine user_id
                sub = r.get("submitted_by", "").strip()
                if sub.isdigit():
                    sub_id = int(sub)
                else:
                    sub_id = default_officer_id

                esc = r.get("escalated", "false").strip().lower() in ("true", "1", "yes")
                grouped[rid] = {
                    "camp_id": int(r["camp_id"]),
                    "submitted_by": sub_id,
                    "status": r.get("status", "pending"),
                    "escalated": esc,
                    "comment": r.get("comment", ""),
                    "created_at": r.get("created_at", "").strip() or None,
                    "items": [],
                }
            grouped[rid]["items"].append((r["item_code"], int(r["qty_requested"])))

        # Insert requests
        req_values = []
        for rid, req in grouped.items():
            req_values.append((
                rid,
                req["camp_id"],
                req["submitted_by"],
                req["status"],
                req["escalated"],
                req["comment"],
                req["created_at"],
            ))

        req_sql = """
            INSERT INTO requests (request_id, camp_id, submitted_by, status, escalated, comment, created_at)
            VALUES %s
            ON CONFLICT (request_id) DO UPDATE SET
                status = EXCLUDED.status,
                escalated = EXCLUDED.escalated,
                comment = EXCLUDED.comment;
        """
        execute_values(cur, req_sql, req_values)

        # Insert request_items
        item_values = []
        for rid, req in grouped.items():
            for item_code, qty in req["items"]:
                iid = code_to_id.get(item_code)
                if not iid:
                    raise ValueError(f"Unknown item_code in seed_requests: {item_code}")
                item_values.append((rid, iid, qty, 0))

        item_sql = """
            INSERT INTO request_items (request_id, item_id, qty_requested, qty_allocated)
            VALUES %s
            ON CONFLICT (request_id, item_id) DO UPDATE SET
                qty_requested = EXCLUDED.qty_requested;
        """
        execute_values(cur, item_sql, item_values)

        cur.execute("SELECT setval('requests_request_id_seq', (SELECT COALESCE(MAX(request_id), 1) FROM requests));")
        return len(grouped), len(item_values)


def check_database_counts(conn, expected: Dict[str, int]):
    """
    Compares database counts with expected CSV counts.
    Prints MISMATCH if any count differs.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM items;")
        db_items = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM camps;")
        db_camps = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM hubs;")
        db_hubs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users;")
        db_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM stock;")
        db_stock = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM requests;")
        db_requests = cur.fetchone()[0]

    mismatches = []
    if db_items != expected.get("items"):
        mismatches.append(f"items: db={db_items} expected={expected.get('items')}")
    if db_camps != expected.get("camps"):
        mismatches.append(f"camps: db={db_camps} expected={expected.get('camps')}")
    if db_hubs != expected.get("hubs"):
        mismatches.append(f"hubs: db={db_hubs} expected={expected.get('hubs')}")
    if db_stock != expected.get("stock"):
        mismatches.append(f"stock: db={db_stock} expected={expected.get('stock')}")
    if db_requests != expected.get("requests"):
        mismatches.append(f"requests: db={db_requests} expected={expected.get('requests')}")

    if mismatches:
        print("[MISMATCH DETECTED]:", ", ".join(mismatches))
    else:
        print("[COUNTS MATCH]: All database counts match expected seed numbers exactly.")

    # Mandatory final line format specified in prompt
    print(f"items: {db_items}, camps: {db_camps}, hubs: {db_hubs}, users: {db_users}, stock: {db_stock}, requests: {db_requests}")


def load_all_seeds(conn=None, reset: bool = True) -> Dict[str, Any]:
    """
    Programmatic entry point to reset and load all seed data into PostgreSQL.
    Used by test fixtures (conftest.py) and deployment scripts.
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        data = validate_seed_data()
        if reset:
            reset_database(conn)

        with conn:
            seed_items_table(conn, data["items"])
            seed_camps_table(conn, data["camps"])
            seed_hubs_table(conn, data["hubs"])
            seed_users_table(conn)
            seed_stock_table(conn, data["stock"])
            seed_requests_tables(conn, data["requests"])

        expected_counts = {
            "items": len(data["items"]),
            "camps": len(data["camps"]),
            "hubs": len(data["hubs"]),
            "stock": len(data["stock"]),
            "requests": data["unique_requests_count"],
        }
        check_database_counts(conn, expected_counts)
        return data
    finally:
        if close_at_end:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Disaster Relief Seed Data Loader (Member C)")
    parser.add_argument("--only", choices=["items"], help="Load only a specific dataset (e.g. --only items)")
    parser.add_argument("--validate", "--dry-run", action="store_true", help="Validate CSVs without DB connection")
    parser.add_argument("--no-reset", action="store_true", help="Do not run database reset before seeding")
    args = parser.parse_args()

    # 1. Validate all CSV files
    data = validate_seed_data()

    if args.validate:
        print("Dry-Run Validation Succeeded:")
        print(f" - items:        {len(data['items'])} rows")
        print(f" - camps:        {len(data['camps'])} rows")
        print(f" - hubs:         {len(data['hubs'])} rows")
        print(f" - stock:        {len(data['stock'])} rows")
        print(f" - requests:     {data['unique_requests_count']} requests ({len(data['requests'])} lines)")
        return

    # 2. Acquire DB connection
    conn = get_db_connection()

    start_time = time.time()
    try:
        if args.only == "items":
            if not args.no_reset:
                # If only items and reset requested, just truncate/replace items
                pass
            with conn:
                item_count = seed_items_table(conn, data["items"])
            print(f"Seeded {item_count} items.")
        else:
            load_all_seeds(conn=conn, reset=not args.no_reset)

        elapsed = time.time() - start_time
        print(f"Seeding completed in {elapsed:.3f} seconds.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
