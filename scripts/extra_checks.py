"""Extra production checks (2026-11-14): sulfate positive control and dust outside Tharsis.

    PYTHONPATH=. python scripts/extra_checks.py https://geoia-planetary-backend.onrender.com

* Sulfate: Aram Chaos, CRISM FRT000098B2 centre (3.922N, 339.5197E). Lichtenberg et al. 2010,
  JGR Planets (doi:10.1029/2009JE003353): kieserite and polyhydrated sulfate in the Aram Chaos deposits.
* Dust outside Tharsis: random CRISM MTRDR observations in Elysium and Arabia (bright, low thermal inertia,
  dust-covered regions; Putzig et al. 2005). Local geology may hold real minerals, so a detection there is
  'to investigate', not automatically a false positive.
Uses the production API (use_cache=false), one analysis at a time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.argv = sys.argv[:2]
from scripts.science_tests import families, run, values  # noqa: E402

OUT = Path("var/prod_abb10cb/extra_checks.json")
HYDRATED = {"olivine", "fe_mg_phyllosilicate", "al_phyllosilicate_silica", "carbonate", "sulfate", "ice",
            "mafic", "pyroxene", "hydrated"}


def main() -> None:
    res = {}
    d = run(dict(body="mars", req=dict(latitude=3.922, longitude=339.5197, longitude_convention="east_360",
                                       radius_km=3)))
    v = values(d)
    res["sulfate_aram"] = {"status": (d.get("mineralogy") or {}).get("status"),
                           "product": (d.get("mineralogy") or {}).get("product_used"),
                           "families": sorted(families(d)),
                           "BD2100_2": v.get("BD2100_2"), "SINDEX2": v.get("SINDEX2"), "BD1900_2": v.get("BD1900_2"),
                           "sites": [(s.get("rank"), s["id"], s["matched_classes"])
                                     for s in (d.get("terrestrial_analogs") or {}).get("sites") or []]}
    print("SULFATE Aram Chaos:", json.dumps(res["sulfate_aram"]), flush=True)
    for region in ("Elysium", "Arabia"):
        rows = []
        for lat, lon in json.loads(Path(f"var/dust_{region}.json").read_text()):
            d = run(dict(body="mars", req=dict(latitude=lat, longitude=lon, longitude_convention="east_360",
                                               radius_km=3)))
            fam = families(d)
            rows.append({"lat": lat, "lon": lon, "status": (d.get("mineralogy") or {}).get("status"),
                         "product": (d.get("mineralogy") or {}).get("product_used"), "families": sorted(fam),
                         "flag": sorted(fam & HYDRATED), "medians": values(d)})
            print(f"{region} {lat} {lon} {rows[-1]['status']} {sorted(fam)}", flush=True)
        res[region] = rows
    OUT.write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
