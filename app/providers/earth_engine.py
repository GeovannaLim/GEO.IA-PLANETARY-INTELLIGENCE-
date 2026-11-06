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
    try:
        emit_masked = extract_emit_masked(ee, roi)
    except Exception as exc:  # noqa: BLE001 - recorded, never substituted
        emit_masked = {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    return {"core": core, "topography": topo_stats, "emit": emit, "counts": counts, "emit_masked": emit_masked}


# --------------------------------------------------------------------------- #
# Quality-masked EMIT measurement (remeasurement of the terrestrial library)
# --------------------------------------------------------------------------- #
EMIT_SCALE_M = 60
# Spectral-index thresholds are conventional screening values, reported with every result:
# NDVI < 0.2 bare/sparsely vegetated surface; NDSI > 0.4 snow (Hall et al. 1995, MODIS);
# NDWI (McFeeters 1996, green/NIR) > 0 open water.
MASK_RULES = {"reflectance_valid_range": [0.0, 1.5], "aggregate_flag": "== 0 (EMIT L2A: cloud, cirrus, water, "
              "spacecraft, dilated cloud)", "ndvi_max": 0.2, "ndsi_snow_min": 0.4, "ndwi_water_min": 0.0}
EMIT_BANDS_NM = {"g": 560, "r": 660, "nir": 860, "swir1": 1640, "c800": 800, "b1000": 1000, "c1300": 1300,
                 "c1700": 1700, "b2000": 2000, "c2300": 2300}
VARIANTS = ("raw", "quality", "rock")


def _nearest(wavelengths: list[float], nm: float) -> int:
    return min(range(len(wavelengths)), key=lambda i: abs(wavelengths[i] - nm))


def extract_emit_masked(ee, roi) -> dict:
    """Band depths from NASA/EMIT/L2A/RFL in three variants over the same ROI and scale:

    raw      median of all scenes, no mask (same composite as the legacy library)
    quality  per-scene invalid-reflectance and EMIT aggregate_flag mask, then median
    rock     quality mask + vegetation (NDVI), snow (NDSI) and water (NDWI) masks, then median

    Band depth per pixel (unclamped), then ROI statistics. Scene ids, dates and the actual band
    wavelengths are returned for provenance. Missing values stay None.
    """
    ic = ee.ImageCollection("NASA/EMIT/L2A/RFL").filterBounds(roi)
    n = ic.size().getInfo()
    out: dict[str, Any] = {"status": "unavailable", "scene_count": n, "scale_m": EMIT_SCALE_M,
                           "mask_rules": MASK_RULES, "scenes": [], "variants": {}}
    if not n:
        return out
    wl = [float(w) for w in ee.List(ic.first().get("reflectance_wavelengths")).getInfo()]
    idx = {k: _nearest(wl, nm) for k, nm in EMIT_BANDS_NM.items()}
    out["band_wavelengths_nm"] = {k: round(wl[i], 2) for k, i in idx.items()}
    src, dst = [f"reflectance_{i}" for i in idx.values()], list(idx.keys())

    feats = ee.FeatureCollection(ic.map(lambda i: ee.Feature(None, {
        "id": i.get("system:index"), "time_start": i.get("system:time_start"),
        "solar_zenith": i.get("SOLAR_ZENITH")}))).getInfo()["features"]
    from datetime import datetime, timezone
    for f in feats:
        p = f.get("properties", {})
        t = p.get("time_start")
        out["scenes"].append({"id": p.get("id"), "solar_zenith": p.get("solar_zenith"),
                              "date": datetime.fromtimestamp(t / 1000, timezone.utc).date().isoformat()
                              if isinstance(t, (int, float)) else None})

    lo, hi = MASK_RULES["reflectance_valid_range"]

    def prep(img):
        s = img.select(src, dst)
        valid = s.gt(lo).And(s.lt(hi)).reduce(ee.Reducer.min())
        quality = valid.And(img.select("aggregate_flag").eq(0))
        ndvi = s.normalizedDifference(["nir", "r"])
        ndsi = s.normalizedDifference(["g", "swir1"])
        ndwi = s.normalizedDifference(["g", "nir"])
        rock = quality.And(ndvi.lt(MASK_RULES["ndvi_max"])).And(ndsi.lte(MASK_RULES["ndsi_snow_min"])) \
            .And(ndwi.lte(MASK_RULES["ndwi_water_min"]))
        return s.addBands(valid.rename("m_valid")).addBands(quality.rename("m_quality")) \
            .addBands(rock.rename("m_rock"))

    pc = ic.map(prep)
    comps = {"raw": pc.select(dst).median(),
             "quality": pc.map(lambda i: i.select(dst).updateMask(i.select("m_quality"))).median(),
             "rock": pc.map(lambda i: i.select(dst).updateMask(i.select("m_rock"))).median()}

    def depths(img, tag):
        c1 = img.select("c800").add(img.select("c1300")).divide(2)
        c2 = img.select("c1700").add(img.select("c2300")).divide(2)
        d1 = c1.subtract(img.select("b1000")).divide(c1).rename(f"{tag}_bd1000")
        d2 = c2.subtract(img.select("b2000")).divide(c2).rename(f"{tag}_bd2000")
        return d1.addBands(d2)

    stats_img = ee.Image.cat([depths(comps[v], v) for v in VARIANTS])
    pos_img = ee.Image.cat([stats_img.select(b).gt(0).rename(f"pos_{b}") for b in
                            [f"{v}_bd{w}" for v in VARIANTS for w in (1000, 2000)]])
    q = comps["quality"]
    ctx_img = ee.Image.cat([
        q.normalizedDifference(["nir", "r"]).rename("ndvi_quality"),
        q.normalizedDifference(["nir", "r"]).gte(MASK_RULES["ndvi_max"]).rename("frac_vegetated"),
        q.normalizedDifference(["g", "swir1"]).gt(MASK_RULES["ndsi_snow_min"]).rename("frac_snow"),
        q.normalizedDifference(["g", "nir"]).gt(MASK_RULES["ndwi_water_min"]).rename("frac_water")])
    reducer = (ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True)
               .combine(ee.Reducer.median(), sharedInputs=True).combine(ee.Reducer.count(), sharedInputs=True))
    common = dict(geometry=roi, scale=EMIT_SCALE_M, maxPixels=1e9, bestEffort=False, tileScale=4)
    st = stats_img.reduceRegion(reducer=reducer, **common).getInfo()
    pos = pos_img.addBands(ctx_img).reduceRegion(reducer=ee.Reducer.mean(), **common).getInfo()
    cover = ee.Image.cat([ee.Image.constant(1).rename("roi"), pc.select("m_valid").max().rename("valid"),
                          pc.select("m_quality").max().rename("quality"), pc.select("m_rock").max().rename("rock")]) \
        .selfMask().reduceRegion(reducer=ee.Reducer.count(), **common).getInfo()
    roi_px = cover.get("roi") or 0

    def num(v):
        return float(v) if isinstance(v, (int, float)) else None

    for v in VARIANTS:
        out["variants"][v] = {
            w: {"mean": num(st.get(f"{v}_{w}_mean")), "std": num(st.get(f"{v}_{w}_stdDev")),
                "median": num(st.get(f"{v}_{w}_median")), "n_pixels": int(st.get(f"{v}_{w}_count") or 0),
                "fraction_positive": num(pos.get(f"pos_{v}_{w}"))}
            for w in ("bd1000", "bd2000")}
    out["coverage"] = {"roi_pixels": int(roi_px),
                       **{f"{k}_pixels": int(cover.get(k) or 0) for k in ("valid", "quality", "rock")},
                       **{f"{k}_fraction": (round((cover.get(k) or 0) / roi_px, 4) if roi_px else None)
                          for k in ("quality", "rock")}}
    out["surface"] = {"ndvi_mean": num(pos.get("ndvi_quality")), "vegetated_fraction": num(pos.get("frac_vegetated")),
                      "snow_fraction": num(pos.get("frac_snow")), "water_fraction": num(pos.get("frac_water")),
                      "basis": "quality-masked median composite"}
    out["status"] = "ok" if out["variants"]["rock"]["bd1000"]["n_pixels"] else "no_rock_pixels"
    return out
