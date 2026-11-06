"""Lunar pipeline: Trek imagery + LOLA topography + M3 spectroscopy + analogs.

No local lunar data is used anywhere. If M3 does not cover the point, the
mineralogy section says so and the rest of the analysis is still delivered.
"""

from __future__ import annotations

import asyncio
import math

import numpy as np

from app.config import get_settings
from app.providers import m3, ode
from app.providers.http import HttpClient, ProviderError
from app.schemas.analysis import (AnalysisResult, AnalyzeRequest, ImagerySection, MineralogySection, Reason,
                                  SectionStatus, TopographySection)
from app.science import analog_sites, similarity, spectral
from app.science.coordinates import footprint_contains, haversine_km, region_box
from app.pipelines.common import (Context, ProgressFn, assess_confidence, build_coordinates, finalize, guarded,
                                  guarded_sync,
                                  imagery_step, pds_step, topography_step, usgs_step)

M3_IIPT = dict(target="moon", ihid="CH1-ORB", iid="M3", pt="REFIMG")


def _rank(products: list[ode.OdeProduct], lat: float, lon: float) -> list[tuple[ode.OdeProduct, bool | None]]:
    out = []
    for p in products:
        inside = footprint_contains(p.footprint_wkt or "", lat, lon)
        d = (haversine_km(lat, lon, p.center_lat, p.center_lon, 1737.4)
             if p.center_lat is not None and p.center_lon is not None else 1e9)
        out.append((p, inside, d))
    # containing first, then unknown, then by distance to footprint centre (avoid edges)
    out.sort(key=lambda t: (0 if t[1] is True else 1 if t[1] is None else 2, t[2]))
    return [(p, inside) for p, inside, _ in out]


