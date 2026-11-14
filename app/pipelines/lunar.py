"""Lunar pipeline: Trek imagery + LOLA topography + M3 spectroscopy + analogs.

No local lunar data is used anywhere. If M3 does not cover the point, the
mineralogy section says so and the rest of the analysis is still delivered.
"""

from __future__ import annotations

import asyncio
import logging
import math

import numpy as np

from app.config import get_settings
from app.providers import lola_illumination, m3, ode
from app.providers.http import HttpClient, ProviderError
from app.schemas.analysis import (AnalysisResult, AnalyzeRequest, EnvironmentSection, GeomorphologySection,
                                  ImagerySection,
                                  MineralogySection, Reason, SectionStatus, TopographySection)
from app.science import analog_sites, geomorph_analogs, similarity, spectral
from app.science.coordinates import footprint_contains, haversine_km, region_box
from app.pipelines.common import (Context, ProgressFn, assess_confidence, build_coordinates, finalize, guarded,
                                  guarded_sync,
                                  imagery_step, pds_step, topography_step, usgs_step)

log = logging.getLogger("geoia.lunar")
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
        if errors:   # a preferred observation could not be read: say which one and why (provenance)
            skipped = "; ".join(f"{pid} ({r.value})" for pid, r, _ in errors)
            ex.limitations = list(ex.limitations) + [
                f"Preferred M3 observation(s) could not be used: {skipped}. This result comes from {ex.product_id}, "
                "another observation containing the point; values can differ from those of the preferred one."]
            for pid, r, m in errors:
                ctx.problem("mineralogy", r, f"{pid} skipped: {m}", search_rec.source_id)
            errors = []
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
        if ex.incidence_deg is not None and ex.incidence_deg >= spectral.MAX_USABLE_INCIDENCE_DEG:
            ctx.problem("mineralogy", Reason.insufficient_data,
                        f"{ex.product_id}: solar incidence {ex.incidence_deg:.1f}° >= "
                        f"{spectral.MAX_USABLE_INCIDENCE_DEG:.0f}° (surface unlit or grazing light); "
                        "reflectance band depths not computed", rec.source_id)
            if prod is not candidates[-1]:
                continue  # another observation may be illuminated
            return MineralogySection(status=SectionStatus.unavailable, reason=Reason.insufficient_data,
                                     product_used=ex.product_id, pixel_distance_m=round(ex.pixel_distance_m, 1),
                                     window_pixels=ex.n_window, valid_pixels=ex.n_valid,
                                     source_ids=[search_rec.source_id, rec.source_id],
                                     limitations=ex.limitations, **base), {}, ex.incidence_deg
        # Permanent-shadow control (south polar region): M3 reflectance inside a permanently shadowed region
        # is not direct sunlight (at best scattered light), so those pixels cannot support a composition.
        shadow_limits: list[str] = []
        if ctx.lat <= -65.0 and ex.pixel_lat is not None and ex.n_valid:
            n_total = ex.n_valid
            try:
                flags = await lola_illumination.permanent_shadow_at(ctx.http, ex.pixel_lat, ex.pixel_lon)
            except lola_illumination.NotApplicable:
                flags = None
            except ProviderError as exc:
                flags = None
                shadow_limits.append("Permanent shadow could not be checked for these M3 pixels (illumination maps "
                                     "unavailable); shadowed pixels may be included.")
                ctx.problem("mineralogy", Reason.provider_error, f"permanent-shadow check failed: {exc}",
                            rec.source_id)
            if flags is not None:
                in_psr = flags == 1.0
                n_psr = int(in_psr.sum())
                if int(np.isnan(flags).sum()):
                    shadow_limits.append(f"{int(np.isnan(flags).sum())} M3 pixels fall outside the illumination "
                                         "grid; their shadow status is unknown.")
                if n_psr:
                    keep = ~in_psr
                    ex.spectra, ex.n_valid = ex.spectra[keep], int(keep.sum())
                    ex.pixel_lat, ex.pixel_lon = ex.pixel_lat[keep], ex.pixel_lon[keep]
                    msg = (f"{n_psr} of {n_total} valid M3 pixels lie in permanent shadow (LOLA/PGDA LPSR, Mazarico "
                           "et al. 2011) and were excluded: reflectance there is not direct sunlight.")
                    shadow_limits.append(msg)
                    if ex.n_valid < 4:
                        ctx.problem("mineralogy", Reason.insufficient_data, f"{ex.product_id}: {msg} "
                                    "Mineralogy is not inferred.", rec.source_id)
                        return MineralogySection(
                            status=SectionStatus.unavailable, reason=Reason.insufficient_data,
                            product_used=ex.product_id, pixel_distance_m=round(ex.pixel_distance_m, 1),
                            window_pixels=ex.n_window, valid_pixels=ex.n_valid,
                            source_ids=[search_rec.source_id, rec.source_id],
                            limitations=list(ex.limitations) + shadow_limits, **base), {}, ex.incidence_deg
        indicators, values = spectral.m3_indicators(ex.spectra, ex.wavelengths)
        ibd1 = values.get("IBD1000")
        ibd1_med = float(np.nanmedian(ibd1)) if ibd1 is not None and np.isfinite(ibd1).any() else None
        convex = ibd1_med is not None and ibd1_med < spectral.M3_CONVEX_1UM
        if convex:
            # a strongly negative integrated 1 um band depth (convex 1 um region) is not a silicate signature;
            # seen on M3 observations that disagree with others over the same ground (Copernicus peak,
            # Apollo 17): treat the observation as suspect and prefer another one
            ctx.problem("mineralogy", Reason.invalid_data,
                        f"{ex.product_id}: IBD1000 median {ibd1_med:.2f} (convex 1 µm region, not a silicate "
                        "absorption); observation treated as spectrally suspect", rec.source_id)
            if prod is not candidates[-1]:
                continue
        mean_spec = np.nanmean(ex.spectra, axis=0)
        analog_inputs = {k: spectral.legacy_analog_input(values[k]) for k in ("legacy_bd1000", "legacy_bd2000")
                         if k in values}
        analog_inputs = {k: v for k, v in analog_inputs.items() if v is not None}
        analog_inputs["_sem"] = {k: spectral.window_sem(values[k]) for k in analog_inputs}
        limitations = list(ex.limitations) + shadow_limits
        if convex:
            limitations.append("Only available observation shows a convex 1 µm region (IBD1000 strongly negative): "
                               "band depths are unreliable here and no mineral family is inferred.")
            analog_inputs = {}
            indicators = [i.model_copy(update={"detected": None}) if i.detected is not None else i
                          for i in indicators]
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


