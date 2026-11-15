"""PDF report: follows the requested language and includes the lunar south-pole sections (offline fakes only)."""
import io

from pypdf import PdfReader

from app.services.reports import render_pdf
from tests.fakes import FakeWorld
from tests.integration.test_pipelines import _run


def _text(pdf: bytes) -> str:
    return " ".join(" ".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages).split())


def _polar_doc(base: dict) -> dict:
    """A synthetic south-pole style document: model-derived environment and an experimental geomorphology."""
    metric = {"value": 7.07, "uncertainty": 2.32, "unit": "deg", "n_windows": 9, "scale_m": 60.0}
    return {**base, "environment": {
        "status": "available", "reason": None, "kind": "model_derived", "method": "LOLA-derived average illumination",
        "sunlit_fraction": {"mean": 0.113, "p05": 0.036, "p95": 0.186}, "permanent_shadow_fraction": 0.028,
        "earth_visible_fraction": {"mean": 0.433, "p05": 0.276, "p95": 0.506},
        "centre": {"sunlit_fraction": 0.103, "permanent_shadow": 0.0, "earth_visible_fraction": 0.425},
        "analyzed_extent": {"radius_km": 3.0, "requested_radius_km": 5.0, "area_km2": 28.27, "pixel_size_m": 60.0},
        "products": ["AVGVISIB_85S_060M_201608", "LPSR_85S_060M_201608"], "limitations": [], "notes": []},
        "geomorphology": {
            "status": "available", "reason": None, "experimental": True, "method": "Terrain-unit profiles",
            "moon_profile": {"baseline_m": 60.0, "windows_valid": 9, "windows_total": 9, "samples": 1000,
                             "metrics": {"slope_median_deg": metric}},
            "comparisons": {
                "rover_mobility": {"label": "rover mobility (slopes and roughness resolved at baseline L)",
                                   "metrics": ["slope_median_deg"], "sites_compared": 10, "result": "correspondence",
                                   "matches": [{"name": "Test Site", "country": "Testland",
                                                "documented_lunar_analog": True}],
                                   "modified_relief_references": [{"name": "Mined Site"}]},
                "traverse_planning": {"label": "traverse and route-planning studies", "metrics": ["slope_p90_deg"],
                                      "sites_compared": 10, "result": "no_demonstrable_correspondence",
                                      "matches": []}},
            "notes": ["Experimental section: calculated geomorphological comparison. Its correspondences are not "
                      "validated or documented analogs and must not be read as recommendations."],
            "limitations": []}}


def test_english_pdf_has_no_portuguese_header():
    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45)
    t = _text(render_pdf(d, "en"))
    assert "ANALYSIS REPORT" in t and "Mars —" in t
    assert "RELATÓRIO" not in t and "Marte" not in t
    assert _text(render_pdf(d)) == t                       # English is the default


def test_portuguese_pdf_uses_portuguese_labels_and_localized_prose():
    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45)
    t = _text(render_pdf(d, "pt-BR"))
    assert "RELATÓRIO DE ANÁLISE" in t and "Marte —" in t
    assert "Estado das seções" in t and "Sítios análogos terrestres (geologia documentada)" in t
    assert "ANALYSIS REPORT" not in t
    assert "Section status" not in t


def test_unknown_language_falls_back_to_english():
    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45)
    assert "ANALYSIS REPORT" in _text(render_pdf(d, "xx"))


def test_polar_pdf_includes_environment_and_experimental_geomorphology():
    d = _polar_doc(_run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0))
    t = _text(render_pdf(d, "en"))
    i_env = t.find("Environment — illumination (model-derived)")
    i_geo = t.find("Moon–Earth geomorphology (experimental)", i_env)
    assert 0 <= i_env < i_geo
    assert "11.3%" in t and "2.8%" in t and "43.3%" in t     # sunlit mean, permanent shadow, Earth visible
    assert "Experimental section: calculated geomorphological comparison" in t
    assert "Calculated correspondences: Test Site (Testland) — documented lunar analog" in t
    assert "No demonstrable correspondence for this purpose." in t
    assert "Relief modified by mining (reference only, not a correspondence): Mined Site" in t
    pt = _text(render_pdf(d, "pt-BR"))
    assert "Ambiente — iluminação (derivada de modelo)" in pt and "Geomorfologia Lua–Terra (experimental)" in pt
    assert "Seção experimental" in pt                       # the note comes translated, as in the JSON


def test_pdf_without_polar_sections_still_renders():
    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45)
    t = _text(render_pdf({**d, "environment": None, "geomorphology": None}, "en"))
    assert "Environment — illumination" not in t and "geomorphology (experimental)" not in t
