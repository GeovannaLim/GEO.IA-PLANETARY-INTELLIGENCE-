"""Run one analysis against the REAL services and print/save the result.

    python scripts/live_run.py moon 35.0 -15.0 5 [out.json]
"""
import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timezone

from app.pipelines import earth, lunar, mars
from app.providers.http import close_http, get_http
from app.schemas.analysis import AnalyzeRequest

RUN = {"moon": lunar.run, "mars": mars.run, "earth": earth.run}


async def main():
    body, lat, lon, r = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    out = sys.argv[5] if len(sys.argv) > 5 else None
    t0 = time.time()

    async def prog(step):
        print(f"  [{time.time() - t0:6.1f}s] {step}", flush=True)

    res = await RUN[body](AnalyzeRequest(latitude=lat, longitude=lon, radius_km=r), get_http(),
                          uuid.uuid4().hex, datetime.now(timezone.utc), prog)
    await close_http()
    d = res.model_dump(mode="json")
    print(f"total {time.time() - t0:.1f}s")
    for k in ("imagery", "topography", "mineralogy", "earth_analogs"):
        print(k, d[k]["status"], d[k].get("reason"))
    t = d["topography"]
    print("topo n", t["n_points"], "elev", t["elevation_m"] and t["elevation_m"]["mean"], "slope", t["regional_slope_degrees"],
          t["local_slope_degrees"] and t["local_slope_degrees"]["median"], "cov", t["coverage_fraction"])
    m = d["mineralogy"]
    print("min", m["product_used"], m["valid_pixels"], m["spectral_character"])
    for i in m["indicators"]:
        print("   ", i["name"], round(i["value"]["median"], 4) if i["value"]["median"] is not None else None, i["interpretation"][:60])
    print("analogs", [(x["name"], x["distance"]) for x in d["earth_analogs"]["matches"][:3]])
    print("confidence", d["confidence"]["level"])
    for p in d["problems"]:
        print("PROBLEM", p)
    for s in d["data_sources"]:
        print("SRC", s["source_id"], s["provider"], "|", s["service"], "|", s["status"], "|", (s["message"] or "")[:120])
    if out:
        open(out, "w").write(json.dumps(d, indent=2, ensure_ascii=False))

asyncio.run(main())
