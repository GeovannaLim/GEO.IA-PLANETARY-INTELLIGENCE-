"""Validate a deployed GEØ.IA backend with REAL requests (no mocks).

    PYTHONPATH=. python scripts/validate_production.py https://<service>.onrender.com [--origin https://skip-app]

Runs tests A-F sequentially (gentle on NASA services), polls jobs, checks
reports, and writes var/production_validation.json. Exit code 1 if any check fails.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
ORIGIN = sys.argv[sys.argv.index("--origin") + 1] if "--origin" in sys.argv else None
results: list[dict] = []
c = httpx.Client(base_url=BASE, timeout=90, follow_redirects=True)


def check(name: str, ok: bool, **detail) -> bool:
    results.append({"check": name, "ok": bool(ok), **detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name} " + json.dumps(detail, default=str)[:300], flush=True)
    return ok


def analyze(path: str, body: dict, timeout_s: float = 300) -> tuple[dict | None, float, int]:
    t0 = time.time()
    r = c.post(f"{path}?use_cache=false&wait_s=0", json=body)
    first = r.status_code
    if first not in (200, 202):
        return {"_error": r.text[:300], "_code": first}, time.time() - t0, first
    doc = r.json()
    while doc.get("status") == "processing" and time.time() - t0 < timeout_s:
        time.sleep(4)
        doc = c.get(doc["links"]["self"]).json()
    return doc, time.time() - t0, first


def sections(d: dict) -> dict:
    return {k: (d[k]["status"], d[k].get("reason")) for k in ("imagery", "topography", "mineralogy", "earth_analogs")}


def numbers_have_sources(d: dict) -> bool:
    ids = {s["source_id"] for s in d["data_sources"]}
    for k in ("topography", "mineralogy"):
        if d[k]["status"] in ("available", "partial") and not (set(d[k]["source_ids"]) and set(d[k]["source_ids"]) <= ids):
            return False
    return True


# A — health
t0 = time.time()
r = c.get("/health")
h = r.json() if r.status_code == 200 else {}
check("A health 200", r.status_code == 200 and h.get("status") == "ok", seconds=round(time.time() - t0, 1),
      database=h.get("database"), version=h.get("version"), environment=h.get("environment"))
check("A https", BASE.startswith("https://") or "localhost" in BASE, base=BASE)

# B — Moon
body = {"latitude": 25.8, "longitude": -15.2, "radius_km": 10}
d, dt, first = analyze("/v1/lunar/analyze", body)
if check("B lunar job created", first in (200, 202) and d and "analysis_id" in d, first_status=first):
    check("B lunar completed", d["status"] == "completed", seconds=round(dt, 1), sections=sections(d))
    t, m = d["topography"], d["mineralogy"]
    check("B coordinates used", d["coordinates"]["latitude"] == 25.8 and abs(d["coordinates"]["longitude_east_360"] - 344.8) < 1e-6)
    check("B LOLA numeric topography", t["status"] in ("available", "partial") and (t["n_points"] or 0) > 0
          and "LOLA" in (t["method"] or ""), n_points=t["n_points"], elev_mean=(t["elevation_m"] or {}).get("mean"))
    check("B ODE queried", any("ODE" in s["service"] for s in d["data_sources"]))
    check("B M3 extraction", m["status"] in ("available", "partial", "unavailable"), status=m["status"],
          product=m["product_used"], valid_pixels=m["valid_pixels"], character=m["spectral_character"])
    check("B provenance links", numbers_have_sources(d))
    check("B no Imbrium fixed vector", "M3G20090418T132620" not in json.dumps(d))
    lunar_id = d["analysis_id"]
else:
    lunar_id = None

# C — Mars (Jezero coordinates from the validated local tests) + no-coverage region
d, dt, first = analyze("/v1/mars/analyze", {"latitude": 18.44, "longitude": 77.45, "radius_km": 5})
if check("C mars job", first in (200, 202) and d and "analysis_id" in d, first_status=first):
    t, m = d["topography"], d["mineralogy"]
    check("C mars completed", d["status"] == "completed", seconds=round(dt, 1), sections=sections(d))
    check("C MOLA topography", "MOLA" in (t["method"] or "") and (t["n_points"] or 0) > 0, n_points=t["n_points"])
    check("C CRISM parameters", m["status"] in ("available", "partial") and "CRISM" in (m["instrument"] or ""),
          product=m["product_used"], character=m["spectral_character"])
    check("C no lunar indices on Mars", not {"IBD1000", "IBD2000", "R750"} & {i["name"] for i in m["indicators"]})
    check("C provenance links", numbers_have_sources(d))
    mars_id = d["analysis_id"]
else:
    mars_id = None
d, dt, _ = analyze("/v1/mars/analyze", {"latitude": -85.0, "longitude": 150.0, "radius_km": 10})
check("C no spectral coverage is explicit", d and d["mineralogy"]["status"] == "unavailable"
      and d["mineralogy"]["reason"] in ("no_coverage", "no_compatible_observations") and not d["mineralogy"]["indicators"],
      seconds=round(dt, 1), mineralogy=d and (d["mineralogy"]["status"], d["mineralogy"]["reason"]))

# D — Earth
d, dt, _ = analyze("/v1/earth/analyze", {"latitude": -24.27, "longitude": -69.07, "radius_km": 5}, timeout_s=240)
if d and d.get("status") == "completed":
    configured = d["topography"]["reason"] != "not_configured"
    if configured:
        check("D earth real analysis", d["topography"]["status"] in ("available", "partial"), sections=sections(d))
    else:
        check("D earth explicit not_configured", all(d[k]["reason"] == "not_configured"
                                                   for k in ("topography", "mineralogy", "earth_analogs"))
              and d["earth_analogs"]["matches"] == [], pending="GEE credentials not set")
else:
    check("D earth", False, doc=str(d)[:200])

# G — localisation and analog explainability (added in the stabilisation mission)
if lunar_id:
    en = c.get(f"/v1/jobs/{lunar_id}").json()
    pt = c.get(f"/v1/jobs/{lunar_id}?lang=pt-BR").json()
    check("G pt-BR prose, science untouched", pt.get("language") == "pt-BR"
          and pt["links"]["self"].endswith("lang=pt-BR")
          and pt["mineralogy"]["indicators"][0]["value"] == en["mineralogy"]["indicators"][0]["value"]
          and pt["coordinates"] == en["coordinates"] and pt["data_sources"] == en["data_sources"]
          and pt["earth_analogs"]["disclaimer"] != en["earth_analogs"]["disclaimer"],
          sample=(pt["mineralogy"].get("spectral_character") or "")[:80])
    a = en["earth_analogs"]
    if a["status"] == "available":
        ok = a.get("discrimination") in ("low", "moderate", "adequate") and all(
            set(m["differences"]) == set(m["attributes_used"]) for m in a["matches"])
        leg = {i["name"]: i for i in en["mineralogy"]["indicators"] if i["name"].startswith("legacy_")}
        ok = ok and all(abs(a["query_values"][k] - max(0.0, leg[k]["value"]["mean"])) < 1e-4 for k in a["query_values"])
        check("G analog explainability + clamp after mean", ok, discrimination=a.get("discrimination"),
              indistinguishable=a.get("indistinguishable_sites"), spread=a.get("top5_distance_spread"))

# E — reports
for rid, label in ((lunar_id, "lunar"), (mars_id, "mars")):
    if not rid:
        continue
    j = c.get(f"/v1/reports/{rid}")
    p = c.get(f"/v1/reports/{rid}?format=pdf")
    ok = j.status_code == 200 and p.status_code == 200 and p.content[:5] == b"%PDF-"
    same = ok and j.json()["analysis_id"] == rid and j.json()["topography"] == c.get(f"/v1/jobs/{rid}").json()["topography"]
    check(f"E {label} report json+pdf", ok and same, pdf_bytes=len(p.content), sources=len(j.json()["data_sources"]) if ok else None,
          limitations=len(j.json()["confidence"]["limitations"]) if ok else None)

# F — edge cases
check("F invalid latitude 422", c.post("/v1/lunar/analyze", json={"latitude": 91, "longitude": 0}).status_code == 422)
check("F invalid radius 422", c.post("/v1/mars/analyze", json={"latitude": 0, "longitude": 0, "radius_km": 9999}).status_code == 422)
check("F unknown job 404", c.get("/v1/jobs/does-not-exist").status_code == 404)
d, dt, _ = analyze("/v1/lunar/analyze", {"latitude": -89.9, "longitude": 0, "radius_km": 5})
check("F lunar south pole", d and d["status"] == "completed", seconds=round(dt, 1), sections=d and sections(d))
d, dt, _ = analyze("/v1/lunar/analyze", {"latitude": 0.5, "longitude": 179.95, "radius_km": 3})
check("F lunar antimeridian", d and d["status"] == "completed", seconds=round(dt, 1), sections=d and sections(d))
if ORIGIN:
    pre = c.options("/v1/lunar/analyze", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST",
                                                  "Access-Control-Request-Headers": "content-type"})
    check("CORS preflight for Skip origin", pre.headers.get("access-control-allow-origin") == ORIGIN, status=pre.status_code)
evil = c.options("/health", headers={"Origin": "https://not-allowed.example", "Access-Control-Request-Method": "GET"})
check("CORS rejects unknown origin", "access-control-allow-origin" not in evil.headers)

Path("var").mkdir(exist_ok=True)
Path("var/production_validation.json").write_text(json.dumps({"base": BASE, "results": results}, indent=2, default=str))
failed = [r for r in results if not r["ok"]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
