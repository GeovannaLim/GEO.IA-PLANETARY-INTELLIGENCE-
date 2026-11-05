"""Google Earth Engine access for the Earth endpoint only.

Reused from the legacy backend (``gee_auth.py`` and
``run_earth_pipeline.extract_gee_indices``) after review:

kept    service-account auth from env JSON / key file / ADC, cached; secrets
        never logged or returned. S2 SR masking + NDVI, ferric ratio and VNIR
        slope; ASTER TIR Ninomiya indices; EMIT L2A band depths with exact
        band-name construction (``reflectance_<n>``, no zero padding).
changed EMIT band depths keep the legacy definition (median composite, then
        3-band depth, then ROI mean) so values stay comparable with the
        reference library. Added Copernicus GLO-30 DEM elevation/slope
        statistics and scene counts for provenance.
removed the nearest-library-deposit fallback (it returned another site's
        measurements for arbitrary coordinates), AlphaEarth texture, EMIT
        entropy and all mining-specific scoring.

``earthengine-api`` is imported lazily, so Moon/Mars never need it.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any

from app.config import get_settings

_LOCK = threading.RLock()
_STATE: dict[str, Any] = {"attempted": False, "initialized": False, "method": None, "detail": None}

S2_START, S2_END, S2_CLOUD = "2020-01-01", "2024-01-01", 60
_TIR_UCC = [6.882e-3, 6.780e-3, 6.590e-3, 5.693e-3, 5.225e-3]  # ASTER B10..B14 unit conversion


def configured_sources() -> list[str]:
    s = get_settings()
    out = []
    if s.gee_service_account_json:
        out.append("GEE_SERVICE_ACCOUNT_JSON")
    if s.gee_service_account_key_file:
        out.append("GEE_SERVICE_ACCOUNT_KEY_FILE" + ("" if os.path.exists(s.gee_service_account_key_file)
                                                     else " (path missing)"))
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        out.append("GOOGLE_APPLICATION_CREDENTIALS")
    return out


def initialize(force: bool = False) -> dict:
    """Initialise once; never raises; returns a secret-free status."""
    s = get_settings()
    with _LOCK:
        if _STATE["attempted"] and not force:
            return dict(_STATE)
        _STATE.update(attempted=True, initialized=False, method=None)
        try:
            import ee
        except Exception as exc:  # noqa: BLE001
            _STATE["detail"] = f"earthengine-api not importable ({type(exc).__name__})"
            return dict(_STATE)
        attempts = []
        if s.gee_service_account_json:
            def via_json() -> None:
                info = json.loads(s.gee_service_account_json)
                fd, path = tempfile.mkstemp(suffix=".json")
                try:
                    with os.fdopen(fd, "w") as fh:
                        fh.write(s.gee_service_account_json)
                    ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], path), project=s.gee_project)
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            attempts.append(("service_account_json_env", via_json))
        for path in (s.gee_service_account_key_file, os.getenv("GOOGLE_APPLICATION_CREDENTIALS")):
            if path and os.path.exists(path):
                def via_file(p: str = path) -> None:
                    with open(p, encoding="utf-8") as fh:
                        email = json.load(fh)["client_email"]
                    ee.Initialize(ee.ServiceAccountCredentials(email, p), project=s.gee_project)
                attempts.append(("service_account_key_file", via_file))
        if not attempts and s.environment == "development":
            attempts.append(("interactive_credentials", lambda: ee.Initialize(project=s.gee_project)))
        errors = []
        for name, fn in attempts:
            try:
                fn()
                _STATE.update(initialized=True, method=name, detail="Earth Engine initialised")
                return dict(_STATE)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {type(exc).__name__}")
        _STATE["detail"] = ("no Earth Engine credential configured" if not attempts
                            else "Earth Engine initialisation failed: " + "; ".join(errors))
        return dict(_STATE)


def status() -> dict:
    st = dict(_STATE) if _STATE["attempted"] else {"attempted": False, "initialized": False,
                                                   "method": None, "detail": "not yet attempted"}
    st["configured_sources"] = configured_sources()
    return st


def emit_band(target_nm: float) -> str:
    """EMIT L2A RFL band name nearest ``target_nm`` (381 nm + 7.4358 nm steps,
    285 bands; GEE names have no zero padding)."""
    idx = max(0, min(284, round((target_nm - 381.0) / 7.4358)))
    return f"reflectance_{idx}"


def extract(lat: float, lon: float, radius_m: int) -> dict:
    """Blocking GEE extraction (run in a worker thread). Raises on failure."""
    import ee

    pt = ee.Geometry.Point([lon, lat])
    roi = pt.buffer(radius_m)

    def mask_s2(img):
        scl = img.select("SCL")
        bad = scl.eq(1).Or(scl.eq(3)).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).Or(scl.eq(11))
        return img.updateMask(bad.Not()).divide(10000).copyProperties(img, ["system:time_start"])

    s2c = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi).filterDate(S2_START, S2_END)
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", S2_CLOUD)).map(mask_s2))
    s2 = s2c.median()
    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("ndvi")
    rock = ndvi.lt(0.3)
    ferric = s2.select("B4").divide(s2.select("B2")).rename("vnir_ferric_ratio").updateMask(rock)
    slope = (s2.select("B8A").subtract(s2.select("B2")).divide((865 - 490) / 1000.0)
             .rename("vnir_slope").updateMask(rock))
    ucc = ee.Image.constant(_TIR_UCC).rename(["B10", "B11", "B12", "B13", "B14"])
    ast = (ee.ImageCollection("ASTER/AST_L1T_003").filterBounds(roi).median()
           .select(["B10", "B11", "B12", "B13", "B14"]).subtract(1).multiply(ucc))
    b10, b11, b12, b13 = (ast.select(b) for b in ("B10", "B11", "B12", "B13"))
    silica = b11.multiply(b11).divide(b10.multiply(b12)).rename("aster_silica_index")
    mafic = b12.divide(b13).rename("aster_mafic_index")
    dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").filterBounds(roi).select("DEM").mosaic() \
        .setDefaultProjection("EPSG:4326", None, 30)
    terrain = ee.Terrain.slope(dem).rename("slope_deg")

    core = ndvi.addBands([ferric, slope, mafic, silica]).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=roi, scale=90, maxPixels=1e9, bestEffort=True, tileScale=4).getInfo()
    topo_stats = dem.rename("elev").addBands(terrain).reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.percentile([5, 50, 95]), sharedInputs=True)
        .combine(ee.Reducer.minMax(), sharedInputs=True).combine(ee.Reducer.count(), sharedInputs=True),
        geometry=roi, scale=90, maxPixels=1e9, bestEffort=True, tileScale=4).getInfo()
    counts = {"s2_images": s2c.size().getInfo()}

    emit: dict[str, Any] = {"status": "unavailable", "scene_count": 0, "hyp_bd_1000": None, "hyp_bd_2000": None}
    try:
        ic = ee.ImageCollection("NASA/EMIT/L2A/RFL").filterBounds(roi)
        n = ic.size().getInfo()
        emit["scene_count"] = n
        if n:
            med = ic.median()
            avail = set(med.bandNames().getInfo())

            def bd(c, l, r, name):
                bc, bl, br = emit_band(c), emit_band(l), emit_band(r)
                if not {bc, bl, br} <= avail:
                    return None
                cont = med.select(bl).add(med.select(br)).divide(2)
                return cont.subtract(med.select(bc)).divide(cont).rename(name)
            imgs = [i for i in (bd(1000, 800, 1300, "hyp_bd_1000"), bd(2000, 1700, 2300, "hyp_bd_2000")) if i]
            if imgs:
                stack = imgs[0] if len(imgs) == 1 else imgs[0].addBands(imgs[1])
                vals = stack.reduceRegion(reducer=ee.Reducer.mean(), geometry=roi, scale=90, maxPixels=1e9,
                                          bestEffort=True, tileScale=4).getInfo()
                emit.update(vals)
                emit["status"] = "ok" if len(imgs) == 2 else "partial"
    except Exception as exc:  # noqa: BLE001 - EMIT is optional, failure recorded
        emit["status"] = "error"
        emit["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    return {"core": core, "topography": topo_stats, "emit": emit, "counts": counts}
