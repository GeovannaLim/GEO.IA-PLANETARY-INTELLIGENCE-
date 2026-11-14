"""Time spent per provider in real analyses (wall time of every HTTP request, summed per provider; requests run
concurrently, so per-provider sums can exceed the analysis wall time). One run per case, sequential (gentle).
    PYTHONPATH=. python scripts/provider_timing.py > var/provider_timing.txt"""
import asyncio
import collections
import time

from app.providers.http import HttpClient
from scripts.local_probe import analyse

STATS = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])   # n, total s, max s, errors
_orig = HttpClient._send


async def timed(self, provider, *a, **k):
    t = time.perf_counter()
    try:
        return await _orig(self, provider, *a, **k)
    except Exception:
        STATS[provider][3] += 1
        raise
    finally:
        dt = time.perf_counter() - t
        s = STATS[provider]; s[0] += 1; s[1] += dt; s[2] = max(s[2], dt)

HttpClient._send = timed
CASES = [("moon", "Mare Imbrium (L3)", 32.80, -15.60, 10), ("moon", "Shackleton (polar)", -89.63, 132.32, 3),
         ("moon", "Copernicus peak (L2)", 9.65, -20.05, 1.5), ("mars", "Jezero (M1-like)", 18.44, 77.45, 3)]


async def main():
    for body, name, la, lo, r in CASES:
        STATS.clear(); t = time.perf_counter()
        d = await analyse(body, la, lo, r)
        wall = time.perf_counter() - t
        print(f"\n== {name}: wall {wall:.1f} s, status {d['status']}; sections: " +
              ", ".join(f"{k}={(d.get(k) or {}).get('status')}" for k in
                        ("imagery", "topography", "mineralogy", "environment", "geomorphology", "terrestrial_analogs")))
        for p, (n, tot, mx, err) in sorted(STATS.items(), key=lambda kv: -kv[1][1]):
            print(f"   {p:42s} requests {n:4d}  sum {tot:7.1f} s  max {mx:6.1f} s  errors {err}")
        print("   mineralogy product:", (d.get("mineralogy") or {}).get("product_used"),
              "| problems:", [p["message"][:90] for p in d["problems"]])

asyncio.run(main())
