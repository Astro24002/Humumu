import os
from app.config import Settings, get_settings

def test_defaults(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    s = get_settings()
    assert s.server_port == 8080
    assert s.fetch_interval_minutes == 30
    assert s.jwt_secret == "test-secret"

def test_jwt_required(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "")
    get_settings.cache_clear()
    try:
        get_settings().validate_for_run()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JWT_SECRET" in str(e)
