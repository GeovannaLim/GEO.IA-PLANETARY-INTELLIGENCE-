"""Real-data controls of the geomorphology comparison (Copernicus GLO-30; no synthetic data).

    PYTHONPATH=. python scripts/geomorph_controls.py
For every catalog site with represents_site=true (and the 6 coarse ones, for the coordinate check), reads one
Copernicus window of 7.5 km and computes terrain-unit profiles at the site and shifted 1, 2, 3, 5 km to
N/E/S/W, at every baseline. Writes var/geomorph_controls.json (profiles only; analysis is separate).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import numpy as np

from app.providers import copernicus_dem as C
from app.providers.http import ProviderError, get_http
from app.science import geomorphology as G
from app.science.coordinates import to_east_360

SHIFTS_KM = (1.0, 2.0, 3.0, 5.0)
AZ = (0, 90, 180, 270)


async def main() -> None:
    http = get_http()
    db = json.load(open("app/data/earth_site_geomorphology.json"))
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "product": C.PRODUCT, "sites": []}
    for s in db["sites"]:
        rec = {"id": s["id"], "represents_site": s.get("represents_site"), "shifted": {}}
        try:
            w = await C.window(http, s["lat"], s["lon"], max(SHIFTS_KM) + G.FAMILY_EXTENT_KM + 0.5)
        except ProviderError as exc:
            rec["error"] = str(exc); out["sites"].append(rec); print(s["id"], "ERROR", exc); continue
        lon360 = np.mod(w["lon"], 360.0)
        lon0 = to_east_360(s["lon"])
        for L in G.BASELINES_M:
            key = f"L{L:g}"
            rec["shifted"][key] = {"0": G.terrain_profile(w["lat"], lon360, w["elev"], lat0=s["lat"], lon0_360=lon0,
                                                          body_radius_km=6371.0, baseline_m=L)}
            for d in SHIFTS_KM:
                for az in AZ:
                    la, lo = G._offset(s["lat"], lon0, 6371.0, d, az)
                    rec["shifted"][key][f"{d:g}@{az}"] = G.terrain_profile(
                        w["lat"], lon360, w["elev"], lat0=la, lon0_360=lo, body_radius_km=6371.0, baseline_m=L)
        out["sites"].append(rec)
        print(s["id"], "ok", flush=True)
    json.dump(out, open("var/geomorph_controls.json", "w"))


if __name__ == "__main__":
    asyncio.run(main())
