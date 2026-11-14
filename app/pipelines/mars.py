"""Martian pipeline: Trek imagery + MOLA topography + CRISM MTRDR + analogs.

Mars-specific spectral logic: CRISM team summary parameters (hydration,
phyllosilicates, carbonates, sulfates, ices, mafics). Lunar indices are not
applied here.
"""

from __future__ import annotations

import asyncio

import numpy as np

from app.config import get_settings
from app.providers import crism, ode
from app.providers.http import HttpClient, ProviderError
from app.schemas.analysis import (AnalysisResult, AnalyzeRequest, ImagerySection, MineralogySection, Reason,
                                  SectionStatus, TopographySection)
from app.science import analog_sites, similarity, spectral
from app.science.coordinates import footprint_contains, region_box
from app.pipelines.common import (Context, ProgressFn, assess_confidence, build_coordinates, finalize, guarded,
                                  guarded_sync,
                                  imagery_step, pds_step, topography_step, usgs_step)

CRISM_IIPT = dict(target="mars", ihid="MRO", iid="CRISM", pt="MTRDR")


async def _trdr_count(ctx: Context, box) -> int | None:
    """Unprojected targeted TRDRs (not processed by the MVP) — reported to
    distinguish 'no CRISM data' from 'no analysis-ready CRISM data'."""
    try:
        prods, _ = await ode.search_products(ctx.http, target="mars", ihid="MRO", iid="CRISM", pt="TRDRFRT07",
                                             box=box, limit=10, results="o")
        return len(prods)
    except ProviderError:
        return None


