"""Earth pipeline (Google Earth Engine). Without credentials every section is
``unavailable / not_configured``; nothing is substituted."""

from __future__ import annotations

import asyncio

from app.providers import earth_engine as gee
from app.providers.http import HttpClient
from app.schemas.analysis import (AnalysisResult, AnalyzeRequest, EarthAnalogSection, ImagerySection,
                                  MineralogySection, Reason, SectionStatus, SpectralIndicator, Stats,
                                  TopographySection)
from app.science import similarity
from app.science.spectral import DETECTION_BASIS, detected_from_stats
from app.pipelines.common import (Context, ProgressFn, assess_confidence, build_coordinates, finalize, safe_float)


def _num(d: dict, k: str) -> float | None:
    v = d.get(k)
    return safe_float(float(v)) if isinstance(v, (int, float)) else None


async def run(req: AnalyzeRequest, http: HttpClient, analysis_id: str, created_at, progress: ProgressFn
              ) -> AnalysisResult:
    done: list[str] = []

    async def prog(step: str) -> None:
        done.append(step)
        await progress(step)

    ctx = Context(body="earth", req=req, coords=build_coordinates(req, "earth"), http=http, progress=prog)
    imagery = ImagerySection(status=SectionStatus.unavailable, reason=Reason.not_supported)
    st = await asyncio.to_thread(gee.initialize)
    if not st["initialized"]:
        rec = ctx.source(provider="Google Earth Engine", service="earthengine-api", status="skipped",
                         message=st.get("detail"))
        ctx.problem("earth_engine", Reason.not_configured, st.get("detail") or "not configured", rec.source_id)
        un = dict(status=SectionStatus.unavailable, reason=Reason.not_configured, source_ids=[rec.source_id])
        conf = assess_confidence(TopographySection(status=SectionStatus.unavailable),
                                 MineralogySection(status=SectionStatus.unavailable),
                                 ["Earth Engine credentials not configured on this host"])
        return finalize(ctx, analysis_id, created_at, imagery, TopographySection(**un), MineralogySection(**un),
                        EarthAnalogSection(**un), conf, done, earth_obs=None)

    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(gee.extract, ctx.lat, ctx.lon, int(req.radius_km * 1000)), timeout=180)
    except Exception as exc:  # noqa: BLE001 - GEE raises many exception types
        rec = ctx.source(provider="Google Earth Engine", service="reduceRegion", status="error",
                         message=f"{type(exc).__name__}: {str(exc)[:300]}")
        ctx.problem("earth_engine", Reason.provider_error, rec.message or "", rec.source_id)
        fail = dict(status=SectionStatus.failed, reason=Reason.provider_error, source_ids=[rec.source_id])
        conf = assess_confidence(TopographySection(status=SectionStatus.failed),
                                 MineralogySection(status=SectionStatus.failed), [])
        return finalize(ctx, analysis_id, created_at, imagery, TopographySection(**fail), MineralogySection(**fail),
                        EarthAnalogSection(**fail), conf, done)
    await prog("earth_engine")

    t = data["topography"]
    dem_rec = ctx.source(provider="Google Earth Engine", service="reduceRegion", mission="Copernicus",
                         product_type="COPERNICUS/DEM/GLO30", spatial_resolution_m=30,
                         processing=["mosaic over ROI; ee.Terrain.slope; mean/percentiles at 90 m scale"])
    topo_s = TopographySection(
        status=SectionStatus.available if _num(t, "elev_mean") is not None else SectionStatus.unavailable,
        reason=None if _num(t, "elev_mean") is not None else Reason.no_coverage,
        method="Copernicus GLO-30 DEM statistics (Earth Engine)", datum="EGM2008 geoid",
        n_points=int(t.get("elev_count") or 0) or None, sampled_radius_km=req.radius_km,
        elevation_m=Stats(mean=_num(t, "elev_mean"), median=_num(t, "elev_p50"), min=_num(t, "elev_min"),
                          max=_num(t, "elev_max"), p05=_num(t, "elev_p5"), p95=_num(t, "elev_p95")),
        relief_m=(_num(t, "elev_p95") - _num(t, "elev_p5")) if _num(t, "elev_p95") is not None
        and _num(t, "elev_p5") is not None else None,
        local_slope_degrees=Stats(mean=_num(t, "slope_deg_mean"), median=_num(t, "slope_deg_p50"),
                                  p05=_num(t, "slope_deg_p5"), p95=_num(t, "slope_deg_p95")),
        slope_baseline_m=30, elevation_m_mean=_num(t, "elev_mean"), slope_degrees=_num(t, "slope_deg_p50"),
        coverage_fraction=None, source_ids=[dem_rec.source_id])

    emit = data["emit"]
    emit_rec = ctx.source(provider="Google Earth Engine", service="reduceRegion", instrument="EMIT",
                          mission="ISS", product_type="NASA/EMIT/L2A/RFL", spatial_resolution_m=60,
                          status="ok" if emit["status"] in ("ok", "partial") else "empty",
                          message=f"{emit.get('scene_count')} scenes; status {emit['status']}"
                          + (f"; {emit['error']}" if emit.get("error") else ""),
                          processing=["median composite", "3-band legacy depths (800/1000/1300, 1700/2000/2300 nm)",
                                      "ROI mean at 90 m scale"])
    indicators, analog_inputs = [], {}
    for k, name in (("hyp_bd_1000", "legacy_bd1000"), ("hyp_bd_2000", "legacy_bd2000")):
        v = _num(emit, k)
        if v is None:
            continue
        analog_inputs[name] = max(0.0, v)
        indicators.append(SpectralIndicator(
            name=name, value=Stats(mean=v), definition="legacy 3-band depth on EMIT median composite (ROI mean, unclamped; clamped at 0 for the analog comparison)",
            reference="GEØ.IA terrestrial EMIT library definition", n_pixels=0,
            interpretation=("ROI-mean value is negative (convex continuum): no absorption at this wavelength. "
                            "The analog comparison uses 0, as in the reference library." if v < 0 else
                            "ROI-mean value; per-pixel distribution not retrieved"), comparability="direct"))
    masked = data.get("emit_masked") or {"status": "unavailable"}
    masked_rec = ctx.source(
        provider="Google Earth Engine", service="reduceRegion", instrument="EMIT", mission="ISS",
        product_type="NASA/EMIT/L2A/RFL", spatial_resolution_m=gee.EMIT_SCALE_M,
        status="ok" if masked.get("status") == "ok" else "empty" if masked.get("status") != "error" else "error",
        message=f"{masked.get('scene_count', 0)} scenes; status {masked.get('status')}"
        + (f"; {masked['error']}" if masked.get("error") else ""),
        processing=["per-scene mask: reflectance range, EMIT aggregate_flag (cloud/cirrus/water/spacecraft)",
                    "rock mask: + NDVI < 0.2, NDSI <= 0.4, NDWI <= 0", "median composite of unmasked pixels",
                    "per-pixel 3-band depths (unclamped), ROI statistics at 60 m"])
    rock = (masked.get("variants") or {}).get("rock") or {}
    for w in ("bd1000", "bd2000"):
        r = rock.get(w) or {}
        if not r.get("n_pixels") or r.get("mean") is None:
            continue
        det = detected_from_stats(r["mean"], r.get("std"), r.get("median"), r["n_pixels"], r.get("fraction_positive"))
        indicators.append(SpectralIndicator(
            name=f"rock_{w}", value=Stats(mean=r["mean"], median=r.get("median"), std=r.get("std")),
            definition=f"3-band depth at {w[2:]} nm on EMIT median composite of rock pixels (cloud/water/vegetation/"
                       "snow masked); per-pixel, unclamped", reference="GEØ.IA remeasurement (EMIT L2A, masked)",
            sensitive_to="Fe2+ absorption (coarse)" if w == "bd1000" else
            "Fe2+ absorption near 2 µm; residual atmospheric CO2 near 2.0 µm",
            screening_threshold=0.0, threshold_basis=DETECTION_BASIS,
            fraction_above_threshold=r.get("fraction_positive"), n_pixels=r["n_pixels"],
            interpretation=("Positive absorption detected." if det else
                            "No statistically significant absorption." if det is False else
                            "Detection not assessed (incomplete statistics)."),
            comparability="proxy", detected=det))
    min_s = MineralogySection(
        status=SectionStatus.available if indicators else SectionStatus.unavailable,
        reason=None if indicators else Reason.no_coverage, instrument="EMIT (imaging spectrometer)",
        method="EMIT L2A surface reflectance band depths", indicators=indicators, source_ids=[emit_rec.source_id, masked_rec.source_id],
        limitations=["EMIT coverage is limited to arid regions within ±52° latitude"])
    core_rec = ctx.source(provider="Google Earth Engine", service="reduceRegion",
                          product_type="COPERNICUS/S2_SR_HARMONIZED + ASTER/AST_L1T_003",
                          query={"s2_window": [gee.S2_START, gee.S2_END], "s2_cloud_lt": gee.S2_CLOUD,
                                 "s2_images": data["counts"].get("s2_images")},
                          processing=["S2 SCL cloud/shadow mask; NDVI<0.3 rock mask for ferric/slope",
                                      "ASTER TIR radiance-ratio Ninomiya indices"])
    earth_obs = {"values": {k: _num(data["core"], k) for k in
                            ("ndvi", "vnir_ferric_ratio", "vnir_slope", "aster_mafic_index", "aster_silica_index")},
                 "source_ids": [core_rec.source_id],
                 "note": "Earth-only context indices; not compared with lunar or Martian data.",
                 "emit_masked": masked, "emit_masked_source_id": masked_rec.source_id}
    analogs = similarity.compare("earth", analog_inputs) if analog_inputs else EarthAnalogSection(
        status=SectionStatus.unavailable, reason=Reason.not_attempted)
    conf = assess_confidence(topo_s, MineralogySection(status=SectionStatus.unavailable), [])
    return finalize(ctx, analysis_id, created_at, imagery, topo_s, min_s, analogs, conf, done, earth_obs=earth_obs)
