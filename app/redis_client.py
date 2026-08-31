"""Async Redis client lifecycle (init / get / dispose)."""

from __future__ import annotations

import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def init_redis(redis_addr: str) -> Redis | None:
    """
    Create and ping an async Redis client from ``host:port``.

    On failure logs a warning and returns None (callers treat missing Redis
    as no-op dedup / soft-fail rather than crashing the app).
    """
    global _redis
    host, _, port_s = (redis_addr or "").partition(":")
    host = host or "localhost"
    try:
        port = int(port_s or "6379")
    except ValueError:
        port = 6379

    # Short timeouts so boot/tests don't hang when Redis is down.
    client = Redis(
        host=host,
        port=port,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001 — soft-fail at boot
        logger.warning(
            "redis unavailable at %s:%s: %s; continuing without dedup",
            host,
            port,
            exc,
        )
        try:
            await client.aclose()
        except Exception:  # noqa: BLE001
            pass
        _redis = None
        return None

    _redis = client
    logger.info("redis connected at %s:%s", host, port)
    return _redis


def get_redis() -> Redis | None:
    """Return the process-wide Redis client, or None if not initialized."""
    return _redis


async def dispose_redis() -> None:
    """Close the Redis client if present."""
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis dispose error: %s", exc)
    _redis = None
