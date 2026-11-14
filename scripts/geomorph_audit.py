"""Discrimination audit of the geomorphology comparison on REAL profiles (no network).
Inputs: var/geomorph_controls.json (Copernicus shifted families), var/geomorph_regions.json and var/lola_*.npz
(LOLA). Evaluates rules as SENSITIVITY ONLY:  rule(zmax, k): metric corresponds iff z <= zmax AND
k * s_combined <= reference_spread  (production at the time of the audit: zmax=2, k=1).
    PYTHONPATH=. python scripts/geomorph_audit.py  > var/geomorph_audit.txt"""
import json, math, itertools
import numpy as np
from app.science import geomorphology as G

C = json.load(open("var/geomorph_controls.json"))
REG = {r["key"]: r for r in json.load(open("var/geomorph_regions.json"))}
ELIG = [s for s in C["sites"] if s.get("represents_site") and "error" not in s]
COARSE = [s for s in C["sites"] if not s.get("represents_site")]
NAMES = list(G.DEFINITIONS)

def spread_of(profiles, robust=False):
    out = {}
    for m in NAMES:
        v = np.array([p["metrics"][m]["value"] for p in profiles if p.get("status") == "valid"])
        if v.size >= 3:
            out[m] = float(1.4826 * np.median(np.abs(v - np.median(v)))) if robust else float(np.std(v, ddof=1))
    return out

def corr(a, b, sp, zmax, k):
    s = math.hypot(a["uncertainty"], b["uncertainty"])
    z = abs(a["value"] - b["value"]) / s if s > 0 else 0.0
    return z <= zmax and k * s <= sp

def purposes(pa, pb, sp, zmax=2.0, k=1.0):
    if pa.get("status") != "valid" or pb.get("status") != "valid":
        return None
    per = {m: corr(pa["metrics"][m], pb["metrics"][m], sp[m], zmax, k) for m in NAMES}
    return {p: all(per[m] for m in spec["metrics"]) for p, spec in G.PURPOSES.items()}, per

def moon_prof(key, L=60.0, lat0=None, lon0=None):
    d = np.load(f"var/lola_{key}.npz"); r = REG[key]
    return G.terrain_profile(d["lat"], d["lon360"], d["z"], lat0=lat0 if lat0 is not None else r["lat"],
                             lon0_360=lon0 if lon0 is not None else r["lon"] % 360, body_radius_km=1737.4, baseline_m=L)

RULES = [(z, k) for k in (1.0, 2.0) for z in (1.0, 1.5, 2.0, 2.5, 3.0)]
for L in ("L60", "L120", "L240", "L480"):
    base = [s["shifted"][L]["0"] for s in ELIG]
    sp, spr = spread_of(base), spread_of(base, robust=True)
    print(f"\n######## baseline {L}: valid sites {sum(p['status']=='valid' for p in base)}/{len(base)}")
    print("reference spread (std):", {m: round(v, 2) for m, v in sp.items()})
    print("reference spread (robust MAD):", {m: round(v, 2) for m, v in spr.items()})
    for spname, S in (("std", sp), ("robust", spr)):
        if len(S) < len(NAMES):
            print("  spread", spname, "incomplete"); continue
        print(f"  spread={spname}")
        print("   rule(z,k)  | POSITIVE same site shifted (full-purpose match rate, all purposes)  | NEGATIVE distinct sites pairwise")
        for zmax, k in RULES:
            pos = {}
            for d in ("1", "2", "3", "5"):
                hits = tot = 0
                for s in ELIG:
                    c = s["shifted"][L]["0"]
                    for az in (0, 90, 180, 270):
                        r = purposes(c, s["shifted"][L][f"{d}@{az}"], S, zmax, k)
                        if r: hits += sum(r[0].values()); tot += 3
                pos[d] = f"{hits}/{tot}" if tot else "-"
            hits = tot = 0
            for a, b in itertools.combinations(ELIG, 2):
                r = purposes(a["shifted"][L]["0"], b["shifted"][L]["0"], S, zmax, k)
                if r: hits += sum(r[0].values()); tot += 3
            print(f"   z<={zmax:<3} k={k:g} | 1km {pos['1']:>7} 2km {pos['2']:>7} 3km {pos['3']:>7} 5km {pos['5']:>7} | {hits}/{tot}")

