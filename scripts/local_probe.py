"""Run real Moon/Mars pipelines locally (current code, real NASA data) for calibration probes.

    PYTHONPATH=. python scripts/local_probe.py mars lat lon [radius_km] ...  (prints JSON per point)
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone

from app.pipelines import lunar, mars
from app.providers.http import get_http
from app.schemas.analysis import AnalyzeRequest


async def _noop(step):
    return None


async def analyse(body: str, lat: float, lon: float, r: float = 5.0) -> dict:
    run = {"mars": mars.run, "moon": lunar.run}[body]
    res = await run(AnalyzeRequest(latitude=lat, longitude=lon, radius_km=r), get_http(), "local",
                    datetime.now(timezone.utc), _noop)
    return res.model_dump(mode="json")


def summary(d: dict) -> dict:
    m = d["mineralogy"]
    ind = {i["name"]: i for i in m.get("indicators") or []}
    return {"status": m["status"], "reason": m.get("reason"), "product": m.get("product_used"),
            "valid": m.get("valid_pixels"),
            "median": {k: (v.get("value") or {}).get("median") for k, v in ind.items()},
            "detected": {k: v.get("detected") for k, v in ind.items()},
            "families": [e["class"] for e in (d.get("terrestrial_analogs") or {}).get("region_evidence") or []],
            "problems": [p["message"][:160] for p in d.get("problems") or []]}


if __name__ == "__main__":
    body, rest = sys.argv[1], sys.argv[2:]
    pts = [rest[i:i + 3] for i in range(0, len(rest), 3)]
    async def main():
        for lat, lon, r in pts:
            d = await analyse(body, float(lat), float(lon), float(r))
            print(json.dumps({"lat": lat, "lon": lon, **summary(d)}), flush=True)
    asyncio.run(main())
