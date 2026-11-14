"""Harmonised geomorphology profiles and Moon-Earth comparison by exploration purpose.

ONE method for both bodies. Inputs are elevation samples (lat, lon, z): LOLA RDR laser shots for the
Moon (irregular tracks) or Copernicus GLO-30 pixel centres for the Earth (30 m grid). Samples are
projected to a local azimuthal-equidistant plane, clipped to a circle of radius R (km) and aggregated on
a square grid of horizontal baseline L (m): cell value = median of the samples in the cell. Only that
gridded surface is used, so both bodies are described at the SAME horizontal scale L and window R.

Metrics (absolute elevation is never compared):
* slope_median_deg, slope_p90_deg, slope_iqr_deg — slope theta = atan(|grad z|), grad by central
  differences between neighbouring cells (distance 2L), for cells with both neighbours on each axis.
* roughness_m (rho_L) — RMS over cells of z_ij - mean(4 neighbours): departure from local planarity at
  baseline L (small-scale roughness; NOT slope, NOT relief).
* relief_sigma_m (sigma_R) — RMS of cell elevations about the least-squares plane over the window
  (relief variability at window scale R).
* relief_amplitude_m (A_R) — p95 - p05 of those plane-detrended cell elevations (relief amplitude).
Uncertainty: spatial BLOCK bootstrap (seeded): the grid is cut into square blocks of BLOCK_CELLS x
BLOCK_CELLS cells and whole blocks are resampled with replacement, so the spatial autocorrelation of
neighbouring cells is kept inside each block (a plain cell bootstrap would underestimate the
uncertainty by treating correlated cells as independent). The standard deviation of each statistic
over the resamples is its uncertainty; it reflects terrain heterogeneity at scales up to a block.

Validity (sampling support, not similarity): coverage (cells with data / cells in the circle) >= 0.8
and >= 30 slope cells and >= 30 roughness cells. Otherwise the profile is 'insufficient'.

Terrain-unit profile (used for comparison): the single-window statistics vary between neighbouring windows
of the same terrain (control: the same terrain shifted 1 km "differed" in ~70% of cases under a
within-window bootstrap). A terrain is therefore described by a FAMILY of FAMILY_WINDOW_KM windows: the
centre plus 8 windows offset by FAMILY_OFFSET_KM at 45-degree azimuths. Metric value = median over the valid
windows; uncertainty = sample standard deviation over them (natural heterogeneity of the terrain unit at
that scale). At least MIN_FAMILY valid windows are required. Data must cover FAMILY_EXTENT_KM.

Comparison: for each metric, z = |m_moon - m_earth| / sqrt(s_moon^2 + s_earth^2) with the terrain-unit
uncertainties. A metric "corresponds" when z <= 2 (the difference is within the combined natural
variability of the two terrains) AND the comparison is discriminating: the combined uncertainty must not
exceed the spread (sample std) of that metric across the reference terrains (all comparable catalog sites at
the same baseline). A very heterogeneous terrain (uncertainty larger than the differences between sites)
would otherwise "match" everything; such metrics are reported as non-discriminating. A purpose corresponds only when ALL its
metrics correspond AND the median slope (GATE_METRIC) corresponds: slope level is the first-order control of
surface operations, and without this gate the traverse / rugged-terrain purposes matched a 16-degree lunar crater
wall with a 1-degree lava plain (real-data audit 2026-11-14, docs/VALIDACAO_GEOMORFOLOGIA_LUA_TERRA.md). The gate
only removes correspondences; it never adds one. z <= 2 is an operational criterion, not a test of equivalence;
the uncertainty is the spatial heterogeneity across the 9 windows, not a measurement error. No universal
score; z_max only orders corresponding sites and is never converted to a percentage. Metrics that
correspond while the purpose does not are reported as partial, without recommending the site.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.science.topography import local_xy

BASELINES_M = (60.0, 120.0, 240.0, 480.0)
WINDOWS_KM = (1.0, 2.0, 3.0, 5.0)
MIN_COVERAGE = 0.8
MIN_CELLS = 30
BOOTSTRAP = 200
BLOCK_CELLS = 5
Z_MAX = 2.0
FAMILY_WINDOW_KM = 1.0
FAMILY_OFFSET_KM = 1.0
FAMILY_EXTENT_KM = FAMILY_WINDOW_KM + FAMILY_OFFSET_KM
MIN_FAMILY = 5

DEFINITIONS = {
    "slope_median_deg": ("deg", "median of theta = atan(|grad z|), central differences over 2L on the L grid"),
    "slope_p90_deg": ("deg", "90th percentile of theta (same slope field)"),
    "slope_iqr_deg": ("deg", "interquartile range p75 - p25 of theta (slope heterogeneity)"),
    "roughness_m": ("m", "RMS of z_ij - mean(4 neighbours) on the L grid (departure from local planarity)"),
    "relief_sigma_m": ("m", "RMS of cell elevations about the least-squares plane over the window R"),
    "relief_amplitude_m": ("m", "p95 - p05 of plane-detrended cell elevations over the window R"),
}

GATE_METRIC = "slope_median_deg"
PURPOSES = {
    "rover_mobility": {
        "metrics": ("slope_median_deg", "slope_p90_deg", "roughness_m"),
        "label": "rover mobility (slopes and roughness resolved at baseline L)",
    },
    "traverse_planning": {
        "metrics": ("slope_p90_deg", "slope_iqr_deg", "relief_sigma_m"),
        "label": "traverse and route-planning studies (steep-slope tail, slope heterogeneity, relief)",
    },
    "rugged_terrain_operations": {
        "metrics": ("relief_amplitude_m", "relief_sigma_m", "slope_iqr_deg"),
        "label": "operations in rugged terrain (relief amplitude and heterogeneity)",
    },
}


def _grid(x: np.ndarray, y: np.ndarray, z: np.ndarray, r_m: float, L: float):
    n = int(math.ceil(2 * r_m / L))
    ix = np.floor((x + r_m) / L).astype(int)
    iy = np.floor((y + r_m) / L).astype(int)
    ok = (ix >= 0) & (ix < n) & (iy >= 0) & (iy < n)
    ix, iy, z = ix[ok], iy[ok], z[ok]
    grid = np.full((n, n), np.nan)
    keys = ix * n + iy
    order = np.argsort(keys, kind="stable")
    keys, zs = keys[order], z[order]
    uniq, starts = np.unique(keys, return_index=True)
    ends = np.append(starts[1:], keys.size)
    for k, s0, s1 in zip(uniq, starts, ends):
        grid[k // n, k % n] = np.median(zs[s0:s1])
    centres = (np.arange(n) + 0.5) * L - r_m
    cx, cy = np.meshgrid(centres, centres, indexing="ij")
    in_circle = (cx ** 2 + cy ** 2) <= r_m ** 2
    grid[~in_circle] = np.nan
    return grid, cx, cy, in_circle


def _block_ids(shape: tuple[int, int], block: int) -> np.ndarray:
    r, c = np.indices(shape)
    nb = math.ceil(shape[1] / block)
    return (r // block) * nb + (c // block)


def _block_boot_std(values: np.ndarray, blocks: np.ndarray, stat, rng: np.random.Generator) -> float:
    """values and blocks are aligned 1-D arrays (finite values only)."""
    uniq = np.unique(blocks)
    groups = [values[blocks == b] for b in uniq]
    if len(groups) < 2:
        return float("nan")
    draws = []
    for _ in range(BOOTSTRAP):
        pick = rng.integers(0, len(groups), size=len(groups))
        draws.append(stat(np.concatenate([groups[i] for i in pick])))
    return float(np.std(draws, ddof=1))


def profile(lat: np.ndarray, lon360: np.ndarray, z: np.ndarray, *, lat0: float, lon0_360: float,
            body_radius_km: float, window_km: float, baseline_m: float, seed: int = 0,
            block: int = BLOCK_CELLS, with_uncertainty: bool = True) -> dict[str, Any]:
    """Harmonised profile at window radius window_km and baseline baseline_m (see module doc)."""
    x, y = local_xy(np.asarray(lat, float), np.asarray(lon360, float), lat0, lon0_360, body_radius_km)
    r_m, L = window_km * 1000.0, baseline_m
    sel = (x * x + y * y) <= r_m * r_m
    grid, cx, cy, in_circle = _grid(x[sel], y[sel], np.asarray(z, float)[sel], r_m, L)
    coverage = float(np.isfinite(grid[in_circle]).mean()) if in_circle.any() else 0.0
    out: dict[str, Any] = {"window_km": window_km, "baseline_m": baseline_m, "samples": int(sel.sum()),
                           "cells_in_window": int(in_circle.sum()), "coverage": round(coverage, 4)}
    gx = (grid[2:, 1:-1] - grid[:-2, 1:-1]) / (2 * L)
    gy = (grid[1:-1, 2:] - grid[1:-1, :-2]) / (2 * L)
    theta_g = np.degrees(np.arctan(np.hypot(gx, gy)))
    nb = (grid[2:, 1:-1] + grid[:-2, 1:-1] + grid[1:-1, 2:] + grid[1:-1, :-2]) / 4.0
    lap_g = grid[1:-1, 1:-1] - nb
    inner_blocks = _block_ids(grid.shape, block)[1:-1, 1:-1]
    all_blocks = _block_ids(grid.shape, block)
    ok_t, ok_l, filled = np.isfinite(theta_g), np.isfinite(lap_g), np.isfinite(grid)
    theta, lap = theta_g[ok_t], lap_g[ok_l]
    zc, xc, yc = grid[filled], cx[filled], cy[filled]
    out["slope_cells"], out["roughness_cells"], out["cells_with_data"] = int(theta.size), int(lap.size), int(zc.size)
    valid = coverage >= MIN_COVERAGE and theta.size >= MIN_CELLS and lap.size >= MIN_CELLS
    out["status"] = "valid" if valid else "insufficient"
    out["block_cells"] = block
    if theta.size < 2 or lap.size < 2 or zc.size < 3:
        out["metrics"] = {}
        return out
    A = np.column_stack([xc, yc, np.ones_like(xc)])
    with np.errstate(all="ignore"):
        coef, *_ = np.linalg.lstsq(A, zc, rcond=None)
        resid = zc - A @ coef
    rng = np.random.default_rng(seed)
    q = lambda v, p: float(np.percentile(v, p))
    stats = {
        "slope_median_deg": (theta, inner_blocks[ok_t], lambda v: q(v, 50)),
        "slope_p90_deg": (theta, inner_blocks[ok_t], lambda v: q(v, 90)),
        "slope_iqr_deg": (theta, inner_blocks[ok_t], lambda v: q(v, 75) - q(v, 25)),
        "roughness_m": (lap, inner_blocks[ok_l], lambda v: float(np.sqrt(np.mean(v ** 2)))),
        "relief_sigma_m": (resid, all_blocks[filled], lambda v: float(np.sqrt(np.mean(v ** 2)))),
        "relief_amplitude_m": (resid, all_blocks[filled], lambda v: q(v, 95) - q(v, 5)),
    }
    metrics = {}
    for name, (vals, blk, fn) in stats.items():
        unit, definition = DEFINITIONS[name]
        unc = _block_boot_std(vals, blk, fn, rng) if with_uncertainty else float("nan")
        metrics[name] = {"value": round(fn(vals), 4), "uncertainty": round(unc, 4) if math.isfinite(unc) else None,
                         "unit": unit, "n": int(vals.size),
                         "scale_m": L if name.startswith(("slope", "rough")) else window_km * 1000.0,
                         "definition": definition}
    out["metrics"] = metrics
    return out


def _offset(lat0: float, lon0_360: float, body_radius_km: float, d_km: float, az_deg: float) -> tuple[float, float]:
    deg = math.degrees(d_km / body_radius_km)
    dlat = deg * math.cos(math.radians(az_deg))
    dlon = deg * math.sin(math.radians(az_deg)) / max(0.02, math.cos(math.radians(lat0)))
    return lat0 + dlat, (lon0_360 + dlon) % 360.0


def terrain_profile(lat, lon360, z, *, lat0: float, lon0_360: float, body_radius_km: float,
                    baseline_m: float) -> dict[str, Any]:
    """Terrain-unit profile from a family of 9 windows (see module doc)."""
    centres = [(lat0, lon0_360)] + [_offset(lat0, lon0_360, body_radius_km, FAMILY_OFFSET_KM, az)
                                    for az in range(0, 360, 45)]
    windows = [profile(lat, lon360, z, lat0=la, lon0_360=lo, body_radius_km=body_radius_km,
                       window_km=FAMILY_WINDOW_KM, baseline_m=baseline_m, seed=i, with_uncertainty=False)
               for i, (la, lo) in enumerate(centres)]
    good = [w for w in windows if w["status"] == "valid"]
    out: dict[str, Any] = {"baseline_m": baseline_m, "window_km": FAMILY_WINDOW_KM,
                           "offset_km": FAMILY_OFFSET_KM, "extent_km": FAMILY_EXTENT_KM,
                           "windows_valid": len(good), "windows_total": len(windows),
                           "coverage_median": round(float(np.median([w["coverage"] for w in windows])), 4),
                           "samples": int(sum(w["samples"] for w in windows))}
    if len(good) < MIN_FAMILY:
        out["status"], out["metrics"] = "insufficient", {}
        return out
    metrics = {}
    for name, (unit, definition) in DEFINITIONS.items():
        vals = np.array([w["metrics"][name]["value"] for w in good])
        metrics[name] = {"value": round(float(np.median(vals)), 4), "uncertainty": round(float(np.std(vals, ddof=1)), 4),
                         "unit": unit, "n_windows": int(vals.size),
                         "scale_m": baseline_m if name.startswith(("slope", "rough")) else FAMILY_WINDOW_KM * 1000.0,
                         "definition": definition}
    out["status"], out["metrics"] = "valid", metrics
    return out


def best_terrain_profile(lat, lon360, z, *, lat0, lon0_360, body_radius_km) -> dict[str, Any] | None:
    """Finest baseline of the ladder with a valid terrain-unit profile (None if none is valid)."""
    last = None
    for L in BASELINES_M:
        last = terrain_profile(lat, lon360, z, lat0=lat0, lon0_360=lon0_360, body_radius_km=body_radius_km,
                               baseline_m=L)
        if last["status"] == "valid":
            return last
    return None


def compare_metric(a: dict, b: dict, spread: float | None = None) -> dict[str, Any]:
    if a.get("uncertainty") is None or b.get("uncertainty") is None:
        return {"moon": a["value"], "earth": b["value"], "difference": round(a["value"] - b["value"], 4),
                "combined_uncertainty": None, "z": None, "discriminating": False, "corresponds": False}
    s = math.sqrt(a["uncertainty"] ** 2 + b["uncertainty"] ** 2)
    d = a["value"] - b["value"]
    z = abs(d) / s if s > 0 else (0.0 if d == 0 else math.inf)
    disc = spread is None or s <= spread
    return {"moon": a["value"], "earth": b["value"], "difference": round(d, 4),
            "combined_uncertainty": round(s, 4), "z": round(z, 3) if math.isfinite(z) else None,
            "reference_spread": None if spread is None else round(spread, 4),
            "discriminating": bool(disc), "corresponds": bool(disc and z <= Z_MAX)}


def reference_spread(profiles: list[dict]) -> dict[str, float]:
    """Sample std of each metric across valid reference terrain profiles (same baseline)."""
    good = [p for p in profiles if p.get("status") == "valid"]
    out = {}
    for name in DEFINITIONS:
        vals = [p["metrics"][name]["value"] for p in good]
        if len(vals) >= 3:
            out[name] = float(np.std(vals, ddof=1))
    return out


def compare(moon: dict, earth_profiles: list[dict], spread: dict[str, float] | None = None) -> dict[str, Any]:
    """Per-purpose correspondences between one lunar terrain profile and terrestrial site profiles computed
    at the SAME baseline. earth_profiles: [{'site': {...}, 'profile': {...}}]; spread: reference spread per
    metric (default: from the valid earth_profiles themselves)."""
    if spread is None:
        spread = reference_spread([i["profile"] for i in earth_profiles])
    result: dict[str, Any] = {}
    for purpose, spec in PURPOSES.items():
        matches, partial, compared, not_comparable = [], [], 0, []
        for item in earth_profiles:
            ep = item["profile"]
            if ep.get("status") != "valid":
                not_comparable.append(item["site"]["id"])
                continue
            compared += 1
            per = {m: compare_metric(moon["metrics"][m], ep["metrics"][m], spread.get(m)) for m in spec["metrics"]}
            gate = per.get(GATE_METRIC) or compare_metric(moon["metrics"][GATE_METRIC], ep["metrics"][GATE_METRIC],
                                                          spread.get(GATE_METRIC))
            if all(v["corresponds"] for v in per.values()) and gate["corresponds"]:
                zmax = max((v["z"] or 0.0) for v in per.values())
                matches.append({**item["site"], "metrics": per, "slope_level_gate": gate, "z_max": round(zmax, 3)})
            elif any(v["corresponds"] for v in per.values()):    # includes: all metrics but gate failed
                partial.append({"id": item["site"]["id"], "slope_level_gate": gate["corresponds"],
                                "corresponding_metrics": [m for m, v in per.items() if v["corresponds"]],
                                "non_discriminating": [m for m, v in per.items() if not v["discriminating"]]})
        matches.sort(key=lambda m: (m["z_max"], m["id"]))
        result[purpose] = {
            "label": spec["label"], "metrics": list(spec["metrics"]), "gate_metric": GATE_METRIC,
            "sites_compared": compared,
            "not_comparable": sorted(not_comparable), "matches": matches, "partial_only": partial,
            "result": "correspondence" if matches else ("no_demonstrable_correspondence" if compared
                                                        else "inconclusive"),
        }
    return result
