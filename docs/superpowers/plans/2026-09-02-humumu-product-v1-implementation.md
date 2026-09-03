# Humumu Product v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the existing FastAPI journal-monitor into Humumu v1: academic paper discovery platform with real admin RBAC, private/public source isolation, SSRF-safe feed fetch, CAS classification, per-subscription notify prefs, reading status, and decoupled notification retry — without Kafka/Celery/microservices.

**Architecture:** Stay on the FastAPI + APScheduler + PostgreSQL + Redis monolith. Extend Journal/Subscription/Notification models via numbered SQL migrations; add CAS category tables and user_article_status; harden fetcher URL validation; filter public lists by directory_status; require `users.is_admin` for admin routes; process notifications via a scheduled outbox sweep instead of inline send-only.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, PostgreSQL 16, Redis 7, APScheduler, httpx, feedparser, pytest, Vue 3 (minimal UI updates)

**Spec:** `docs/superpowers/specs/2026-09-02-humumu-product-v1-design.md`

## Global Constraints

- Stay **monolith**: FastAPI + APScheduler + PG + Redis. No Kafka, Celery, or microservices.
- **Metadata only** — never store full-text PDF/HTML bodies.
- Public catalog/API returns **only** journals with `directory_status = 'public'` (and active where applicable).
- Private = not in public catalog/API; same normalized feed URL is fetched once globally.
- CAS classification is **display/filter only** — does **not** drive notifications.
- Preprints use `content_type='preprint'` and do **not** get CAS zones.
- Dedup final authority is **PostgreSQL unique constraints**; Redis is acceleration only.
- SSRF: only http(s); reject localhost/private/link-local/metadata IPs; re-check after every redirect; timeouts + max body.
- Admin APIs require **real admin role** (`users.is_admin = true`); any JWT is not enough.
- Email is primary channel; WeChat is enhancement; WeChat failure must not block Email.
- Default user push frequency becomes **daily**; per-subscription can override to realtime.
- API prefix `/api/v1`; errors `{"error":"<string>"}`; list wrappers keep existing shapes.
- `fetch_interval` in JSON remains **integer seconds**.
- Migrations are numbered SQL files under `migrations/` applied by `scripts/migrate.py`.
- Tests are primarily ASGI + mocked services (match existing test style); pure unit tests for SSRF/normalize/dedup helpers.
- Do not commit secrets. Prefer frequent small commits.
- YAGNI: no AI summary, no full-text reader, no school custom zones, no team collab in this plan.
- Frontend: update only what is required for the new API fields/flows; no full redesign.

## File structure (target additions)

```
migrations/
  009_users_is_admin.sql
  010_journals_v1_fields.sql
  011_articles_guid_unique.sql
  012_cas_categories.sql
  013_journal_subscriptions_notify.sql
  014_user_article_status.sql
  015_notifications_retry.sql
app/
  deps.py                          # + require_admin
  models/user.py                   # + is_admin
  models/journal.py                # + v1 fields, CAS models
  models/article.py                # + guid
  models/subscription.py           # + notify prefs
  models/user_article_status.py    # NEW
  models/notification.py           # + attempt/next_attempt
  services/url_safety.py           # NEW SSRF
  services/feed_url.py             # NEW normalize
  services/fetcher.py              # use safe client
  services/fetcher_meta.py         # use safe client + preview items
  services/dedup.py                # multi-key
  services/journals.py             # visibility filters
  services/categories.py           # NEW
  services/reading_status.py       # NEW
  services/matcher.py              # hit reasons + sub prefs
  jobs/fetch_pipeline.py           # health + enqueue only
  jobs/notify_dispatch.py          # NEW outbox sender
  jobs/scheduler.py                # + notify job
  routers/admin.py                 # require_admin + review/hide
  routers/journals.py              # public filter + CAS query
  routers/articles.py              # public filter
  routers/user_journals.py         # private/public apply
  routers/my_updates.py            # NEW
  routers/reading.py               # NEW
  schemas/...
tests/
  test_url_safety.py
  test_feed_url_normalize.py
  test_admin_rbac.py
  test_journal_visibility.py
  test_ssrf_fetcher_meta.py
  test_reading_status_api.py
  test_subscription_notify_prefs.py
  test_notify_dispatch.py
  test_categories_api.py
```

## Phase map (spec §4.4)

| Phase | Tasks | Theme |
|-------|-------|-------|
| 1 Platform foundation | 1–8 | admin RBAC, journal visibility, isolation, SSRF, feed health |
| 2 User closed loop | 9–16 | CAS, custom RSS private/public, sub prefs, reading status, notify outbox |
| 3 Catalog cold start | 17–18 | seed quality + content_type tagging |
| 4 Hardening | 19–20 | regression suite + docs |

