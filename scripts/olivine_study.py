"""Study of OLINDEX3 vs BDI1000IR on real CRISM MTRDR windows (investigation only; no app change).

Runs the real Mars pipeline locally and captures the per-pixel summary parameters of the observation
used. Groups:
  positive_lit  - olivine documented at the point in the literature
  positive_reg  - inside the documented Nili Fossae regional olivine unit (not point-verified)
  negative      - dust-mantled regions (Tharsis/Amazonis, Elysium, Arabia)
Points: the 59 fixed controls in tests/data/olivine_controls.json (selected 2026-11-14 from CRISM MTRDR
listings: Nili Fossae box 18-23N 74-80E, random seed 42; dust from Tharsis/Amazonis, Elysium and Arabia).
Writes var/olivine_study.json.  PYTHONPATH=. python scripts/olivine_study.py
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np

from app.providers import crism
from scripts.local_probe import analyse

CAPTURED: dict = {}
_real_extract = crism.extract


async def _capture(*a, **k):
    ex = await _real_extract(*a, **k)
    CAPTURED["last"] = ex
    return ex
crism.extract = _capture


def spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return None
    ra = np.argsort(np.argsort(a[m])).astype(float)
    rb = np.argsort(np.argsort(b[m])).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def points() -> list[tuple[str, str, float, float, float]]:
    """The 59 fixed controls (tests/data/olivine_controls.json): 4 literature positives, 10 regional positives
    inside the Nili Fossae olivine unit, 45 dust negatives (Tharsis/Amazonis, Elysium, Arabia). The radius only
    sets the circular mask; the CRISM window is capped at ~1.1 km anyway (see analyzed_extent)."""
    radius = {"Jezero": 5, "Nili Fossae trough": 10}
    ctl = json.loads(Path("tests/data/olivine_controls.json").read_text())["controls"]
    return [(c["group"], c["label"], c["lat"], c["lon"],
             next((v for k, v in radius.items() if c["label"].startswith(k)), 3)) for c in ctl]


async def main() -> None:
    out = []
    for group, label, la, lo, r in points():
        CAPTURED.clear()
        d = await analyse("mars", la, lo, r)
        ex = CAPTURED.get("last")
        m = d["mineralogy"]
        rec = {"group": group, "label": label, "lat": la, "lon": lo, "status": m["status"],
               "product": m.get("product_used")}
        if ex is not None and m["status"] in ("available", "partial") and "OLINDEX3" in ex.params:
            o, b = ex.params["OLINDEX3"], ex.params.get("BDI1000IR")
            l, h = ex.params.get("LCPINDEX2"), ex.params.get("HCPINDEX2")
            rec.update(n=int(o.size), olindex3=float(np.median(o)), bdi1000ir=float(np.median(b)),
                       lcp=float(np.median(l)), hcp=float(np.median(h)), rho=spearman(o, b),
                       frac_ol_floor=float(np.mean(o >= 0.05)),
                       olindex3_p90=float(np.percentile(o, 90)), bdi_p90=float(np.percentile(b, 90)))
        out.append(rec)
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()}), flush=True)
    Path("var/olivine_study.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
