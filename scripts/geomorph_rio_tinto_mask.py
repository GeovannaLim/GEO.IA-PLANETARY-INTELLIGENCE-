"""Phase 3A (VALIDATION ONLY): sensitivity of the Rio Tinto terrain profile to mining features.
Masks Copernicus GLO-30 pixels inside (a) the OSM landuse=quarry polygons, (b) CORINE 2012 class 131 (mineral
extraction) polygons, and recomputes the production terrain-unit profile and the comparison with the lunar units.
Inputs (retrieved 2026-11-14): var/rio_tinto_osm_overpass.json (Overpass API), var/rio_tinto_clc2012.json (EEA
CLC2012 ArcGIS REST), var/dem_cache/rio_tinto.npz, var/lola_*.npz.
    PYTHONPATH=. python scripts/geomorph_rio_tinto_mask.py > var/rio_tinto_mask.txt"""
import json
import numpy as np
from app.science import geomorphology as G

LAT0, LON0 = 37.72512, -6.55643


def inside(lat, lon, ring):                       # ring: [(lat, lon)], even-odd rule, vectorised
    c = np.zeros(lat.shape, bool)
    for (y0, x0), (y1, x1) in zip(ring, ring[1:] + ring[:1]):
        m = (y0 > lat) != (y1 > lat)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (x1 - x0) * (lat - y0) / (y1 - y0) + x0
        c ^= m & (lon < xi)
    return c


osm = json.load(open("var/rio_tinto_osm_overpass.json"))["elements"]
quarry = [[(p["lat"], p["lon"]) for p in e["geometry"]] for e in osm
          if e.get("type") == "way" and e.get("tags", {}).get("landuse") == "quarry" and "geometry" in e]
clc = json.load(open("var/rio_tinto_clc2012.json"))["features"]
c131 = [[(p[1], p[0]) for p in r] for f in clc if (f["attributes"].get("Code_12") == "131") for r in f["geometry"]["rings"]]
print("OSM quarry polygons:", len(quarry), " CLC131 rings:", len(c131))

d = np.load("var/dem_cache/rio_tinto.npz"); lat, lon, z = d["lat"], d["lon"], d["elev"]
near = (np.abs(lat - LAT0) < 0.04) & (np.abs(lon - LON0) < 0.05)
lat, lon, z = lat[near], lon[near], z[near]
masks = {"none": np.zeros(lat.shape, bool)}
masks["osm_quarry"] = np.any([inside(lat, lon, r) for r in quarry], axis=0) if quarry else masks["none"]
masks["clc131"] = np.any([inside(lat, lon, r) for r in c131], axis=0) if c131 else masks["none"]
masks["osm+clc131"] = masks["osm_quarry"] | masks["clc131"]

db = json.load(open("app/data/earth_site_geomorphology.json"))
moon = {k: np.load(f"var/lola_{k}.npz") for k in ("shackleton", "malapert", "haworth")}
MC = {"shackleton": (-89.63, 132.32), "malapert": (-85.98, -1.67), "haworth": (-86.8, -4.0)}
for L in (60.0, 120.0):
    spread = G.reference_spread([s["profiles"][f"L{L:g}"] for s in db["sites"] if s.get("represents_site")])
    mp = {k: G.terrain_profile(v["lat"], v["lon360"], v["z"], lat0=MC[k][0], lon0_360=MC[k][1] % 360,
                               body_radius_km=1737.4, baseline_m=L) for k, v in moon.items()}
    print(f"\n#### L{L:g}  (reference spread = production, unchanged)")
    for name, m in masks.items():
        keep = ~m
        p = G.terrain_profile(lat[keep], np.mod(lon[keep], 360), z[keep], lat0=LAT0, lon0_360=LON0 % 360,
                              body_radius_km=6371.0, baseline_m=L)
        print(f"  mask {name:11s} pixels masked {m.sum():6d}  windows {p['windows_valid']}/9  status {p['status']}")
        if p["status"] != "valid":
            continue
        print("    " + "  ".join(f"{k.split('_')[0]}{'_'+k.split('_')[1] if k.startswith('relief') else ''} "
                                  f"{v['value']:.2f}±{v['uncertainty']:.2f}" for k, v in p["metrics"].items()))
        for k, mprof in mp.items():
            r = G.compare(mprof, [{"site": {"id": "rio_tinto"}, "profile": p}], spread)
            print(f"    vs {k:10s}: " + ", ".join(f"{pp}={'MATCH' if c['matches'] else 'no'}" for pp, c in r.items()))
