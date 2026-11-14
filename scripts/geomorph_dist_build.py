"""Phase 3A (VALIDATION ONLY): read REAL Copernicus GLO-30 windows once (cached in var/dem_cache/, gitignored) and
compute per-window statistics + slope CDFs for every catalog site (and experimental candidates) at the site and
shifted 1-3 km (families overlap: family radius 2 km) and 4-6 km (families do NOT overlap), at L = 60/120/240 m.
Also the lunar units from the LOLA shots saved by scripts/geomorph_regions.py (var/lola_*.npz).

    PYTHONPATH=. python scripts/geomorph_dist_build.py [catalog|candidates|moon]
Writes var/geomorph_dist_<set>.npz (pickled dict)."""
from __future__ import annotations

import asyncio
import json
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.providers import copernicus_dem as C
from app.providers.http import ProviderError, get_http
from app.science import geomorphology as G
from app.science.coordinates import to_east_360
from scripts.geomorph_dist_lib import family

CACHE = Path("var/dem_cache")
LS = (60.0, 120.0, 240.0)
SHIFTS = [(d, az) for d in (1.0, 2.0, 3.0) for az in (0, 90, 180, 270)] + \
         [(d, az) for d in (4.0, 5.0, 6.0) for az in range(0, 360, 45)]
HALF_KM = 6.0 + G.FAMILY_EXTENT_KM + 0.4
MOON = {"shackleton": (-89.63, 132.32), "malapert": (-85.98, -1.67), "haworth": (-86.8, -4.0)}


async def dem(http, sid, lat, lon):
    f = CACHE / f"{sid}.npz"
    if f.exists():
        d = np.load(f, allow_pickle=True)
        return {k: d[k] for k in d.files}
    w = await C.window(http, lat, lon, HALF_KM)
    rec = {"lat": w["lat"], "lon": w["lon"], "elev": w["elev"], "urls": np.array(w["urls"]),
           "retrieved_at": np.array(datetime.now(timezone.utc).isoformat()), "pixel_m": np.array(w["pixel_m"])}
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **rec)
    return rec


def sites_for(which):
    if which == "catalog":
        return [(s["id"], s["lat"], s["lon"], s.get("represents_site")) for s in
                json.load(open("app/data/earth_site_geomorphology.json"))["sites"]]
    return [(c["id"], c["lat"], c["lon"], None) for c in json.load(open("var/phase3a_candidates.json"))["candidates"]]


async def main(which):
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "set": which, "units": {}}
    if which == "moon":
        for key, (la, lo) in MOON.items():
            d = np.load(f"var/lola_{key}.npz")
            out["units"][key] = {"L%g" % L: {"0": family(d["lat"], d["lon360"], d["z"], lat0=la, lon0_360=lo % 360,
                                                       body_radius_km=1737.4, baseline_m=L)} for L in LS}
            print(key, {k: v["0"]["n_valid"] for k, v in out["units"][key].items()}, flush=True)
    else:
        http = get_http()
        for sid, lat, lon, rep in sites_for(which):
            t = time.time()
            try:
                w = await dem(http, sid, lat, lon)
            except ProviderError as exc:
                out["units"][sid] = {"error": str(exc)}; print(sid, "ERROR", exc, flush=True); continue
            lon360, lon0 = np.mod(w["lon"], 360.0), to_east_360(lon)
            u = {"represents_site": rep, "urls": [str(x) for x in w["urls"]], "retrieved_at": str(w["retrieved_at"])}
            for L in LS:
                fams = {"0": family(w["lat"], lon360, w["elev"], lat0=lat, lon0_360=lon0, body_radius_km=6371.0,
                                    baseline_m=L)}
                for d, az in SHIFTS:
                    la, lo = G._offset(lat, lon0, 6371.0, d, az)
                    fams[f"{d:g}@{az}"] = family(w["lat"], lon360, w["elev"], lat0=la, lon0_360=lo,
                                                 body_radius_km=6371.0, baseline_m=L)
                u["L%g" % L] = fams
            out["units"][sid] = u
            print(sid, "ok", round(time.time() - t, 1), "s", flush=True)
    pickle.dump(out, open(f"var/geomorph_dist_{which}.pkl", "wb"))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "catalog"))
