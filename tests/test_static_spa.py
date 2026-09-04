"""Tests for Vue SPA static hosting helpers."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.static_spa import mount_spa


def test_mount_spa_missing_dist_does_not_crash(tmp_path: Path, caplog):
    app = FastAPI()
    missing = tmp_path / "no-such-dist"
    with caplog.at_level("WARNING"):
        mount_spa(app, str(missing))
    assert any("SPA dist missing" in r.message for r in caplog.records)
    # No catch-all route registered when index is absent
    paths = [getattr(r, "path", None) for r in app.routes]
    assert "/{full_path:path}" not in paths


@pytest.mark.asyncio
async def test_mount_spa_serves_index_and_assets(tmp_path: Path):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    index = dist / "index.html"
    index.write_text("<!doctype html><html><body>spa</body></html>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/ping")
    async def ping():
        return {"pong": True}

    mount_spa(app, str(dist))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/foo/bar")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "spa" in r.text

        r = await client.get("/")
        assert r.status_code == 200
        assert "spa" in r.text

        r = await client.get("/assets/app.js")
        assert r.status_code == 200
        assert "console.log" in r.text

        # API routes still win
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

        r = await client.get("/api/v1/ping")
        assert r.status_code == 200
        assert r.json() == {"pong": True}


@pytest.mark.asyncio
async def test_mount_spa_serves_real_dist_files(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")
    (dist / "favicon.ico").write_bytes(b"\x00\x01favicon")
    (dist / "robots.txt").write_text("User-agent: *\nDisallow:\n", encoding="utf-8")

    app = FastAPI()
    mount_spa(app, str(dist))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/favicon.ico")
        assert r.status_code == 200
        assert r.content.startswith(b"\x00\x01")

        r = await client.get("/robots.txt")
        assert r.status_code == 200
        assert "User-agent" in r.text

        # Unknown paths still fall back to index.html (history mode).
        r = await client.get("/journals/some-id")
        assert r.status_code == 200
        assert "spa" in r.text