---

### Task 1: Admin role — migration + model + require_admin

**Files:**
- Create: `migrations/009_users_is_admin.sql`
- Modify: `app/models/user.py`
- Modify: `app/deps.py`
- Modify: `app/routers/admin.py` (swap `get_current_user_id` → `require_admin` on every route)
- Modify: `app/services/users.py` (optional helper `is_admin_user`)
- Create: `tests/test_admin_rbac.py`
- Modify: `tests/test_admin_api.py` (authed fixture must mark admin)

**Interfaces:**
- Produces: `async def require_admin(authorization: str | None = Header(default=None), session: AsyncSession = Depends(get_session)) -> str` returning admin user_id or 401/403
- Produces: `User.is_admin: bool` default False
- Consumes: existing JWT via `decode_token`

- [ ] **Step 1: Write failing RBAC tests**

```python
# tests/test_admin_rbac.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id, require_admin
from app.main import app


class _EmptySession:
    async def execute(self, statement):
        raise AssertionError("not used")
    async def commit(self):
        return None


@pytest.fixture
async def client():
    async def override_get_session():
        yield _EmptySession()
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_stats_401_without_token(client):
    # Ensure require_admin path is used (clear any overrides)
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user_id, None)
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_403_for_non_admin(client):
    async def override_require_admin():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="admin required")

    app.dependency_overrides[require_admin] = override_require_admin
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 403
    assert r.json()["error"] == "admin required"
    app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_admin_stats_200_for_admin(client):
    uid = str(uuid.uuid4())

    async def override_require_admin():
        return uid

    app.dependency_overrides[require_admin] = override_require_admin
    with (
        patch("app.routers.admin.journal_service.count_journals", new_callable=AsyncMock, return_value=1),
        patch("app.routers.admin.article_service.count_articles", new_callable=AsyncMock, return_value=2),
        patch("app.routers.admin.user_service.count_users", new_callable=AsyncMock, return_value=3),
        patch("app.routers.admin.journal_service.count_pending_requests", new_callable=AsyncMock, return_value=0),
    ):
        r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    assert r.json()["journal_count"] == 1
    app.dependency_overrides.pop(require_admin, None)
```

- [ ] **Step 2: Run test — expect fail (require_admin missing)**

Run: `.venv/bin/pytest tests/test_admin_rbac.py -v`
Expected: import error or 401/200 mismatch because admin still uses `get_current_user_id` only

- [ ] **Step 3: Migration + model**

`migrations/009_users_is_admin.sql`:
```sql
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- Optional bootstrap: leave false; ops can UPDATE users SET is_admin=true WHERE email='...';
```

`app/models/user.py` add field after `wechat_template_subscribed`:
```python
is_admin: Mapped[bool] = mapped_column(
    Boolean, nullable=False, server_default="false"
)
```

- [ ] **Step 4: Implement require_admin in deps.py**

```python
# app/deps.py — full file replacement pattern
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.services.auth_tokens import decode_token
from app.services import users as user_service


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="invalid authorization format")

    settings = get_settings()
    try:
        payload = decode_token(parts[1], settings.jwt_secret)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token") from None

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return str(user_id)


async def require_admin(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> str:
    user_id = await get_current_user_id(authorization)
    user = await user_service.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    if not bool(getattr(user, "is_admin", False)):
        raise HTTPException(status_code=403, detail="admin required")
    return user_id
```

- [ ] **Step 5: Wire admin router**

In `app/routers/admin.py`, replace every `Depends(get_current_user_id)` with `Depends(require_admin)`. Update import.

- [ ] **Step 6: Fix existing admin tests fixture**

In `tests/test_admin_api.py`, change the authed fixture to override `require_admin` (not only `get_current_user_id`):

```python
@pytest.fixture
def authed_user_id():
    uid = str(uuid.uuid4())
    from app.deps import require_admin, get_current_user_id

    async def _admin():
        return uid

    async def _user():
        return uid

    app.dependency_overrides[require_admin] = _admin
    app.dependency_overrides[get_current_user_id] = _user
    yield uid
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user_id, None)
```

(Adapt to whatever fixture shape already exists — the key is overriding `require_admin`.)

- [ ] **Step 7: Run tests**

