"""Measure harmonised geomorphology profiles of the catalog's terrestrial sites (REAL Copernicus GLO-30).

    PYTHONPATH=. python scripts/build_earth_geomorphology.py [--only id1,id2]
(--only rebuilds just those sites and keeps every other site of the existing JSON unchanged.)
Writes app/data/earth_site_geomorphology.json: for each verified catalog site, terrain-unit profiles
(app.science.geomorphology.terrain_profile: 9 windows of 1 km, offsets 1 km) at every baseline of
BASELINES_M, with the DEM tiles, URLs, product and retrieval time. A site whose coordinate precision is
coarser than the family extent (2 km) is flagged represents_site=false (the windows may miss the
documented unit) and is not compared. Nothing is estimated: a site whose DEM cannot be read keeps the error.
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.providers import copernicus_dem as C
from app.providers.http import ProviderError, get_http
from app.science import analog_sites
from app.science import geomorphology as G
from app.science.coordinates import to_east_360

OUT = Path("app/data/earth_site_geomorphology.json")

# Documented study units measured instead of the catalog reference point (Phase 3A coordinate audit,
# docs/VALIDACAO_FASE3A_ANALOGOS_TERRESTRES.md). Only coordinates quoted verbatim from an opened scholarly source.
# The mineral catalog (terrestrial_analog_sites.json) keeps its own reference point.
UNIT_OVERRIDES = {
    "craters_of_the_moon": {
        "lat": 43.463336, "lon": -113.571361, "coordinate_precision_km": 0.1,
        "unit": "Highway Flow (block a'a lava), sample HF16001",
        "coordinate_quoted": "HF16001 43\u00b027'48.01\" N, 113\u00b034'16.90 \"W",
        "coordinate_source": "Tolometti 2021, PhD thesis, Western University (Neish group, FINESSE line), Table 2.2: "
                             "https://uwo.scholaris.ca/bitstreams/8a90b505-fda3-46d6-8f08-16ae2d73feaf/download",
        "datum": "not stated (handheld GPS); treated as WGS84",
        "note": "0.7 km from the catalog reference point; US-20/26/93 crosses the measured area",
    },
}


async def main() -> None:
    http = get_http()
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    old = {r["id"]: r for r in json.loads(OUT.read_text())["sites"]} if OUT.exists() else {}
    sites = [s for s in analog_sites.catalog()["sites"] if s.get("verification") == "verified"]
    out = {"product": C.PRODUCT, "source": C.BASE, "method": "app/science/geomorphology.py",
           "family": {"window_km": G.FAMILY_WINDOW_KM, "offset_km": G.FAMILY_OFFSET_KM,
                      "extent_km": G.FAMILY_EXTENT_KM, "min_valid_windows": G.MIN_FAMILY},
           "baselines_m": list(G.BASELINES_M), "block_cells": G.BLOCK_CELLS, "generated_at": datetime.now(timezone.utc).isoformat(), "sites": []}
    for s in sites:
        if only is not None and s["id"] not in only:
            out["sites"].append(old[s["id"]])
            continue
        ov = UNIT_OVERRIDES.get(s["id"])
        if ov:
            s = {**s, "lat": ov["lat"], "lon": ov["lon"], "coordinate_precision_km": ov["coordinate_precision_km"]}
        rec = {"id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"],
               "coordinate_precision_km": s["coordinate_precision_km"], "profiles": {}}
        if ov:
            cat = next(c for c in analog_sites.catalog()["sites"] if c["id"] == s["id"])
            rec["measured_unit"] = {k: ov[k] for k in ("unit", "coordinate_quoted", "coordinate_source", "datum", "note")}
            rec["catalog_reference_point"] = {"lat": cat["lat"], "lon": cat["lon"],
                                              "coordinate_precision_km": cat["coordinate_precision_km"]}
        try:
            w = await C.window(http, s["lat"], s["lon"], G.FAMILY_EXTENT_KM + 0.3)
        except ProviderError as exc:
            rec["error"] = str(exc)
            out["sites"].append(rec)
            print(f"{s['id']:28s} ERROR {exc}", flush=True)
            continue
        rec.update(tiles=w["tiles"], urls=w["urls"], dem_pixel_m=w["pixel_m"],
                   retrieved_at=datetime.now(timezone.utc).isoformat(),
                   represents_site=s["coordinate_precision_km"] <= G.FAMILY_EXTENT_KM)
        for L in G.BASELINES_M:
            rec["profiles"][f"L{L:g}"] = G.terrain_profile(w["lat"], np.mod(w["lon"], 360.0), w["elev"],
                                                           lat0=s["lat"], lon0_360=to_east_360(s["lon"]),
                                                           body_radius_km=6371.0, baseline_m=L)
        if old.get(s["id"], {}).get("relief_modification"):          # documented audit result, kept on rebuild
            rec["relief_modification"] = old[s["id"]]["relief_modification"]
        out["sites"].append(rec)
        p = rec["profiles"]["L60"]
        m = p.get("metrics") or {}
        print(f"{s['id']:28s} prec {s['coordinate_precision_km']:>4} km represents={rec['represents_site']!s:5s} "
              f"L60 {p['status']:12s} "
              + (f"slope {m['slope_median_deg']['value']:.1f}±{m['slope_median_deg']['uncertainty']:.1f} "
                 f"p90 {m['slope_p90_deg']['value']:.1f}±{m['slope_p90_deg']['uncertainty']:.1f} "
                 f"rough {m['roughness_m']['value']:.2f}±{m['roughness_m']['uncertainty']:.2f} "
                 f"sigma {m['relief_sigma_m']['value']:.0f} A {m['relief_amplitude_m']['value']:.0f}" if m else ""),
              flush=True)
    if only is not None:                     # keep the original header (generation date) of the untouched sites
        prev = json.loads(OUT.read_text())
        out["generated_at"] = prev["generated_at"]
        out["updated_at"] = datetime.now(timezone.utc).isoformat()
        out["updated_sites"] = sorted(only)
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