async def mineralogy_step(ctx: Context) -> tuple[MineralogySection, dict[str, float], float | None]:
    s = get_settings()
    box = region_box(ctx.lat, ctx.lon, min(ctx.req.radius_km, 0.5), "mars")
    try:
        products, query = await ode.search_products(ctx.http, box=box, limit=s.spectral_max_products_considered,
                                                    **CRISM_IIPT)
    except ProviderError as exc:
        rec = ctx.source(provider="PDS Geosciences Node", service="ODE REST product search", instrument="CRISM",
                         mission="Mars Reconnaissance Orbiter", product_type="MTRDR", status="error", message=str(exc))
        ctx.problem("mineralogy", Reason.provider_error, str(exc), rec.source_id)
        return MineralogySection(status=SectionStatus.failed, reason=Reason.provider_error, instrument="CRISM",
                                 source_ids=[rec.source_id]), {}, None

    flagged = [(p, footprint_contains(p.footprint_wkt or "", ctx.lat, ctx.lon)) for p in products]
    containing = [p for p, inside in flagged if inside is True]
    # best spatial sampling first, then lowest incidence
    candidates = sorted([p for p, inside in flagged if inside is not False],
                        key=lambda p: (p.map_scale_m or 1e9, p.incidence_deg if p.incidence_deg is not None else 90))[:3]
    search_rec = ctx.source(
        provider="PDS Geosciences Node", service="ODE REST product search", instrument="CRISM",
        mission="Mars Reconnaissance Orbiter", product_type="MTRDR (mro-m-crism-5-rdr-mptargeted-v1)",
        query=query, status="ok" if products else "empty",
        message=f"{len(products)} MTRDR footprints intersect the search box; {len(containing)} contain the point")
    await ctx.progress("crism_discovery")
    base = dict(instrument="CRISM (Compact Reconnaissance Imaging Spectrometer for Mars)",
                products_found=len(products), products_containing_point=len(containing))

    if not candidates:
        n_trdr = await _trdr_count(ctx, box)
        if n_trdr:
            msg = (f"No map-projected CRISM MTRDR covers the point, but {n_trdr} unprojected targeted TRDR "
                   "observation(s) exist; processing TRDRs (geometry + atmospheric correction) is outside the MVP.")
            reason = Reason.no_compatible_observations
        elif products:
            msg, reason = "MTRDR footprints intersect the box but none contains the point", Reason.no_compatible_observations
        else:
            msg, reason = "no CRISM targeted observation covers the point", Reason.no_coverage
        ctx.problem("mineralogy", reason, msg, search_rec.source_id)
        return MineralogySection(status=SectionStatus.unavailable, reason=reason, source_ids=[search_rec.source_id],
                                 limitations=[msg], **base), {}, None

    errors = []
    for prod in candidates:
        try:
            ex = await crism.extract(ctx.http, prod, ctx.lat, ctx.lon, ctx.req.radius_km)
        except crism.OutsideImage as exc:
            errors.append((prod.pdsid, Reason.no_compatible_observations, str(exc)))
            continue
        except ProviderError as exc:
            errors.append((prod.pdsid, Reason.provider_error, str(exc)))
            continue
        rec = ctx.source(
            provider="PDS Geosciences Node", service="HTTP byte-range read of CRISM MTRDR SU/IF cubes",
            instrument="CRISM", mission="Mars Reconnaissance Orbiter", product_type="MTRDR",
            product_id=ex.product_id, url=ex.su_url, observation_start=ex.observation_start,
            observation_end=ex.observation_end, spatial_resolution_m=ex.pixel_size_m,
            processing=ex.processing, limitations=ex.limitations)
        await ctx.progress("crism_extraction")
        if ex.n_valid < 4:
            ctx.problem("mineralogy", Reason.insufficient_data,
                        f"{ex.n_valid} valid CRISM pixels in {ex.product_id}", rec.source_id)
            if prod is not candidates[-1]:
                continue  # another observation may have valid pixels at the point
            return MineralogySection(status=SectionStatus.unavailable, reason=Reason.insufficient_data,
                                     product_used=ex.product_id, window_pixels=ex.n_window, valid_pixels=ex.n_valid,
                                     analyzed_extent=ex.analyzed_extent,
                                     source_ids=[search_rec.source_id, rec.source_id], limitations=ex.limitations,
                                     **base), {}, ex.incidence_deg
        if ex.incidence_deg is not None and ex.incidence_deg >= spectral.MAX_USABLE_INCIDENCE_DEG:
            ctx.problem("mineralogy", Reason.insufficient_data,
                        f"{ex.product_id}: solar incidence {ex.incidence_deg:.1f}° >= "
                        f"{spectral.MAX_USABLE_INCIDENCE_DEG:.0f}° (surface unlit or grazing light); "
                        "summary parameters not used", rec.source_id)
            if prod is not candidates[-1]:
                continue  # another observation may be illuminated
            return MineralogySection(status=SectionStatus.unavailable, reason=Reason.insufficient_data,
                                     product_used=ex.product_id, window_pixels=ex.n_window, valid_pixels=ex.n_valid,
                                     analyzed_extent=ex.analyzed_extent,
                                     source_ids=[search_rec.source_id, rec.source_id], limitations=ex.limitations,
                                     **base), {}, ex.incidence_deg
        indicators = [spectral.crism_indicator(n, v) for n, v in ex.params.items()]
        analog_inputs: dict = {}
        sems: dict[str, float | None] = {}
        if ex.legacy_spectra is not None and ex.legacy_spectra.shape[0] >= 4:
            wl = ex.legacy_wavelengths
            for name, (c, l, r) in {"legacy_bd1000": (1000, 800, 1300), "legacy_bd2000": (2000, 1700, 2300)}.items():
                arr = spectral.legacy_band_depth(ex.legacy_spectra, wl, c, l, r)
                if arr is not None and np.isfinite(arr).any():
                    analog_inputs[name] = spectral.legacy_analog_input(arr)
                    sems[name] = spectral.window_sem(arr)
                    ind = spectral.SpectralIndicator(
                        name=name, value=spectral.stats(arr),
                        definition=spectral.LEGACY_DEF.format(c=c, l=l, r=r, on=" on MTRDR I/F"),
                        reference="GEØ.IA terrestrial EMIT library definition", sensitive_to="Fe2+ absorption (coarse)",
                        screening_threshold=0.0, threshold_basis=spectral.DETECTION_BASIS,
                        fraction_above_threshold=float(np.mean(arr[np.isfinite(arr)] > 0)),
                        n_pixels=int(np.isfinite(arr).sum()),
                        interpretation=spectral.legacy_interpretation(arr, detailed=False),
                        comparability="direct", detected=spectral.detected(arr))
                    indicators.append(ind)
        if sems:
            analog_inputs["_sem"] = sems
        limitations = list(ex.limitations)
        ext = ex.analyzed_extent or {}
        if ext.get("fraction_of_requested_area") is not None and ext["fraction_of_requested_area"] < 0.95:
            w = ext["window_km"]
            limitations.append(
                f"CRISM mineralogy describes a {w[0]:.1f} x {w[1]:.1f} km window ({ext['area_km2']:.1f} km², "
                f"{100 * ext['fraction_of_requested_area']:.0f}% of the requested {ext['requested_radius_km']:g} km "
                f"circle) centred on the point; it is not representative of the whole region.")
        if ex.incidence_deg is not None and ex.incidence_deg > 70:
            limitations.append(f"high solar incidence ({ex.incidence_deg:.0f}°)")
        status = SectionStatus.available if ex.n_valid >= 25 else SectionStatus.partial
        return MineralogySection(
            status=status, reason=None if status == SectionStatus.available else Reason.insufficient_data,
            method="CRISM MTRDR summary parameters (CRISM team) over a pixel window",
            product_used=ex.product_id, pixel_distance_m=round(ex.pixel_size_m / 2, 1),
            window_pixels=ex.n_window, valid_pixels=ex.n_valid, analyzed_extent=ex.analyzed_extent,
            indicators=indicators, spectral_character=spectral.crism_character(indicators, ex.params),
            source_ids=[search_rec.source_id, rec.source_id], limitations=limitations, **base), \
            analog_inputs, ex.incidence_deg

    reason = Reason.provider_error if any(r == Reason.provider_error for _, r, _ in errors) \
        else Reason.no_compatible_observations
    for pid, r, msg in errors:
        ctx.problem("mineralogy", r, f"{pid}: {msg}", search_rec.source_id)
    st = SectionStatus.failed if reason == Reason.provider_error else SectionStatus.unavailable
    return MineralogySection(status=st, reason=reason, source_ids=[search_rec.source_id], **base), {}, None


