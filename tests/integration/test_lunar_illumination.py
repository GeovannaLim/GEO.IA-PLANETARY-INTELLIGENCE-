"""Moon south polar illumination section (LOLA-derived maps, Mazarico et al. 2011) against a synthetic
archive. Real-data checks (Shackleton interior, Mons Malapert, Haworth) are in
docs/DIAGNOSTICO_ANALOGOS_LUNARES_POLARES.md and the step-1 report."""

import numpy as np
import pytest

from app.providers import lola_illumination as L
from tests.fakes import FakeWorld
from tests.integration.test_pipelines import _run


def test_projection_round_trip_and_pole_position():
    g = L.Grid(name="t", lines=5058, samples=5058, record_bytes=10116, scale_m=60.0, line_offset=2528.5,
               sample_offset=2528.5, radius_m=1737400.0, factor=1.0, offset=0.0)
    r, c = L.to_pixel(g, -90.0, 0.0)
    assert r == pytest.approx(2527.5) and c == pytest.approx(2527.5)       # 1-based offset -> 0-based
    for lat, lon in ((-89.63, 132.32), (-85.98, 358.33), (-86.8, 356.0)):
        r, c = L.to_pixel(g, lat, lon)
        la, lo = L.window_latlon(g, np.array([r]), np.array([c]))
        assert la[0] == pytest.approx(lat, abs=1e-6) and lo[0] == pytest.approx(lon % 360, abs=1e-5)


def test_label_parser_accepts_south_and_rejects_others():
    from tests.fakes import illum_label
    g = L.parse_label(illum_label("X", 0.00004, 0.0), "X")
    assert g.lines == 600 and g.scale_m == 60.0 and g.radius_m == 1737400.0
    with pytest.raises(Exception):
        L.parse_label(illum_label("X", 0.00004, 0.0).replace("-90 <deg>", "90 <deg>"), "X")


def test_shadowed_point_reports_permanent_shadow_as_model_context():
    d = _run("moon", FakeWorld(-89.9, 45.0), -89.9, 45.0, r=1.0)
    env = d["environment"]
    assert env["status"] == "available" and env["kind"] == "model_derived"
    assert env["centre"]["permanent_shadow"] == pytest.approx(1.0)
    assert env["centre"]["sunlit_fraction"] == pytest.approx(0.0)
    assert env["permanent_shadow_fraction"] > 0.5
    assert any("permanently shadowed" in n and "Ice is not measured" in n for n in env["notes"])
    assert env["products"] == ["AVGVISIB_85S_060M_201608", "LPSR_85S_060M_201608", "AVGVISIB_85S_060M_201608_EARTH"]
    src = next(s for s in d["data_sources"] if s["source_id"] in env["source_ids"])
    assert "Mazarico" in src["product_type"] and src["spatial_resolution_m"] == 60.0



def test_environment_section_never_ranks_analogs_on_a_sunlit_point():
    """On a point with no permanent shadow, analog sites are identical with or without the illumination
    archive: the environment section is context only (the shadow map only invalidates shadowed M3 pixels)."""
    ids = lambda doc: [(s["id"], s["rank"]) for s in (doc["terrestrial_analogs"] or {}).get("sites") or []]
    lit = _run("moon", FakeWorld(-89.9, -135.0), -89.9, -135.0, r=1.0)
    lit_down = _run("moon", FakeWorld(-89.9, -135.0, illum_status=503), -89.9, -135.0, r=1.0)
    assert lit["environment"]["permanent_shadow_fraction"] == 0.0
    assert ids(lit) == ids(lit_down)
    assert lit["mineralogy"]["valid_pixels"] == lit_down["mineralogy"]["valid_pixels"]


def test_sunlit_point_reports_numbers_without_shadow():
    d = _run("moon", FakeWorld(-89.9, -135.0), -89.9, -135.0, r=1.0)
    env = d["environment"]
    assert env["sunlit_fraction"]["median"] == pytest.approx(0.30, abs=1e-3)
    assert env["earth_visible_fraction"]["median"] == pytest.approx(0.50, abs=1e-3)
    assert env["permanent_shadow_fraction"] == 0.0 and env["notes"] == []


def test_window_is_bounded_and_declared():
    d = _run("moon", FakeWorld(-89.9, -135.0), -89.9, -135.0, r=10.0)
    ext = d["environment"]["analyzed_extent"]
    assert ext["radius_km"] == L.MAX_HALF_WINDOW_KM and ext["requested_radius_km"] == 10.0
    assert any("not the whole requested" in x for x in d["environment"]["limitations"])


def test_non_polar_moon_is_not_applicable_and_makes_no_request():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    env = d["environment"]
    assert env["status"] == "unavailable" and env["reason"] == "not_supported"
    assert env["sunlit_fraction"] is None and env["source_ids"] == []
    assert d["mineralogy"]["status"] == "available"                    # rest of the analysis unchanged


def test_archive_outage_fails_only_this_section_with_no_numbers():
    d = _run("moon", FakeWorld(-89.9, -135.0, illum_status=503), -89.9, -135.0, r=1.0)
    env = d["environment"]
    assert env["status"] == "failed" and env["reason"] == "provider_error"
    assert env["sunlit_fraction"] is None and env["permanent_shadow_fraction"] is None
    assert d["topography"]["status"] == "available"
    assert any(p["section"] == "environment" for p in d["problems"])


def test_mars_has_no_environment_section():
    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45)
    assert d.get("environment") is None


def test_environment_prose_is_translated_to_pt_br():
    from app import i18n
    d = _run("moon", FakeWorld(-89.9, 45.0), -89.9, 45.0, r=10.0)
    env = i18n.localize(d, "pt-BR")["environment"]
    assert env["method"].startswith("Iluminação média derivada do LOLA")
    assert all("Model product" not in x and "Long-term" not in x for x in env["limitations"])
    assert any("sombra permanente no modelo" in n for n in env["notes"])
    assert env["sunlit_fraction"] == d["environment"]["sunlit_fraction"]      # numbers untouched


def test_tiny_shadow_fraction_is_not_shown_as_zero_percent():
    from app import i18n
    t = i18n.translate("<1% of the analysed area is permanently shadowed in the model (never sunlit): a potential "
                       "cold trap. Ice is not measured by this section.")
    assert t.startswith("<1% da área analisada")
