"""Remeasure terrestrial sites with the quality-masked EMIT measurement of the Earth endpoint.

Usage
  python scripts/remeasure_library.py library  <deposits_master.json>  [--base URL] [--radius 10]
  python scripts/remeasure_library.py analogs                          [--base URL]
  python scripts/remeasure_library.py compare

``library``  recovers the coordinates of the 90 production-library sites from the legacy
             ``deposits_master.json`` (coordinates only; no legacy value is reused as a result),
             grades coordinate precision, and measures each site.
``analogs``  measures the curated analog sites of ``app/data/terrestrial_analog_sites.json``
             and writes the masked EMIT record back into each site (``emit``).
``compare``  old library values vs remeasured raw / quality / rock variants, vegetation effect.

Each site is one sequential POST /v1/earth/analyze?use_cache=false followed by polling; results
are saved after every site so an interrupted run resumes. Nothing is estimated: a site without
EMIT scenes or rock pixels keeps None.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.science.spectral import detected_from_stats  # noqa: E402

LIB = ROOT / "app" / "data" / "earth_emit_reference_library.json"
CATALOG = ROOT / "app" / "data" / "terrestrial_analog_sites.json"
OUT_DIR = ROOT / "data" / "remeasurement"
SITES_FILE = OUT_DIR / "library_sites_coordinates.json"
RESULTS_FILE = OUT_DIR / "library_emit_remeasured.json"
COMPARE_FILE = OUT_DIR / "COMPARACAO.md"
DEFAULT_BASE = "https://geoia-planetary-backend.onrender.com"


def precision_km(lat: float, lon: float) -> tuple[int, float]:
    """Decimal places actually written and the implied half-step in km (worst axis)."""
    def places(x: float) -> int:
        s = repr(float(x))
        return len(s.split(".")[1].rstrip("0")) if "." in s else 0
    d = min(places(lat), places(lon))
    return d, round(0.5 * 10 ** (-d) * 111.32, 3)


def recover_coordinates(master_path: Path) -> list[dict]:
    lib = json.loads(LIB.read_text())["entries"]
    master = {d["deposit_name"]: d for d in json.loads(Path(master_path).read_text())["deposits"]}
    out = []
    for e in lib:
        m = master.get(e["name"])
        rec = {"name": e["name"], "country": e["country"], "setting": e["setting"],
               "old_library": {k: e.get(k) for k in ("legacy_bd1000", "legacy_bd2000", "raw_bd1000", "raw_bd2000",
                                                     "emit_scene_count")}}
        if m is None or not m.get("centroid"):
            rec.update(lat=None, lon=None, coordinate_quality="missing")
        else:
            lat, lon = m["centroid"]["lat"], m["centroid"]["lon"]
            places, half_km = precision_km(lat, lon)
            rec.update(lat=lat, lon=lon, deposit_id=m.get("deposit_id"), coordinate_decimals=places,
                       coordinate_half_step_km=half_km,
                       coordinate_quality="low" if half_km >= 1 else "moderate" if half_km >= 0.1 else "high",
                       coordinate_source=f"legacy deposits_master.json ({m.get('provenance', {}).get('source_file')}); "
                                         "original citation not recorded",
                       legacy_master_ndvi=(m.get("raw_spectral") or {}).get("ndvi"))
        out.append(rec)
    return out


def measure(client: httpx.Client, base: str, lat: float, lon: float, radius_km: float) -> dict:
    r = client.post(f"{base}/v1/earth/analyze", params={"wait_s": 60, "use_cache": "false"},
                    json={"latitude": lat, "longitude": lon, "radius_km": radius_km})
    r.raise_for_status()
    doc = r.json()
    t0 = time.time()
    while doc.get("status") == "processing" and time.time() - t0 < 600:
        time.sleep(10)
        doc = client.get(base + doc["links"]["self"]).json()
    if doc.get("status") != "completed":
        return {"status": "job_" + str(doc.get("status")), "analysis_id": doc.get("analysis_id")}
    obs = doc.get("earth_observation") or {}
    m = dict(obs.get("emit_masked") or {"status": "missing"})
    for v in (m.get("variants") or {}).values():
        for w in ("bd1000", "bd2000"):
            s = v.get(w) or {}
            s["detected"] = detected_from_stats(s.get("mean"), s.get("std"), s.get("median"),
                                                s.get("n_pixels") or 0, s.get("fraction_positive"))
    rock = (m.get("variants") or {}).get("rock") or {}
    m["detected"] = {w: (rock.get(w) or {}).get("detected") for w in ("bd1000", "bd2000")}
    m["legacy_endpoint"] = {i["name"]: i["value"]["mean"] for i in doc["mineralogy"].get("indicators", [])
                            if i["name"].startswith("legacy_")}
    m["s2_ndvi"] = (obs.get("values") or {}).get("ndvi")
    m.update(analysis_id=doc["analysis_id"], radius_km=radius_km,
             measured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
             endpoint=f"{base}/v1/reports/{doc['analysis_id']}")
    return m


def run_library(master: Path, base: str, radius: float) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SITES_FILE.exists():
        SITES_FILE.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                          "note": "Coordinates recovered from the legacy deposits_master.json; "
                                                  "precision graded from the decimals actually written.",
                                          "sites": recover_coordinates(master)}, ensure_ascii=False, indent=1))
    sites = json.loads(SITES_FILE.read_text())["sites"]
    res = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else {
        "name": "GEØ.IA EMIT library remeasurement (candidate, not used for scoring)",
        "status": "candidate", "radius_km": radius, "base_url": base, "results": {}}
    with httpx.Client(timeout=120) as c:
        for i, s in enumerate(sites, 1):
            if s["name"] in res["results"] or s.get("lat") is None:
                continue
            t = time.time()
            try:
                m = measure(c, base, s["lat"], s["lon"], radius)
            except Exception as exc:  # noqa: BLE001 - recorded per site
                m = {"status": "request_error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            res["results"][s["name"]] = m
            RESULTS_FILE.write_text(json.dumps(res, ensure_ascii=False, indent=1))
            print(f"[{i}/{len(sites)}] {s['name']}: {m.get('status')} ({time.time() - t:.0f} s)", flush=True)
            time.sleep(2)


def run_analogs(base: str) -> None:
    cat = json.loads(CATALOG.read_text())
    with httpx.Client(timeout=120) as c:
        for s in cat["sites"]:
            if s.get("emit") and s["emit"].get("status") == "ok":
                continue
            t = time.time()
            try:
                s["emit"] = measure(c, base, s["lat"], s["lon"], s.get("measurement_radius_km", 5))
            except Exception as exc:  # noqa: BLE001
                s["emit"] = {"status": "request_error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=1))
            print(f"{s['name']}: {s['emit'].get('status')} ({time.time() - t:.0f} s)", flush=True)
            time.sleep(2)


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if not sx or not sy else round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 3)


def compare() -> None:
    sites = {s["name"]: s for s in json.loads(SITES_FILE.read_text())["sites"]}
    res = json.loads(RESULTS_FILE.read_text())["results"]
    rows, stats = [], {"ok": 0, "no_rock_pixels": 0, "no_scenes": 0, "other": 0}
    pairs: dict[str, list] = {"ndvi_raw2": [], "ndvi_rock2": [], "veg_delta2": []}
    for name, m in res.items():
        s = sites[name]
        st = m.get("status")
        stats["ok" if st == "ok" else "no_rock_pixels" if st == "no_rock_pixels" else
              "no_scenes" if st == "unavailable" else "other"] += 1
        v = m.get("variants") or {}
        g = lambda var, w, k="mean": ((v.get(var) or {}).get(w) or {}).get(k)  # noqa: E731
        ndvi = (m.get("surface") or {}).get("ndvi_mean")
        if ndvi is not None and g("raw", "bd2000") is not None:
            pairs["ndvi_raw2"].append((ndvi, g("raw", "bd2000")))
        if ndvi is not None and g("rock", "bd2000") is not None:
            pairs["ndvi_rock2"].append((ndvi, g("rock", "bd2000")))
        if g("raw", "bd2000") is not None and g("rock", "bd2000") is not None:
            pairs["veg_delta2"].append(((m.get("surface") or {}).get("vegetated_fraction") or 0,
                                        g("raw", "bd2000") - g("rock", "bd2000")))
        rows.append((name, s.get("coordinate_quality"), st, s["old_library"]["raw_bd1000"], g("raw", "bd1000"),
                     g("rock", "bd1000"), s["old_library"]["raw_bd2000"], g("raw", "bd2000"), g("rock", "bd2000"),
                     (m.get("coverage") or {}).get("rock_fraction"), (m.get("surface") or {}).get("vegetated_fraction"),
                     (m.get("detected") or {}).get("bd1000"), (m.get("detected") or {}).get("bd2000"),
                     m.get("scene_count")))

    def f(x, n=3):
        return "—" if x is None else (f"{x:.{n}f}" if isinstance(x, float) else str(x))
    old_vs_raw = [(r[6], r[7]) for r in rows if r[6] is not None and r[7] is not None]
    lines = ["# Remedição da biblioteca EMIT — comparação", "",
             f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} a partir de "
             f"`{RESULTS_FILE.relative_to(ROOT)}`.", "",
             f"Sítios: {len(rows)} · com pixels de rocha: {stats['ok']} · sem pixels de rocha: "
             f"{stats['no_rock_pixels']} · sem cenas EMIT: {stats['no_scenes']} · outros: {stats['other']}", "",
             "## Efeito da vegetação em 2 µm", "",
             f"* Correlação NDVI (EMIT, composto de qualidade) × bd2000 bruto: "
             f"{f(_corr(*zip(*pairs['ndvi_raw2'])) if pairs['ndvi_raw2'] else None)} (n={len(pairs['ndvi_raw2'])})",
             f"* Correlação NDVI × bd2000 só rocha: "
             f"{f(_corr(*zip(*pairs['ndvi_rock2'])) if pairs['ndvi_rock2'] else None)} (n={len(pairs['ndvi_rock2'])})",
             f"* Correlação fração vegetada × (bd2000 bruto − rocha): "
             f"{f(_corr(*zip(*pairs['veg_delta2'])) if pairs['veg_delta2'] else None)} (n={len(pairs['veg_delta2'])})",
             f"* Mediana de (bd2000 bruto − rocha): "
             f"{f(statistics.median([d for _, d in pairs['veg_delta2']]) if pairs['veg_delta2'] else None)}",
             f"* Reprodutibilidade: mediana |bd2000 biblioteca antiga − bruto remedido| = "
             f"{f(statistics.median([abs(a - b) for a, b in old_vs_raw]) if old_vs_raw else None)} "
             f"(n={len(old_vs_raw)}; mesmo composto sem máscara, cenas possivelmente diferentes)", "",
             "## Por sítio", "",
             "| Sítio | Coord. | Status | bd1000 antigo | bruto | rocha | bd2000 antigo | bruto | rocha | "
             "fração rocha | fração vegetada | 1 µm detect. | 2 µm detect. | cenas |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(f(x) for x in r) + " |")
    COMPARE_FILE.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:14]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["library", "analogs", "compare"])
    ap.add_argument("master", nargs="?")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--radius", type=float, default=10.0)
    a = ap.parse_args()
    if a.mode == "library":
        run_library(Path(a.master), a.base, a.radius)
    elif a.mode == "analogs":
        run_analogs(a.base)
    else:
        compare()
