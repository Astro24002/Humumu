"""Serve the built Vue SPA (web/dist) alongside the API.

Parity with Go cmd/server/main.go:
- /api/* and /health are handled by FastAPI routers registered first
- /assets/* is served from {dist}/assets
- other GET paths fall back to index.html (Vue history mode)
- missing dist → log warning and run API-only
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def mount_spa(app: FastAPI, dist_dir: str = "web/dist") -> None:
    """Mount static assets and SPA history-mode fallback.

    Must be called **after** all API routers so /api and /health match first.
    """
    dist = Path(dist_dir)
    assets = dist / "assets"
    index = dist / "index.html"

    if not index.is_file():
        logger.warning("SPA dist missing at %s — API only", dist.resolve())
        return

    logger.info("serving SPA from %s", dist.resolve())

    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        # Defensive: routers already own these; never serve SPA for them.
        if full_path.startswith("api/") or full_path == "api" or full_path == "health":
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(index)
