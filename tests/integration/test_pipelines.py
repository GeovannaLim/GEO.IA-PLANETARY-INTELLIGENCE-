"""Moon/Mars pipelines end-to-end against offline fakes (no network)."""
import uuid
from datetime import datetime, timezone

import pytest
import respx

from app.pipelines import lunar, mars
from app.providers.http import get_http
from app.schemas.analysis import AnalyzeRequest
from tests.conftest import run
from tests.fakes import FakeWorld


async def _noop(step):
    return None


def _run(body, world, lat, lon, r=3.0):
    mod = lunar if body == "moon" else mars

    async def go():
        with respx.mock(assert_all_called=False) as router:
            world.install(router)
            return await mod.run(AnalyzeRequest(latitude=lat, longitude=lon, radius_km=r), get_http(),
                                 uuid.uuid4().hex, datetime.now(timezone.utc), _noop)
    return run(go()).model_dump(mode="json")


def test_lunar_full_pipeline_with_m3():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    assert d["status"] == "completed"
    assert d["imagery"]["status"] == "available" and len(d["imagery"]["layers"]) == 2
    t = d["topography"]
    assert t["status"] == "available" and t["n_points"] > 100
    assert t["regional_slope_degrees"] == pytest.approx(2.0, abs=0.2)
    m = d["mineralogy"]
    assert m["status"] == "available" and m["product_used"] == "M3GFAKE_V01_RFL"
    assert m["valid_pixels"] > 25 and m["pixel_distance_m"] < 500
    names = {i["name"] for i in m["indicators"]}
    assert {"IBD1000", "IBD2000", "legacy_bd1000", "legacy_bd2000"} <= names
    assert "pyroxene" in m["spectral_character"]
    assert d["earth_analogs"]["status"] == "available"
    assert d["earth_analogs"]["directly_comparable"] == ["legacy_bd1000", "legacy_bd2000"]
    # every section's source ids resolve to data_sources
    ids = {s["source_id"] for s in d["data_sources"]}
    for sec in ("topography", "mineralogy", "imagery"):
        assert set(d[sec]["source_ids"]) <= ids and d[sec]["source_ids"]
    assert d["coordinates"]["longitude_east_360"] == pytest.approx(345.0)


@pytest.mark.parametrize("lat,lon", [(0.0, 0.01), (0.2, 179.99), (-89.95, 45.0), (89.95, -120.0)])
def test_lunar_equator_antimeridian_and_poles(lat, lon):
    world = FakeWorld(lat, lon)
    d = _run("moon", world, lat, lon, r=2.0)
    assert d["status"] == "completed"
    assert d["topography"]["status"] in ("available", "partial")
    for b in world.gds_boxes:   # every GDS request is a valid, non-wrapping east_360 box
        assert 0 <= b["westernlon"] <= b["easternlon"] <= 360 and -90 <= b["minlat"] <= b["maxlat"] <= 90
    if abs(lat) < 1:
        assert d["mineralogy"]["status"] in ("available", "partial")


def test_lunar_without_m3_coverage_keeps_topography():
    d = _run("moon", FakeWorld(10.0, -15.0, m3=False), 10.0, -15.0)
    assert d["mineralogy"]["status"] == "unavailable" and d["mineralogy"]["reason"] == "no_coverage"
    assert d["mineralogy"]["indicators"] == []
    assert d["topography"]["status"] == "available"
    assert d["earth_analogs"]["status"] == "unavailable" and d["earth_analogs"]["matches"] == []
    assert any(p["reason"] == "no_coverage" and p["section"] == "mineralogy" for p in d["problems"])


def test_temporary_provider_failures_are_isolated():
    d = _run("moon", FakeWorld(10.0, -15.0, gds_status=503, trek_status=502), 10.0, -15.0)
    assert d["topography"]["status"] == "failed" and d["topography"]["reason"] == "provider_error"
    assert d["topography"]["elevation_m"] is None
    assert d["imagery"]["status"] == "failed"
    assert d["mineralogy"]["status"] == "available"          # independent step still delivered
    reasons = {(p["section"], p["reason"]) for p in d["problems"]}
    assert ("topography", "provider_error") in reasons and ("imagery", "provider_error") in reasons


def test_empty_pds_is_not_reported_as_no_coverage():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    pds = [s for s in d["data_sources"] if s["provider"] == "NASA PDS"]
    assert pds and all(s["status"] == "empty" for s in pds)
    assert all("ODE results are authoritative" in s["message"] for s in pds)
    assert d["mineralogy"]["status"] == "available"


def test_gds_without_shots_is_no_coverage():
    d = _run("moon", FakeWorld(10.0, -15.0, gds_empty=True), 10.0, -15.0)
    assert d["topography"]["status"] == "unavailable" and d["topography"]["reason"] == "no_coverage"


