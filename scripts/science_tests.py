"""Scientific acceptance tests against a deployed GEØ.IA backend (REAL data, no mocks).

Expectations and pass criteria are fixed in CASES *before* running (pre-registered); sources in `ref`.
Runs one analysis at a time (gentle on NASA services) with use_cache=false, saves every raw
result, then evaluates. Usage:

    PYTHONPATH=. python scripts/science_tests.py https://geoia-planetary-backend.onrender.com

Writes var/science_tests.json (raw + verdicts) and prints a summary.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

from app.science import analog_sites

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
OUT = Path("var/science_tests.json")
c = httpx.Client(base_url=BASE, timeout=90)

MARS_HYDRATED = {"fe_mg_phyllosilicate", "al_phyllosilicate_silica", "carbonate", "sulfate"}

# Each case: id, body, request, ref (where the expectation comes from), expect (plain words).
CASES = [
    dict(id="M1", body="mars", req=dict(latitude=18.4386, longitude=77.5031, radius_km=5),
         name="Jezero (Perseverance)", ref="Jezero coordinates: Caltech Mars 2020 site-selection paper; olivine + "
         "carbonate/Fe-Mg clays in Jezero: Ehlmann et al. 2008 (Science 322, 1828); Horgan et al. 2020",
         expect="CRISM detects olivine AND (Fe/Mg phyllosilicate OR carbonate)"),
    dict(id="M2", body="mars", req=dict(latitude=18.4386, longitude=77.5031, radius_km=5),
         name="Jezero, repeated", ref="determinism", expect="same product and identical indicator values as M1"),
    dict(id="M3", body="mars", req=dict(latitude=18.4476, longitude=77.5031, radius_km=5),
         name="Jezero shifted 1 km north", ref="stability",
         expect="mostly the same mineral families as M1 (overlap >= 60%)"),
    dict(id="M4", body="mars", req=dict(latitude=21.0, longitude=74.5, radius_km=10),
         name="Nili Fossae trough (MSL candidate)", ref="coordinates: Grant/Golombek et al. EPSC 2018-578; "
         "olivine and Fe/Mg clays in Nili Fossae: Mangold et al. 2007; Ehlmann et al. 2009",
         expect="if CRISM covers it: olivine OR Fe/Mg phyllosilicate detected"),
    dict(id="M5", body="mars", req=dict(latitude=24.0, longitude=341.1, radius_km=10, longitude_convention="east_360"),
         name="Mawrth Vallis (MSL candidate), 0-360 east", ref="coordinates: EPSC 2018-578; phyllosilicates: "
         "Bishop et al. 2008 (Science 321, 830)",
         expect="if CRISM covers it: Fe/Mg OR Al phyllosilicate detected"),
    dict(id="M6", body="mars", req=dict(latitude=24.0, longitude=-18.9, radius_km=10),
         name="Mawrth Vallis, -180..180", ref="longitude convention",
         expect="same location, product and values as M5"),
    dict(id="M7", body="mars", req=dict(latitude=-4.5895, longitude=137.4417, radius_km=2),
         name="Bradbury Landing (Curiosity)", ref="Vasavada et al. 2014, JGR Planets: 4.5895S 137.4417E, -4501 m",
         expect="MOLA median elevation within +/-50 m of -4501 m"),
    dict(id="M8", body="mars", req=dict(latitude=18.96, longitude=226.41, longitude_convention="east_360",
                                        radius_km=10),
         name="Olympus Mons (dust-covered, negative control)", ref="Tharsis is mantled by bright dust",
         expect="no clay, carbonate, sulfate or silica detection (no invented hydrated minerals)"),
    dict(id="M9", body="mars", req=dict(latitude=0.99, longitude=-31.47, radius_km=10),
         name="Mars point without CRISM", ref="known gap (earlier tests)",
         expect="mineralogy not measured; analog sites only as clearly labelled global context"),
    dict(id="L1", body="moon", req=dict(latitude=44.1214, longitude=-19.5116, radius_km=2),
         name="Chang'e-3 landing site", ref="LROC (ASU): 44.1214N 340.4884E, -2630 m (LOLA ref.) / -2640 m (NAC DTM)",
         expect="LOLA median elevation within +/-50 m of -2635 m; if M3 covers it, pyroxene (mare basalt)"),
    dict(id="L2", body="moon", req=dict(latitude=9.65, longitude=-20.05, radius_km=1.5),
         name="Copernicus central peak olivine", ref="Isaacson et al. 2011, JGR Planets 116, E00G11 "
         "(doi:10.1029/2010JE003731): M3 central-peak olivine at 9.63-9.68N, 339.9-340.0E",
         expect="1 um band detected; classed as olivine/glass rather than pyroxene"),
    dict(id="L3", body="moon", req=dict(latitude=32.80, longitude=-15.60, radius_km=10),
         name="Mare Imbrium", ref="mare basalt (pyroxene)", expect="pyroxene (1 and 2 um bands); basalt analog sites"),
    # held-out controls: NOT used to calibrate the detection floors
    dict(id="D1", body="mars", req=dict(latitude=0.0125, longitude=226.8946, longitude_convention="east_360",
                                        radius_km=3), name="Dust: Amazonis/Tharsis (held out)",
         ref="Tharsis/Amazonis dust mantle", expect="no olivine, clay, carbonate, sulfate, silica or ice"),
    dict(id="D2", body="mars", req=dict(latitude=21.433, longitude=222.1729, longitude_convention="east_360",
                                        radius_km=3), name="Dust: Olympus aureole (held out in round 1; now in calibration)",
         ref="Tharsis/Amazonis dust mantle", expect="no olivine, clay, carbonate, sulfate, silica or ice"),
    dict(id="D4", body="mars", req=dict(latitude=5.473, longitude=224.3693, longitude_convention="east_360",
                                        radius_km=3), name="Dust: Amazonis S (held out, round 2)",
         ref="Tharsis/Amazonis dust mantle", expect="no olivine, clay, carbonate, sulfate, silica or ice"),
    dict(id="D5", body="mars", req=dict(latitude=15.071, longitude=229.6985, longitude_convention="east_360",
                                        radius_km=3), name="Dust: Olympus W (held out, round 2)",
         ref="Tharsis/Amazonis dust mantle", expect="no olivine, clay, carbonate, sulfate, silica or ice"),
    dict(id="D6", body="mars", req=dict(latitude=24.56, longitude=217.9007, longitude_convention="east_360",
                                        radius_km=3), name="Dust: Amazonis N (held out, round 2)",
         ref="Tharsis/Amazonis dust mantle", expect="no olivine, clay, carbonate, sulfate, silica or ice"),
    dict(id="D3", body="mars", req=dict(latitude=10.6569, longitude=224.7566, longitude_convention="east_360",
                                        radius_km=3), name="Dust: Amazonis (held out)",
         ref="Tharsis/Amazonis dust mantle", expect="no olivine, clay, carbonate, sulfate, silica or ice"),
    dict(id="I1", body="mars", req=dict(latitude=85.0572, longitude=0.8178, longitude_convention="east_360",
                                        radius_km=3), name="North residual cap, summer (held out)",
         ref="exposed H2O ice in northern summer", expect="ice detected; no mineral analogs from ice-affected bands"),
    dict(id="I2", body="mars", req=dict(latitude=-87.1681, longitude=333.4512, longitude_convention="east_360",
                                        radius_km=3), name="South residual cap (held out)",
         ref="south residual CO2 ice cap", expect="ice detected; no mineral analogs from ice-affected bands"),
    dict(id="L4", body="moon", req=dict(latitude=-89.5, longitude=0.0, radius_km=5),
         name="Lunar south pole", ref="M3 coverage/illumination is poor at the poles",
         expect="topography measured; no mineral result invented when M3 is unusable"),
]


def run(case: dict) -> dict:
    path = "/v1/lunar/analyze" if case["body"] == "moon" else "/v1/mars/analyze"
    t0 = time.time()
    r = c.post(f"{path}?use_cache=false&wait_s=0", json=case["req"])
    if r.status_code not in (200, 202):
        return {"_error": f"HTTP {r.status_code}: {r.text[:300]}", "_seconds": time.time() - t0}
    doc = r.json()
    while doc.get("status") == "processing" and time.time() - t0 < 420:
        time.sleep(6)
        doc = c.get(doc["links"]["self"]).json()
    doc["_seconds"] = round(time.time() - t0, 1)
    return doc


def detected(doc: dict) -> dict:
    return {i["name"]: i.get("detected") for i in (doc.get("mineralogy") or {}).get("indicators") or []}


def families(doc: dict) -> set[str]:
    return {e["class"] for e in ((doc.get("terrestrial_analogs") or {}).get("region_evidence") or [])}


def median_elev(doc: dict):
    return ((doc.get("topography") or {}).get("elevation_m") or {}).get("median")


def has_mineralogy(doc: dict) -> bool:
    return (doc.get("mineralogy") or {}).get("status") in ("available", "partial")


def values(doc: dict) -> dict:
    return {i["name"]: (i.get("value") or {}).get("median") for i in (doc.get("mineralogy") or {}).get("indicators") or []}


def analog_consistency(doc: dict) -> tuple[bool, str]:
    """Every offered site must document a geology that explains a detected family (no invented links)."""
    ta = doc.get("terrestrial_analogs") or {}
    fam = families(doc)
    cat = {s["id"]: s for s in analog_sites.catalog()["sites"]}
    body = doc.get("planet")
    for s in ta.get("sites") or []:
        site = cat.get(s["id"])
        if site is None or site.get("verification") != "verified":
            return False, f"{s['id']} not a verified catalog site"
        documented = set().union(*[set(a["classes"]) for a in site["analog_for"] if a["body"] == body] or [set()])
        for m in s.get("matched_classes") or []:
            if m not in fam or not (analog_sites.EVIDENCE[m]["sites"] & documented):
                return False, f"{s['id']}: '{m}' not supported"
        if not s.get("references"):
            return False, f"{s['id']} without references"
    return True, f"{len(ta.get('sites') or [])} sites, all consistent"


def evaluate(cid: str, d: dict, R: dict) -> tuple[str, str]:
    if "_error" in d or d.get("status") != "completed":
        return "FAIL", f"analysis did not complete: {d.get('_error') or d.get('status')}"
    det, fam = detected(d), families(d)
    if cid == "M1":
        if not has_mineralogy(d):
            return "FAIL", "no CRISM result"
        ok = "olivine" in fam and bool({"fe_mg_phyllosilicate", "carbonate"} & fam)
        return ("PASS" if ok else "FAIL"), f"families: {sorted(fam)}"
    if cid == "M2":
        a, b = R.get("M1", {}), d
        same = values(a) == values(b) and (a.get("mineralogy") or {}).get("product_used") == \
            (b.get("mineralogy") or {}).get("product_used")
        return ("PASS" if same else "FAIL"), "identical values and product" if same else "values differ"
    if cid == "M3":
        f1 = families(R.get("M1", {}))
        j = len(f1 & fam) / max(1, len(f1 | fam))
        return ("PASS" if j >= 0.6 else "FAIL"), f"overlap {j:.0%}: M1 {sorted(f1)} vs {sorted(fam)}"
    if cid in ("M4", "M5"):
        if not has_mineralogy(d):
            return "INCONCLUSIVE", f"CRISM: {(d.get('mineralogy') or {}).get('reason')} (no data to judge)"
        want = {"olivine", "fe_mg_phyllosilicate"} if cid == "M4" else {"fe_mg_phyllosilicate", "al_phyllosilicate_silica"}
        return ("PASS" if want & fam else "FAIL"), f"families: {sorted(fam)}"
    if cid == "M6":
        a = R.get("M5", {})
        ca, cb = a.get("coordinates") or {}, d.get("coordinates") or {}
        same_loc = abs((ca.get("longitude_east_360") or 0) - (cb.get("longitude_east_360") or 0)) < 1e-6
        same = same_loc and values(a) == values(d)
        return ("PASS" if same else "FAIL"), f"east_360 {ca.get('longitude_east_360')} vs {cb.get('longitude_east_360')}; " \
            f"{'identical values' if values(a) == values(d) else 'values differ'}"
    if cid == "M7":
        m = median_elev(d)
        if m is None:
            return "FAIL", "no MOLA elevation"
        return ("PASS" if abs(m - (-4501)) <= 50 else "FAIL"), f"median {m:.0f} m (published -4501 m, diff {m + 4501:+.0f} m)"
    if cid == "M8":
        if not has_mineralogy(d):
            return "INCONCLUSIVE", f"CRISM: {(d.get('mineralogy') or {}).get('reason')}"
        bad = MARS_HYDRATED & fam
        return ("PASS" if not bad else "FAIL"), f"families: {sorted(fam)}" + (f"; unexpected {sorted(bad)}" if bad else "")
    if cid == "M9":
        ta = d.get("terrestrial_analogs") or {}
        ok = not has_mineralogy(d) and (ta.get("basis") in ("global_context", None)) and \
            (ta.get("basis") != "global_context" or bool(ta.get("notes")))
        return ("PASS" if ok else "FAIL"), f"mineralogy {(d.get('mineralogy') or {}).get('status')}, analog basis {ta.get('basis')}"
    if cid == "L1":
        m = median_elev(d)
        if m is None:
            return "FAIL", "no LOLA elevation"
        ok = abs(m - (-2635)) <= 50
        note = f"median {m:.0f} m (published -2630/-2640 m, diff {m + 2635:+.0f} m)"
        if has_mineralogy(d):
            note += f"; M3 families {sorted(fam)}"
        return ("PASS" if ok else "FAIL"), note
    if cid == "L2":
        if not has_mineralogy(d):
            return "INCONCLUSIVE", "no M3 data"
        b1 = det.get("IBD1000")
        ok = bool(b1) and "lunar_olivine_or_glass" in fam
        return ("PASS" if ok else "FAIL"), f"IBD1000 {b1}, IBD2000 {det.get('IBD2000')}, families {sorted(fam)}"
    if cid == "L3":
        if not has_mineralogy(d):
            return "FAIL", "no M3 data"
        ok = "lunar_pyroxene" in fam and len((d.get("terrestrial_analogs") or {}).get("sites") or []) > 0
        return ("PASS" if ok else "FAIL"), f"families {sorted(fam)}"
    if cid in ("D1", "D2", "D3", "D4", "D5", "D6"):
        if not has_mineralogy(d):
            return "INCONCLUSIVE", f"CRISM: {(d.get('mineralogy') or {}).get('reason')}"
        bad = fam & {"olivine", "fe_mg_phyllosilicate", "al_phyllosilicate_silica", "carbonate", "sulfate", "ice",
                     "mafic", "pyroxene", "hydrated"}
        return ("PASS" if not bad else "FAIL"), f"families {sorted(fam)}" + (f"; false positives {sorted(bad)}" if bad else "")
    if cid in ("I1", "I2"):
        if not has_mineralogy(d):
            return "INCONCLUSIVE", f"CRISM: {(d.get('mineralogy') or {}).get('reason')}"
        ta = d.get("terrestrial_analogs") or {}
        leaked = [m for s in ta.get("sites") or [] for m in s.get("matched_classes") or []
                  if m in analog_sites.ICE_AFFECTED]
        ok = "ice" in fam and not leaked
        return ("PASS" if ok else "FAIL"), f"families {sorted(fam)}, masked {ta.get('masked_evidence')}, " \
            f"BD1435 {values(d).get('BD1435'):.3f}, BD1500_2 {values(d).get('BD1500_2'):.3f}"
    if cid == "L4":
        topo_ok = median_elev(d) is not None
        ta = d.get("terrestrial_analogs") or {}
        honest = not has_mineralogy(d) and not ta.get("sites")      # unlit: no mineral result at all
        return ("PASS" if topo_ok and honest else "FAIL"), \
            f"topography {(d.get('topography') or {}).get('status')}, mineralogy {(d.get('mineralogy') or {}).get('status')}, " \
            f"sites {len(ta.get('sites') or [])}"
    return "INCONCLUSIVE", "no rule"


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    print("health:", c.get("/health").status_code, flush=True)
    raw: dict = {}
    for case in CASES:
        print(f"[{case['id']}] {case['name']} ...", flush=True)
        raw[case["id"]] = run(case)
        print(f"     {raw[case['id']].get('status')} in {raw[case['id']].get('_seconds')} s", flush=True)
        OUT.write_text(json.dumps({"cases": CASES, "raw": raw}, default=str))
    verdicts = {}
    for case in CASES:
        v, why = evaluate(case["id"], raw[case["id"]], raw)
        ok, why_a = analog_consistency(raw[case["id"]])
        verdicts[case["id"]] = {"verdict": v, "detail": why, "analogs_consistent": ok, "analogs_detail": why_a,
                                "seconds": raw[case["id"]].get("_seconds")}
        print(f"{v:12} {case['id']} {case['name']}: {why} | analogs: {why_a}", flush=True)
    OUT.write_text(json.dumps({"cases": CASES, "raw": raw, "verdicts": verdicts}, default=str, indent=1))


if __name__ == "__main__":
    main()
