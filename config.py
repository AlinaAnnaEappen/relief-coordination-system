# config.py
# System configuration and environment loading

import os
from pathlib import Path
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/relief_db")

# Developer convenience flags for teammate testing without real login sessions
DEV_BYPASS_LOGIN = os.getenv("DEV_BYPASS_LOGIN", "true").lower() in ("true", "1", "yes")
DEV_FAKE_ROLE = os.getenv("DEV_FAKE_ROLE", "admin")
DEV_FAKE_CAMP_ID = int(os.getenv("DEV_FAKE_CAMP_ID", "1")) if os.getenv("DEV_FAKE_CAMP_ID") else 1
DEV_FAKE_HUB_ID = int(os.getenv("DEV_FAKE_HUB_ID", "1")) if os.getenv("DEV_FAKE_HUB_ID") else 1

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-relief-coordination-2026")
