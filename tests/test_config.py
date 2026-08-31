from app.config import Settings, get_settings


def test_defaults(monkeypatch):
    # Isolate from process env and any leftover gitignored .env (E2E residue).
    for key in (
        "SERVER_PORT",
        "FETCH_INTERVAL_MINUTES",
        "JWT_SECRET",
        "DB_DSN",
        "DB_DSN_SYNC",
        "REDIS_ADDR",
        "WEB_DIST",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    s = Settings(_env_file=None)
    assert s.server_port == 8080
    assert s.fetch_interval_minutes == 30
    assert s.jwt_secret == "test-secret"


def test_jwt_required(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "")
    get_settings.cache_clear()
    s = Settings(_env_file=None, jwt_secret="")
    try:
        s.validate_for_run()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "JWT_SECRET" in str(e)
