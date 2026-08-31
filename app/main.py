from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import dispose_engine, init_engine
from app.errors import error_response
from app.routers import articles, auth, health, journals


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_engine(settings.db_dsn)
    try:
        yield
    finally:
        await dispose_engine()


app = FastAPI(title="Humumu", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
app.include_router(journals.router)
app.include_router(articles.router)
