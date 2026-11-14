"""Moon-Earth geomorphological correspondences by exploration purpose (see app/science/geomorphology.py).

Terrestrial profiles are measured once from REAL Copernicus GLO-30 data by
scripts/build_earth_geomorphology.py (app/data/earth_site_geomorphology.json, with tiles, URLs and dates);
the lunar profile is measured at request time from the LOLA RDR shots already fetched for topography.
A correspondence says only that the terrain statistics named differ by at most twice their combined spatial
variability at the stated scale (an operational criterion, not proof of equivalence): it says nothing about
composition, gravity, illumination, temperature or operations.

Sites whose sampled relief is documented as substantially modified by people (relief_modification.class in
MODIFIED_RELIEF, with evidence and sources in the Earth JSON) are never presented as natural geomorphological
correspondences: they are compared separately and reported under 'modified_relief_references'.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.analysis import GeomorphologySection, Reason, SectionStatus
from app.science import analog_sites
from app.science import geomorphology as G
from app.science.coordinates import to_east_360

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "earth_site_geomorphology.json"
MODIFIED_RELIEF = ("mixed_natural_and_mining", "predominantly_anthropogenic")
MODIFIED_NOTE = ("Sites listed under modified_relief_references have relief documented as modified by mining: "
                 "their correspondence is a reference to modified terrain, not evidence of a natural "
                 "geomorphological analog.")
METHOD = ("Terrain-unit profiles (9 windows of 1 km, offsets 1 km) on a common grid baseline; LOLA RDR shots for "
          "the Moon and Copernicus GLO-30 for the Earth, aggregated with the same method; per-purpose comparison "
          "with standardised differences (z <= 2), a discriminating-power check and a median-slope gate")
NOTES = [
    "Experimental section: calculated geomorphological comparison. Its correspondences are not validated or "
    "documented analogs and must not be read as recommendations.",
    "A geomorphological correspondence means only that, at the stated scale, each listed terrain statistic and the "
    "median slope differ by at most twice their combined spatial variability (an operational criterion, not a "
    "statistical proof of equivalence). It does not imply similar composition, gravity, illumination, "
    "temperature, regolith or operational conditions.",
    "These correspondences are calculated by this system; they are different from the documented analog "
    "relationships of the mineral catalog.",
]
LIMITATIONS = [
    "Copernicus GLO-30 is a surface model (DSM): vegetation and buildings are included in Earth elevations.",
    "Obstacles, rocks and regolith properties below the grid baseline are not resolved.",
    "No route, traversability or safety assessment is made.",
    "Uncertainties are the spatial heterogeneity across the 9 windows, not measurement errors; a very "
    "heterogeneous site is reported as non-discriminating instead of matching.",
    "Discrimination is reliable between strongly contrasting terrains but limited between terrains of "
    "intermediate relief (real-data audit: 22% of distinct catalog site pairs also correspond).",
]


@lru_cache(maxsize=1)
def earth_db() -> dict:
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def section(lat: float, lon: float, altimetry: Any, sampled_radius_km: float | None,
            source_id: str | None) -> GeomorphologySection:
    src = [source_id] if source_id else []
    elev = getattr(altimetry, "elev_m", None)
    if elev is None or elev.size == 0:
        return GeomorphologySection(status=SectionStatus.unavailable, reason=Reason.not_attempted,
                                    notes=["No altimetry available for this request."], source_ids=src)
    if (sampled_radius_km or 0.0) < G.FAMILY_EXTENT_KM:
        return GeomorphologySection(
            status=SectionStatus.unavailable, reason=Reason.insufficient_data, source_ids=src,
            notes=[f"Terrain comparison needs altimetry within {G.FAMILY_EXTENT_KM:g} km of the point "
                   f"(sampled: {sampled_radius_km or 0:g} km); request a radius of at least "
                   f"{G.FAMILY_EXTENT_KM:g} km."])
    lon360 = to_east_360(lon)
    moon = G.best_terrain_profile(altimetry.lat, altimetry.lon360, altimetry.elev_m, lat0=lat,
                                  lon0_360=lon360, body_radius_km=1737.4)
    if moon is None:
        coarse = G.terrain_profile(altimetry.lat, altimetry.lon360, altimetry.elev_m, lat0=lat, lon0_360=lon360,
                                   body_radius_km=1737.4, baseline_m=G.BASELINES_M[-1])
        return GeomorphologySection(
            status=SectionStatus.unavailable, reason=Reason.insufficient_data, method=METHOD, source_ids=src,
            moon_profile=coarse,
            notes=[f"LOLA shot coverage is too sparse for a terrain profile at any baseline up to "
                   f"{G.BASELINES_M[-1]:g} m (median window coverage {coarse['coverage_median']:.0%} at "
                   f"{G.BASELINES_M[-1]:g} m; at least {G.MIN_COVERAGE:.0%} of cells in "
                   f"{G.MIN_FAMILY} of 9 windows is required). Result: inconclusive."])
    L = moon["baseline_m"]
    db, cat = earth_db(), {s["id"]: s for s in analog_sites.catalog()["sites"]}
    items, info, modified = [], {}, {}
    for s in db["sites"]:
        mod = s.get("relief_modification") or {}
        if mod.get("class") in MODIFIED_RELIEF:
            modified[s["id"]] = mod
        prof = (s.get("profiles") or {}).get(f"L{L:g}")
        if prof is None:
            prof = {"status": "no_dem", "error": s.get("error")}
        elif not s.get("represents_site"):
            prof = {"status": "coordinate_too_coarse"}
        site = cat.get(s["id"], {})
        info[s["id"]] = {"id": s["id"], "name": s["name"], "country": site.get("country"), "latitude": s["lat"],
                         "longitude": s["lon"], "coordinate_precision_km": s["coordinate_precision_km"],
                         "documented_lunar_analog": any(a["body"] == "moon" for a in site.get("analog_for", [])),
                         "relationship": "calculated_geomorphological_correspondence",
                         "dem_tiles": s.get("tiles"), "dem_retrieved_at": s.get("retrieved_at")}
        if s.get("measured_unit"):            # documented study unit measured instead of the catalog reference point
            info[s["id"]]["measured_unit"] = s["measured_unit"]
        items.append({"site": {"id": s["id"]}, "profile": prof})
    # The reference spread describes the variability of measured Earth terrain and keeps every valid profile
    # (a mining-modified relief is still real terrain); only the CORRESPONDENCE is withheld for modified relief.
    spread = G.reference_spread([i["profile"] for i in items])
    comps = G.compare(moon, [i for i in items if i["site"]["id"] not in modified], spread)
    mod_items = [i for i in items if i["site"]["id"] in modified]
    mod_comps = G.compare(moon, mod_items, spread) if mod_items else {}
    for p, c in comps.items():
        c["matches"] = [{**info[m["id"]], "metrics": m["metrics"], "slope_level_gate": m["slope_level_gate"],
                         "z_max": m["z_max"]} for m in c["matches"]]
        if mod_items:
            c["modified_relief_references"] = [
                {**info[m["id"]], "relationship": "calculated_correspondence_with_anthropogenically_modified_relief",
                 "relief_modification": modified[m["id"]], "metrics": m["metrics"],
                 "slope_level_gate": m["slope_level_gate"], "z_max": m["z_max"]}
                for m in mod_comps[p]["matches"]]
    any_match = any(c["matches"] for c in comps.values())
    return GeomorphologySection(
        status=SectionStatus.available, method=METHOD, moon_profile=moon, comparisons=comps, source_ids=src,
        earth_reference={"product": db["product"], "source": db["source"], "generated_at": db["generated_at"],
                         "baseline_m": L, "reference_spread": {k: round(v, 4) for k, v in spread.items()},
                         "sites_with_profiles": sum(1 for s in db["sites"] if s.get("profiles"))},
        limitations=list(LIMITATIONS), notes=list(NOTES) + ([] if any_match else [
            "No catalog site shows a demonstrable geomorphological correspondence for any purpose."]) + (
            [MODIFIED_NOTE] if any(c.get("modified_relief_references") for c in comps.values()) else []))
