"""Phase 3A (VALIDATION ONLY, no network): does the full slope distribution discriminate better than the current
method (V1 = production: per-purpose z <= 2 + discriminating check + median-slope gate)?

Inputs: var/geomorph_dist_catalog.pkl, var/geomorph_dist_moon.pkl (scripts/geomorph_dist_build.py).
    PYTHONPATH=. python scripts/geomorph_dist_study.py > var/geomorph_dist_study.txt

Decisions compared (all on the SAME production 1 km windows, same L grid):
  V1            production purposes (rover_mobility / traverse_planning / rugged_terrain_operations)
  GATE          median-slope correspondence alone (z <= 2 + discriminating) - slope-only baseline of V1
  W1, KS        slope-distribution correspondence alone (window-relabelling permutation, q95 fixed a priori)
  V1&W1, V1&KS  production purpose AND slope distribution (complement: can only remove matches)
  V1/W1         purpose metrics as production but the median-slope gate replaced by W1
Controls (REAL Copernicus terrain only):
  positive overlapping      same terrain, family shifted 1-3 km (families of radius 2 km share area)
  positive non-overlapping  same terrain, family shifted 4-6 km (no shared windows; may leave the unit)
  distinct terrains         all pairs of the 16 measured locations; NOT assumed false positives. Only the a-priori
                            contrast pairs (alpine massif vs plain/shield, from geological descriptions, fixed before
                            this study) are treated as "should not correspond".
Leakage: method choice is made on one half of the terrains (seeded split) with a criterion fixed below, and
evaluated on the other half (and vice versa). Thresholds are never tuned (z <= 2 and q95 are fixed).
"""
from __future__ import annotations

import itertools
import pickle

import numpy as np

from app.science import geomorphology as G
from scripts.geomorph_dist_lib import perm_test, unit_profile

CAT = pickle.load(open("var/geomorph_dist_catalog.pkl", "rb"))["units"]
MOON = pickle.load(open("var/geomorph_dist_moon.pkl", "rb"))["units"]
LS = ("L60", "L120", "L240")
IDS = sorted(k for k, v in CAT.items() if "error" not in v)
ELIG = [k for k in IDS if CAT[k].get("represents_site")]
OVER = [f"{d}@{az}" for d in (1, 2, 3) for az in (0, 90, 180, 270)]
NONOVER = [f"{d}@{az}" for d in (4, 5, 6) for az in range(0, 360, 45)]
MASSIF = {"twin_sisters", "samail_bt1b", "stillwater"}           # alpine / ophiolite massifs (geology text)
PLAIN = {"shawmere", "sudbury_creighton", "kau_desert", "craters_of_the_moon", "el_tatio"}  # shield / lava plain / plateau
CONTRAST = {frozenset(p) for p in itertools.product(MASSIF, PLAIN)}
PURP = list(G.PURPOSES)
METHODS = ["V1", "V1&W1", "V1&KS", "V1/W1"]          # per purpose
SLOPE_ONLY = ["GATE", "W1", "KS"]                      # one decision per pair


def spread(L):
    return G.reference_spread([unit_profile(CAT[k][L]["0"]) or {"status": "x"} for k in ELIG])


def decide(fa, fb, sp, seed=0):
    ua, ub = unit_profile(fa), unit_profile(fb)
    if ua is None or ub is None:
        return None
    pt = perm_test(fa["cdf"], fb["cdf"], seed=seed)
    gate = G.compare_metric(ua["metrics"][G.GATE_METRIC], ub["metrics"][G.GATE_METRIC], sp.get(G.GATE_METRIC))["corresponds"]
    out = {"GATE": gate, "W1": pt["w1_ok"], "KS": pt["ks_ok"], "w1": pt["w1_deg"], "w1_q95": pt["w1_q95"],
           "dslope": abs(ua["metrics"]["slope_median_deg"]["value"] - ub["metrics"]["slope_median_deg"]["value"])}
    for p, spec in G.PURPOSES.items():
        allm = all(G.compare_metric(ua["metrics"][m], ub["metrics"][m], sp.get(m))["corresponds"] for m in spec["metrics"])
        v1 = allm and gate
        out[("V1", p)], out[("V1&W1", p)], out[("V1&KS", p)] = v1, v1 and pt["w1_ok"], v1 and pt["ks_ok"]
        out[("V1/W1", p)] = allm and pt["w1_ok"]
    return out