M3_TIMEOUT_MSG = ("M3 reads from the PDS Imaging Node did not finish within {s:.0f} s; mineralogy was not measured. "
                  "A timeout is not evidence that minerals are absent; the other sections are unaffected.")


async def mineralogy_with_deadline(ctx: Context) -> tuple[MineralogySection, dict[str, float], float | None]:
    """mineralogy_step under its own budget (same pattern as the altimetry deadline): a slow PDS fails only the
    mineralogy section instead of timing out the whole job and losing every other completed section."""
    s = get_settings()
    try:
        return await asyncio.wait_for(mineralogy_step(ctx), timeout=s.mineralogy_deadline_s)
    except asyncio.TimeoutError:
        msg = M3_TIMEOUT_MSG.format(s=s.mineralogy_deadline_s)
        rec = ctx.source(provider="PDS Imaging Node (via ODE)", service="HTTP byte-range read of M3 L2 RFL + L1B LOC",
                         instrument="M3", mission="Chandrayaan-1", product_type="L2 reflectance", status="error",
                         message=msg)
        ctx.problem("mineralogy", Reason.provider_error, msg, rec.source_id)
        return MineralogySection(status=SectionStatus.failed, reason=Reason.provider_error,
                                 instrument="M3 (Moon Mineralogy Mapper)", source_ids=[rec.source_id],
                                 limitations=[msg]), {}, None


