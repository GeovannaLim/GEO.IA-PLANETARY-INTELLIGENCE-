"""Guards against fabricated or recycled scientific values."""
import json
import re
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.reports import render_pdf

APP_DIR = Path(__file__).resolve().parents[2] / "app"
# The legacy Mare Imbrium M3 vector that the old pipeline returned for ANY coordinate.
IMBRIUM = ["0.4384", "0.7307", "0.1077", "0.4209", "0.5483", "M3G20090418T132620"]


def test_application_code_has_no_legacy_lunar_data_or_fixed_vectors():
    files = list(APP_DIR.rglob("*.py")) + list(APP_DIR.rglob("*.json"))
    blob = "\n".join(p.read_text(encoding="utf-8") for p in files)
    for token in IMBRIUM + ["lunar_earth_similarity_result", "lunar_intelligence_result", "Mare Imbrium"]:
        assert token not in blob, token
    assert not re.search(r"import\s+tests|from\s+tests", blob)  # test fakes never reach the app


def _all_numbers(doc, path=""):
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from _all_numbers(v, f"{path}.{k}")
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _all_numbers(v, f"{path}[{i}]")
    elif isinstance(doc, (int, float)) and not isinstance(doc, bool):
        yield path, doc


def test_total_outage_returns_no_scientific_numbers():
    with respx.mock(assert_all_called=False) as r:
        r.route(host="testserver").pass_through()
        r.route().mock(return_value=httpx.Response(503))
        with TestClient(create_app()) as c:
            for ep, body in (("/v1/lunar/analyze", {"latitude": 35, "longitude": -15, "radius_km": 5}),
                             ("/v1/mars/analyze", {"latitude": 18.44, "longitude": 77.45, "radius_km": 5})):
                d = c.post(ep + "?wait_s=30", json=body).json()
                assert d["status"] == "completed"
                for sec in ("imagery", "topography", "mineralogy"):
                    assert d[sec]["status"] == "failed", (ep, sec, d[sec])
                assert d["earth_analogs"]["matches"] == []
                assert d["confidence"]["level"] == "not_assessed"
                allowed = (".coordinates.", ".radius_km", ".query.")  # request echo + provenance of queries
                science = [(p, v) for p, v in _all_numbers(d) if not any(a in p for a in allowed)]
                assert science == [], science
                assert render_pdf(d)[:5] == b"%PDF-"
                assert all(p["reason"] == "provider_error" for p in d["problems"])


def test_reference_library_contains_only_measured_emit_fields():
    lib = json.loads((APP_DIR / "data" / "earth_emit_reference_library.json").read_text())
    allowed = {"name", "country", "setting", "legacy_bd1000", "legacy_bd2000", "raw_bd1000", "raw_bd2000",
               "emit_scene_count"}
    for e in lib["entries"]:
        assert set(e) <= allowed