Run: `.venv/bin/pytest tests/test_admin_rbac.py tests/test_admin_api.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add migrations/009_users_is_admin.sql app/models/user.py app/deps.py app/routers/admin.py tests/test_admin_rbac.py tests/test_admin_api.py
git commit -m "$(cat <<'EOF'
feat: require real admin role for admin APIs

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Journal v1 fields — migration + ORM

**Files:**
- Create: `migrations/010_journals_v1_fields.sql`
- Modify: `app/models/journal.py`
- Modify: `app/schemas/journal.py` (add optional new fields to JournalOut)
- Modify: `app/services/journals.py` (`_journal_out` pass-through)
- Create: `tests/test_journal_model_fields.py` (schema validation unit test)

**Interfaces:**
- Produces Journal columns:
  - `content_type` TEXT NOT NULL DEFAULT `'journal'` CHECK IN (`journal`,`preprint`)
  - `directory_status` TEXT NOT NULL DEFAULT `'public'` CHECK IN (`private`,`pending_review`,`public`,`rejected`,`hidden`)
  - `homepage_url` TEXT NOT NULL DEFAULT `''`
  - `normalized_source_url` TEXT NULL
  - `etag` TEXT NULL
  - `last_modified` TEXT NULL
  - `last_fetched_at` TIMESTAMPTZ NULL
  - `last_success_at` TIMESTAMPTZ NULL
  - `consecutive_failures` INT NOT NULL DEFAULT 0
  - `last_error` TEXT NULL
- Index: `(directory_status)`, unique partial index on `normalized_source_url` WHERE NOT NULL
- Existing rows backfill: `directory_status='public'`, `content_type='journal'` (seed may retag preprints later)
- Expand `source_type` check to include at least: `rss`,`atom`,`arxiv`,`crossref`,`pubmed`,`cnki`

- [ ] **Step 1: Write schema unit test for new JournalOut fields**

```python
# tests/test_journal_model_fields.py
from datetime import datetime, timezone
from app.schemas.journal import JournalOut

def test_journal_out_accepts_v1_fields():
    j = JournalOut.model_validate({
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Nature",
        "slug": "nature",
        "source_type": "rss",
        "source_url": "https://example.com/n.rss",
        "description": "",
        "fetch_interval": 1800,
        "is_active": True,
        "created_by": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "content_type": "journal",
        "directory_status": "public",
        "homepage_url": "https://nature.com",
        "consecutive_failures": 0,
    })
    assert j.content_type == "journal"
    assert j.directory_status == "public"
    assert j.homepage_url == "https://nature.com"
```

- [ ] **Step 2: Run — expect fail (fields missing on schema)**

Run: `.venv/bin/pytest tests/test_journal_model_fields.py -v`

- [ ] **Step 3: Migration**

```sql
-- migrations/010_journals_v1_fields.sql
ALTER TABLE journals DROP CONSTRAINT IF EXISTS journals_source_type_check;
ALTER TABLE journals ADD CONSTRAINT journals_source_type_check
    CHECK (source_type IN ('rss', 'atom', 'arxiv', 'crossref', 'pubmed', 'cnki'));

ALTER TABLE journals ADD COLUMN IF NOT EXISTS content_type VARCHAR(20) NOT NULL DEFAULT 'journal';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS directory_status VARCHAR(20) NOT NULL DEFAULT 'public';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS homepage_url TEXT NOT NULL DEFAULT '';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS normalized_source_url TEXT;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS etag TEXT;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_modified TEXT;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_fetched_at TIMESTAMPTZ;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_success_at TIMESTAMPTZ;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER NOT NULL DEFAULT 0;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_error TEXT;

ALTER TABLE journals DROP CONSTRAINT IF EXISTS journals_content_type_check;
ALTER TABLE journals ADD CONSTRAINT journals_content_type_check
    CHECK (content_type IN ('journal', 'preprint'));

ALTER TABLE journals DROP CONSTRAINT IF EXISTS journals_directory_status_check;
ALTER TABLE journals ADD CONSTRAINT journals_directory_status_check
    CHECK (directory_status IN ('private', 'pending_review', 'public', 'rejected', 'hidden'));

