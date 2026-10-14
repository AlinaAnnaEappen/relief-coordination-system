# config.py (Owner: Member A)
# Project configuration, environment settings, and SAW weights contract (Guide Sections 6.2, 8.2)

import os
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
load_dotenv()  # also load from current dir if any

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/relief_db")
SECRET_KEY = os.environ.get("SECRET_KEY", "relief-coordination-system-dev-secret-key-2026")

# Development login bypass settings (Guide Section 10)
DEV_BYPASS_LOGIN = os.environ.get("DEV_BYPASS_LOGIN", "false").lower() == "true"
DEV_FAKE_ROLE = os.environ.get("DEV_FAKE_ROLE", "admin")
DEV_FAKE_CAMP_ID = int(os.environ.get("DEV_FAKE_CAMP_ID", "1"))
DEV_FAKE_HUB_ID = int(os.environ.get("DEV_FAKE_HUB_ID", "1"))

# SAW Priority Engine Weights Contract (Guide Section 8.2)
SAW_WEIGHTS = {
    "people": 0.20,
    "vulnerable": 0.25,
    "damage": 0.20,
    "access": 0.15,
    "time": 0.10,
    "escalation": 0.10,
}
TIME_CAP_HOURS = 72.0
