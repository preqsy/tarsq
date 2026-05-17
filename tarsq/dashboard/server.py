"""
Tarsq Dashboard server.

Serves the compiled frontend from static/ and exposes JSON API endpoints
that read live data from Redis.

Usage:
    # Programmatic
    from tarsq.dashboard.server import create_app
    import uvicorn
    uvicorn.run(create_app(app="myproject.tasks"), host="0.0.0.0", port=8265)

    # CLI (after tarsq adds the dashboard command)
    tarsq dashboard --app myproject.tasks --port 8265
"""

import importlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tarsq.dashboard.api import router as api_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app(app: str | None = None) -> FastAPI:
    """Create and return the dashboard FastAPI application.

    Args:
        app: Optional dotted module path to import before starting (e.g.
             ``"myproject.tasks"``).  Importing this module runs all
             ``@task`` and ``@schedule`` decorators so the schedules
             endpoint can list them.
    """
    if app:
        importlib.import_module(app)

    dashboard = FastAPI(
        title="Tarsq Dashboard",
        description="Real-time task queue monitoring",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )

    dashboard.include_router(api_router, prefix="/api")

    if STATIC_DIR.exists():
        dashboard.mount(
            "/",
            StaticFiles(directory=STATIC_DIR, html=True),
            name="static",
        )

    return dashboard