CREATE INDEX IF NOT EXISTS idx_journals_directory_status ON journals(directory_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_journals_normalized_source_url
    ON journals (normalized_source_url)
    WHERE normalized_source_url IS NOT NULL;
```

- [ ] **Step 4: Update ORM + JournalOut + _journal_out**

Add Mapped columns on `Journal` matching migration.

`JournalOut` add with defaults so old tests keep working:
```python
content_type: str = "journal"
directory_status: str = "public"
homepage_url: str = ""
consecutive_failures: int = 0
last_error: str | None = None
last_success_at: datetime | None = None
# health summary for public UI optional:
health_status: str | None = None  # "ok" | "paused" | None — computed in service later OK
```

Update `_journal_out` in `journals.py` to include the new attributes from the ORM object.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/test_journal_model_fields.py tests/test_journals_articles_api.py tests/test_admin_api.py -v`
Expected: PASS (defaults keep old fixtures valid)

- [ ] **Step 6: Commit**

```bash
git add migrations/010_journals_v1_fields.sql app/models/journal.py app/schemas/journal.py app/services/journals.py tests/test_journal_model_fields.py
git commit -m "$(cat <<'EOF'
feat: extend journals with visibility, content type, and fetch health fields

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Public catalog visibility filter

**Files:**
- Modify: `app/services/journals.py` (`list_journals`, `get_journal` public paths)
- Modify: `app/services/articles.py` (public list/get join filter)
- Modify: `app/routers/journals.py` / `articles.py` if they bypass service filters
- Create: `tests/test_journal_visibility.py`

**Interfaces:**
- `list_journals(session, *, public_only: bool = True, ...)` 
- Public endpoints call with `public_only=True`
- Admin list uses `public_only=False`
- Article public lists must INNER JOIN journals and require `directory_status='public'`
- Owner can still see own non-public journals via `/api/v1/my/...` (later tasks); this task only locks **public** routes

- [ ] **Step 1: Failing tests**

```python
# tests/test_journal_visibility.py
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.db import get_session
from app.main import app
from app.schemas.journal import JournalOut


class _EmptySession:
    async def execute(self, statement):
        raise AssertionError("unused")


def _j(**kw):
    base = dict(
        id=str(uuid.uuid4()), name="X", slug="x", source_type="rss",
        source_url="https://ex.com/x.rss", description="", fetch_interval=1800,
        is_active=True, created_by=None,
        created_at=datetime(2026,1,1,tzinfo=timezone.utc),
        directory_status="public", content_type="journal",
    )
    base.update(kw)
    return JournalOut.model_validate(base)


@pytest.fixture
async def client():
    async def ov():
        yield _EmptySession()
    app.dependency_overrides[get_session] = ov
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_public_list_does_not_return_private(client):
    """Router must call list_journals with public_only=True (or equivalent)."""
    with patch(
        "app.routers.journals.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=[_j(directory_status="public")],
    ) as m:
        r = await client.get("/api/v1/journals")
    assert r.status_code == 200
    assert all(j["directory_status"] == "public" for j in r.json()["journals"])
    # Prefer asserting kwargs if service supports public_only
    if m.await_args and m.await_args.kwargs:
        assert m.await_args.kwargs.get("public_only", True) is True
```

Also add a **service-level** unit test if easier: patch session execute — or test SQL construction via a small pure helper:

```python
# In journals service
PUBLIC_DIRECTORY_STATUSES = frozenset({"public"})

def is_public_directory_status(status: str) -> bool:
    return status == "public"
```

- [ ] **Step 2: Run — may pass vacuously until service filters; strengthen with service test**

Add service test using real SQLAlchemy compilation or an integration-style mock of `session.execute` capturing the statement — simplest approach accepted by plan:

Implement `list_journals(..., public_only: bool = True)` and when True add `Journal.directory_status == "public"`.

Admin `list_journals` call sites pass `public_only=False`.

- [ ] **Step 3: Implement filters in journals.py and articles.py**

`list_journals`:
```python
async def list_journals(
    session: AsyncSession,
    *,
    public_only: bool = True,
    content_type: str | None = None,
    q: str | None = None,
) -> list[JournalOut]:
    stmt = select(Journal)
    if public_only:
        stmt = stmt.where(Journal.directory_status == "public")
        stmt = stmt.where(Journal.is_active.is_(True))
    if content_type:
        stmt = stmt.where(Journal.content_type == content_type)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Journal.name.ilike(like))
    stmt = stmt.order_by(Journal.name)
    # ... existing article_count aggregation logic preserved
```

`get_journal` for public router: if found but not public → behave as 404.

Articles public list: join Journal, filter `directory_status=='public'`.

- [ ] **Step 4: Admin router passes public_only=False**

- [ ] **Step 5: Tests green + commit**

```bash
git add app/services/journals.py app/services/articles.py app/routers/journals.py app/routers/articles.py app/routers/admin.py tests/test_journal_visibility.py
git commit -m "$(cat <<'EOF'
feat: filter public journal/article APIs by directory_status

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Feed URL normalize + unique lookup

**Files:**
- Create: `app/services/feed_url.py`
- Create: `tests/test_feed_url_normalize.py`
- Modify: `app/services/journals.py` (`find_by_url` uses normalized form; set `normalized_source_url` on create)

**Interfaces:**
```python
def normalize_feed_url(url: str) -> str:
    """Lowercase scheme/host; strip default ports; remove fragment; strip trailing slash on path;
    sort query unless order-significant (keep simple: drop empty query, keep as-is otherwise).
    """
```

