import asyncio

import pytest

from app.config import get_settings
from app.providers import http as http_mod
from app.services import cache, jobs, store


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOIA_DB_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("GEOIA_HTTP_RETRIES", "1")
    monkeypatch.setenv("GEOIA_HTTP_BACKOFF_S", "0")
    monkeypatch.setenv("GEOIA_CORS_ORIGINS", "https://app.example.org")
    for var in ("GEE_SERVICE_ACCOUNT_JSON", "GEE_SERVICE_ACCOUNT_KEY_FILE", "GOOGLE_APPLICATION_CREDENTIALS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GEOIA_ENVIRONMENT", "test")
    get_settings.cache_clear()
    cache.metadata_cache.clear()
    store.set_store(None)
    http_mod.set_http(None)
    jobs._sem = None
    from app.providers import earth_engine
    earth_engine._STATE.update(attempted=False, initialized=False, method=None, detail=None)
    yield
    http_mod.set_http(None)
    store.set_store(None)
    get_settings.cache_clear()


def run(coro):
    """Run a coroutine and close the shared HTTP client inside the same loop."""
    async def wrapper():
        try:
            return await coro
        finally:
            await http_mod.close_http()
    return asyncio.run(wrapper())