async def run(req: AnalyzeRequest, http: HttpClient, analysis_id: str, created_at, progress: ProgressFn
              ) -> AnalysisResult:
    done: list[str] = []

    async def prog(step: str) -> None:
        done.append(step)
        await progress(step)

    ctx = Context(body="mars", req=req, coords=build_coordinates(req, "mars"), http=http, progress=prog)
    failed = SectionStatus.failed
    imagery, topo_s, (min_s, analog_inputs, incidence), _, _ = await asyncio.gather(
        guarded(ctx, "imagery", imagery_step(ctx), lambda: ImagerySection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "topography", topography_step(ctx),
                lambda: TopographySection(status=failed, reason=Reason.invalid_data)),
        guarded(ctx, "mineralogy", mineralogy_step(ctx),
                lambda: (MineralogySection(status=failed, reason=Reason.invalid_data), {}, None)),
        guarded(ctx, "discovery", pds_step(ctx, ["crism"]), lambda: None),
        guarded(ctx, "discovery", usgs_step(ctx), lambda: None))
    analogs = similarity.compare("mars", analog_inputs)
    if min_s.status not in (SectionStatus.available, SectionStatus.partial):
        analogs.reason = Reason.not_attempted
    extra = ["CRISM I/F and terrestrial EMIT reflectance differ in atmospheric/photometric correction; "
             "band-depth comparison is a shape comparison, not a compositional match."]
    conf = assess_confidence(topo_s, min_s, extra, incidence)
    terrestrial = guarded_sync(ctx, lambda: analog_sites.match("mars", min_s, ctx.lat))
    return finalize(ctx, analysis_id, created_at, imagery, topo_s, min_s, analogs, conf, done,
                    terrestrial=terrestrial)
