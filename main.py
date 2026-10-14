# main.py
# Disaster Relief Coordination System - Main Application

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Import all member routers
from routers.items_router import router as items_router
from routers.camps_router import router as camps_router
from routers.requests_router import router as requests_router
from routers.priority_router import router as priority_router
from routers.hubs_router import router as hubs_router
from routers.stock_router import router as stock_router
from routers.allocation_router import router as allocation_router

app = FastAPI(
    title="Priority-Based Disaster Relief Allocation Platform",
    description="Emergency relief coordination system for Kerala disaster response.",
    version="1.0.0",
)

# Mount all application routers
app.include_router(items_router)
app.include_router(camps_router)
app.include_router(requests_router)
app.include_router(priority_router)
app.include_router(hubs_router)
app.include_router(stock_router)
app.include_router(allocation_router)

# Mount static assets if directory exists
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/health")
def health_check():
    """Health check endpoint specified in DisasterRelief Team Guide Section 10."""
    return {"status": "ok"}


@app.get("/")
def root():
    """Redirect root to relief camps dashboard."""
    return RedirectResponse(url="/camps")
