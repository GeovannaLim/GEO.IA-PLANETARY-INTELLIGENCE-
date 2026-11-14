"""Variant comparison (SENSITIVITY ONLY, real profiles, no network). V0 = rule at audit time.
V1 = V0 + median slope must correspond in every purpose (slope level gate). V2 = V1 with robust (MAD) spread.
Also: window-count sensitivity (5..9 of the 9 windows) on Earth sites and lunar regions.
    PYTHONPATH=. python scripts/geomorph_audit_variants.py > var/geomorph_audit_variants.txt"""
import json, math, itertools
import numpy as np
from app.science import geomorphology as G
from app.providers import copernicus_dem as C  # noqa: F401  (provenance only)

Cj = json.load(open("var/geomorph_controls.json"))
REG = {r["key"]: r for r in json.load(open("var/geomorph_regions.json"))}
ELIG = [s for s in Cj["sites"] if s.get("represents_site") and "error" not in s]
NAMES = list(G.DEFINITIONS)

def spread_of(ps, robust):
    out = {}
    for m in NAMES:
        v = np.array([p["metrics"][m]["value"] for p in ps if p.get("status") == "valid"])
        out[m] = float(1.4826 * np.median(np.abs(v - np.median(v)))) if robust else float(np.std(v, ddof=1))
    return out

def purposes(pa, pb, sp, gate):
    if pa.get("status") != "valid" or pb.get("status") != "valid":
        return None
    def ok(m):
        a, b = pa["metrics"][m], pb["metrics"][m]
        s = math.hypot(a["uncertainty"], b["uncertainty"])
        z = abs(a["value"] - b["value"]) / s if s > 0 else 0.0
        return z <= 2.0 and s <= sp[m]
    per = {m: ok(m) for m in NAMES}
    return {p: all(per[m] for m in spec["metrics"]) and (per["slope_median_deg"] if gate else True)
            for p, spec in G.PURPOSES.items()}

VARIANTS = {"V0": (False, False), "V1 slope gate": (True, False), "V2 gate+robust": (True, True)}
moon = {k: REG[k]["geomorphology"]["moon_profile"] for k in ("shackleton", "malapert", "haworth")}
for L in ("L60", "L120", "L240"):
    base = [s["shifted"][L]["0"] for s in ELIG]
    print(f"\n######## {L}")
    for name, (gate, robust) in VARIANTS.items():
        sp = spread_of(base, robust)
        def rate(d):
            h = t = 0
            for s in ELIG:
                for az in (0, 90, 180, 270):
                    r = purposes(s["shifted"][L]["0"], s["shifted"][L][f"{d}@{az}"], sp, gate)
                    if r: h += sum(r.values()); t += 3
            return h, t
        neg_h = neg_t = 0
        for a, b in itertools.combinations(ELIG, 2):
            r = purposes(a["shifted"][L]["0"], b["shifted"][L]["0"], sp, gate)
            if r: neg_h += sum(r.values()); neg_t += 3
        pos = {d: rate(d) for d in ("1", "2", "3", "5")}
        print(f"  {name:15s} positive 1km {pos['1'][0]}/{pos['1'][1]}  2km {pos['2'][0]}/{pos['2'][1]}  "
              f"3km {pos['3'][0]}/{pos['3'][1]}  5km {pos['5'][0]}/{pos['5'][1]} | negative pairs {neg_h}/{neg_t}")
        if L == "L60":
            prof = {s["id"]: s["shifted"][L]["0"] for s in ELIG}
            for k, mp in moon.items():
                res = {p: [sid for sid, ep in prof.items() if purposes(mp, ep, sp, gate)[p]] for p in G.PURPOSES}
                print(f"     moon {k:10s} {res}")
            for a, b in (("haworth", "puu_nene"), ("malapert", "puu_nene"), ("haworth", "shawmere"),
                         ("haworth", "twin_sisters")):
                print(f"     contrast {a} vs {b}: {purposes(moon[a], prof[b], sp, gate)}")

# window-count sensitivity: recompute families from the first n valid windows
print("\n######## window-count sensitivity, L60: max relative change of the median vs 9 windows, and std ratio")
def windows(lat, lon, z, lat0, lon0, R):
    cs = [(lat0, lon0)] + [G._offset(lat0, lon0, R, G.FAMILY_OFFSET_KM, az) for az in range(0, 360, 45)]
    return [G.profile(lat, lon, z, lat0=a, lon0_360=b, body_radius_km=R, window_km=1.0, baseline_m=60.0,
                      seed=i, with_uncertainty=False) for i, (a, b) in enumerate(cs)]
def win_sens(ws, label):
    good = [w for w in ws if w["status"] == "valid"]
    if len(good) < 9: print(f"  {label}: only {len(good)} valid windows"); return
    rng = np.random.default_rng(0)
    out = {}
    for m in NAMES:
        v9 = np.array([w["metrics"][m]["value"] for w in good])
        med9, sd9 = np.median(v9), np.std(v9, ddof=1)
        row = []
        for n in (5, 6, 7, 8):
            meds, sds = [], []
            for _ in range(200):
                v = rng.choice(v9, n, replace=False); meds.append(np.median(v)); sds.append(np.std(v, ddof=1))
            row.append(f"n{n}: dmed {np.percentile(np.abs(np.array(meds)-med9),90)/max(sd9,1e-9):.2f}sd, sd {np.median(sds)/max(sd9,1e-9):.2f}x")
        out[m] = row
    print(f"  {label}:"); [print(f"    {m:20s} {' | '.join(r)}") for m, r in out.items()]
for key in ("shackleton", "malapert", "haworth"):
    d = np.load(f"var/lola_{key}.npz"); r = REG[key]
    win_sens(windows(d["lat"], d["lon360"], d["z"], r["lat"], r["lon"] % 360, 1737.4), "moon " + key)
