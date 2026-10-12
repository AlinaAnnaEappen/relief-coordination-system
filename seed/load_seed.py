"""
load_seed.py (Owner: Member C)
===============================
Standard Seed Data Loader for DisasterReliefMVP.

Loads test seed datasets into PostgreSQL in the exact required foreign-key sequence:
    1. Items (seed_items.csv)
    2. Camps (seed_camps.csv)
    3. Hubs (seed_hubs.csv)
    4. Users (seed/seed_users.py or fallback test users)
    5. Stock (seed_stock.csv)
    6. Requests & Request Items (seed_requests.csv)

Supports:
    --only items : Loads ONLY the item catalog (for Member B)
    --dry-run / --validate : Validates all CSV rows and foreign key integrity without connecting to DB

Reference: DisasterReliefMVP Team Guide - Section 7, 11 (Task C1)
"""

import sys
import os
import csv
import argparse
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SEED_DIR = os.path.dirname(__file__)


def get_db_connection():
    """
    Attempts to acquire a database connection:
    1. First tries to import get_conn() from database.py (Member A's module).
    2. Falls back to reading DATABASE_URL from .env or os.environ via psycopg2.
    Returns the connection or None if unavailable.
    """
    try:
        from database import get_conn
        return get_conn()
    except ImportError:
        pass

    try:
        import psycopg2
        from dotenv import load_dotenv
        # Load .env from project root if it exists
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            return psycopg2.connect(db_url)
    except Exception:
        pass

    return None


