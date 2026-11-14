"""Impact of an Earth geomorphology JSON change on the lunar section (REAL LOLA shots saved in var/lola_*.npz).
    PYTHONPATH=. python scripts/geomorph_db_impact.py OLD.json [NEW.json]"""
import json, sys
from types import SimpleNamespace
import numpy as np
from app.science import geomorph_analogs as GA

old = json.load(open(sys.argv[1]))
new = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "app/data/earth_site_geomorphology.json"))
REG = {"shackleton": (-89.63, 132.32, 3), "malapert": (-85.98, -1.67, 2.5), "haworth": (-86.8, -4.0, 2.5)}


def run(db, key):
    GA.earth_db = lambda: db
    la, lo, r = REG[key]
    d = np.load(f"var/lola_{key}.npz")
    return GA.section(la, lo, SimpleNamespace(lat=d["lat"], lon360=d["lon360"], elev_m=d["z"]), r, "x")


for key in REG:
    a, b = run(old, key), run(new, key)
    print(f"== {key}  baseline {b.moon_profile['baseline_m']:g} m")
    sa, sb = a.earth_reference["reference_spread"], b.earth_reference["reference_spread"]
    print("   spread old -> new:", {m: f"{sa[m]:.2f}->{sb[m]:.2f}" for m in sa})
    for p in a.comparisons:
        ca, cb = a.comparisons[p], b.comparisons[p]
        ma, mb = [m["id"] for m in ca["matches"]], [m["id"] for m in cb["matches"]]
        print(f"   {p:26s} compared {ca['sites_compared']}->{cb['sites_compared']}  matches {ma} -> {mb}"
              + ("" if ma == mb else "   <-- CHANGED"))
        cm = next((x for x in cb["partial_only"] if x["id"] == "craters_of_the_moon"), None)
        if cm:
            print(f"      craters_of_the_moon partial: {cm}")