- [ ] **Step 1: Tests**

```python
# tests/test_feed_url_normalize.py
from app.services.feed_url import normalize_feed_url

def test_lowercase_host_and_strip_slash():
    assert normalize_feed_url("HTTPS://Example.COM/Feed/") == "https://example.com/Feed"

def test_strip_fragment():
    assert normalize_feed_url("https://example.com/a.rss#x") == "https://example.com/a.rss"

def test_default_https_port():
    assert normalize_feed_url("https://example.com:443/a.rss") == "https://example.com/a.rss"
```

- [ ] **Step 2: Implement + wire create/find**

`find_by_url`: compare against `normalized_source_url` first, fallback `source_url`.

On `create_journal`, compute and store `normalized_source_url`.

- [ ] **Step 3: Commit**

```bash
git add app/services/feed_url.py app/services/journals.py tests/test_feed_url_normalize.py
git commit -m "$(cat <<'EOF'
feat: normalize feed URLs for journal dedup lookup

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: SSRF-safe outbound HTTP

**Files:**
- Create: `app/services/url_safety.py`
- Create: `tests/test_url_safety.py`
- Modify: `app/services/fetcher.py` and `fetcher_meta.py` to use safe fetch helper
- Modify: `app/routers/user_journals.py` to call validation before fetch

**Interfaces:**
```python
class UnsafeURLError(ValueError): ...

def validate_public_http_url(url: str) -> str:
    """Return normalized URL or raise UnsafeURLError.
    - scheme http/https only
    - resolve host; reject if any A/AAAA is private/loopback/link-local/multicast/unspecified
      or literal such IPs; reject metadata hostnames (metadata.google.internal, etc.)
    """

async def safe_get_text(
    url: str,
    *,
    timeout: float = 15.0,
    max_bytes: int = 2_000_000,
    headers: dict[str, str] | None = None,
    max_redirects: int = 5,
) -> tuple[str, str, dict[str, str]]:
    """GET with manual redirect handling; validate each hop.
    Returns (final_url, body_text, response_headers_of_interest).
    """
```

- [ ] **Step 1: Unit tests for validate_public_http_url**

```python
# tests/test_url_safety.py
import pytest
from app.services.url_safety import UnsafeURLError, validate_public_http_url

def test_rejects_non_http():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("file:///etc/passwd")

def test_rejects_localhost():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://localhost/x")

def test_rejects_127():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://127.0.0.1/x")

def test_rejects_private_ip():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://192.168.1.1/x")

def test_rejects_metadata_ip():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://169.254.169.254/latest/meta-data")

def test_allows_public_literal_docs_example():
    # 8.8.8.8 is public; validation of literals should allow public IPs
    assert validate_public_http_url("https://8.8.8.8/robots.txt").startswith("https://")
```

For hostname resolution tests, mock `socket.getaddrinfo` to return private vs public.

- [ ] **Step 2: Implement url_safety.py** using stdlib `ipaddress` + `socket.getaddrinfo`

Manual redirects with httpx `follow_redirects=False`; on 3xx read Location; validate; continue. Cap body via stream read.

- [ ] **Step 3: Switch fetcher_meta.fetch_feed_meta and fetcher.fetch_articles HTTP get to safe_get_text**

- [ ] **Step 4: user_journals preview/create call validate before fetch; map UnsafeURLError → 400**

- [ ] **Step 5: Tests + commit**

```bash
git add app/services/url_safety.py app/services/fetcher.py app/services/fetcher_meta.py app/routers/user_journals.py tests/test_url_safety.py
git commit -m "$(cat <<'EOF'
feat: SSRF-safe outbound HTTP for feed fetch and preview

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Article guid + DB-backed dedup keys

**Files:**
- Create: `migrations/011_articles_guid_unique.sql`
- Modify: `app/models/article.py` add `guid: Mapped[str | None]`
- Modify: `app/services/fetcher.py` RawArticle + parse guid from entry id/guid
- Modify: `app/services/dedup.py` multi-key helpers (still Redis accel)
- Modify: `app/jobs/fetch_pipeline.py` insert uses guid; catch IntegrityError as dup
- Modify: `tests/test_dedup_keys.py`
- Modify: `tests/test_fetcher_parse.py` if needed

**Interfaces:**
- Dedup priority: DOI > guid > normalized url > (title+date within journal) soft
- DB:
```sql
ALTER TABLE articles ADD COLUMN IF NOT EXISTS guid TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_journal_doi
  ON articles (journal_id, doi) WHERE doi IS NOT NULL AND doi <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_journal_guid
  ON articles (journal_id, guid) WHERE guid IS NOT NULL AND guid <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_journal_url
  ON articles (journal_id, url) WHERE url IS NOT NULL AND url <> '';
-- Keep old UNIQUE(doi,journal_id) behavior compatible; if constraint name exists, drop and replace carefully
```

