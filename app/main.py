from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import dispose_engine, init_engine
from app.errors import error_response
from app.jobs.scheduler import shutdown_scheduler, start_scheduler
from app.redis_client import dispose_redis, init_redis
from app.routers import (
    admin,
    articles,
    auth,
    categories,
    health,
    journals,
    my_updates,
    notifications,
    reading,
    requests,
    settings,
    subscriptions,
    user_journals,
    wechat,
)
from app.static_spa import mount_spa


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_engine(settings.db_dsn)
    await init_redis(settings.redis_addr)
    # Scheduler gated by HUMUMU_ENABLE_SCHEDULER=1 (default off for tests)
    start_scheduler(settings)
    try:
        yield
    finally:
        shutdown_scheduler()
        await dispose_redis()
        await dispose_engine()


app = FastAPI(title="Humumu", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "error"
    return error_response(exc.status_code, msg)


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = first.get("loc") or ()
        msg = first.get("msg") or "validation error"
        # Drop leading "body" from location for a cleaner message
        fields = [str(p) for p in loc if p != "body"]
        if fields:
            message = f"{'.'.join(fields)}: {msg}"
        else:
            message = str(msg)
    else:
        message = str(exc)
    return error_response(400, message)


app.include_router(health.router)
app.include_router(auth.router)
# Static /journals/requests before journals /{journal_id}
app.include_router(requests.router)
app.include_router(user_journals.router)
app.include_router(journals.router)
app.include_router(articles.router)
app.include_router(categories.router)
app.include_router(subscriptions.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(reading.router)
app.include_router(my_updates.router)
app.include_router(wechat.router)
app.include_router(admin.router)

# SPA last so /api/* and /health are not overridden by the catch-all
mount_spa(app, get_settings().web_dist)
