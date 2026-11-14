"""Geomorphology section inside the real pipelines (synthetic ODE/GDS/M3 fakes, tests/fakes.py).
The section is additive: it never changes mineralogy, environment, terrestrial analogs or Mars."""

from app.schemas.analysis import AnalysisResult
from tests.fakes import FakeWorld
from tests.integration.test_pipelines import _run

KEYS = ("mineralogy", "terrestrial_analogs", "topography", "environment", "imagery")


def test_lunar_section_present_and_honest_with_sparse_altimetry():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    g = d["geomorphology"]
    assert g["status"] in ("available", "unavailable")
    if g["status"] == "unavailable":                                   # sparse fake LOLA: no confident result
        assert g["reason"] == "insufficient_data" and g["comparisons"] == {} and g["notes"]
    assert d["mineralogy"]["status"] == "available"                   # mineral pipeline untouched


def test_mineralogy_unavailable_does_not_block_geomorphology():
    d = _run("moon", FakeWorld(10.0, -15.0, m3=False), 10.0, -15.0)
    assert d["mineralogy"]["status"] != "available"
    assert d["geomorphology"]["status"] in ("available", "unavailable")
    assert d["geomorphology"]["reason"] != "not_attempted"            # altimetry was there, so it was tried


def test_lola_failure_gives_partial_response():
    d = _run("moon", FakeWorld(10.0, -15.0, gds_status=503), 10.0, -15.0)
    assert d["topography"]["status"] != "available"
    g = d["geomorphology"]
    assert g["status"] == "unavailable" and g["reason"] == "not_attempted" and g["moon_profile"] is None
    assert d["mineralogy"]["status"] == "available" and d["status"] in ("completed", "partial")


def test_small_radius_is_declared_not_estimated():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0, r=1.0)
    g = d["geomorphology"]
    assert g["status"] == "unavailable" and g["reason"] == "insufficient_data"
    assert any("at least 2 km" in n for n in g["notes"]) and g["comparisons"] == {}


def test_other_sections_identical_with_and_without_geomorphology(monkeypatch):
    from app.science import geomorph_analogs
    base = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    monkeypatch.setattr(geomorph_analogs, "section", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    crashed = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    assert crashed["geomorphology"]["status"] == "failed"
    for k in KEYS:
        a, b = dict(base[k] or {}), dict(crashed[k] or {})
        for x in (a, b):
            x.pop("retrieved_at", None)
        assert a == b, k
    assert any(p["section"] == "geomorphology" for p in crashed["problems"])


def test_mars_has_no_geomorphology_section():
    d = _run("mars", FakeWorld(-4.6, 137.4), -4.6, 137.4)
    assert d["geomorphology"] is None


def test_schema_backward_compatible():
    d = _run("mars", FakeWorld(-4.6, 137.4), -4.6, 137.4)
    d.pop("geomorphology")                                             # payload stored before this phase
    assert AnalysisResult.model_validate(d).geomorphology is None


def test_geomorphology_translated():
    from app import i18n
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0, r=1.0)
    pt = i18n.localize(d, "pt-BR")
    assert pt["geomorphology"]["notes"] != d["geomorphology"]["notes"]