Note: existing `UNIQUE(doi, journal_id)` from 003 — with nullable doi, multiple NULLs are allowed in PostgreSQL. Prefer explicit partial unique indexes above; drop old constraint if it conflicts:
```sql
ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_doi_journal_id_key;
```

- [ ] **Steps:** TDD on `dedup_key` variants + pipeline IntegrityError path treated as skip; commit

```bash
git commit -m "$(cat <<'EOF'
feat: article guid column and DB-first multi-key dedup

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Feed health recording in fetch pipeline

**Files:**
- Modify: `app/jobs/fetch_pipeline.py`
- Create: `tests/test_fetch_health.py` (unit-test helpers with mocked session)

**Behavior:**
- Before/after each journal fetch update `last_fetched_at`
- On success: `last_success_at=now`, `consecutive_failures=0`, `last_error=NULL`, store etag/last-modified if present
- On failure: `consecutive_failures += 1`, `last_error=str(exc)[:1000]`
- If `consecutive_failures >= 10`: set `is_active=False` (paused) — admin can re-enable
- Conditional GET: pass If-None-Match / If-Modified-Since when etag/last_modified set; on 304 skip parse

- [ ] Implement + tests + commit

```bash
git commit -m "$(cat <<'EOF'
feat: record journal fetch health and auto-pause after repeated failures

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Admin feed health + hide/unhide + review directory_status

**Files:**
- Modify: `app/routers/admin.py`
- Modify: `app/schemas/admin.py` / `journal.py`
- Modify: `app/services/journals.py` (`review_user_journal`, `set_directory_status`)
- Modify: `tests/test_admin_api.py`

**Endpoints (add):**
- `POST /api/v1/admin/journals/{id}/directory_status` body `{"directory_status":"public"|"hidden"|...}`
- Extend existing request review: when approving a journal request OR pending journal, set `directory_status='public'`
- List journals admin response includes health fields

Also: when user applies for public (Task 11), admin approves by setting status public.

- [ ] Tests for 403 still, and status update message
- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: admin directory_status controls and health fields in admin list

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: CAS category tables + admin/public filter API

**Files:**
- Create: `migrations/012_cas_categories.sql`
- Create: `app/models/category.py` (or extend journal.py)
- Create: `app/services/categories.py`
- Create: `app/routers/categories.py` (public list facets)
- Modify: `app/main.py` include router
- Modify: `app/routers/journals.py` accept query params `major`, `minor`, `zone`, `top`, `year`, `content_type`
- Create: `tests/test_categories_api.py`

**Schema:**
```sql
CREATE TABLE cas_category_years (
  year INT PRIMARY KEY
);

CREATE TABLE cas_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  year INT NOT NULL REFERENCES cas_category_years(year) ON DELETE CASCADE,
  major VARCHAR(64) NOT NULL,
  minor VARCHAR(128) NOT NULL,
  zone SMALLINT NOT NULL CHECK (zone BETWEEN 1 AND 4),
  is_top BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (year, major, minor, zone, is_top)
);

CREATE TABLE journal_cas_categories (
  journal_id UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES cas_categories(id) ON DELETE CASCADE,
  PRIMARY KEY (journal_id, category_id)
);
```

Public journals list joins categories when filters present. Preprints never required to have rows.

Admin CRUD minimal: `POST /api/v1/admin/cas/categories` and attach `POST /api/v1/admin/journals/{id}/cas` body `{category_ids:[]}` — keep minimal for v1.

- [ ] TDD API shape + commit

```bash
git commit -m "$(cat <<'EOF'
feat: CAS category tables and public journal filters

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Richer feed preview (recent items)

**Files:**
- Modify: `app/services/fetcher_meta.py` return items list (title, url, published)
- Modify: `app/schemas/journal.py` PreviewResponse
- Modify: `app/routers/user_journals.py`
- Modify: `tests/test_journal_requests_user_journals_api.py`

**PreviewResponse:**
```python
class PreviewItem(BaseModel):
    title: str
    url: str = ""
    published: str = ""

class PreviewResponse(BaseModel):
    name: str
    source_type: str
    items: list[PreviewItem] = []
```

Cap items at 5. Still SSRF-safe.

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: RSS preview returns recent item metadata

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: User add source — private vs apply public

**Files:**
- Modify: `app/schemas/journal.py` CreateUserJournalRequest
- Modify: `app/routers/user_journals.py`
- Modify: `app/services/journals.py`
- Modify: tests

**Request:**
```python
class CreateUserJournalRequest(BaseModel):
    source_url: str = ""
    name: str = ""
    visibility: str = "private"  # "private" | "apply_public"
