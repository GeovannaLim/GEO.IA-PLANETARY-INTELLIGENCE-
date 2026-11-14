"""Phase 3A study helpers (VALIDATION ONLY, not production): per-window terrain statistics AND the full slope
distribution of each 1 km window, computed with exactly the production grid of app/science/geomorphology.py
(same projection, same L-grid median aggregation, same central-difference slope over 2L).

A terrain unit is the production family (centre + 8 windows at FAMILY_OFFSET_KM). Its slope distribution is the
equal-weight mixture of the 9 window distributions, kept as an empirical CDF on THETA_GRID (deg). From the
window CDFs we derive, for two units A and B:
  * W1 (deg)  = integral |F_A - F_B| d theta  (1-D Wasserstein / earth-mover distance between slope distributions:
                the mean slope shift needed to turn one distribution into the other)
  * KS        = max |F_A - F_B|  (Kolmogorov-Smirnov distance)
and a window-label permutation null (windows are the exchangeable units, which keeps spatial heterogeneity):
the 18 windows are relabelled at random into 9 + 9 and the distance is recomputed; a pair "corresponds in slope
distribution" when its observed distance does not exceed the 95th percentile of that null. q95 is fixed a priori
(conventional), never tuned. Like z <= 2, not exceeding it is an operational criterion, NOT proof of equivalence.
"""
from __future__ import annotations

import math

import numpy as np

from app.science import geomorphology as G
from app.science.topography import local_xy

THETA_GRID = np.arange(0.0, 70.0 + 1e-9, 0.25)
DTHETA = 0.25
N_PERM = 999
Q_NULL = 95.0


def window_stats(lat, lon360, z, *, lat0, lon0_360, body_radius_km, baseline_m):
    """Production window profile (G.profile, no bootstrap) + empirical slope CDF of the window."""
    r_m = G.FAMILY_WINDOW_KM * 1000.0
    dlat = math.degrees((r_m + 2 * baseline_m) / (body_radius_km * 1000.0))
    dlon = dlat / max(0.02, math.cos(math.radians(lat0)))
    dl = (lon360 - lon0_360 + 180.0) % 360.0 - 180.0
    pre = (np.abs(lat - lat0) <= dlat) & (np.abs(dl) <= dlon)
    if abs(lat0) > 85:                                     # near the pole the lon box is meaningless
        pre = np.abs(lat - lat0) <= dlat * 1.5
    la, lo, zz = lat[pre], lon360[pre], z[pre]
    p = G.profile(la, lo, zz, lat0=lat0, lon0_360=lon0_360, body_radius_km=body_radius_km,
                  window_km=G.FAMILY_WINDOW_KM, baseline_m=baseline_m, with_uncertainty=False)
    if p["status"] != "valid":
        return p, None
    x, y = local_xy(la, lo, lat0, lon0_360, body_radius_km)
    sel = x * x + y * y <= r_m * r_m
    grid, *_ = G._grid(x[sel], y[sel], zz[sel], r_m, baseline_m)
    L = baseline_m
    gx = (grid[2:, 1:-1] - grid[:-2, 1:-1]) / (2 * L)
    gy = (grid[1:-1, 2:] - grid[1:-1, :-2]) / (2 * L)
    th = np.degrees(np.arctan(np.hypot(gx, gy)))
    th = th[np.isfinite(th)]
    cdf = np.searchsorted(np.sort(th), THETA_GRID, side="right") / th.size
    return p, cdf


def family(lat, lon360, z, *, lat0, lon0_360, body_radius_km, baseline_m):
    """9 production windows; returns {'n_valid', 'metrics': [9 dicts or None], 'cdf': (n_valid, len(THETA_GRID))}."""
    centres = [(lat0, lon0_360)] + [G._offset(lat0, lon0_360, body_radius_km, G.FAMILY_OFFSET_KM, az)
                                    for az in range(0, 360, 45)]
    mets, cdfs = [], []
    for la, lo in centres:
        p, c = window_stats(lat, lon360, z, lat0=la, lon0_360=lo, body_radius_km=body_radius_km, baseline_m=baseline_m)
        if c is not None:
            mets.append({k: v["value"] for k, v in p["metrics"].items()})
            cdfs.append(c)
    return {"n_valid": len(cdfs), "metrics": mets, "cdf": np.array(cdfs) if cdfs else np.zeros((0, THETA_GRID.size))}


def unit_profile(fam) -> dict | None:
    """Production terrain-unit profile (median / std over valid windows) from a family."""
    if fam["n_valid"] < G.MIN_FAMILY:
        return None
    out = {}
    for m in G.DEFINITIONS:
        v = np.array([w[m] for w in fam["metrics"]])
        out[m] = {"value": float(np.median(v)), "uncertainty": float(np.std(v, ddof=1))}
    return {"status": "valid", "metrics": out}


def distances(ca: np.ndarray, cb: np.ndarray) -> tuple[float, float]:
    fa, fb = ca.mean(axis=0), cb.mean(axis=0)
    d = np.abs(fa - fb)
    return float(d.sum() * DTHETA), float(d.max())


def perm_test(ca: np.ndarray, cb: np.ndarray, seed: int = 0) -> dict:
    """Observed W1 / KS and their window-relabelling q95 null (seeded)."""
    w_obs, k_obs = distances(ca, cb)
    allc = np.vstack([ca, cb])
    na, n = ca.shape[0], allc.shape[0]
    rng = np.random.default_rng(seed)
    w_null, k_null = np.empty(N_PERM), np.empty(N_PERM)
    for i in range(N_PERM):
        idx = rng.permutation(n)
        w_null[i], k_null[i] = distances(allc[idx[:na]], allc[idx[na:]])
    w_q, k_q = float(np.percentile(w_null, Q_NULL)), float(np.percentile(k_null, Q_NULL))
    return {"w1_deg": w_obs, "w1_q95": w_q, "w1_ok": w_obs <= w_q, "ks": k_obs, "ks_q95": k_q, "ks_ok": k_obs <= k_q}
