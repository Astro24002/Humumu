from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import dispose_engine, init_engine
from app.errors import error_response
from app.routers import health


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


app.include_router(health.router)
