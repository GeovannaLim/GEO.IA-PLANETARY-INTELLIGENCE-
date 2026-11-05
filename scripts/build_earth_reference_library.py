"""Build app/data/earth_emit_reference_library.json from the legacy library.

Only the EMIT hyperspectral band depths that the legacy pipeline MEASURED in
Earth Engine are kept (hyp_bd_1000_raw, hyp_bd_2000_raw). ASTER/Sentinel-2
proxies, AlphaEarth texture, commodity fields and mining scores are dropped:
they have no same-physics counterpart on the Moon or Mars.

Usage:
    python scripts/build_earth_reference_library.py ../geoia-mining-backend-main/data/earth_proxy_library_100.json
"""
import hashlib
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
raw = src.read_bytes()
legacy = json.loads(raw)
entries = []
for d in legacy["deposits"]:
    ctx = d.get("earth_context") or {}
    b1, b2 = ctx.get("hyp_bd_1000_raw"), ctx.get("hyp_bd_2000_raw")
    if not isinstance(b1, (int, float)) or not isinstance(b2, (int, float)):
        continue
    entries.append({
        "name": d.get("deposit_name"),
        "country": d.get("country"),
        "setting": d.get("deposit_type"),
        "legacy_bd1000": round(max(0.0, float(b1)), 5),
        "legacy_bd2000": round(max(0.0, float(b2)), 5),
        "raw_bd1000": round(float(b1), 5),
        "raw_bd2000": round(float(b2), 5),
        "emit_scene_count": ctx.get("emit_scene_count"),
    })
out = {
    "name": "GEØ.IA terrestrial EMIT band-depth reference library",
    "version": "1.0.0",
    "derived_from": {"file": src.name, "sha256": hashlib.sha256(raw).hexdigest()},
    "measurement": ("NASA/EMIT/L2A/RFL (Earth Engine) median composite over a 10 km buffer around each "
                    "site centroid; band depth per pixel then buffer mean; extracted by the legacy GEØ.IA "
                    "pipeline (run_earth_pipeline.extract_gee_indices)."),
    "definition": {
        "legacy_bd1000": "(C - R1000)/C, C = (R800 + R1300)/2, EMIT bands nearest to each wavelength, clamped >= 0",
        "legacy_bd2000": "(C - R2000)/C, C = (R1700 + R2300)/2, clamped >= 0",
    },
    "limitations": [
        "Extraction date and exact EMIT scene list were not archived by the legacy pipeline.",
        "Most entries are hydrothermal ore systems; many 2 µm depths are affected by alteration minerals "
        "and vegetation residue, not only by Fe2+ in mafic silicates.",
        "Site centroids were not stored with the vectors, so entries cannot be re-measured without the "
        "original site list.",
    ],
    "n_entries": len(entries),
    "entries": entries,
}
dst = Path(__file__).resolve().parents[1] / "app" / "data" / "earth_emit_reference_library.json"
dst.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{len(entries)} entries -> {dst}")
