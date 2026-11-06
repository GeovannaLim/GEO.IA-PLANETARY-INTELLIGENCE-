"""HTTP routes. Analysis endpoints share one contract for all three bodies."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from app import __version__, i18n
from app.config import get_settings
from app.providers import earth_engine
from app.schemas.analysis import SCHEMA_VERSION, AnalysisResult, AnalyzeRequest
from app.services import datasets, jobs, reports
from app.services.store import get_store

router = APIRouter()
_STARTED = time.time()

LANG = Query("en", pattern="^(en|pt-BR)$",
             description="Language of the prose fields (interpretations, limitations, notes). Values, codes, "
                         "units and provenance are never translated. The PDF stays in English.")
WAIT_DOC = ("Seconds to wait for completion before answering (0-60). With 0 the job is accepted and "
            "polled via GET /v1/jobs/{analysis_id}.")


async def _analyze(planet: str, req: AnalyzeRequest, wait_s: float | None, use_cache: bool,
                   lang: str = "en") -> JSONResponse:
    wait = get_settings().default_wait_s if wait_s is None else wait_s
    try:
        doc = await jobs.submit(planet, req, wait_s=wait, use_cache=use_cache)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    code = 202 if doc["status"] == "processing" else 200
    return JSONResponse(i18n.localize(doc, lang), status_code=code)


ANALYZE_RESPONSES = {200: {"model": AnalysisResult, "description": "Completed (or cached) analysis"},
                     202: {"model": AnalysisResult, "description": "Accepted; poll links.self"}}


@router.post("/v1/earth/analyze", responses=ANALYZE_RESPONSES, tags=["analysis"])
async def earth_analyze(req: AnalyzeRequest, wait_s: float | None = Query(None, ge=0, le=60, description=WAIT_DOC),
                        use_cache: bool = True, lang: str = LANG):
    return await _analyze("earth", req, wait_s, use_cache, lang)


@router.post("/v1/lunar/analyze", responses=ANALYZE_RESPONSES, tags=["analysis"])
async def lunar_analyze(req: AnalyzeRequest, wait_s: float | None = Query(None, ge=0, le=60, description=WAIT_DOC),
                        use_cache: bool = True, lang: str = LANG):
    return await _analyze("moon", req, wait_s, use_cache, lang)


@router.post("/v1/mars/analyze", responses=ANALYZE_RESPONSES, tags=["analysis"])
async def mars_analyze(req: AnalyzeRequest, wait_s: float | None = Query(None, ge=0, le=60, description=WAIT_DOC),
                       use_cache: bool = True, lang: str = LANG):
    return await _analyze("mars", req, wait_s, use_cache, lang)


@router.get("/v1/jobs/{analysis_id}", response_model=None, tags=["analysis"])
async def job_status(analysis_id: str, lang: str = LANG):
    doc = jobs.get(analysis_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="unknown analysis_id")
    return JSONResponse(i18n.localize(doc, lang), status_code=202 if doc["status"] == "processing" else 200)


@router.get("/v1/reports/{report_id}", tags=["reports"],
            responses={200: {"content": {"application/json": {}, "application/pdf": {}}}})
async def get_report(report_id: str, format: str = Query("json", pattern="^(json|pdf)$"), lang: str = LANG):
    doc = jobs.get(report_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="unknown report_id")
    if doc["status"] == "processing":
        raise HTTPException(status_code=409, detail="analysis still processing")
    if format == "pdf":
        pdf = reports.render_pdf(doc)
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="geoia-{doc["planet"]}-{report_id}.pdf"'})
    return JSONResponse(i18n.localize(doc, lang))


@router.get("/v1/planetary/datasets", tags=["datasets"])
async def list_datasets(body: str | None = Query(None, pattern="^(earth|moon|mars)$")):
    return {"datasets": datasets.list_datasets(body),
            "conventions": {"latitude": "planetocentric degrees",
                            "longitude": "east-positive; API default [-180, 180) ('east_180'), "
                                         "'east_360' accepted; converted per provider"}}


@router.get("/health", tags=["infra"])
async def health():
    s = get_settings()
    try:
        db_ok = get_store().ping()
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "version": __version__, "schema_version": SCHEMA_VERSION,
            "environment": s.environment, "uptime_s": round(time.time() - _STARTED, 1),
            "database": "ok" if db_ok else "error", "jobs_running": jobs.running(),
            "earth_engine": earth_engine.status(),
            "endpoints": ["/v1/earth/analyze", "/v1/lunar/analyze", "/v1/mars/analyze", "/v1/jobs/{id}",
                          "/v1/reports/{id}", "/v1/planetary/datasets"]}
