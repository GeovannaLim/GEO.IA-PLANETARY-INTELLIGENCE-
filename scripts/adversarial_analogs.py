"""Adversarial checks of the terrestrial analog ranking, on REAL mineralogy results.

Uses the stored real results of scripts/science_tests.py (var/science_tests.json) and the real catalog.
Asks where the ranking could lead to a scientifically wrong reading:
  A1 catalog order    - does the file order of the catalog change the ranking?
  A2 absence-agreement - does "both lack the band" score like a similarity?
  A3 cross-body        - can a Moon-only site be offered for Mars (or vice versa)?
  A4 single family     - does dropping one detected family change the top site?
  A5 broad vs specific - can broad evidence alone outrank specific evidence?
Run: PYTHONPATH=. python scripts/adversarial_analogs.py   (no network)
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path

from app.schemas.analysis import MineralogySection
from app.science import analog_sites, spectral

RAW = json.loads(Path("var/science_tests.json").read_text())["raw"]
CASES = {k: v for k, v in RAW.items() if v.get("status") == "completed"
         and (v.get("mineralogy") or {}).get("status") in ("available", "partial")}


def section(doc: dict) -> MineralogySection:
    """Stored section with the CURRENT detection floors applied (stored flags predate them)."""
    sec = MineralogySection(**doc["mineralogy"])
    for i in sec.indicators:
        floor = spectral.MAGNITUDE_FLOOR.get(i.name)
        if floor is not None and i.detected and (i.value.median or 0) < floor:
            i.detected = False
    return sec


def ranking(doc: dict, sec: MineralogySection | None = None) -> list[str]:
    out = analog_sites.match(doc["planet"], sec or section(doc), doc["coordinates"]["latitude"])
    return [s.id for s in out.sites]


def top(doc: dict, sec: MineralogySection | None = None) -> set[str]:
    """Sites sharing rank 1 (ties are announced, so the whole group is the 'top')."""
    out = analog_sites.match(doc["planet"], sec or section(doc), doc["coordinates"]["latitude"])
    return {s.id for s in out.sites if s.rank == 1}


def with_catalog(cat: dict, fn):
    original = analog_sites.catalog
    analog_sites.catalog = lambda: cat
    try:
        return fn()
    finally:
        analog_sites.catalog = original


def a1_catalog_order() -> list[str]:
    msgs, base_cat = [], analog_sites.catalog()
    for k, doc in CASES.items():
        base = ranking(doc)
        for seed in range(20):
            cat = copy.deepcopy(base_cat)
            random.Random(seed).shuffle(cat["sites"])
            r = with_catalog(cat, lambda: ranking(doc))
            if r != base:
                msgs.append(f"{k}: order-dependent ranking (seed {seed}): {base} -> {r}")
                break
    return msgs


def a2_absence_agreement() -> list[str]:
    """Recompute the agreement bonus counting only agreement on PRESENCE; report changed rankings."""
    msgs = []
    for k, doc in CASES.items():
        base = ranking(doc)
        real_match = analog_sites.match
        # re-rank with the region's legacy band flags forced to 'unknown' when absent
        sec = section(doc)
        sec2 = sec.model_copy(deep=True)
        for i in sec2.indicators:
            if i.name in ("legacy_bd1000", "legacy_bd2000") and i.detected is False:
                i.detected = None
        r = real_match(doc["planet"], sec2, doc["coordinates"]["latitude"])
        alt = [s.id for s in r.sites]
        if alt != base:
            msgs.append(f"{k}: ranking depends on agreement-on-absence: {base} -> {alt}")
    return msgs


def a3_cross_body() -> list[str]:
    msgs, cat = [], {s["id"]: s for s in analog_sites.catalog()["sites"]}
    for k, doc in CASES.items():
        for sid in ranking(doc):
            if not any(a["body"] == doc["planet"] for a in cat[sid]["analog_for"]):
                msgs.append(f"{k}: {sid} has no documented analogy for {doc['planet']}")
    return msgs


def a4_single_family() -> list[str]:
    msgs = []
    for k, doc in CASES.items():
        base = top(doc)
        if not base:
            continue
        for ind in section(doc).indicators:
            if not ind.detected or ind.name.startswith("legacy"):
                continue
            sec = section(doc)
            for i in sec.indicators:
                if i.name == ind.name:
                    i.detected = False
            alt = top(doc, sec)
            if not (alt & base):
                med = ind.value.median
                msgs.append(f"{k}: top {sorted(base)} -> {sorted(alt) or 'none'} without {ind.name} "
                            f"(median {med:.4f})")
    return msgs


def a5_broad_vs_specific() -> list[str]:
    msgs = []
    for k, doc in CASES.items():
        out = analog_sites.match(doc["planet"], section(doc), doc["coordinates"]["latitude"])
        strength = {e["class"]: e["strength"] for e in out.region_evidence}
        spec_seen_after_broad_only, prev_broad_only = False, False
        for s in out.sites:
            broad_only = all(strength.get(m) == "broad" for m in s.matched_classes)
            if prev_broad_only and not broad_only:
                spec_seen_after_broad_only = True
            prev_broad_only = broad_only
        if spec_seen_after_broad_only:
            msgs.append(f"{k}: a broad-only site is ranked above a site with specific evidence")
    return msgs


if __name__ == "__main__":
    print(f"cases with mineralogy: {sorted(CASES)}")
    for name, fn in (("A1 catalog order", a1_catalog_order), ("A2 absence agreement", a2_absence_agreement),
                     ("A3 cross-body", a3_cross_body), ("A4 single family", a4_single_family),
                     ("A5 broad vs specific", a5_broad_vs_specific)):
        msgs = fn()
        print(f"\n{name}: {'OK' if not msgs else f'{len(msgs)} finding(s)'}")
        for m in msgs:
            print("  -", m)
