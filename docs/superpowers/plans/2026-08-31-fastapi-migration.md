# Humumu FastAPI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Go/Gin backend with Python 3.12 + FastAPI at full feature parity (API, fetch/match/notify pipeline, SPA hosting), then delete Go sources; keep `web/` and `miniprogram/` on the same `/api/v1` contract.

**Architecture:** Single Uvicorn process: FastAPI routers + APScheduler jobs + static `web/dist` SPA fallback. Async SQLAlchemy/asyncpg to PostgreSQL, redis.asyncio for fetch dedup. JWT/bcrypt and WeChat flows match the former Go service.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 async, asyncpg, redis, APScheduler, PyJWT, bcrypt, httpx, feedparser, pydantic-settings, pytest

**Spec:** `docs/superpowers/specs/2026-08-31-fastapi-migration-design.md`

## Global Constraints

- Python **3.12**; API prefix **`/api/v1`**; health **`GET /health`** → `{"status":"ok"}`
- Errors always `{"error":"<string>"}` with appropriate HTTP status
- JWT HS256 claims: `user_id`, `email`; TTL **72h**; header `Authorization: Bearer …`
- List wrappers: `{journals|articles|authors|keywords|notifications|requests|users: [...]}`
- GET journal/article **by id returns bare object** (not wrapped)
- Admin routes: JWT only, **no RBAC** (parity with Go)
- Reuse SQL files `migrations/001`–`008` + `schema_migrations` runner semantics
- Redis dedup keys: `dedup:{journal_id}:{doi}` or `dedup:{journal_id}:url:{url}`, TTL 7 days
- `fetch_interval` in JSON: **integer seconds**
- Do not commit secrets; `.env` gitignored
- Git commit author if needed: env `GIT_AUTHOR_NAME`/`EMAIL` (no `git config` writes unless user asks)
- End state: **no** `cmd/`, `internal/`, `go.mod`, `go.sum`, Go Docker stage

## File structure (target)

```
app/
  main.py
  config.py
  db.py
  redis_client.py
  deps.py
  errors.py
  models/__init__.py          # ORM
  schemas/…                   # Pydantic
  routers/…
  services/auth_tokens.py
  services/password.py
  services/wechat_api.py
  services/fetcher.py
  services/matcher.py
  services/dedup.py
  services/notifier_email.py
  services/notifier_wechat.py
  jobs/scheduler.py
  jobs/fetch_pipeline.py
  jobs/daily_summary.py
  static_spa.py
scripts/migrate.py
tests/…
requirements.txt
pyproject.toml                # optional; requirements.txt is enough
Dockerfile / docker-compose.yml / Makefile / entrypoint.sh / .env.example
```

---

### Task 1: Python project skeleton + config + error helper

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py` (empty)
- Create: `app/config.py`
- Create: `app/errors.py`
- Create: `tests/test_config.py`
- Create: `.env.example` (replace Go-oriented notes; keep keys)
- Modify: `.gitignore` (add `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`)

**Interfaces:**
- Produces: `Settings` via `get_settings()`; `app.errors.error_response(status, msg)` → `JSONResponse`

- [ ] **Step 1: Write failing config test**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run test — expect fail (no module)**

Run: `python -m venv .venv && . .venv/bin/activate && pip install pydantic-settings pytest && pytest tests/test_config.py -v`  
Expected: import error or fail

- [ ] **Step 3: Implement requirements + config + errors**

`requirements.txt`:
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy[asyncio]>=2.0.36
asyncpg>=0.30.0
psycopg2-binary>=2.9.10
redis>=5.2.0
httpx>=0.28.0
feedparser>=6.0.11
PyJWT>=2.9.0
bcrypt>=4.2.0
pydantic-settings>=2.6.0
apscheduler>=3.10.4
email-validator>=2.2.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
```

`app/config.py`:
```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    server_port: int = 8080
    db_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/journal_monitor"
    db_dsn_sync: str = ""  # optional; default derived from db_dsn
    redis_addr: str = "localhost:6379"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""
    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_template_realtime: str = ""
    wechat_template_daily: str = ""
    jwt_secret: str = "change-me-to-something-secure"
    fetch_interval_minutes: int = 30
    web_dist: str = "web/dist"

    def sync_dsn(self) -> str:
        if self.db_dsn_sync:
            return self.db_dsn_sync
        return self.db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    def validate_for_run(self) -> None:
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must not be empty")

    def redis_host_port(self) -> tuple[str, int]:
        host, _, port = self.redis_addr.partition(":")
        return host or "localhost", int(port or "6379")

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Map env names with Field aliases if needed (`JWT_SECRET` → `jwt_secret` works automatically with case-insensitive env in pydantic-settings v2).

`app/errors.py`:
```python
from fastapi.responses import JSONResponse