def read_csv(filename: str) -> List[Dict[str, str]]:
    """Reads a CSV file from the seed directory into a list of row dictionaries."""
    filepath = os.path.join(SEED_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Seed file not found: {filepath}")
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def validate_seed_data() -> Dict[str, Any]:
    """
    Validates CSV formats, headers, and foreign-key references across all seed files.
    Returns a dictionary of loaded and validated rows.
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
    """Inserts item records into the items table adhering to the official 14-group schema."""
    with conn.cursor() as cur:
        for r in items:
            perishable = r.get("perishable", "No").strip()
            requires_approval = r.get("requires_approval", "No").strip()
            emergency_eligible = r.get("emergency_eligible", "no").strip().lower() in ("true", "1", "yes")

            cur.execute(
                """
                INSERT INTO items (
                    item_code, name, group_code, group_kind, unit,
                    item_type, perishable, requires_approval, emergency_eligible,
                    notes, active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
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
                """,
                (
                    r["item_code"],
                    r["name"],
                    r["group_code"],
                    r["group_kind"],
                    r["unit"],
                    r.get("item_type", "Consumable"),
                    perishable,
                    requires_approval,
                    emergency_eligible,
                    r.get("notes") or None,
                ),
            )
    return len(items)



def seed_camps_table(conn, camps: List[Dict[str, str]]) -> int:
    """Inserts camps into camps table and updates auto-increment sequence."""
    with conn.cursor() as cur:
        for r in camps:
            last_supply = r.get("last_supply_at") or None
            cur.execute(
                """
                INSERT INTO camps (
                    camp_id, name, district, address, latitude, longitude,
                    capacity, occupancy, children_count, elderly_count,
                    pregnant_count, disabled_count, damage_level, access_difficulty,
                    status, last_supply_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (camp_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    occupancy = EXCLUDED.occupancy,
                    children_count = EXCLUDED.children_count,
                    elderly_count = EXCLUDED.elderly_count,
                    pregnant_count = EXCLUDED.pregnant_count,
                    disabled_count = EXCLUDED.disabled_count,
                    damage_level = EXCLUDED.damage_level,
                    access_difficulty = EXCLUDED.access_difficulty,
                    last_supply_at = EXCLUDED.last_supply_at;
                """,
                (
                    int(r["camp_id"]),
                    r["name"],
                    r["district"],
                    r.get("address"),
                    float(r["latitude"]),
                    float(r["longitude"]),
                    int(r.get("capacity", 0)),
                    int(r.get("occupancy", 0)),
                    int(r.get("children_count", 0)),
                    int(r.get("elderly_count", 0)),
                    int(r.get("pregnant_count", 0)),
                    int(r.get("disabled_count", 0)),
                    int(r.get("damage_level", 1)),
                    int(r.get("access_difficulty", 1)),
                    r.get("status", "active"),
                    last_supply,
                ),
            )
        cur.execute("SELECT setval('camps_camp_id_seq', (SELECT COALESCE(MAX(camp_id), 1) FROM camps));")
    return len(camps)


def seed_hubs_table(conn, hubs: List[Dict[str, str]]) -> int:
    """Inserts hubs into hubs table and updates auto-increment sequence."""
    with conn.cursor() as cur:
        for r in hubs:
            active = r.get("active", "true").lower() in ("true", "1", "yes")
            cur.execute(
                """
                INSERT INTO hubs (
                    hub_id, name, district, address, latitude, longitude, active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hub_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    district = EXCLUDED.district,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    active = EXCLUDED.active;
                """,
                (
                    int(r["hub_id"]),
                    r["name"],
                    r["district"],
                    r.get("address"),
                    float(r["latitude"]),
                    float(r["longitude"]),
                    active,
                ),
            )
        cur.execute("SELECT setval('hubs_hub_id_seq', (SELECT COALESCE(MAX(hub_id), 1) FROM hubs));")
    return len(hubs)


def seed_users_fallback(conn) -> int:
    """
    Creates the 4 required test users (Guide Section 11 A2 & Section 7.1)
    if seed_users.py has not yet been implemented by Member A.
    """
    # Try calling Member A's seed_users module first if available
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
    # Simple test hash placeholder for development
    test_hash = "$2b$12$e80MvQ0108u7c8FqTq8Q4eL3sB1Dk9P1A0X9M2W7F4G6H8J0K2L4"

    count = 0
    with conn.cursor() as cur:
        for username, full_name, role, camp_id, hub_id, district in test_users:
            cur.execute(
                """
                INSERT INTO users (username, full_name, password_hash, role, camp_id, hub_id, district, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (username) DO UPDATE SET
                    role = EXCLUDED.role,
                    camp_id = EXCLUDED.camp_id,
                    hub_id = EXCLUDED.hub_id,
                    district = EXCLUDED.district;
                """,
                (username, full_name, test_hash, role, camp_id, hub_id, district),
            )
            count += 1
    return count


def seed_stock_table(conn, stock: List[Dict[str, str]]) -> int:
    """Inserts initial inventory records into the stock table."""
    with conn.cursor() as cur:
        # Build item_code -> item_id lookup
        cur.execute("SELECT item_code, item_id FROM items;")
        code_to_id = {row[0]: row[1] for row in cur.fetchall()}

        for r in stock:
            hid = int(r["hub_id"])
            item_code = r["item_code"]
            qty = int(r["qty_available"])
            item_id = code_to_id.get(item_code)
            if not item_id:
                continue

            cur.execute(
                """
                INSERT INTO stock (hub_id, item_id, qty_available, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (hub_id, item_id) DO UPDATE SET
                    qty_available = EXCLUDED.qty_available,
                    updated_at = NOW();
                """,
                (hid, item_id, qty),
            )
    return len(stock)


def seed_requests_tables(conn, request_rows: List[Dict[str, str]]) -> tuple[int, int]:
    """
    Inserts requests and their associated request_items into the database.
    Groups request lines by request_id.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT item_code, item_id FROM items;")
        code_to_id = {row[0]: row[1] for row in cur.fetchall()}

        # Group rows by request_id
        grouped = {}
        for r in request_rows:
            rid = int(r["request_id"])
            if rid not in grouped:
                grouped[rid] = {
                    "camp_id": int(r["camp_id"]),
                    "submitted_by": int(r.get("submitted_by", 2)),
                    "status": r.get("status", "pending"),
                    "escalated": r.get("escalated", "false").lower() in ("true", "1", "yes"),
                    "comment": r.get("comment", ""),
                    "created_at": r.get("created_at"),
                    "items": [],
                }
            grouped[rid]["items"].append((r["item_code"], int(r["qty_requested"])))

        total_requests = 0
        total_items = 0

        for rid, req in grouped.items():
            cur.execute(
                """
                INSERT INTO requests (request_id, camp_id, submitted_by, status, escalated, comment, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    escalated = EXCLUDED.escalated,
                    comment = EXCLUDED.comment;
                """,
                (
                    rid,
                    req["camp_id"],
                    req["submitted_by"],
                    req["status"],
                    req["escalated"],
                    req["comment"],
                    req["created_at"],
                ),
            )
            total_requests += 1

            for item_code, qty in req["items"]:
                iid = code_to_id.get(item_code)
                if not iid:
                    continue
                cur.execute(
                    """
                    INSERT INTO request_items (request_id, item_id, qty_requested, qty_allocated)
                    VALUES (%s, %s, %s, 0)
                    ON CONFLICT (request_id, item_id) DO UPDATE SET
                        qty_requested = EXCLUDED.qty_requested;
                    """,
                    (rid, iid, qty),
                )
                total_items += 1

        cur.execute("SELECT setval('requests_request_id_seq', (SELECT COALESCE(MAX(request_id), 1) FROM requests));")
        return total_requests, total_items


def main():
    parser = argparse.ArgumentParser(description="DisasterReliefMVP Seed Data Loader")
    parser.add_argument("--only", choices=["items"], help="Load only a specific dataset (e.g. --only items)")
    parser.add_argument("--validate", "--dry-run", action="store_true", help="Validate CSVs without database connection")
    args = parser.parse_args()

    # 1. Validate all CSV files
    try:
        data = validate_seed_data()
    except Exception as e:
        print(f"\n[ERROR] CSV Validation failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("      DISASTER RELIEF MVP - SEED DATA LOADER")
    print("=" * 60)

    # If dry-run requested, print validation report and exit
    if args.validate:
        print("[SUCCESS] All CSV files validated successfully (Dry-Run Mode):")
        print(f" - items:        {len(data['items'])} rows")
        print(f" - camps:        {len(data['camps'])} rows")
        print(f" - hubs:         {len(data['hubs'])} rows")
        print(f" - stock:        {len(data['stock'])} rows")
        print(f" - requests:     {data['unique_requests_count']} requests ({len(data['requests'])} item lines)")
        print("=" * 60 + "\n")
        return

    # 2. Acquire Database Connection
    conn = get_db_connection()
    if conn is None:
        print("\n[NOTE] Database connection not found (PostgreSQL or database.py not yet configured).")
        print("Running automatic CSV validation summary instead:")
        print(f" - items:        {len(data['items'])} rows")
        print(f" - camps:        {len(data['camps'])} rows")
        print(f" - hubs:         {len(data['hubs'])} rows")
        print(f" - stock:        {len(data['stock'])} rows")
        print(f" - requests:     {data['unique_requests_count']} requests ({len(data['requests'])} item lines)")
        print("\nWhen Member A pushes database.py and PostgreSQL is started,")
        print("re-running 'python seed/load_seed.py' will populate the database automatically.")
        print("=" * 60 + "\n")
        return

    # 3. Perform Database Ingestion inside one transaction
    try:
        with conn:
            if args.only == "items":
                item_count = seed_items_table(conn, data["items"])
                print(f"[OK] Seeded items catalog: {item_count} items")
            else:
                item_count = seed_items_table(conn, data["items"])
                camp_count = seed_camps_table(conn, data["camps"])
                hub_count = seed_hubs_table(conn, data["hubs"])
                user_count = seed_users_fallback(conn)
                stock_count = seed_stock_table(conn, data["stock"])
                req_count, req_item_count = seed_requests_tables(conn, data["requests"])

                print("[SUCCESS] All seed data loaded successfully into database:")
                print(f" - items:         {item_count}")
                print(f" - camps:         {camp_count}")
                print(f" - hubs:          {hub_count}")
                print(f" - users:         {user_count}")
                print(f" - stock:         {stock_count}")
                print(f" - requests:      {req_count} requests ({req_item_count} items)")
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Database loading failed: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
