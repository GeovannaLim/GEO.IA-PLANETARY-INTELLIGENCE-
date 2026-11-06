"""Shared orchestration for Moon and Mars (and the bookkeeping used by Earth).

Moon and Mars share infrastructure (imagery discovery, laser-altimetry
topography, product discovery, provenance, confidence rules) but NOT
mineralogical assumptions: each body plugs in its own spectral step.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.config import get_settings
from app.providers import ode, pds, trek, usgs
from app.providers.http import HttpClient, ProviderError
from app.schemas.analysis import (
    AnalysisResult, AnalysisStatus, AnalyzeRequest, ConfidenceSection, Coordinates, Criterion,
    EarthAnalogSection, ImagerySection, MineralogySection, ProblemDetail, Reason, SectionStatus,
    SourceRecord, TerrestrialAnalogSection, TopographySection)
from app.science import topography as topo
from app.science.coordinates import (BODY_RADIUS_KM, REFERENCE_FRAME, region_box, to_east_180,
                                     to_east_360)

log = logging.getLogger("geoia.pipeline")

ProgressFn = Callable[[str], Awaitable[None]]


def now() -> datetime:
    return datetime.now(timezone.utc)


def build_coordinates(req: AnalyzeRequest, body: str) -> Coordinates:
    lon = to_east_180(req.longitude)
    box = region_box(req.latitude, lon, req.radius_km, body)
    return Coordinates(latitude=req.latitude, longitude=lon, radius_km=req.radius_km,
                       longitude_east_360=to_east_360(lon), reference_frame=REFERENCE_FRAME[body],
                       reference_radius_km=BODY_RADIUS_KM[body], bounding_box=box.as_dict())


def validate_limits(req: AnalyzeRequest, body: str) -> None:
    s = get_settings()
    if req.radius_km > s.max_radius_km(body):
        raise ValueError(f"radius_km {req.radius_km} exceeds the operational limit "
                         f"{s.max_radius_km(body)} km for {body}")
    if req.radius_km < s.min_radius_km:
        raise ValueError(f"radius_km must be >= {s.min_radius_km}")


@dataclass
class Context:
    body: str
    req: AnalyzeRequest
    coords: Coordinates
    http: HttpClient
    progress: ProgressFn
    sources: list[SourceRecord] = field(default_factory=list)
    problems: list[ProblemDetail] = field(default_factory=list)
    _n: int = 0

    def source(self, **kw) -> SourceRecord:
        self._n += 1
        rec = SourceRecord(source_id=f"src-{self._n:02d}", retrieved_at=kw.pop("retrieved_at", now()), **kw)
        self.sources.append(rec)
        return rec

    def problem(self, section: str, reason: Reason, message: str, source_id: str | None = None) -> None:
        self.problems.append(ProblemDetail(section=section, reason=reason, message=message[:500],
                                           source_id=source_id))

    @property
    def lat(self) -> float:
        return self.coords.latitude

    @property
    def lon(self) -> float:
        return self.coords.longitude


# --------------------------------------------------------------------------- #
# Imagery (Trek WMTS)
# --------------------------------------------------------------------------- #
async def imagery_step(ctx: Context) -> ImagerySection:
    try:
        layers, n_regional, meta = await trek.imagery_for_point(ctx.http, ctx.body, ctx.lat, ctx.lon)
    except ProviderError as exc:
        rec = ctx.source(provider="NASA Trek", service="WMTS layer catalogue", status="error", message=str(exc))
        ctx.problem("imagery", Reason.provider_error, str(exc), rec.source_id)
        return ImagerySection(status=SectionStatus.failed, reason=Reason.provider_error, source_ids=[rec.source_id])
    rec = ctx.source(provider="NASA Trek", service="WMTS GetCapabilities + layer catalogue",
                     url=meta["catalog_url"], query={"catalog_size": meta["catalog_size"]},
                     processing=["curated global layers verified in catalogue and capabilities",
                                 "regional layers selected by catalogue bbox containing the point"],
                     limitations=["WMTS tiles are rendered imagery for visualisation; not physical values"])
    await ctx.progress("imagery")
    status = SectionStatus.available if layers else SectionStatus.unavailable
    return ImagerySection(status=status, reason=None if layers else Reason.no_coverage, layers=layers,
                          regional_layers_covering_point=n_regional, source_ids=[rec.source_id])


# --------------------------------------------------------------------------- #
# Topography (ODE GDS laser altimetry)
# --------------------------------------------------------------------------- #
ALT_META = {
    "moon": dict(instrument="LOLA", mission="Lunar Reconnaissance Orbiter", product_type="LOLA RDR (GDS lolardr)",
                 datum="radius minus 1737.4 km reference sphere (LOLA RDR topography)", footprint_m=5.0),
    "mars": dict(instrument="MOLA", mission="Mars Global Surveyor", product_type="MOLA PEDR (GDS molapedr)",
                 datum="radius minus MOLA areoid (PEDR topography)", footprint_m=168.0),
}


async def topography_step(ctx: Context) -> TopographySection:
    s = get_settings()
    meta = ALT_META[ctx.body]
    radius = ctx.req.radius_km
    box = region_box(ctx.lat, ctx.lon, radius, ctx.body)
    result, last_err = None, None
    for _ in range(s.altimetry_shrink_steps + 1):
        try:
            result = await ode.query_altimetry(ctx.http, ctx.body, box)
            break
        except ode.AltimetryTooLarge as exc:
            last_err = str(exc)
            radius /= 2.0
            box = region_box(ctx.lat, ctx.lon, radius, ctx.body)
        except ProviderError as exc:
            rec = ctx.source(provider="PDS Geosciences Node", service="ODE GDS", status="error",
                             instrument=meta["instrument"], mission=meta["mission"],
                             product_type=meta["product_type"], message=str(exc), query={"bbox": box.as_dict()})
            ctx.problem("topography", Reason.provider_error, str(exc), rec.source_id)
            return TopographySection(status=SectionStatus.failed, reason=Reason.provider_error,
                                     source_ids=[rec.source_id])
    if result is None:
        rec = ctx.source(provider="PDS Geosciences Node", service="ODE GDS", status="error",
                         instrument=meta["instrument"], message=f"query too large even at {radius:.2f} km: {last_err}")
        ctx.problem("topography", Reason.provider_error, rec.message or "", rec.source_id)
        return TopographySection(status=SectionStatus.failed, reason=Reason.provider_error, source_ids=[rec.source_id])

    times = sorted(t for t in result.times if t)
    rec = ctx.source(
        provider="PDS Geosciences Node", service="ODE Granular Data System (GDS)", instrument=meta["instrument"],
        mission=meta["mission"], product_type=meta["product_type"],
        url=result.files[0] if result.files else None, observation_start=times[0] if times else None,
        observation_end=times[-1] if times else None, spatial_resolution_m=meta["footprint_m"],
        query=result.query, retrieved_at=result.retrieved_at,
        status="ok" if result.elev_m.size else "empty",
        message=result.status_note,
        processing=["GDS topography CSV (valid shots only, quality flag 0)",
                    "points clipped to the circular region; azimuthal-equidistant local projection",
                    "least-squares plane for regional slope; gridded central differences for local slope"],
        limitations=[f"{meta['instrument']} shot spacing leaves gaps between ground tracks"])
    await ctx.progress("topography")
    if result.elev_m.size == 0:
        ctx.problem("topography", Reason.no_coverage, "no valid altimeter shots in the region", rec.source_id)
        return TopographySection(status=SectionStatus.unavailable, reason=Reason.no_coverage, n_points=0,
                                 method=f"{meta['instrument']} shots", datum=meta["datum"],
                                 sampled_radius_km=radius, source_ids=[rec.source_id])
    return topo.summarize(result.lat, result.lon360, result.elev_m, lat0=ctx.lat, lon0_360=to_east_360(ctx.lon),
                          roi_radius_km=ctx.req.radius_km, sampled_radius_km=radius,
                          body_radius_km=BODY_RADIUS_KM[ctx.body], datum=meta["datum"],
                          method=f"{meta['instrument']} laser altimeter shots via ODE GDS",
                          source_ids=[rec.source_id])


# --------------------------------------------------------------------------- #
# Complementary discovery (PDS registry, USGS STAC) — never blocks the result
# --------------------------------------------------------------------------- #
async def pds_step(ctx: Context, instruments: list[str]) -> None:
    for inst in instruments:
        try:
            res = await pds.search_spatial(ctx.http, instrument=inst, lat=ctx.lat, lon360=to_east_360(ctx.lon))
        except ProviderError as exc:
            rec = ctx.source(provider="NASA PDS", service="PDS Registry API", instrument=inst.upper(),
                             status="error", message=str(exc))
            ctx.problem("discovery", Reason.provider_error, str(exc), rec.source_id)
            continue
        hits = res.get("hits") or 0
        ctx.source(provider="NASA PDS", service="PDS Registry API (spatial, PDS4 cart:Bounding_Coordinates)",
                   instrument=inst.upper(), query=res["query"], status="ok" if hits else "empty",
                   message=(f"{hits} PDS4 products whose bounding box contains the point; examples: "
                            + "; ".join(i["lid"] or "" for i in res["items"][:3])) if hits else
                   ("No PDS4 products indexed for this point. The PDS registry does not index every node's "
                    "PDS3 holdings; ODE results are authoritative for coverage."),
                   limitations=["discovery only; products are not downloaded"])
    await ctx.progress("pds_discovery")


async def usgs_step(ctx: Context) -> None:
    try:
        res = await usgs.dtms_at_point(ctx.http, ctx.body, ctx.lat, ctx.lon)
    except ProviderError as exc:
        rec = ctx.source(provider="USGS Astrogeology", service="STAC API", status="error", message=str(exc))
        ctx.problem("discovery", Reason.provider_error, str(exc), rec.source_id)
        return
    items = res["items"]
    ctx.source(provider="USGS Astrogeology", service="STAC API (high-resolution DTMs)", query=res["query"],
               status="ok" if items else "empty",
               message=(f"{len(items)} DTM(s) intersect the point: "
                        + "; ".join(f"{i['collection']}/{i['id']}" for i in items)) if items else
               "No USGS high-resolution DTM intersects the point.",
               limitations=["listed for follow-up analysis; not read by the MVP pipeline"])
    await ctx.progress("usgs_discovery")


# --------------------------------------------------------------------------- #
# Confidence (documented rules, see docs/CIENCIA.md)
# --------------------------------------------------------------------------- #
def assess_confidence(topo_s: TopographySection, min_s: MineralogySection, extra_limits: list[str],
                      incidence: float | None = None) -> ConfidenceSection:
    crit: list[Criterion] = []
    if topo_s.status in (SectionStatus.available, SectionStatus.partial):
        crit.append(Criterion(criterion="altimetry_points>=30", met=(topo_s.n_points or 0) >= 30,
                              detail=f"{topo_s.n_points} valid shots in the sampled circle"))
        crit.append(Criterion(criterion="altimetry_cell_coverage>=0.3", met=(topo_s.coverage_fraction or 0) >= 0.3,
                              detail=f"coverage {topo_s.coverage_fraction}"))
        crit.append(Criterion(criterion="altimetry_covers_requested_radius",
                              met=not any("sampled within" in x for x in topo_s.limitations),
                              detail=f"sampled radius {topo_s.sampled_radius_km} km"))
    if min_s.status in (SectionStatus.available, SectionStatus.partial):
        crit.append(Criterion(criterion="spectral_pixel_within_tolerance", met=min_s.pixel_distance_m is not None,
                              detail=f"nearest pixel {min_s.pixel_distance_m} m from target"))
        crit.append(Criterion(criterion="valid_spectral_pixels>=25", met=(min_s.valid_pixels or 0) >= 25,
                              detail=f"{min_s.valid_pixels} valid pixels"))
        if incidence is not None:
            crit.append(Criterion(criterion="solar_incidence<=70deg", met=incidence <= 70.0,
                                  detail=f"incidence {incidence:.1f}°"))
    limitations = list(dict.fromkeys(topo_s.limitations + min_s.limitations + extra_limits))
    if not crit:
        return ConfidenceSection(level="not_assessed", criteria=[], limitations=limitations)
    frac = sum(c.met for c in crit) / len(crit)
    level = "high" if frac == 1.0 else "moderate" if frac >= 2 / 3 else "low"
    if min_s.status not in (SectionStatus.available, SectionStatus.partial) and level == "high":
        level = "moderate"  # mineralogy missing: never 'high' for the analysis as a whole
    return ConfidenceSection(level=level, criteria=crit, limitations=limitations)


def finalize(ctx: Context, analysis_id: str, created_at: datetime, imagery: ImagerySection,
             topo_s: TopographySection, min_s: MineralogySection, analogs: EarthAnalogSection,
             confidence: ConfidenceSection, progress: list[str], earth_obs: dict | None = None,
             terrestrial: TerrestrialAnalogSection | None = None) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id, planet=ctx.body, status=AnalysisStatus.completed, created_at=created_at,
        completed_at=now(), progress=progress, coordinates=ctx.coords, data_sources=ctx.sources,
        imagery=imagery, topography=topo_s, mineralogy=min_s, earth_analogs=analogs,
        terrestrial_analogs=terrestrial, earth_observation=earth_obs, confidence=confidence, problems=ctx.problems, report_id=analysis_id,
        links={"self": f"/v1/jobs/{analysis_id}", "report": f"/v1/reports/{analysis_id}",
               "report_pdf": f"/v1/reports/{analysis_id}?format=pdf"})


def safe_float(x: float | None) -> float | None:
    return None if x is None or not math.isfinite(x) else float(x)


def guarded_sync(ctx: Context, fn):
    """Optional derived section: a bug is recorded as a problem and the section is omitted (None)."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - optional section boundary
        log.exception("derived section crashed", extra={"body": ctx.body})
        ctx.problem("terrestrial_analogs", Reason.invalid_data, f"internal error: {type(exc).__name__}: {exc}")
        return None


async def guarded(ctx: Context, section: str, coro, fallback):
    """Run one pipeline step; an unexpected bug becomes a 'failed' section with
    a recorded problem instead of aborting the other steps."""
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - step boundary
        log.exception("step crashed", extra={"section": section, "body": ctx.body})
        ctx.problem(section, Reason.invalid_data, f"internal error in {section}: {type(exc).__name__}: {exc}")
        return fallback()