def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})
```

Update `.env.example` with all keys including `WECHAT_TEMPLATE_REALTIME`, `WECHAT_TEMPLATE_DAILY`, and note async DSN form.

- [ ] **Step 4: Pytest pass**

Run: `pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app/ tests/test_config.py .env.example .gitignore
git commit -m "feat: scaffold FastAPI config and project layout"
```

---

### Task 2: DB session + migration runner

**Files:**
- Create: `app/db.py`
- Create: `scripts/__init__.py`
- Create: `scripts/migrate.py`
- Create: `tests/test_migrate_helpers.py` (pure helpers if any)
- Modify: `Makefile` (python targets; can keep old go targets until Task 14)

**Interfaces:**
- Produces: `get_session` async generator; `init_engine(settings)`; `python -m scripts.migrate` applies `migrations/*.sql` via `schema_migrations`

- [ ] **Step 1: Implement `app/db.py`**

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

def init_engine(dsn: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(dsn, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session

async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
```

- [ ] **Step 2: Implement `scripts/migrate.py`**

Behavior must match Go:
1. Connect with **sync** psycopg2 using `settings.sync_dsn()`
2. `CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`
3. Read applied versions
4. Sort `migrations/*.sql` by filename
5. For each not applied: execute full file SQL; insert version

```python
# scripts/migrate.py
from __future__ import annotations
import sys
from pathlib import Path
import psycopg2
from app.config import get_settings

def main() -> int:
    settings = get_settings()
    root = Path(__file__).resolve().parents[1]
    mig_dir = root / "migrations"
    conn = psycopg2.connect(settings.sync_dsn())
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("SELECT version FROM schema_migrations")
            applied = {r[0] for r in cur.fetchall()}
            files = sorted(p for p in mig_dir.glob("*.sql"))
            for path in files:
                name = path.name
                if name in applied:
                    print(f"  skipping {name} (already applied)")
                    continue
                sql = path.read_text(encoding="utf-8")
                print(f"  running {name} ...")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (name,),
                )
                print("  done")
        conn.commit()
        print("migrate: all migrations complete")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"migrate failed: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Manual migrate against local or docker postgres**

Run:  
`docker compose up -d postgres` (compose still Go-oriented until later — or use existing PG)  
`.venv/bin/python -m scripts.migrate`  
Expected: all 001–008 applied or skipped

If only remote DB is available, use env:
`DB_DSN_SYNC=postgres://bokang:Conti%401234@116.62.106.128:25432/humumu`  
Do **not** put password in committed files.

- [ ] **Step 4: Commit**

```bash
git add app/db.py scripts/migrate.py
git commit -m "feat: add async DB setup and SQL migration runner"
```

---

### Task 3: SQLAlchemy ORM models

**Files:**
- Create: `app/models/__init__.py` exporting all
- Create: `app/models/user.py`, `journal.py`, `article.py`, `subscription.py`, `notification.py`

**Interfaces:**
- Produces: ORM classes matching tables `users`, `journals`, `articles`, `journal_subscriptions`, `author_tracking`, `keyword_subscriptions`, `notifications`, `journal_requests`

- [ ] **Step 1: Implement models (no migration autogen)**

Key mappings:
- UUID primary keys as `Uuid` / `GUID`, server default `gen_random_uuid()` where applicable
- `User.password_hash` never in API schemas later
- `Article.authors`: `ARRAY(Text)`
- `Journal.fetch_interval`: use `Interval` or store as mapped; expose seconds in schema layer
- Relationships optional; prefer explicit queries in routers for parity clarity

Example user:
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    wechat_openid: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    push_frequency: Mapped[str] = mapped_column(String(20), default="realtime")
    wechat_template_subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

Mirror remaining tables from `migrations/*.sql`.

- [ ] **Step 2: Import check**

Run: `python -c "from app.models import User, Journal, Article"`  
Expected: no error

- [ ] **Step 3: Commit**

```bash
git add app/models/
git commit -m "feat: add SQLAlchemy ORM models for existing schema"
```

---

### Task 4: Pydantic schemas + password/JWT services

**Files:**
- Create: `app/schemas/auth.py`, `common.py`, `journal.py`, `article.py`, `subscription.py`, `notification.py`, `admin.py`, `wechat.py`
- Create: `app/services/password.py`
- Create: `app/services/auth_tokens.py`
- Create: `tests/test_password.py`, `tests/test_auth_tokens.py`

**Interfaces:**
- Produces: `hash_password`, `verify_password`, `create_access_token`, `decode_token`  
- Token payload: `{"user_id": str, "email": str, "exp": ...}`

- [ ] **Step 1: Failing tests**

```python
# tests/test_password.py
from app.services.password import hash_password, verify_password

def test_hash_and_verify():
    h = hash_password("secret12")
    assert h != "secret12"
    assert verify_password("secret12", h)
    assert not verify_password("wrong", h)
```

```python
# tests/test_auth_tokens.py
from app.services.auth_tokens import create_access_token, decode_token

def test_roundtrip():
    tok = create_access_token("uid-1", "a@b.com", secret="s", hours=72)
    claims = decode_token(tok, secret="s")
    assert claims["user_id"] == "uid-1"
    assert claims["email"] == "a@b.com"
```

- [ ] **Step 2: Implement services + core schemas**

```python
# app/services/password.py
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False
```

```python
# app/services/auth_tokens.py
from datetime import datetime, timedelta, timezone
import jwt

def create_access_token(user_id: str, email: str, secret: str, hours: int = 72) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=hours),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])
```

Schemas: `RegisterRequest`, `LoginRequest`, `AuthUser` (no password_hash), `AuthResponse(token, user, has_email: bool = True)`, journal/article list wrappers, etc. Use `model_config = ConfigDict(from_attributes=True)`.

`has_email` helper: `not email.endswith("@wechat.user")`.

- [ ] **Step 3: Pytest pass + commit**

```bash
pytest tests/test_password.py tests/test_auth_tokens.py -v
git add app/schemas app/services/password.py app/services/auth_tokens.py tests/
git commit -m "feat: add auth crypto helpers and API schemas"
```

---

### Task 5: FastAPI app shell, deps, CORS, health

**Files:**
- Create: `app/deps.py`
- Create: `app/routers/health.py`
- Create: `app/main.py`
- Create: `tests/test_health.py`

**Interfaces:**
- Produces: `app.main:app`; `get_current_user_id` dependency; CORS `*` methods GET/POST/PUT/DELETE/OPTIONS headers Content-Type, Authorization

- [ ] **Step 1: Health test with httpx ASGI**

```python
# tests/test_health.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
```

- [ ] **Step 2: Implement main + deps**

`deps.py`: parse Bearer, decode JWT, yield `user_id: str` or raise 401 via `HTTPException` **or** return `error_response` pattern — prefer small dependency that raises `HTTPException(status_code=401, detail=...)` **but** FastAPI default detail shape is not `{error:}` — **override** with exception handler:

```python
# in main.py
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from app.errors import error_response

app = FastAPI(title="Humumu")

@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "error"
    return error_response(exc.status_code, msg)
```

Lifespan: `init_engine(settings.db_dsn)`; later tasks add redis + scheduler.

- [ ] **Step 3: Pass health test + commit**

```bash
pytest tests/test_health.py -v
git add app/main.py app/deps.py app/routers/health.py tests/test_health.py
git commit -m "feat: add FastAPI app shell, CORS, and health endpoint"
```

---

### Task 6: Auth routes (register / login)

**Files:**
- Create: `app/routers/auth.py`
- Create: `tests/test_auth_api.py` (use sqlite? prefer **postgres test** or transactional — if no local PG, mock session; preferred: docker postgres DB `journal_monitor_test`)

**Minimal approach without full testcontainers:** unit-test handlers with overridden `get_session` dependency returning in-memory fakes is heavy. Practical path:
1. Integration test marked `@pytest.mark.integration` if `TEST_DB_DSN` set
2. Always keep pure JWT/password tests

For this task include at least one ASGI test with dependency override:

```python
# Override get_session with a fake async session / service layer
```

Alternatively implement a thin `UserRepository` protocol and mock it.

**Recommended structure for routers:** keep SQL in router or small `app/services/users.py` with functions `create_user`, `get_by_email`.

- [ ] **Step 1: Implement `app/services/users.py` + auth router**

Endpoints:
- `POST /api/v1/auth/register` → 201 AuthResponse
- `POST /api/v1/auth/login` → 200 AuthResponse  
Conflicts 409 `"email already registered"`; bad login 401 `"invalid email or password"`

- [ ] **Step 2: Test register validation (password min 6) returns 400 with error key**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add email register and login API"
```

---

### Task 7: Journals + Articles public read + My feed

**Files:**
- Create: `app/routers/journals.py`, `articles.py`
- Create: `app/services/journals.py`, `articles.py` (query helpers)
- Tests: list shape + 404 bare error

**Query parity:**
- List journals: include `article_count`, `last_article_date` via subquery/lateral equivalent
- Articles list: `limit` default 20 max 100, `offset`, optional `journal_id`
- Article/Journal GET by id: **bare model dump**
- `GET /api/v1/my/feed`: JWT; articles from user's subscribed journals

- [ ] **Step 1: Implement routers + services**
- [ ] **Step 2: Manual or pytest smoke**
- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add journals and articles public APIs and my feed"
```

---

### Task 8: Subscriptions + push frequency + notifications

**Files:**
- Create: `app/routers/subscriptions.py`, `settings.py`, `notifications.py`

**Endpoints:** exact paths from spec §3.2  
Subscribe journal: POST body empty OK → `{"message":"subscribed"}`  
Delete → `{"message":"unsubscribed"}`  
Authors/keywords 201 on create with message  
`PUT /settings/push-frequency` body `{push_frequency}` one of realtime|daily

- [ ] Implement + commit: `feat: add subscriptions, settings, and notifications APIs`

---

### Task 9: Journal requests + user self-service RSS journals

**Files:**
- Create: `app/routers/requests.py`, `user_journals.py`
- Create: `app/services/fetcher_meta.py` (Feed preview using feedparser + httpx)

**Endpoints:**
- `POST/GET /api/v1/journals/requests`
- `POST /api/v1/my/journals/preview` `{source_url}` → `{name, source_type}`
- `POST /api/v1/my/journals` `{name, source_url}` → `{journal, already_existed}` + auto subscribe  
Slugify name; `FindByURL` if exists reuse; source_type rss/cnki heuristic optional (default rss)

- [ ] Implement + test preview with sample RSS XML fixture  
- [ ] Commit: `feat: add journal requests and user RSS self-service`

---

### Task 10: WeChat login, bind-account, template settings

**Files:**
- Create: `app/services/wechat_api.py`
- Extend: `app/routers/auth.py`
- Create: `app/routers/wechat.py`
- Test: mock httpx for `jscode2session`

**Behavior:**
- `code2session` URL: `https://api.weixin.qq.com/sns/jscode2session`
- New user stub email `{openid}@wechat.user`
- `has_email` false when email endswith `@wechat.user`
- Template setting get/put `{subscribed: bool}`
- Template ids: `[realtime, daily]` from settings (filter empty)

- [ ] Commit: `feat: add WeChat auth and template setting APIs`

---

### Task 11: Admin routes

**Files:**
- Create: `app/routers/admin.py`

**Endpoints:** stats counts; journals CRUD; list/review requests (`approved`|`rejected`); list users (no password_hash)

- [ ] Commit: `feat: add admin APIs`

---

### Task 12: Fetcher, dedup, matcher, notifiers, scheduler

**Files:**
- Create: `app/redis_client.py`
- Create: `app/services/dedup.py`
- Create: `app/services/fetcher.py`
- Create: `app/services/matcher.py`
- Create: `app/services/notifier_email.py`
- Create: `app/services/notifier_wechat.py`
- Create: `app/jobs/fetch_pipeline.py`
- Create: `app/jobs/daily_summary.py`
- Create: `app/jobs/scheduler.py`
- Create: `tests/test_matcher.py`, `tests/test_dedup_keys.py`, `tests/test_fetcher_parse.py` (fixture XML)

**Dedup:**
```python
async def is_duplicate_and_mark(r, journal_id: str, doi: str | None, url: str) -> bool:
    if doi:
        key = f"dedup:{journal_id}:{doi}"
    else:
        key = f"dedup:{journal_id}:url:{url}"
    # SET NX EX 604800 → True if set (new), False if existed
```

**Matcher:** journal subscribers ∪ author casefold equality ∪ keyword substring in title/abstract; channel wechat if openid else email; **ignore** push_frequency for realtime path.

**Fetcher:** httpx get; feedparser; RawArticle dict; support rss+cnki source types only.

**Scheduler lifespan:**
- interval job every `fetch_interval_minutes`
- cron daily 8:00 local for summary
- shutdown on app stop

**Email/WeChat:** skip send cleanly if SMTP/WeChat env missing (log warning); mark failed with message if attempted and error.

- [ ] Tests for matcher + feed parse fixture  
- [ ] Commit: `feat: add fetch-match-notify pipeline and schedulers`

---

### Task 13: SPA static hosting + wire routers in main

**Files:**
- Create: `app/static_spa.py`
- Modify: `app/main.py` include all routers under `/api/v1`, mount SPA last

**SPA logic (parity with Go):**
- If path starts with `/api/` or path == `/health` → API (already routed)
- If path starts with `/assets/` → FileResponse from `web/dist/assets`
- Else if `web/dist/index.html` exists → return it (history fallback)
- If dist missing → API-only (log warning)

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# catch-all route last:
@app.get("/{full_path:path}")
async def spa(full_path: str):
    ...
```

Do not steal `/api` or `/health`.

- [ ] Commit: `feat: serve Vue SPA from FastAPI`

---

### Task 14: Docker, Makefile, entrypoint, docs; remove Go

**Files:**
- Replace: `Dockerfile`, `entrypoint.sh`, `Makefile`, `docker-compose.yml` app service build
- Update: `README.md`, `docs/architecture.md`, `docs/deployment.md`, `docs/api-reference.md`
- Delete: `cmd/`, `internal/`, `go.mod`, `go.sum`

**Dockerfile:**
```dockerfile
FROM node:20-alpine AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations
COPY --from=web-builder /web/dist ./web/dist
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV SERVER_PORT=8080
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
```

**entrypoint.sh:**
```sh
#!/bin/sh
set -e
python -m scripts.migrate
exec uvicorn app.main:app --host 0.0.0.0 --port "${SERVER_PORT:-8080}"
```

**Makefile:**
```make
.PHONY: install run migrate test frontend docker-build
install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt
frontend:
	cd web && npm run build
run:
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
migrate:
	.venv/bin/python -m scripts.migrate
test:
	.venv/bin/pytest -v
docker-build:
	docker build -t journal-monitor .
```

**compose app environment:** set `DB_DSN=postgresql+asyncpg://postgres:postgres@postgres:5432/journal_monitor` and `DB_DSN_SYNC=postgresql://postgres:postgres@postgres:5432/journal_monitor`.

- [ ] Delete Go tree  
- [ ] Commit: `feat: switch deploy stack to FastAPI and remove Go backend`

---

### Task 15: Miniprogram API client fixes

**Files:**
- Modify: `miniprogram/src/api/articles.ts` — `getArticle` return type `Promise<Article>`; pages use bare object
- Modify: `miniprogram/src/api/journals.ts` — `getJournal` → `Promise<Journal>`
- Modify: `miniprogram/src/pages/article/detail.vue` — stop using `res.article`
- Modify: `miniprogram/src/pages/journals/detail.vue` — stop using `jr.journal`
- Modify: `miniprogram/src/api/subscriptions.ts` — export `updatePushFrequency`
- Modify: `miniprogram/src/api/client.ts` — `BASE_URL` from build env or clear constant comment for production host

- [ ] Commit: `fix: align miniprogram clients with bare API detail responses`

---

### Task 16: End-to-end verification

**Files:** none required beyond fixes

- [ ] **Step 1:** `pip install -r requirements.txt && pytest -v`
- [ ] **Step 2:** migrate + `uvicorn` up; `curl -s localhost:8080/health`
- [ ] **Step 3:** register/login roundtrip via curl
- [ ] **Step 4:** `cd web && npm run build` and confirm `/` serves index through FastAPI
- [ ] **Step 5:** Confirm no `go.mod` left; README describes Python
- [ ] **Step 6:** Final commit if fixes: `chore: verification fixes after FastAPI migration`

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Full `/api/v1` route table | 5–11 |
| JWT/bcrypt/WeChat auth | 4, 6, 10 |
| Migrations 001–008 runner | 2 |
| Redis dedup + fetch/match/notify | 12 |
| Daily summary 08:00 | 12 |
| SPA hosting | 13 |
| Docker/Makefile/docs | 14 |
| Delete Go | 14 |
| Miniprogram bare detail + push freq export | 15 |
| Admin JWT-only | 11 |
| Error shape `{error}` | 5 exception handler |
| fetch_interval seconds | 3–7 schemas |

## Execution notes

- Prefer **subagent-driven-development**: one task per subagent, review between tasks.
- Do not start Task 14 delete-Go until API parity tasks 6–13 are green.
- Never commit `.env` with production passwords.