async def illumination_step(ctx: Context) -> EnvironmentSection:
    """South polar illumination context (model-derived, Mazarico et al. 2011). Independent of mineralogy."""
    L = lola_illumination
    try:
        res = await L.sample(ctx.http, ctx.lat, ctx.lon, ctx.req.radius_km)
    except L.NotApplicable as exc:
        return EnvironmentSection(status=SectionStatus.unavailable, reason=Reason.not_supported, notes=[str(exc)])
    except ProviderError as exc:
        rec = ctx.source(provider=L.PROVIDER, service="HTTP byte-range read of PDS IMG polar illumination maps",
                         instrument="LOLA (derived)", mission="LRO", status="error", message=str(exc))
        ctx.problem("environment", Reason.provider_error, str(exc), rec.source_id)
        return EnvironmentSection(status=SectionStatus.failed, reason=Reason.provider_error,
                                  source_ids=[rec.source_id])
    await ctx.progress("illumination")
    rec = ctx.source(
        provider=L.PROVIDER, service="HTTP byte-range read of PDS IMG polar illumination maps",
        instrument="LOLA (derived)", mission="LRO", product_type="polar illumination model (Mazarico et al. 2011)",
        product_id=res.products["sun"], url=L.BASE + res.products["sun"] + ".IMG",
        spatial_resolution_m=res.scale_m,
        processing=[f"grid {res.grid} ({res.scale_m:.0f} m/px), polar stereographic sphere R=1737.4 km",
                    f"{res.n_pixels} pixels within {res.half_window_km:g} km of the point",
                    "layers: " + ", ".join(res.products.values())],
        limitations=list(L.LIMITATIONS))
    psr = float((res.values["psr"] > 0.5).mean()) if res.n_pixels else None
    notes = []
    if psr:
        pct = round(100 * psr)
        notes.append(f"{pct if pct >= 1 else '<1'}% of the analysed area is permanently shadowed in the model "
                     "(never sunlit): a potential cold trap. Ice is not measured by this section.")
    limitations = list(L.LIMITATIONS)
    if res.half_window_km < res.requested_radius_km:
        limitations.append(f"Illumination statistics use the {res.half_window_km:g} km around the point, not the "
                           f"whole requested {res.requested_radius_km:g} km radius.")
    req_area = math.pi * res.requested_radius_km ** 2
    area = res.n_pixels * (res.scale_m / 1000.0) ** 2
    return EnvironmentSection(
        status=SectionStatus.available if res.n_pixels else SectionStatus.unavailable,
        reason=None if res.n_pixels else Reason.insufficient_data, kind="model_derived",
        method="LOLA-derived average illumination over the 18.6-year nutation cycle (Mazarico et al. 2011)",
        sunlit_fraction=spectral.stats(res.values["sun"]), permanent_shadow_fraction=psr,
        earth_visible_fraction=spectral.stats(res.values["earth"]),
        centre={"sunlit_fraction": res.centre["sun"], "permanent_shadow": res.centre["psr"],
                "earth_visible_fraction": res.centre["earth"]},
        analyzed_extent={"radius_km": res.half_window_km, "pixel_size_m": res.scale_m, "pixels": res.n_pixels,
                         "area_km2": round(area, 2), "requested_radius_km": res.requested_radius_km,
                         "fraction_of_requested_area": round(min(1.0, area / req_area), 4) if req_area else None},
        products=list(res.products.values()), source_ids=[rec.source_id], limitations=limitations, notes=notes)


async def run(req: AnalyzeRequest, http: HttpClient, analysis_id: str, created_at, progress: ProgressFn
              ) -> AnalysisResult:
    done: list[str] = []

    async def prog(step: str) -> None:
        done.append(step)
        await progress(step)

    ctx = Context(body="moon", req=req, coords=build_coordinates(req, "moon"), http=http, progress=prog)
    failed = SectionStatus.failed
    imagery, topo_s, (min_s, analog_inputs, incidence), environment, _, _ = await asyncio.gather(
        guarded(ctx, "imagery", imagery_step(ctx), lambda: ImagerySection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "topography", topography_step(ctx),
                lambda: TopographySection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "mineralogy", mineralogy_with_deadline(ctx),
                lambda: (MineralogySection(status=failed, reason=Reason.invalid_data), {}, None)),
        guarded(ctx, "environment", illumination_step(ctx),
                lambda: EnvironmentSection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "discovery", pds_step(ctx, ["lola", "diviner"]), lambda: None),
        guarded(ctx, "discovery", usgs_step(ctx), lambda: None))
    analogs = similarity.compare("moon", analog_inputs)
    if min_s.status not in (SectionStatus.available, SectionStatus.partial):
        analogs.reason = Reason.not_attempted
    extra = ["Earth analogs use only band depths with identical definitions; Moon and Earth surfaces differ "
             "(space weathering, no water or vegetation, regolith grain size)."]
    conf = assess_confidence(topo_s, min_s, extra, incidence)
    terrestrial = guarded_sync(ctx, lambda: analog_sites.match("moon", min_s, ctx.lat))
    try:   # CPU-bound (terrain families); off the event loop. Independent of mineralogy.
        geomorph = await asyncio.to_thread(geomorph_analogs.section, ctx.lat, ctx.lon, ctx.altimetry,
                                           ctx.altimetry_radius_km, ctx.altimetry_source_id)
        await prog("geomorphology")
    except Exception as exc:  # noqa: BLE001 - optional section boundary
        log.exception("geomorphology crashed")
        ctx.problem("geomorphology", Reason.invalid_data, f"internal error: {type(exc).__name__}: {exc}")
        geomorph = GeomorphologySection(status=SectionStatus.failed, reason=Reason.invalid_data)
    return finalize(ctx, analysis_id, created_at, imagery, topo_s, min_s, analogs, conf, done,
                    terrestrial=terrestrial, environment=environment, geomorphology=geomorph)
