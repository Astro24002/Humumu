"""SSRF-safe URL validation and outbound HTTP for feed fetch."""

from __future__ import annotations

import ipaddress
import socket
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
        "metadata.goog",
    }
)

_DEFAULT_TIMEOUT = 15.0
_DEFAULT_MAX_BYTES = 2_000_000
_DEFAULT_MAX_REDIRECTS = 5
_USER_AGENT = "JournalMonitor/1.0"


class UnsafeURLError(ValueError):
    """Raised when a URL is not safe for outbound fetch."""


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _hostname_blocked(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    if not host:
        return True
    if host in _BLOCKED_HOSTNAMES:
        return True
    if host.endswith(".localhost") or host.endswith(".local"):
        return True
    return False


def _resolve_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve hostname to IPs. Literal IPs return themselves."""
    host = hostname.strip().lower().rstrip(".")
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve host: {host}") from exc

    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    seen: set[str] = set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        try:
            ips.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    if not ips:
        raise UnsafeURLError(f"cannot resolve host: {host}")
    return ips


def validate_public_http_url(url: str) -> str:
    """
    Validate that url is http(s) and does not target private/metadata networks.

    Returns the stripped URL string on success.
    Raises UnsafeURLError otherwise.
    """
    raw = (url or "").strip()
    if not raw:
        raise UnsafeURLError("empty url")

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsafeURLError("only http and https are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("missing hostname")

    if _hostname_blocked(hostname):
        raise UnsafeURLError(f"blocked hostname: {hostname}")

    # Reject embedded credentials (odd SSRF/proxy patterns)
    if parsed.username or parsed.password:
        raise UnsafeURLError("url must not contain credentials")

    for ip in _resolve_ips(hostname):
        if _is_blocked_ip(ip):
            raise UnsafeURLError(f"blocked address: {ip}")

    return raw


def _header_map(resp: httpx.Response) -> dict[str, str]:
    interesting = {}
    for key in ("etag", "last-modified", "content-type", "location"):
        val = resp.headers.get(key)
        if val:
            interesting[key] = val
    return interesting


async def safe_get_text(
    url: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    headers: dict[str, str] | None = None,
    max_redirects: int = _DEFAULT_MAX_REDIRECTS,
) -> tuple[str, str, dict[str, str]]:
    """
    GET url with SSRF checks on each hop and body size limit.

    Returns (final_url, body_text, response_headers_of_interest).
    """
    current = validate_public_http_url(url)
    req_headers = {"User-Agent": _USER_AGENT}
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for _ in range(max_redirects + 1):
            validate_public_http_url(current)
            resp = await client.get(current, headers=req_headers)

            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location")
                if not location:
                    raise UnsafeURLError("redirect without location")
                next_url = urljoin(current, location)
                current = validate_public_http_url(next_url)
                continue

            if resp.status_code == 304:
                return current, "", _header_map(resp)

            if resp.status_code != 200:
                raise ValueError(f"feed fetch status {resp.status_code}")

            # Bound body size
            body = resp.content
            if len(body) > max_bytes:
                raise UnsafeURLError(f"response exceeds max_bytes ({max_bytes})")
            text = body.decode(resp.encoding or "utf-8", errors="replace")
            return current, text, _header_map(resp)

    raise UnsafeURLError("too many redirects")


def assert_urls_public(urls: Iterable[str]) -> None:
    for u in urls:
        validate_public_http_url(u)