def test_mars_full_pipeline_with_crism():
    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45, r=0.5)
    assert d["topography"]["status"] in ("available", "partial")
    assert "MOLA" in d["topography"]["method"] and "areoid" in d["topography"]["datum"]
    m = d["mineralogy"]
    assert m["status"] == "available" and "CRISM" in m["instrument"]
    ol = next(i for i in m["indicators"] if i["name"] == "OLINDEX3")
    assert ol["value"]["median"] == pytest.approx(0.08, abs=0.005) and "Positive" in ol["interpretation"]
    lcp = next(i for i in m["indicators"] if i["name"] == "LCPINDEX2")
    assert "No statistically significant" in lcp["interpretation"]
    # lunar-specific indices are never applied to Mars
    assert not {"IBD1000", "IBD2000", "R750"} & {i["name"] for i in m["indicators"]}
    assert d["earth_analogs"]["status"] == "available"


def test_mars_without_crism_distinguishes_no_coverage():
    d = _run("mars", FakeWorld(-85.0, 150.0, crism=False), -85.0, 150.0, r=5)
    assert d["mineralogy"]["status"] == "unavailable" and d["mineralogy"]["reason"] == "no_coverage"


def test_ode_outage_marks_mineralogy_failed_not_absent():
    d = _run("mars", FakeWorld(18.44, 77.45, ode_status=503), 18.44, 77.45, r=0.5)
    assert d["mineralogy"]["status"] == "failed" and d["mineralogy"]["reason"] == "provider_error"


@pytest.mark.parametrize("body,lat,lon", [("moon", 10.0, -15.0), ("mars", 18.44, 77.45)])
def test_slow_gds_fails_only_topography_within_deadline(monkeypatch, body, lat, lon):
    """A hanging ODE GDS must not time out the whole job (seen in production, 2026-11-11)."""
    import asyncio
    import time

    from app.config import get_settings
    from app.providers import ode

    monkeypatch.setenv("GEOIA_ALTIMETRY_DEADLINE_S", "0.3")
    get_settings.cache_clear()

    async def hang(*a, **k):
        await asyncio.sleep(30)
    monkeypatch.setattr(ode, "query_altimetry", hang)
    t0 = time.time()
    d = _run(body, FakeWorld(lat, lon), lat, lon)
    assert time.time() - t0 < 10
    assert d["topography"]["status"] == "failed" and d["topography"]["elevation_m"] is None
    msgs = [p["message"] for p in d["problems"] if p["section"] == "topography"]
    assert msgs and "did not return" in msgs[0] and "other sections unaffected" in msgs[0]
    assert d["mineralogy"]["status"] in ("available", "partial")   # delivered despite the slow GDS
    assert d["terrestrial_analogs"] is not None
    assert d["confidence"]["level"] != "high"                      # no altimetry: never 'high'
    assert d["terrestrial_analogs"] is not None


def test_pdf_lists_analog_sites_before_the_illustrative_spectral_appendix():
    import io

    from pypdf import PdfReader

    from app.services.reports import render_pdf

    d = _run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45)
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(render_pdf(d))).pages)
    text = " ".join(text.split())
    i_sites = text.find("Terrestrial analog sites (documented geology)")
    i_appx = text.find("Appendix — illustrative spectral comparison")
    assert 0 <= i_sites < i_appx
    assert "Earth analogs" not in text
    earth = {**d, "terrestrial_analogs": None}            # Earth / old records have no analog-site section
    assert render_pdf(earth)[:5] == b"%PDF-"


def test_mars_unlit_observation_gives_no_mineralogy():
    d = _run("mars", FakeWorld(18.44, 77.45, crism_incidence="88"), 18.44, 77.45)
    assert d["mineralogy"]["status"] == "unavailable" and d["mineralogy"]["reason"] == "insufficient_data"
    assert d["mineralogy"]["indicators"] == []
    assert any("incidence 88.0" in p["message"] for p in d["problems"])
    ta = d["terrestrial_analogs"] or {}
    # no regional measurement -> only the explicitly labelled global context, never regional evidence
    assert ta.get("region_evidence") in (None, []) or ta.get("basis") == "global_context"
    assert not ta.get("sites") or (ta["basis"] == "global_context" and ta["notes"])


def test_moon_unlit_pixel_gives_no_mineralogy(monkeypatch):
    from app.providers import m3
    real = m3.extract

    async def dark(*a, **k):
        ex = await real(*a, **k)
        ex.incidence_deg = 91.5                    # sun below the horizon, as at the lunar south pole test
        return ex
    monkeypatch.setattr(m3, "extract", dark)
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    assert d["mineralogy"]["status"] == "unavailable" and d["mineralogy"]["indicators"] == []
    assert d["topography"]["status"] == "available"          # other sections unaffected
    assert not (d["terrestrial_analogs"] or {}).get("sites")
