"""Phase 3A (VALIDATION ONLY): experimental terrestrial candidates vs lunar units, production method V1.
Reference spread = production (10 eligible catalog sites); candidates never enter it nor the catalog.
Classification per lunar unit and purpose: exploratory_correspondence (all purpose metrics + median-slope gate
correspond) / partial (some metrics) / no_correspondence / inconclusive (profile insufficient).
W1 (slope-distribution distance, deg) is shown as a descriptive diagnostic only (Phase 3A study: not adopted).
    PYTHONPATH=. python scripts/geomorph_candidates_compare.py > var/geomorph_candidates.txt"""
import json, pickle
from app.science import geomorphology as G
from scripts.geomorph_dist_lib import perm_test, unit_profile

CAND = pickle.load(open("var/geomorph_dist_candidates.pkl", "rb"))["units"]
CAT = pickle.load(open("var/geomorph_dist_catalog.pkl", "rb"))["units"]
MOON = pickle.load(open("var/geomorph_dist_moon.pkl", "rb"))["units"]
META = {c["id"]: c for c in json.load(open("var/phase3a_candidates.json"))["candidates"]}
ELIG = [k for k, v in CAT.items() if v.get("represents_site")]
NONOVER = [f"{d}@{az}" for d in (4, 5, 6) for az in range(0, 360, 45)]
SHORT = {"slope_median_deg": "med", "slope_p90_deg": "p90", "slope_iqr_deg": "iqr", "roughness_m": "rough",
         "relief_sigma_m": "sigma", "relief_amplitude_m": "A"}
out = {}
for L in ("L60", "L120", "L240"):
    sp = G.reference_spread([unit_profile(CAT[k][L]["0"]) for k in ELIG])
    print(f"\n################ {L}")
    for cid, u in CAND.items():
        if "error" in u:
            print(cid, "ERROR", u["error"]); continue
        f0 = u[L]["0"]; up = unit_profile(f0)
        print(f"\n== {cid}  ({META[cid]['analog_documentation'][:60]})  windows {f0['n_valid']}/9")
        if up is None:
            print("   inconclusive: insufficient windows"); out.setdefault(cid, {})[L] = "inconclusive"; continue
        print("   " + "  ".join(f"{SHORT[m]} {v['value']:.2f}±{v['uncertainty']:.2f}" for m, v in up["metrics"].items()))
        selfr = [G.compare(up, [{"site": {"id": "s"}, "profile": unit_profile(u[L][s])}], sp)
                 for s in NONOVER if unit_profile(u[L][s])]
        hits = sum(bool(r[p]["matches"]) for r in selfr for p in r)
        print(f"   self-consistency (non-overlapping 4-6 km, V1 purposes): {hits}/{3*len(selfr)}")
        for mk in ("shackleton", "malapert", "haworth"):
            mp = unit_profile(MOON[mk][L]["0"])
            if mp is None:
                print(f"   vs {mk}: lunar profile insufficient"); continue
            r = G.compare(mp, [{"site": {"id": cid}, "profile": up}], sp)
            pt = perm_test(MOON[mk][L]["0"]["cdf"], f0["cdf"])
            cls = {}
            for p, c in r.items():
                if c["matches"]:
                    cls[p] = "EXPLORATORY_CORRESPONDENCE"
                elif c["partial_only"]:
                    po = c["partial_only"][0]
                    cls[p] = f"partial[{','.join(SHORT[m] for m in po['corresponding_metrics'])}; gate={'ok' if po['slope_level_gate'] else 'FAIL'}]"
                else:
                    cls[p] = "no_correspondence"
            g = G.compare_metric(mp["metrics"]["slope_median_deg"], up["metrics"]["slope_median_deg"], sp["slope_median_deg"])
            print(f"   vs {mk:10s} median slope moon {g['moon']:.1f} earth {g['earth']:.1f} z {g['z']} | "
                  f"W1 {pt['w1_deg']:.2f} (q95 {pt['w1_q95']:.2f}) | " + "; ".join(f"{p.split('_')[0]}: {v}" for p, v in cls.items()))
            out.setdefault(cid, {}).setdefault(L, {})[mk] = cls
json.dump(out, open("var/geomorph_candidates.json", "w"), indent=1)
