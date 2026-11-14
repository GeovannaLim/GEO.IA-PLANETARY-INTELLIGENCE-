"""Harmonised geomorphology (app/science/geomorphology.py) on controlled synthetic terrains.
Real-data validation (LOLA, Copernicus GLO-30): docs/VALIDACAO_GEOMORFOLOGIA_LUA_TERRA.md."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from app.science import geomorph_analogs, geomorphology as G

R_MOON = 1737.4


def terrain(kind: str, *, sampling: str = "random", n: int = 60000, extent_km: float = 2.4, lat0: float = 0.0,
            lon0: float = 10.0, seed: int = 0):
    """Synthetic terrain around (lat0, lon0) on the Moon sphere, as (lat, lon360, z)."""
    rng = np.random.default_rng(seed)
    if sampling == "random":                 # LOLA-like irregular samples
        x = rng.uniform(-extent_km, extent_km, n) * 1000
        y = rng.uniform(-extent_km, extent_km, n) * 1000
    else:                                    # DEM-like regular 30 m grid
        g = np.arange(-extent_km * 1000, extent_km * 1000, 30.0)
        x, y = (a.ravel() for a in np.meshgrid(g, g))
    if kind == "flat":
        z = 0.002 * x + rng.normal(0, 0.3, x.size)
    elif kind == "steep":
        z = math.tan(math.radians(20)) * x + 40 * np.sin(2 * np.pi * y / 700.0)
    elif kind == "hummocky":
        z = 25 * np.sin(2 * np.pi * x / 500.0) * np.cos(2 * np.pi * y / 650.0) + 0.05 * x
    else:
        raise ValueError(kind)
    lat = lat0 + np.degrees(y / (R_MOON * 1000))
    lon = lon0 + np.degrees(x / (R_MOON * 1000 * math.cos(math.radians(lat0))))
    return lat, lon % 360, z


def tp(kind, **kw):
    lat, lon, z = terrain(kind, **kw)
    return G.terrain_profile(lat, lon, z, lat0=0.0, lon0_360=10.0, body_radius_km=R_MOON, baseline_m=60.0)


def test_metrics_are_defined_and_documented():
    p = tp("hummocky")
    assert p["status"] == "valid" and p["windows_valid"] == 9
    for name, (unit, definition) in G.DEFINITIONS.items():
        m = p["metrics"][name]
        assert m["unit"] == unit and m["definition"] == definition and m["n_windows"] == 9
        assert m["scale_m"] in (60.0, G.FAMILY_WINDOW_KM * 1000.0)


def test_same_terrain_irregular_points_vs_regular_grid_agree_at_the_same_baseline():
    a, b = tp("hummocky", sampling="random"), tp("hummocky", sampling="grid")
    for name in ("slope_median_deg", "slope_p90_deg", "relief_sigma_m", "relief_amplitude_m"):
        va, vb = a["metrics"][name]["value"], b["metrics"][name]["value"]
        assert abs(va - vb) <= 0.1 * max(abs(vb), 1.0), (name, va, vb)


def test_scale_matters_so_baselines_are_never_mixed():
    lat, lon, z = terrain("hummocky", sampling="grid")
    f = lambda L: G.profile(lat, lon, z, lat0=0, lon0_360=10, body_radius_km=R_MOON, window_km=2.0, baseline_m=L)
    assert f(60)["metrics"]["roughness_m"]["value"] != pytest.approx(f(240)["metrics"]["roughness_m"]["value"], rel=0.2)


def test_partial_coverage_is_insufficient_not_confident():
    lat, lon, z = terrain("hummocky")
    keep = lon > 10.0                                     # data only on the eastern half
    p = G.terrain_profile(lat[keep], lon[keep], z[keep], lat0=0, lon0_360=10, body_radius_km=R_MOON, baseline_m=60)
    assert p["status"] == "insufficient" and p["metrics"] == {}
    assert G.best_terrain_profile(lat[keep], lon[keep], z[keep], lat0=0, lon0_360=10, body_radius_km=R_MOON) is None


def test_same_terrain_corresponds_and_clearly_different_terrains_do_not():
    steep, flat, hummocky = tp("steep"), tp("flat"), tp("hummocky")
    shifted = tp("hummocky", seed=7)
    ref = G.reference_spread([steep, flat, hummocky])
    same = G.compare(hummocky, [{"site": {"id": "same"}, "profile": shifted}], ref)
    assert all(v["matches"] for v in same.values())
    diff = G.compare(steep, [{"site": {"id": "flat"}, "profile": flat}], ref)
    assert diff["rover_mobility"]["matches"] == [] and diff["rover_mobility"]["result"] == "no_demonstrable_correspondence"


def test_heterogeneous_reference_is_non_discriminating():
    a = {"value": 10.0, "uncertainty": 1.0}
    b = {"value": 12.0, "uncertainty": 9.0}             # heterogeneous terrain: huge spread
    r = G.compare_metric(a, b, spread=5.0)
    assert r["discriminating"] is False and r["corresponds"] is False
    assert G.compare_metric(a, {"value": 11.0, "uncertainty": 1.0}, spread=5.0)["corresponds"] is True
    assert G.compare_metric(a, {"value": 11.0, "uncertainty": None}, spread=5.0)["corresponds"] is False


def test_section_without_altimetry_or_with_small_radius_is_inconclusive():
    s = geomorph_analogs.section(0.0, 10.0, None, None, None)
    assert s.status.value == "unavailable" and s.moon_profile is None and s.comparisons == {}
    lat, lon, z = terrain("hummocky")
    alt = SimpleNamespace(lat=lat, lon360=lon, elev_m=z)
    s = geomorph_analogs.section(0.0, 10.0, alt, 1.0, "src-01")
    assert s.reason.value == "insufficient_data" and "at least 2 km" in s.notes[0]


def test_section_on_real_reference_database_labels_relationships():
    lat, lon, z = terrain("hummocky")
    alt = SimpleNamespace(lat=lat, lon360=lon, elev_m=z)
    s = geomorph_analogs.section(0.0, 10.0, alt, 2.4, "src-01")
    assert s.status.value == "available" and s.moon_profile["baseline_m"] == 60.0
    assert s.earth_reference["product"].startswith("Copernicus")
    assert set(s.comparisons) == set(G.PURPOSES)
    for c in s.comparisons.values():
        assert c["result"] in ("correspondence", "no_demonstrable_correspondence", "inconclusive")
        for m in c["matches"]:
            assert m["relationship"] == "calculated_geomorphological_correspondence"
            assert isinstance(m["documented_lunar_analog"], bool)
            assert all(v["corresponds"] and v["discriminating"] for v in m["metrics"].values())
    assert any("does not imply" in n.lower() or "does not imply" in n for n in s.notes)


def test_cog_tile_decoder_roundtrip():
    """DEFLATE + TIFF floating-point predictor (predictor 3), as written by GDAL for GLO-30."""
    import zlib
    from app.providers.copernicus_dem import decode_tile
    w, h = 8, 4
    z = (np.arange(w * h, dtype=">f4").reshape(h, w) * 1.5 - 427.0).astype(">f4")
    planes = z.view(np.uint8).reshape(h, w, 4).transpose(0, 2, 1).reshape(h, 4 * w)   # byte planes, MSB first
    diff = np.concatenate([planes[:, :1], np.diff(planes.astype(np.int16), axis=1) % 256], axis=1).astype(np.uint8)
    out = decode_tile(zlib.compress(diff.tobytes()), w, h)
    assert np.array_equal(out, z.astype(np.float32))


def test_reference_spread_and_absolute_elevation_ignored():
    a, b = tp("hummocky"), tp("hummocky")
    lat, lon, z = terrain("hummocky")
    c = G.terrain_profile(lat, lon, z + 5000.0, lat0=0, lon0_360=10, body_radius_km=R_MOON, baseline_m=60)
    for k in G.DEFINITIONS:
        assert c["metrics"][k]["value"] == pytest.approx(a["metrics"][k]["value"], rel=1e-6)   # offset-invariant
    assert G.reference_spread([a, b]) == {}                                   # < 3 references: no spread claimed
    assert G.reference_spread([a, b, c])["slope_median_deg"] == pytest.approx(0.0, abs=1e-6)


def _p(**vals):
    return {"status": "valid", "metrics": {m: {"value": v[0], "uncertainty": v[1]} for m, v in vals.items()}}


def test_slope_level_gate_blocks_steep_vs_flat_even_when_purpose_metrics_match():
    """Real-data audit case (Haworth vs Puu Nene): traverse metrics compatible only through heterogeneity."""
    moon = _p(slope_median_deg=(15.8, 1.1), slope_p90_deg=(20.4, 2.0), slope_iqr_deg=(3.7, 0.9), roughness_m=(3.3, 0.2),
              relief_sigma_m=(13.9, 7.8), relief_amplitude_m=(45.5, 27.7))
    earth = _p(slope_median_deg=(1.3, 1.5), slope_p90_deg=(6.3, 7.4), slope_iqr_deg=(1.9, 3.0), roughness_m=(1.6, 0.9),
               relief_sigma_m=(9.5, 7.3), relief_amplitude_m=(26.8, 26.6))
    spread = {"slope_median_deg": 8.6, "slope_p90_deg": 12.2, "slope_iqr_deg": 4.4, "roughness_m": 1.8,
              "relief_sigma_m": 31.1, "relief_amplitude_m": 106.0}
    r = G.compare(moon, [{"site": {"id": "puu_nene"}, "profile": earth}], spread)
    for p in ("traverse_planning", "rugged_terrain_operations"):
        assert r[p]["matches"] == [] and r[p]["result"] == "no_demonstrable_correspondence"
        part = r[p]["partial_only"][0]
        assert part["slope_level_gate"] is False and part["corresponding_metrics"]    # reported, not recommended


def test_mining_modified_relief_is_never_a_natural_correspondence(monkeypatch):
    """Phase 3A: a site flagged relief_modification (e.g. open pits) is reported only as a modified-relief reference;
    every other site's result and the reference spread stay identical."""
    import copy
    lat, lon, z = terrain("hummocky")
    alt = SimpleNamespace(lat=lat, lon360=lon, elev_m=z)
    base = geomorph_analogs.section(0.0, 10.0, alt, 2.4, "src-01")
    db = copy.deepcopy(geomorph_analogs.earth_db())
    flagged = {m["id"] for c in base.comparisons.values() for m in c["matches"]} or {"rio_tinto"}
    for s in db["sites"]:
        if s["id"] in flagged:
            s["relief_modification"] = {"class": "mixed_natural_and_mining", "evidence": "test", "sources": []}
    monkeypatch.setattr(geomorph_analogs, "earth_db", lambda: db)
    s = geomorph_analogs.section(0.0, 10.0, alt, 2.4, "src-01")
    assert s.earth_reference["reference_spread"] == base.earth_reference["reference_spread"]
    for p, c in s.comparisons.items():
        assert not {m["id"] for m in c["matches"]} & flagged
        assert {m["id"] for m in c["matches"]} == {m["id"] for m in base.comparisons[p]["matches"]} - flagged
        assert {m["id"] for m in c["modified_relief_references"]} == \
            {m["id"] for m in base.comparisons[p]["matches"]} & flagged
        for m in c["modified_relief_references"]:
            assert m["relationship"] == "calculated_correspondence_with_anthropogenically_modified_relief"
    if any(c["modified_relief_references"] for c in s.comparisons.values()):
        assert geomorph_analogs.MODIFIED_NOTE in s.notes
