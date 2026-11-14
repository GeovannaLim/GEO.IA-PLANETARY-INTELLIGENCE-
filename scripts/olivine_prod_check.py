"""Check the 59 olivine controls and Aram Chaos against a deployed backend (real data, use_cache=false).

    PYTHONPATH=. python scripts/olivine_prod_check.py https://geoia-planetary-backend.onrender.com
Expected: positives -> OLINDEX3 confident; Elysium (27.4387N 143.3358E) -> uncertain; other negatives ->
not detected. Also checks that analyzed_extent, spatial_coverage and uncertain_evidence are present.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.argv = sys.argv[:2]
from scripts.science_tests import run  # noqa: E402

FLOOR = 0.05


def main() -> None:
    ctl = json.loads(Path("tests/data/olivine_controls.json").read_text())["controls"]
    out, bad = [], []
    for c in ctl + [{"group": "sulfate", "label": "Aram Chaos FRT000098B2", "lat": 3.922, "lon": -20.4803,
                     "olindex3": None}]:
        r = 5 if c["label"].startswith("Jezero") else 10 if c["label"].startswith("Nili Fossae trough") else 3
        d = run(dict(body="mars", req=dict(latitude=c["lat"], longitude=c["lon"], radius_km=r)))
        m = d.get("mineralogy") or {}
        ta = d.get("terrestrial_analogs") or {}
        ol = next((i for i in m.get("indicators") or [] if i["name"] == "OLINDEX3"), None)
        st = ("no_data" if ol is None else "not_detected" if not ol.get("detected") else
              "uncertain" if ol.get("uncertain") else "confident")
        if c["group"].startswith("positive"):
            exp = "confident"
        elif c["group"] == "negative":
            exp = "uncertain" if (c["olindex3"] or 0) >= FLOOR else "not_detected"
        else:
            exp = None
        fields = {"analyzed_extent": m.get("analyzed_extent") is not None,
                  "spatial_coverage": ol is not None and "spatial_coverage" in ol,
                  "uncertain_evidence": "uncertain_evidence" in ta}
        rec = {"group": c["group"], "label": c["label"], "lat": c["lat"], "lon": c["lon"], "status": st,
               "expected": exp, "ok": exp is None or st == exp, "olindex3": ol and (ol.get("value") or {}).get("median"),
               "coverage": ol and ol.get("spatial_coverage"), "uncertain_evidence": ta.get("uncertain_evidence"),
               "families": [e["class"] for e in ta.get("region_evidence") or []],
               "top": sorted(s["id"] for s in ta.get("sites") or [] if s.get("rank") == 1),
               "extent": m.get("analyzed_extent"), "fields_ok": all(fields.values()), "product": m.get("product_used")}
        out.append(rec)
        if not rec["ok"] or not rec["fields_ok"]:
            bad.append(rec)
        print(f"{'OK ' if rec['ok'] and rec['fields_ok'] else 'BAD'} {c['group']:12s} {c['lat']:8.4f} {c['lon']:9.4f} "
              f"{st:12s} exp={exp} ol={rec['olindex3']} cov={rec['coverage']} fields={fields}", flush=True)
    Path("var/prod_46f3a88").mkdir(parents=True, exist_ok=True)
    Path("var/prod_46f3a88/olivine_prod_check.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n{len(out) - len(bad)}/{len(out)} as expected; mismatches: {len(bad)}")


if __name__ == "__main__":
    main()
