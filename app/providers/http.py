"""Shared outbound HTTP: timeouts, retries with backoff, host allow-list (SSRF
protection), download size caps, per-host concurrency and byte-range reads.

Every provider goes through ``HttpClient``; no module opens its own client.
URLs that come back from remote services (e.g. GDS output files, product file
links in ODE metadata) are validated against ``ALLOWED_HOSTS`` before use.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import random
from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.config import Settings, get_settings

log = logging.getLogger("geoia.http")

ALLOWED_HOSTS = frozenset({
    "oderest.rsl.wustl.edu",        # ODE REST + GDS
    "ode.rsl.wustl.edu",            # ODE web / derived files
    "pds-geosciences.wustl.edu",    # PDS Geosciences node (CRISM, LOLA, MOLA)
    "planetarydata.jpl.nasa.gov",   # PDS Imaging node (M3)
    "pds-imaging.jpl.nasa.gov",
    "pds.nasa.gov",                 # PDS Registry API
    "pds.mcp.nasa.gov",             # PDS API redirect target
    "trek.nasa.gov",                # Moon/Mars Trek
    "stac.astrogeology.usgs.gov",   # USGS Astrogeology STAC
    "planetarymaps.usgs.gov",       # USGS Astrogeology WMS
    "astrogeology.usgs.gov",
})

RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class ProviderError(Exception):
    """A remote service failed (network, timeout, HTTP error, invalid payload)."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.status_code = status_code
        self.message = message


class UnsafeURLError(ValueError):
    pass


def validate_url(url: str) -> str:
    """Allow only https URLs on allow-listed public hosts."""
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http"):
        raise UnsafeURLError(f"scheme not allowed: {parts.scheme!r}")
    host = (parts.hostname or "").lower()
    if not host:
        raise UnsafeURLError("missing host")
    try:
        ipaddress.ip_address(host)
        raise UnsafeURLError("IP literal hosts are not allowed")
    except ValueError as exc:
        if isinstance(exc, UnsafeURLError):
            raise
    if host not in ALLOWED_HOSTS:
        raise UnsafeURLError(f"host not in allow-list: {host}")
    if parts.port not in (None, 80, 443):
        raise UnsafeURLError("non-standard port")
    if parts.username or parts.password:
        raise UnsafeURLError("credentials in URL")
    # Normalise to https where the host supports it (all listed hosts do).
    if parts.scheme == "http":
        url = "https" + url[4:]
    return url


class HttpClient:
    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.s = settings or get_settings()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.s.http_timeout_s, connect=self.s.http_connect_timeout_s),
            follow_redirects=False,
            headers={"User-Agent": "GEOIA-Planetary-Backend/1.0 (+scientific research client)"},
            transport=transport,
        )
        self._sems: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(self.s.http_max_concurrency_per_host))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _send(self, provider: str, method: str, url: str, *, params: dict | None = None,
                    headers: dict | None = None, max_bytes: int | None = None,
                    timeout: float | None = None) -> httpx.Response:
        url = validate_url(url)
        limit = max_bytes or self.s.http_max_download_bytes
        attempt, redirects = 0, 0
        while True:
            host = urlsplit(url).hostname or ""
            try:
                async with self._sems[host]:
                    req = self._client.build_request(method, url, params=params, headers=headers,
                                                     timeout=timeout or httpx.USE_CLIENT_DEFAULT)
                    resp = await self._client.send(req, stream=True)
                    try:
                        if resp.is_redirect and redirects < 5:
                            loc = resp.headers.get("location", "")
                            url = validate_url(str(httpx.URL(url).join(loc)))
                            params = None  # already encoded in Location
                            redirects += 1
                            continue
                        declared = resp.headers.get("content-length")
                        if declared and declared.isdigit() and int(declared) > limit:
                            raise ProviderError(provider, f"response too large ({declared} B > {limit} B)")
                        chunks, total = [], 0
                        async for chunk in resp.aiter_bytes():
                            total += len(chunk)
                            if total > limit:
                                raise ProviderError(provider, f"response exceeded {limit} B")
                            chunks.append(chunk)
                        resp._content = b"".join(chunks)  # noqa: SLF001 - buffered body
                    finally:
                        await resp.aclose()
                if resp.status_code in RETRY_STATUS and attempt < self.s.http_retries:
                    raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
                if resp.status_code >= 400:
                    raise ProviderError(provider, f"HTTP {resp.status_code} for {url}",
                                        status_code=resp.status_code)
                return resp
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt >= self.s.http_retries:
                    raise ProviderError(provider, f"{type(exc).__name__} after {attempt + 1} attempts: {url}") from exc
                delay = self.s.http_backoff_s * (2 ** attempt) * (0.75 + random.random() / 2)
                log.warning("retrying", extra={"provider": provider, "url": url,
                                               "attempt": attempt + 1, "delay_s": round(delay, 2),
                                               "error": type(exc).__name__})
                attempt += 1
                await asyncio.sleep(delay)

    async def get_json(self, provider: str, url: str, params: dict | None = None,
                       timeout: float | None = None, max_bytes: int | None = None) -> Any:
        resp = await self._send(provider, "GET", url, params=params, timeout=timeout,
                                headers={"Accept": "application/json"}, max_bytes=max_bytes)
        try:
            return resp.json()
        except ValueError as exc:
            raise ProviderError(provider, f"invalid JSON from {url}") from exc

    async def get_text(self, provider: str, url: str, params: dict | None = None,
                       timeout: float | None = None, max_bytes: int | None = None) -> str:
        resp = await self._send(provider, "GET", url, params=params, timeout=timeout, max_bytes=max_bytes)
        return resp.text

    async def get_range(self, provider: str, url: str, start: int, length: int) -> bytes:
        """Read ``length`` bytes at ``start`` with an HTTP Range request."""
        if length <= 0:
            return b""
        end = start + length - 1
        resp = await self._send(provider, "GET", url, headers={"Range": f"bytes={start}-{end}"},
                                max_bytes=length + 1024)
        if resp.status_code != 206:
            raise ProviderError(provider, f"server ignored Range request (HTTP {resp.status_code}) for {url}")
        data = resp.content
        if len(data) != length:
            raise ProviderError(provider, f"short range read: got {len(data)} of {length} B")
        return data


_client: HttpClient | None = None


def get_http() -> HttpClient:
    global _client
    if _client is None:
        _client = HttpClient()
    return _client


async def close_http() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def set_http(client: HttpClient | None) -> None:
    """Test hook."""
    global _client
    _client = client
