"""Cross-body comparison with explicit attribute compatibility.

Reused idea from the legacy ``compare_lunar_to_earth.masked_cosine``: compare
only attributes present on both sides. Revised because (a) the legacy 8-axis
vector mixed same-named fields derived from different physics (ASTER TIR vs
M3 VSWIR), and (b) cosine similarity over 2-3 non-negative dimensions saturates
near 1 for almost any pair. Here:

* Attributes are classified as ``direct`` (identical definition computed from
  VSWIR reflectance on both bodies), ``proxy`` (same physical target, different
  definition — reported but never scored), ``not comparable`` and ``missing``.
* Only ``direct`` attributes enter the score: Euclidean distance in band-depth
  units, converted to a ranking aid ``similarity = 1 - d / d_max`` with
  ``d_max = 0.4·sqrt(n)`` (0.4 = top of the legacy band-depth scale).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.schemas.analysis import AnalogMatch, EarthAnalogSection, Reason, SectionStatus

LIBRARY_PATH = Path(__file__).resolve().parents[1] / "data" / "earth_emit_reference_library.json"
DIRECT = ("legacy_bd1000", "legacy_bd2000")
MIN_DIRECT = 2
BD_SCALE = 0.40


@lru_cache
def load_library() -> dict:
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


COMPATIBILITY = {
    "earth": {
        "proxy": [],
        "not_comparable": ["Sentinel-2 ferric ratio, NDVI and ASTER TIR indices (reported as Earth context only)"],
    },
    "moon": {
        "proxy": ["IBD1000 (vs EMIT 1 µm depth: same absorption, different integration)",
                  "IBD2000 (vs EMIT 2 µm depth: same absorption, different integration)"],
        "not_comparable": ["R750 / slope_750_1550 (lunar space weathering has no terrestrial analogue)",
                           "ASTER TIR silica/mafic indices (thermal infrared, not measured on the Moon here)",
                           "Sentinel-2 ferric ratio, NDVI (aqueous alteration / vegetation; absent on the Moon)"],
    },
    "mars": {
        "proxy": ["BDI1000IR / LCPINDEX2 / HCPINDEX2 (Fe2+ absorptions; CRISM-specific definitions)"],
        "not_comparable": ["BD1900_2, D2300, BD2210_2, carbonate and sulfate parameters "
                           "(no equivalent attribute in the terrestrial reference library)",
                           "CO2/H2O ice parameters (no terrestrial counterpart in the library)",
                           "ASTER TIR indices, NDVI (not measured on Mars here)"],
    },
}


def compare(body: str, values: dict[str, float]) -> EarthAnalogSection:
    lib = load_library()
    present = [a for a in DIRECT if isinstance(values.get(a), (int, float)) and math.isfinite(values[a])]
    missing = [a for a in DIRECT if a not in present]
    comp = COMPATIBILITY[body]
    base = dict(method="Euclidean distance over directly comparable band depths (legacy definition)",
                reference_library=f"{lib['name']} v{lib['version']} ({lib['n_entries']} sites)",
                directly_comparable=present, approximate_proxies=comp["proxy"],
                not_comparable=comp["not_comparable"], missing=missing,
                query_values={a: round(values[a], 5) for a in present})
    if len(present) < MIN_DIRECT:
        return EarthAnalogSection(status=SectionStatus.unavailable, reason=Reason.insufficient_data, **base)
    d_max = BD_SCALE * math.sqrt(len(present))
    rows = []
    for e in lib["entries"]:
        ev = {a: e[a] for a in present if isinstance(e.get(a), (int, float))}
        if len(ev) != len(present):
            continue
        d = math.sqrt(sum((values[a] - ev[a]) ** 2 for a in present))
        rows.append(AnalogMatch(name=e["name"], country=e.get("country"), setting=e.get("setting"),
                                distance=round(d, 5), similarity=round(max(0.0, 1 - d / d_max), 4),
                                attributes_used=present, earth_values=ev))
    rows.sort(key=lambda r: r.distance)
    top = rows[:5]
    sec = EarthAnalogSection(status=SectionStatus.available, matches=top, **base)
    if len(top) >= 2 and top[-1].distance - top[0].distance < 0.05:
        sec.disclaimer += (f" Low discrimination: the top {len(top)} sites lie within "
                           f"{top[-1].distance - top[0].distance:.3f} band-depth units of each other.")
    if len(present) <= 2:
        sec.disclaimer += (" Only two attributes are compared; many geologically unrelated sites can match "
                           "equally well (the library is dominated by hydrothermal ore systems).")
    return sec
