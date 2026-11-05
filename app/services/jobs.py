"""In-process asynchronous jobs with bounded concurrency and persistence.

POST /v1/{planet}/analyze creates a job and returns immediately (or waits up
to ``wait_s`` seconds). The job's current state — the full AnalysisResult with
``status=processing`` and section placeholders — is always readable from the
store, so a restart never loses completed results.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.pipelines import earth, lunar, mars
from app.pipelines.common import build_coordinates, validate_limits
from app.providers.http import get_http
from app.schemas.analysis import (AnalysisStatus, AnalyzeRequest, CacheInfo, ProblemDetail, Reason,
                                  SectionStatus, processing_placeholder)
from app.services.store import get_store

log = logging.getLogger("geoia.jobs")

PIPELINES = {"earth": earth.run, "moon": lunar.run, "mars": mars.run}
_tasks: dict[str, asyncio.Task] = {}
_sem: asyncio.Semaphore | None = None


def _semaphore() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(get_settings().max_concurrent_jobs)
    return _sem


def request_key(planet: str, req: AnalyzeRequest) -> str:
    c = build_coordinates(req, planet)
    return f"{planet}:{c.latitude:.5f}:{c.longitude:.5f}:{req.radius_km:.3f}"


async def _run(analysis_id: str, planet: str, req: AnalyzeRequest, created_at: datetime, key: str) -> None:
    store = get_store()
    placeholder = processing_placeholder(analysis_id, planet, build_coordinates(req, planet), created_at)

    async def progress(step: str) -> None:
        placeholder.progress.append(step)
        store.save(analysis_id, planet, key, "processing", placeholder.model_dump(mode="json"))

    async with _semaphore():
        try:
            result = await asyncio.wait_for(
                PIPELINES[planet](req, get_http(), analysis_id, created_at, progress),
                timeout=get_settings().job_timeout_s)
            store.save(analysis_id, planet, key, "completed", result.model_dump(mode="json"))
            log.info("job completed", extra={"analysis_id": analysis_id, "planet": planet})
        except Exception as exc:  # noqa: BLE001 - job boundary: record, never crash the server
            log.exception("job failed", extra={"analysis_id": analysis_id, "planet": planet})
            failed = placeholder.model_copy(deep=True)
            failed.status = AnalysisStatus.failed
            failed.completed_at = datetime.now(timezone.utc)
            for sec in (failed.imagery, failed.topography, failed.mineralogy, failed.earth_analogs):
                sec.status = SectionStatus.failed
            msg = "pipeline timed out" if isinstance(exc, asyncio.TimeoutError) else f"{type(exc).__name__}: {exc}"
            failed.problems.append(ProblemDetail(section="job", reason=Reason.provider_error, message=msg[:500]))
            store.save(analysis_id, planet, key, "failed", failed.model_dump(mode="json"))
        finally:
            _tasks.pop(analysis_id, None)


async def submit(planet: str, req: AnalyzeRequest, *, wait_s: float = 0.0, use_cache: bool = True) -> dict:
    validate_limits(req, planet)
    store = get_store()
    key = request_key(planet, req)
    s = get_settings()
    if use_cache:
        cached = store.find_recent(key, s.result_cache_ttl_s)
        if cached:
            cached["cache"] = CacheInfo(hit=True, original_analysis_id=cached["analysis_id"],
                                        computed_at=cached.get("completed_at")).model_dump(mode="json")
            return cached
    analysis_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc)
    placeholder = processing_placeholder(analysis_id, planet, build_coordinates(req, planet), created_at)
    placeholder.links = {"self": f"/v1/jobs/{analysis_id}"}
    store.save(analysis_id, planet, key, "processing", placeholder.model_dump(mode="json"))
    task = asyncio.create_task(_run(analysis_id, planet, req, created_at, key))
    _tasks[analysis_id] = task
    if wait_s > 0:
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=wait_s)
        except asyncio.TimeoutError:
            pass
    doc = store.get(analysis_id)
    doc.setdefault("links", {})["self"] = f"/v1/jobs/{analysis_id}"
    return doc


def get(analysis_id: str) -> dict | None:
    return get_store().get(analysis_id)


def running() -> int:
    return len(_tasks)


async def shutdown() -> None:
    for t in list(_tasks.values()):
        t.cancel()