```

**Behavior:**
1. validate + normalize URL (SSRF)
2. if existing normalized URL → subscribe caller; do not leak other creator identity; return already_existed
3. else create journal:
   - `directory_status='private'` if visibility private
   - `directory_status='pending_review'` if apply_public
   - `created_by=user`
   - `content_type` default journal (user cannot set preprint arbitrarily in v1 unless URL host in allowlist arxiv/biorxiv/medrxiv → preprint)
4. auto-subscribe creator
5. creator can use immediately either way

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: user journal create supports private and apply-public visibility

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Per-subscription notify preferences

**Files:**
- Create: `migrations/013_journal_subscriptions_notify.sql`
- Modify: `app/models/subscription.py`
- Modify: `app/schemas/subscription.py`
- Modify: `app/routers/subscriptions.py`
- Modify: `app/services/subscriptions.py`
- Modify: `app/services/users.py` default `push_frequency` server default → `daily` (migration alter default for new users)
- Create: `tests/test_subscription_notify_prefs.py`

**Columns on journal_subscriptions:**
```sql
ALTER TABLE journal_subscriptions
  ADD COLUMN IF NOT EXISTS push_frequency VARCHAR(20) NOT NULL DEFAULT 'default'
    CHECK (push_frequency IN ('default', 'realtime', 'daily')),
  ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS wechat_enabled BOOLEAN NOT NULL DEFAULT true;
```

API:
- `PATCH /api/v1/subscriptions/journals/{journal_id}` body optional fields
- List subscribed journals includes these fields

User settings default frequency remains on users.push_frequency; change **default for new users** to `daily` via:
```sql
ALTER TABLE users ALTER COLUMN push_frequency SET DEFAULT 'daily';
```
Do not mass-update existing users in migration (avoid surprise); document in README.

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: per-journal subscription notify frequency and channel toggles

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Matcher hit reasons + subscription-aware channel selection

**Files:**
- Modify: `app/services/matcher.py`
- Modify: `app/jobs/fetch_pipeline.py` / notify path
- Modify: `tests/test_matcher.py`

**MatchResult extends:**
```python
@dataclass(frozen=True):
class MatchResult:
    user_id: str
    article_id: str
    channel: str = "email"
    reasons: tuple[str, ...] = ()  # e.g. ("journal", "keyword")
```

When matching journal subscribers, load sub prefs:
- effective frequency = sub.push_frequency if not default else user.push_frequency
- For **realtime path** in fetch pipeline: only enqueue users whose effective frequency is `realtime`
- Daily users handled by daily_summary job (already exists) — ensure it still selects daily users **or** subs with daily effective
- Channels: create separate notification rows per enabled channel (email/wechat) respecting sub toggles and user having email/openid

Store reasons on notification optional: add `reason TEXT` column in Task 15 migration bundle if needed — or encode in error-free text field `match_reasons` TEXT DEFAULT ''

Add in Task 15: `match_reasons TEXT NOT NULL DEFAULT ''`

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: match hit reasons and per-subscription realtime gating

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: User article reading status

**Files:**
- Create: `migrations/014_user_article_status.sql`
- Create: `app/models/user_article_status.py`
- Create: `app/services/reading_status.py`
- Create: `app/routers/reading.py`
- Create: `app/schemas/reading.py`
- Modify: `app/main.py`
- Create: `tests/test_reading_status_api.py`

**Schema:**
```sql
CREATE TABLE user_article_status (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  is_read BOOLEAN NOT NULL DEFAULT false,
  is_starred BOOLEAN NOT NULL DEFAULT false,
  is_later BOOLEAN NOT NULL DEFAULT false,
  original_clicked_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, article_id)
);
```

**API:**
- `PUT /api/v1/my/articles/{article_id}/status` body `{is_read?, is_starred?, is_later?}`
- `POST /api/v1/my/articles/{article_id}/original-click` sets `original_clicked_at=now()`
- `GET /api/v1/my/articles?filter=starred|later|unread` returns article metadata + status (join; only articles user can access: subscribed or public — v1: any article row is OK if user knows id, but list endpoints filter to user's matched/subscribed set preferred)

Visibility: status rows are always private to user.

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: per-user read/star/later status and original-click tracking

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Notification outbox + retry dispatcher

**Files:**
- Create: `migrations/015_notifications_retry.sql`
- Modify: `app/models/notification.py`
- Create: `app/jobs/notify_dispatch.py`
- Modify: `app/jobs/fetch_pipeline.py` — **enqueue only** (status=pending), do not send inline
- Modify: `app/jobs/daily_summary.py` — enqueue pending rows instead of direct send where applicable
- Modify: `app/jobs/scheduler.py` — interval job every 1–2 min for `run_notify_dispatch`
- Create: `tests/test_notify_dispatch.py`

**Columns:**
```sql
ALTER TABLE notifications
  ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS match_reasons TEXT NOT NULL DEFAULT '';
