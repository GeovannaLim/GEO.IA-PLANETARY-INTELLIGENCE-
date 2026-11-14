"""Full lunar pipeline (REAL data) on the five validation regions, one at a time; keeps the full geomorphology
section, the geomorphology step time and the LOLA shots used (var/lola_<id>.npz, for the positive control).
    PYTHONPATH=. python scripts/geomorph_regions.py"""
import asyncio, json, time
import numpy as np
from app.science import geomorph_analogs
from scripts.local_probe import analyse

PTS = [("shackleton", "Shackleton interior", -89.63, 132.32, 3), ("malapert", "Mons Malapert", -85.98, -1.67, 5),
       ("haworth", "Haworth", -86.8, -4.0, 5), ("copernicus", "Copernicus (central peak)", 9.65, -20.05, 5),
       ("imbrium", "Mare Imbrium", 32.80, -15.60, 10)]
_orig = geomorph_analogs.section
CAP = {}

def wrapped(lat, lon, alt, r, src):
    t = time.perf_counter(); s = _orig(lat, lon, alt, r, src); CAP["dt"] = time.perf_counter() - t
    CAP["alt"], CAP["r"] = alt, r
    return s

geomorph_analogs.section = wrapped

async def main():
    out = []
    for key, name, la, lo, r in PTS:
        CAP.clear(); t0 = time.time(); d = await analyse("moon", la, lo, r); dt = round(time.time() - t0, 1)
        alt = CAP.get("alt")
        if alt is not None and getattr(alt, "elev_m", None) is not None:
            np.savez_compressed(f"var/lola_{key}.npz", lat=alt.lat, lon360=alt.lon360, z=alt.elev_m)
        m, ta, e = d.get("mineralogy") or {}, d.get("terrestrial_analogs") or {}, d.get("environment") or {}
        rec = {"key": key, "region": name, "lat": la, "lon": lo, "r": r, "seconds_total": dt,
               "seconds_geomorph": round(CAP.get("dt", 0), 3), "sampled_radius_km": CAP.get("r"),
               "n_shots": int(alt.elev_m.size) if alt is not None and getattr(alt, "elev_m", None) is not None else 0,
               "geomorphology": d.get("geomorphology"), "mineralogy": m.get("status"),
               "valid_pixels": m.get("valid_pixels"), "families": [x["class"] for x in ta.get("region_evidence") or []],
               "sites": [s["id"] for s in ta.get("sites") or []], "env": e.get("status"),
               "psr": e.get("permanent_shadow_fraction"), "problems": d.get("problems")}
        out.append(rec)
        g = rec["geomorphology"] or {}
        print(name, dt, "s; geomorph", g.get("status"), g.get("reason"), rec["seconds_geomorph"], "s", rec["n_shots"], "shots", flush=True)
    json.dump(out, open("var/geomorph_regions.json", "w"), indent=1)

asyncio.run(main())