async def mineralogy_step(ctx: Context) -> tuple[MineralogySection, dict[str, float], float | None]:
    s = get_settings()
    box = region_box(ctx.lat, ctx.lon, min(ctx.req.radius_km, 0.5), "moon")
    try:
        products, query = await ode.search_products(ctx.http, box=box, limit=s.spectral_max_products_considered,
                                                    **M3_IIPT)
    except ProviderError as exc:
        rec = ctx.source(provider="PDS Geosciences Node", service="ODE REST product search", instrument="M3",
                         mission="Chandrayaan-1", product_type="M3 L2 reflectance (REFIMG)", status="error",
                         message=str(exc))
        ctx.problem("mineralogy", Reason.provider_error, str(exc), rec.source_id)
        return MineralogySection(status=SectionStatus.failed, reason=Reason.provider_error, instrument="M3",
                                 source_ids=[rec.source_id]), {}, None

    ranked = _rank(products, ctx.lat, ctx.lon)
    containing = [p for p, inside in ranked if inside is True]
    search_rec = ctx.source(
        provider="PDS Geosciences Node", service="ODE REST product search", instrument="M3",
        mission="Chandrayaan-1", product_type="M3 L2 reflectance (CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0)",
        query=query, status="ok" if products else "empty",
        message=f"{len(products)} footprints intersect the search box; {len(containing)} contain the point")
    await ctx.progress("m3_discovery")
    base = dict(instrument="M3 (Moon Mineralogy Mapper)", products_found=len(products),
                products_containing_point=len(containing))
    if not products:
        ctx.problem("mineralogy", Reason.no_coverage, "no M3 L2 observation intersects the point", search_rec.source_id)
        return MineralogySection(status=SectionStatus.unavailable, reason=Reason.no_coverage,
                                 source_ids=[search_rec.source_id], **base), {}, None

    candidates = [p for p, inside in ranked if inside is not False][:3]
    errors = []
    for prod in candidates:
        try:
            ex = await m3.extract(ctx.http, prod, ctx.lat, ctx.lon, ctx.req.radius_km)
        except m3.NoPixelNearPoint as exc:
            errors.append((prod.pdsid, Reason.no_compatible_observations, str(exc)))
            continue
        except ProviderError as exc:
            errors.append((prod.pdsid, Reason.provider_error, str(exc)))
            continue
        rec = ctx.source(
            provider="PDS Imaging Node (via ODE)", service="HTTP byte-range read of M3 L2 RFL + L1B LOC",
            instrument="M3", mission="Chandrayaan-1", product_type="L2 reflectance", product_id=ex.product_id,
            url=ex.rfl_url, observation_start=ex.observation_start, observation_end=ex.observation_end,
            spatial_resolution_m=round(ex.pixel_size_m, 1) if ex.pixel_size_m else None,
            processing=ex.processing, limitations=ex.limitations)
        await ctx.progress("m3_extraction")
        if ex.n_valid < 4:
            ctx.problem("mineralogy", Reason.insufficient_data,
                        f"{ex.n_valid} valid M3 pixels in the window of {ex.product_id}", rec.source_id)
            if prod is not candidates[-1]:
                continue  # try the next observation covering the point
            return MineralogySection(status=SectionStatus.unavailable, reason=Reason.insufficient_data,
                                     product_used=ex.product_id, pixel_distance_m=round(ex.pixel_distance_m, 1),
                                     window_pixels=ex.n_window, valid_pixels=ex.n_valid,
                                     source_ids=[search_rec.source_id, rec.source_id],
                                     limitations=ex.limitations, **base), {}, ex.incidence_deg
        indicators, values = spectral.m3_indicators(ex.spectra, ex.wavelengths)
        mean_spec = np.nanmean(ex.spectra, axis=0)
        analog_inputs = {k: spectral.legacy_analog_input(values[k]) for k in ("legacy_bd1000", "legacy_bd2000")
                         if k in values}
        analog_inputs = {k: v for k, v in analog_inputs.items() if v is not None}
        analog_inputs["_sem"] = {k: spectral.window_sem(values[k]) for k in analog_inputs}
        limitations = list(ex.limitations)
        if ex.incidence_deg is not None and ex.incidence_deg > 70:
            limitations.append(f"high solar incidence at the pixel ({ex.incidence_deg:.0f}°)")
        status = SectionStatus.available if ex.n_valid >= 25 else SectionStatus.partial
        return MineralogySection(
            status=status, reason=None if status == SectionStatus.available else Reason.insufficient_data,
            method="M3 L2 reflectance window; band depths over valid pixels (see indicator definitions)",
            product_used=ex.product_id, pixel_distance_m=round(ex.pixel_distance_m, 1),
            window_pixels=ex.n_window, valid_pixels=ex.n_valid, indicators=indicators,
            spectral_character=spectral.m3_character(values),
            mean_spectrum={"wavelength_nm": [round(float(w), 2) for w in ex.wavelengths],
                           "reflectance": [round(float(v), 5) if math.isfinite(v) else None for v in mean_spec]},
            source_ids=[search_rec.source_id, rec.source_id], limitations=limitations, **base), \
            analog_inputs, ex.incidence_deg

    for pid, reason, msg in errors:
        ctx.problem("mineralogy", reason, f"{pid}: {msg}", search_rec.source_id)
    if not candidates:
        reason = Reason.no_compatible_observations
        msg = "M3 footprints intersect the search box but none contains the point"
        ctx.problem("mineralogy", reason, msg, search_rec.source_id)
    else:
        reason = Reason.provider_error if any(r == Reason.provider_error for _, r, _ in errors) \
            else Reason.no_compatible_observations
    st = SectionStatus.failed if reason == Reason.provider_error else SectionStatus.unavailable
    return MineralogySection(status=st, reason=reason, source_ids=[search_rec.source_id], **base), {}, None


async def run(req: AnalyzeRequest, http: HttpClient, analysis_id: str, created_at, progress: ProgressFn
              ) -> AnalysisResult:
    done: list[str] = []

    async def prog(step: str) -> None:
        done.append(step)
        await progress(step)

    ctx = Context(body="moon", req=req, coords=build_coordinates(req, "moon"), http=http, progress=prog)
    failed = SectionStatus.failed
    imagery, topo_s, (min_s, analog_inputs, incidence), _, _ = await asyncio.gather(
        guarded(ctx, "imagery", imagery_step(ctx), lambda: ImagerySection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "topography", topography_step(ctx),
                lambda: TopographySection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "mineralogy", mineralogy_step(ctx),
                lambda: (MineralogySection(status=failed, reason=Reason.invalid_data), {}, None)),
        guarded(ctx, "discovery", pds_step(ctx, ["lola", "diviner"]), lambda: None),
        guarded(ctx, "discovery", usgs_step(ctx), lambda: None))
    analogs = similarity.compare("moon", analog_inputs)
    if min_s.status not in (SectionStatus.available, SectionStatus.partial):
        analogs.reason = Reason.not_attempted
    extra = ["Earth analogs use only band depths with identical definitions; Moon and Earth surfaces differ "
             "(space weathering, no water or vegetation, regolith grain size)."]
    conf = assess_confidence(topo_s, min_s, extra, incidence)
    terrestrial = guarded_sync(ctx, lambda: analog_sites.match("moon", min_s, ctx.lat))
    return finalize(ctx, analysis_id, created_at, imagery, topo_s, min_s, analogs, conf, done,
                    terrestrial=terrestrial)
