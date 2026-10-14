"""
main.py (Owner: Member A)
=========================
FastAPI application entry point for relief-coordination-system.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Relief Coordination System", version="1.0.0")

# Health check (Guide Section 10)
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Mount priority router (Member C)
from routers.priority_router import router as priority_router
app.include_router(priority_router)

# Mount items router (Member B) if available
try:
    from routers.items_router import router as items_router
    app.include_router(items_router)
except Exception:
    pass

# Mount camp router (Member B) if available
try:
    from routers.camp_router import router as camp_router
    app.include_router(camp_router)
except Exception:
    pass