def rate(decs, key):
    d = [x for x in decs if x is not None]
    if not d:
        return "-"
    if key in SLOPE_ONLY:
        return f"{sum(x[key] for x in d)}/{len(d)}"
    return f"{sum(x[(key, p)] for x in d for p in PURP)}/{3 * len(d)}"


def frac(decs, key):
    d = [x for x in decs if x is not None]
    if not d:
        return float("nan")
    return (sum(x[key] for x in d) / len(d)) if key in SLOPE_ONLY else sum(x[(key, p)] for x in d for p in PURP) / (3 * len(d))


def auc(pos, neg):
    """Fraction of (non-overlapping self, distinct) combinations ordered correctly (smaller distance for self)."""
    pos, neg = np.asarray(pos), np.asarray(neg)
    if not pos.size or not neg.size:
        return float("nan")
    return float(((pos[:, None] < neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (pos.size * neg.size))


RES = {}
for L in LS:
    sp = spread(L)
    pos_o, pos_n, neg = {}, {}, {}
    for k in IDS:
        c = CAT[k][L]["0"]
        pos_o[k] = [decide(c, CAT[k][L][s], sp, seed=i) for i, s in enumerate(OVER)]
        pos_n[k] = [decide(c, CAT[k][L][s], sp, seed=i) for i, s in enumerate(NONOVER)]
    for a, b in itertools.combinations(IDS, 2):
        neg[(a, b)] = decide(CAT[a][L]["0"], CAT[b][L]["0"], sp)
    RES[L] = {"sp": sp, "pos_o": pos_o, "pos_n": pos_n, "neg": neg}


def table(L, ids):
    R = RES[L]
    po = [x for k in ids for x in R["pos_o"][k]]
    pn = [x for k in ids for x in R["pos_n"][k]]
    ng = [v for (a, b), v in R["neg"].items() if a in ids and b in ids]
    cn = [v for (a, b), v in R["neg"].items() if a in ids and b in ids and frozenset((a, b)) in CONTRAST]
    return po, pn, ng, cn


print("Phase 3A slope-distribution study (REAL Copernicus GLO-30; 1 km windows as production)")
print("terrains:", len(IDS), "eligible:", len(ELIG), "a-priori contrast pairs:", len(CONTRAST))
for L in LS:
    po, pn, ng, cn = table(L, IDS)
    print(f"\n######## {L}  (V-methods: purpose-matches / (3 x pairs); slope-only: pairs)")
    print(f"  valid pairs: pos-overlap {sum(x is not None for x in po)}, pos-nonoverlap {sum(x is not None for x in pn)}, "
          f"distinct {sum(x is not None for x in ng)}, contrast {sum(x is not None for x in cn)}")
    print(f"  {'method':8s} | pos overlap 1-3 km | pos NON-overlap 4-6 km | distinct pairs | a-priori contrasts")
    for m in METHODS + SLOPE_ONLY:
        print(f"  {m:8s} | {rate(po, m):>18s} | {rate(pn, m):>22s} | {rate(ng, m):>14s} | {rate(cn, m):>8s}")
    w_self = [x["w1"] for x in pn if x]; w_neg = [x["w1"] for x in ng if x]
    d_self = [x["dslope"] for x in pn if x]; d_neg = [x["dslope"] for x in ng if x]
    print(f"  ranking diagnostic (non-overlap self vs distinct, fraction correctly ordered): "
          f"W1 {auc(w_self, w_neg):.3f}  |d median slope| {auc(d_self, d_neg):.3f}")
    print(f"  W1 medians (deg): self non-overlap {np.median(w_self):.2f}, distinct {np.median(w_neg):.2f}; "
          f"null q95 median (distinct) {np.median([x['w1_q95'] for x in ng if x]):.2f}")
    # per purpose for V1 vs V1&W1
    for p in PURP:
        f = lambda xs, m: f"{sum(x[(m, p)] for x in xs if x)}/{sum(1 for x in xs if x)}"
        print(f"    {p:26s} V1: nonover {f(pn,'V1'):>8s} distinct {f(ng,'V1'):>7s} | V1&W1: nonover {f(pn,'V1&W1'):>8s} "
              f"distinct {f(ng,'V1&W1'):>7s}")

# ---- distance by shift (does the self-match decay with distance, i.e. leaving the unit?)
print("\n######## self-correspondence by shift distance, L60 (pairs)")
for d in (1, 2, 3, 4, 5, 6):
    keys = [f"{d}@{az}" for az in ((0, 90, 180, 270) if d <= 3 else range(0, 360, 45))]
    xs = [decide(CAT[k]["L60"]["0"], CAT[k]["L60"][s], RES["L60"]["sp"]) for k in IDS for s in keys]
    print(f"  {d} km: " + "  ".join(f"{m} {rate(xs, m)}" for m in ("V1", "V1&W1", "GATE", "W1", "KS")))

# ---- leakage-free selection: choose on one half, evaluate on the other (criterion fixed: maximise
#      non-overlap self rate - distinct rate, subject to zero a-priori contrast matches; ties -> simpler = V1)
print("\n######## split-half selection (seed 2026), L60")
rng = np.random.default_rng(2026)
perm = list(rng.permutation(IDS))
halves = (sorted(perm[:8]), sorted(perm[8:]))
for sel, ev in ((0, 1), (1, 0)):
    po, pn, ng, cn = table("L60", halves[sel])
    crit = {}
    for m in METHODS:
        crit[m] = (frac(cn, m) == 0 or not any(cn), frac(pn, m) - frac(ng, m))
    ok = {m: c for m, c in crit.items() if c[0]}
    best = max(ok, key=lambda m: (round(ok[m][1], 6), m == "V1"))
    po2, pn2, ng2, cn2 = table("L60", halves[ev])
    print(f"  select on {halves[sel]}")
    print("    criterion:", {m: round(c[1], 3) for m, c in crit.items()}, "-> chosen", best)
    print(f"  evaluate on {halves[ev]}")
    for m in METHODS:
        print(f"    {m:6s} nonoverlap {rate(pn2, m):>8s} distinct {rate(ng2, m):>7s} contrast {rate(cn2, m):>6s} "
              f"diff {frac(pn2, m) - frac(ng2, m):+.3f}")

# ---- stability across scales: same decision at 60 vs 120 and 60 vs 240
print("\n######## decision agreement across baselines (same pairs, valid at both)")
for m in METHODS + SLOPE_ONLY:
    row = []
    for L2 in ("L120", "L240"):
        agree = tot = 0
        for part in ("pos_o", "pos_n"):
            for k in IDS:
                for a, b in zip(RES["L60"][part][k], RES[L2][part][k]):
                    if a and b:
                        ks = [m] if m in SLOPE_ONLY else [(m, p) for p in PURP]
                        agree += sum(a[q] == b[q] for q in ks); tot += len(ks)
        for key, a in RES["L60"]["neg"].items():
            b = RES[L2]["neg"][key]
            if a and b:
                ks = [m] if m in SLOPE_ONLY else [(m, p) for p in PURP]
                agree += sum(a[q] == b[q] for q in ks); tot += len(ks)
        row.append(f"60 vs {L2[1:]}: {agree}/{tot}")
    print(f"  {m:6s} " + "   ".join(row))

# ---- lunar application (eligible Earth sites only, as production)
print("\n######## lunar units vs eligible Earth sites")
for L in LS:
    sp = RES[L]["sp"]
    for key in ("shackleton", "malapert", "haworth"):
        fm = MOON[key][L]["0"]
        if unit_profile(fm) is None:
            print(f"  {L} {key}: insufficient"); continue
        row = {m: [] for m in METHODS + SLOPE_ONLY}
        w = {}
        for k in ELIG:
            d = decide(fm, CAT[k][L]["0"], sp)
            if d is None:
                continue
            w[k] = (round(d["w1"], 2), round(d["w1_q95"], 2))
            for m in SLOPE_ONLY:
                if d[m]: row[m].append(k)
            for m in METHODS:
                for p in PURP:
                    if d[(m, p)]: row[m].append(f"{k}:{p.split('_')[0]}")
        print(f"  {L} {key}:")
        for m in METHODS + SLOPE_ONLY:
            print(f"     {m:6s} {row[m]}")
        print(f"     W1 (obs, q95) deg: {w}")
pickle.dump(RES, open("var/geomorph_dist_results.pkl", "wb"))
