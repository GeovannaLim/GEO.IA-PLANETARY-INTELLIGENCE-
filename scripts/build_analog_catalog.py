"""Assemble app/data/terrestrial_analog_sites.json from the curated source lists.

Validates every entry (coordinates, classes, references) and keeps any EMIT measurement already
recorded in the existing catalog (written by scripts/remeasure_library.py analogs).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import analog_catalog_mars as mars  # noqa: E402
import analog_catalog_moon as moon  # noqa: E402

OUT = ROOT / "app" / "data" / "terrestrial_analog_sites.json"
CLASSES = {"pyroxene_basalt", "norite", "anorthosite", "olivine_rich", "volcanic_glass", "fe_mg_phyllosilicate",
           "al_phyllosilicate_silica", "carbonate", "sulfate", "ferric_oxide", "altered_basaltic_soil"}
VERIFIED_ON = "2026-11-06"
BASIS = {"published_analog", "simulant_source", "published_analog_general", "mineralogical_reference", "outreach",
         "candidate"}


def build() -> dict:
    sites = [dict(s) for s in mars.SITES + moon.SITES]
    by_id = {s["id"]: s for s in sites}
    assert len(by_id) == len(sites), "duplicate site id"
    kau = by_id["kau_desert"]                      # one physical site, analog for both bodies
    kau["analog_for"] = kau["analog_for"] + [moon.KAU_MOON]
    kau["references"] = kau["references"] + moon.KAU_MOON_REFS
    old = {}
    if OUT.exists():
        old = {s["id"]: s.get("emit") for s in json.loads(OUT.read_text())["sites"]}
    for s in sites:
        assert -90 <= s["lat"] <= 90 and -180 <= s["lon"] <= 180, s["id"]
        ref_ids = {r["id"] for r in s["references"]}
        for a in s["analog_for"]:
            assert a["body"] in ("moon", "mars") and set(a["classes"]) <= CLASSES, (s["id"], a["classes"])
            assert set(a["reference_ids"]) <= ref_ids, (s["id"], a["reference_ids"])
            assert a["rationale_en"] and a["rationale_pt"]
            assert a["basis"] in BASIS, (s["id"], a.get("basis"))
        for r in s["references"]:
            r["doi_verified"] = f"Crossref/DataCite {VERIFIED_ON}" if r.get("doi") else None
        for k in ("similarities", "differences", "limitations"):
            assert len(s.get(k + "_en", [])) == len(s.get(k + "_pt", [])), (s["id"], k)
        s["emit"] = old.get(s["id"])
    return {"name": "GEØ.IA terrestrial analog sites", "version": "1.0.0",
            "curated_on": VERIFIED_ON,
            "method": "Sites selected from published analog studies; coordinates from the cited source; DOIs "
                      "resolved on Crossref/DataCite. Unverified entries are kept for transparency but never "
                      "offered by the matcher.",
            "site_classes": sorted(CLASSES), "sites": sites}


if __name__ == "__main__":
    cat = build()
    OUT.write_text(json.dumps(cat, ensure_ascii=False, indent=1))
    v = sum(s["verification"] == "verified" for s in cat["sites"])
    print(f"{len(cat['sites'])} sites ({v} verified) -> {OUT.relative_to(ROOT)}")
