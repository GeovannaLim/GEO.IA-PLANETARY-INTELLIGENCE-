"""Topographic attributes from georeferenced laser-altimeter shots.

Inputs are individual LOLA / MOLA shots (lon, lat, elevation) — real numeric
measurements, never rendered imagery. Points are projected to a local
azimuthal-equidistant plane around the region centre, clipped to the circle,
and summarised:

* elevation statistics (m, relative to the instrument datum);
* regional slope/aspect of the least-squares plane z = a·x + b·y + c;
* roughness = RMS of residuals about that plane;
* local slopes: median elevation on a square grid (cell = baseline), central
  differences between neighbouring cells with data -> slope distribution at
  that baseline;
* coverage = fraction of grid cells inside the circle that contain data.
"""

from __future__ import annotations

import math

import numpy as np

from app.schemas.analysis import Reason, SectionStatus, Stats, TopographySection

MIN_POINTS = 30


def local_xy(lat: np.ndarray, lon360: np.ndarray, lat0: float, lon0: float, radius_km: float
             ) -> tuple[np.ndarray, np.ndarray]:
    """Azimuthal-equidistant projection (metres) around (lat0, lon0)."""
    R = radius_km * 1000.0
    p0, l0 = math.radians(lat0), math.radians(lon0)
    p, lam = np.radians(lat), np.radians(lon360)
    cosc = math.sin(p0) * np.sin(p) + math.cos(p0) * np.cos(p) * np.cos(lam - l0)
    c = np.arccos(np.clip(cosc, -1, 1))
    k = np.where(c > 1e-12, c / np.sin(np.where(c > 1e-12, c, 1)), 1.0)
    x = R * k * np.cos(p) * np.sin(lam - l0)
    y = R * k * (math.cos(p0) * np.sin(p) - math.sin(p0) * np.cos(p) * np.cos(lam - l0))
    return x, y


def _stats(v: np.ndarray) -> Stats:
    p05, med, p95 = np.percentile(v, [5, 50, 95])
    return Stats(mean=float(v.mean()), median=float(med), min=float(v.min()), max=float(v.max()),
                 std=float(v.std(ddof=1)) if v.size > 1 else 0.0, p05=float(p05), p95=float(p95))


def summarize(lat: np.ndarray, lon360: np.ndarray, elev: np.ndarray, *, lat0: float, lon0_360: float,
              roi_radius_km: float, sampled_radius_km: float, body_radius_km: float,
              datum: str, method: str, source_ids: list[str]) -> TopographySection:
    x, y = local_xy(lat, lon360, lat0, lon0_360, body_radius_km)
    r_m = sampled_radius_km * 1000.0
    inside = (x * x + y * y) <= r_m * r_m
    x, y, z = x[inside], y[inside], elev[inside]
    base = dict(method=method, datum=datum, sampled_radius_km=round(sampled_radius_km, 4),
                n_points=int(z.size), source_ids=source_ids)
    if z.size < MIN_POINTS:
        return TopographySection(status=SectionStatus.unavailable if z.size == 0 else SectionStatus.partial,
                                 reason=Reason.no_coverage if z.size == 0 else Reason.insufficient_data,
                                 elevation_m=_stats(z) if z.size else None,
                                 elevation_m_mean=float(z.mean()) if z.size else None,
                                 limitations=[f"only {z.size} valid altimeter shots inside the sampled circle "
                                              f"(minimum {MIN_POINTS} for slope metrics)"], **base)

    est = _stats(z)
    # centre the design matrix (numerical conditioning); spurious FP flags from
    # some BLAS builds (Apple Accelerate) are silenced, results are checked below
    A = np.column_stack([x - x.mean(), y - y.mean(), np.ones_like(x)])
    with np.errstate(all="ignore"):
        coef, *_ = np.linalg.lstsq(A, z, rcond=None)
        fitted = A @ coef
    if not np.all(np.isfinite(coef)):
        raise ArithmeticError("plane fit did not converge")
    a, b = coef[0], coef[1]
    regional_slope = math.degrees(math.atan(math.hypot(a, b)))
    aspect = (math.degrees(math.atan2(-a, -b)) + 360.0) % 360.0  # downslope azimuth, from north
    resid = z - fitted
    rough = float(np.sqrt(np.mean(resid ** 2)))

    # grid for local slopes; baseline adapts to region size and shot density
    area = math.pi * r_m * r_m
    baseline = max(2 * math.sqrt(area / z.size), r_m / 25.0)
    n = int(math.ceil(2 * r_m / baseline))
    ix = np.clip(((x + r_m) / baseline).astype(int), 0, n - 1)
    iy = np.clip(((y + r_m) / baseline).astype(int), 0, n - 1)
    grid = np.full((n, n), np.nan)
    order = np.lexsort((iy, ix))
    keys = ix[order] * n + iy[order]
    zs = z[order]
    uniq, starts = np.unique(keys, return_index=True)
    ends = np.append(starts[1:], keys.size)
    for k, s0, s1 in zip(uniq, starts, ends):
        grid[k // n, k % n] = np.median(zs[s0:s1])
    gx = (grid[2:, 1:-1] - grid[:-2, 1:-1]) / (2 * baseline)
    gy = (grid[1:-1, 2:] - grid[1:-1, :-2]) / (2 * baseline)
    g = np.degrees(np.arctan(np.hypot(gx, gy)))
    g = g[np.isfinite(g)]
    centres = (np.arange(n) + 0.5) * baseline - r_m
    cx, cy = np.meshgrid(centres, centres, indexing="ij")
    in_circle = (cx ** 2 + cy ** 2) <= r_m ** 2
    coverage = float(np.isfinite(grid[in_circle]).mean()) if in_circle.any() else None

    limitations = []
    if sampled_radius_km < roi_radius_km - 1e-9:
        limitations.append(f"altimetry sampled within {sampled_radius_km:.2f} km of the centre (requested "
                           f"{roi_radius_km} km) to respect GDS query-size limits")
    if coverage is not None and coverage < 0.3:
        limitations.append(f"sparse shot coverage ({coverage:.0%} of {baseline:.0f} m cells); "
                           "local slopes describe track-adjacent terrain only")
    if g.size < 10:
        limitations.append("too few adjacent grid cells for a robust local-slope distribution")

    status = SectionStatus.available if (coverage or 0) >= 0.3 and g.size >= 10 else SectionStatus.partial
    return TopographySection(
        status=status, reason=None if status == SectionStatus.available else Reason.insufficient_data,
        elevation_m=est, relief_m=float(est.p95 - est.p05), regional_slope_degrees=regional_slope,
        regional_aspect_degrees=aspect, local_slope_degrees=_stats(g) if g.size else None,
        slope_baseline_m=round(baseline, 1), roughness_m=rough, coverage_fraction=coverage,
        elevation_m_mean=est.mean, slope_degrees=float(np.median(g)) if g.size else regional_slope,
        limitations=limitations, **base)