```

**Dispatcher:**
- Select `status='pending' AND (next_attempt_at IS NULL OR next_attempt_at <= now())` LIMIT 100
- Send per channel; on success `sent`; on failure `attempt_count+=1`, set `next_attempt_at` exponential backoff (1m, 5m, 30m, 2h), `error_message`
- If `attempt_count >= 5`: `status='failed'` terminal
- Process email and wechat in isolation (try/except per row)

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: notification outbox with scheduled retry dispatcher

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 16: My Updates feed API

**Files:**
- Create: `app/routers/my_updates.py`
- Create: `app/services/my_updates.py`
- Modify: `app/main.py`
- Create: `tests/test_my_updates_api.py`
- Modify: `web/src/views/my/Feed.vue` + api client minimally if needed

**Endpoint:** `GET /api/v1/my/updates?cursor=&limit=20&filter=`

Returns articles matching user's journal/author/keyword subscriptions (reuse matcher inputs), newest first, with:
- article metadata
- journal name, content_type
- optional CAS zone labels (if public journal has categories)
- `reasons` from notifications or recomputed
- user status flags
- `original_url` (article.url)

Only include articles from journals the user may see: public OR owned OR subscribed (subscribed private OK).

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: my updates feed with hit reasons and reading status

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 17: Seed data content_type + normalized URLs

**Files:**
- Modify: `data/journals_seed.json` (tag arxiv/* as preprint; set content_type)
- Modify: `scripts/seed_journals.py` to set content_type, directory_status=public, normalized_source_url
- Modify: `tests/test_seed_journals.py`

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
feat: seed journals with content_type and normalized URLs

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 18: Expand seed toward catalog cold start (subset)

**Files:**
- Modify: `data/journals_seed.json` — add more **verified public** academic RSS entries across disciplines (quality over quantity; aim +50–100 high-confidence feeds if URLs known stable: arXiv cats, bioRxiv, medRxiv, PLOS, eLife, etc.)
- Do **not** invent broken URLs; only include feeds that are well-known public endpoints
- Document that full 200–300 is operational follow-up

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
chore: expand built-in academic feed seed list

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 19: Full regression + fix drift

**Files:** any broken tests/schemas from cumulative changes

- [ ] Run: `.venv/bin/pytest -v`
- [ ] Fix failures without weakening assertions
- [ ] Commit fixes as needed

```bash
git commit -m "$(cat <<'EOF'
test: fix regressions after product v1 changes

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

### Task 20: Docs — README, deployment, mark spec approved pointer

**Files:**
- Modify: `README.md` (product blurb, admin is_admin, visibility, seed)
- Modify: `docs/deployment.md` (migrations 009+, set is_admin, SSRF note)
- Modify: `docs/superpowers/specs/2026-09-02-humumu-product-v1-design.md` status → 已批准（实现中） if user already approved

- [ ] Commit

```bash
git commit -m "$(cat <<'EOF'
docs: product v1 admin role, visibility, and migration notes

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

---

## Self-review (plan author)

**Spec coverage:**
- Admin RBAC → Task 1
- Private isolation public APIs → Task 3, 11, 16
- SSRF → Task 5
- Feed health/retry pause → Task 7–8
- CAS display-only → Task 9
- Custom RSS private/apply public → Task 10–11
- Per-source frequency/channels → Task 12–13
- Reading status + original click → Task 14
- Notify decoupling/retry → Task 15
- My updates closed loop → Task 16
- Seed cold start → Task 17–18
- Dedup DOI>guid>url + DB → Task 6
- Email primary / wechat isolated → Task 13, 15
- No Kafka/Celery/AI/fulltext → Global constraints

**Placeholders:** None intentional; Task 18 acknowledges full 200–300 as operational follow-up with expanded seed subset.

**Type consistency:** `directory_status` enum strings reused across migration, ORM, schemas, APIs; `require_admin` returns `str` user_id like `get_current_user_id`.

---

## Execution notes

- Implement on branch `feat/product-v1` (worktree), not directly on `master`, unless user says otherwise.
- Prefer Subagent-Driven Development: one task per subagent, review between tasks.
- Independent pure-library tasks (URL normalize vs SSRF unit tests) may be parallelized only when they do not touch the same files; default serial for safety.