# lunar positive control (only overlapping shifts are possible with the sampled LOLA radius)
print("\n######## lunar positive control, L60 (sampled radius limits shifts to <= 1 km)")
base = [s["shifted"]["L60"]["0"] for s in ELIG]; sp = spread_of(base)
for key in ("shackleton", "malapert", "haworth"):
    c = moon_prof(key); r = REG[key]
    for d in (0.5, 1.0):
        for az in (0, 90, 180, 270):
            la, lo = G._offset(r["lat"], r["lon"] % 360, 1737.4, d, az)
            p = moon_prof(key, lat0=la, lon0=lo)
            res = purposes(c, p, sp)
            print(f"  {key:10s} shift {d} km az {az:3d}: windows {p['windows_valid']}/9",
                  "->", res[0] if res else "insufficient")

# named negative contrasts
print("\n######## named negative contrasts, L60, production rule (z<=2, k=1) and k=2")
prof = {s["id"]: s["shifted"]["L60"]["0"] for s in ELIG}
for key in ("shackleton", "malapert", "haworth"):
    prof["moon:" + key] = REG[key]["geomorphology"]["moon_profile"]
pairs = [("twin_sisters", "shawmere"), ("twin_sisters", "puu_nene"), ("twin_sisters", "sudbury_creighton"),
         ("moon:haworth", "twin_sisters"), ("moon:haworth", "shawmere"), ("moon:haworth", "puu_nene"),
         ("moon:malapert", "puu_nene"), ("moon:malapert", "el_tatio"), ("moon:shackleton", "el_tatio"),
         ("moon:haworth", "merriam_jsc1")]
for a, b in pairs:
    for k in (1.0, 2.0):
        r = purposes(prof[a], prof[b], sp, 2.0, k)
        diffs = {m: f"{prof[a]['metrics'][m]['value']:.1f}/{prof[b]['metrics'][m]['value']:.1f}" for m in NAMES}
        print(f"  {a:16s} vs {b:18s} k={k:g}: purposes {r[0]} | {diffs if k == 1 else ''}")

# specificity: how many of the 10 eligible sites does each terrain match per purpose
print("\n######## specificity at L60: number of eligible sites matched per purpose (of 10, or 9 for Earth self-excluded)")
for k in (1.0, 2.0):
    print(f"  k={k:g}")
    for q in list(prof):
        cnt = {p: 0 for p in G.PURPOSES}
        for s in ELIG:
            if s["id"] == q: continue
            r = purposes(prof[q], prof[s["id"]], sp, 2.0, k)
            if r:
                for p, v in r[0].items(): cnt[p] += v
        print(f"   {q:22s} {cnt}")

# metric-level discriminating power: fraction of site pairs whose metric is non-discriminating
print("\n######## metric-level: fraction of distinct-site pairs where the metric is non-discriminating (k*s > spread), L60")
for k in (1.0, 2.0):
    row = {}
    for m in NAMES:
        nd = tot = 0
        for a, b in itertools.combinations(ELIG, 2):
            pa, pb = a["shifted"]["L60"]["0"], b["shifted"]["L60"]["0"]
            s = math.hypot(pa["metrics"][m]["uncertainty"], pb["metrics"][m]["uncertainty"])
            nd += k * s > sp[m]; tot += 1
        row[m] = f"{nd}/{tot}"
    print(f"  k={k:g}", row)

# windows-valid sensitivity: drop windows from the lunar families (recompute from 5..9 windows)
print("\n######## number of valid windows (Earth sites, L60): metric value change when only the first n windows are used")
# coordinate check
print("\n######## coarse-coordinate sites (excluded from comparison):",
      [(s["id"]) for s in COARSE])
