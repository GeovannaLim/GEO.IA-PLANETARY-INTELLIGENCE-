"""External M3/PDS failures must never be read as a scientific result (final integration, 2026-11-14).
* a slow PDS fails ONLY the mineralogy section (provider_error, explicit 'not evidence of absence'), the job still
  completes with every other section;
* when the preferred M3 observation cannot be read and another one is used, the response says so (provenance)."""
import asyncio
import dataclasses

from app import i18n
from app.config import Settings
from app.pipelines import lunar
from app.providers import m3
from app.providers.http import ProviderError
from tests.fakes import FakeWorld
from tests.integration.test_pipelines import _run

OTHER = ("topography", "environment", "imagery", "geomorphology")


def _strip(sec):
    sec = dict(sec or {})
    sec.pop("retrieved_at", None)
    return sec


def test_m3_timeout_fails_only_mineralogy_and_is_not_an_absence(monkeypatch):
    base = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)

    async def hang(*a, **k):
        await asyncio.sleep(30)

    monkeypatch.setattr(lunar, "get_settings", lambda: Settings(mineralogy_deadline_s=0.3))
    monkeypatch.setattr(m3, "extract", hang)
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    assert d["status"] == "completed"                                  # the job is not lost
    mn = d["mineralogy"]
    assert mn["status"] == "failed" and mn["reason"] == "provider_error"
    assert mn["indicators"] == [] and mn["product_used"] is None        # nothing measured, nothing invented
    assert any("not evidence that minerals are absent" in x for x in mn["limitations"])
    assert any(p["section"] == "mineralogy" and p["reason"] == "provider_error" for p in d["problems"])
    ta = d["terrestrial_analogs"]
    assert ta["status"] != "available" and not ta.get("sites")           # no analog from a missing measurement
    for k in OTHER:                                                      # everything else delivered, unchanged
        assert _strip(d[k]) == _strip(base[k]), k
    pt = i18n.localize(d, "pt-BR")
    assert any("não é evidência de ausência de minerais" in x for x in pt["mineralogy"]["limitations"])


def test_fallback_to_another_m3_observation_is_declared(monkeypatch):
    real_rank, real_extract = lunar._rank, m3.extract

    def rank_with_preferred(products, lat, lon):
        out = real_rank(products, lat, lon)
        p, inside = out[0]
        return [(dataclasses.replace(p, pdsid="M3GPREFERRED_V01_RFL"), True)] + out

    async def extract(http, prod, *a, **k):
        if prod.pdsid == "M3GPREFERRED_V01_RFL":
            raise ProviderError("PDS Imaging (M3)", "ReadTimeout")
        return await real_extract(http, prod, *a, **k)

    monkeypatch.setattr(lunar, "_rank", rank_with_preferred)
    monkeypatch.setattr(m3, "extract", extract)
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    mn = d["mineralogy"]
    assert mn["status"] == "available" and mn["product_used"] != "M3GPREFERRED_V01_RFL"
    assert any("Preferred M3 observation(s) could not be used: M3GPREFERRED_V01_RFL (provider_error)" in x
               and mn["product_used"] in x for x in mn["limitations"])
    assert any(p["message"].startswith("M3GPREFERRED_V01_RFL skipped:") for p in d["problems"])
    pt = i18n.localize(d, "pt-BR")
    assert any("não pôde(puderam) ser usada(s)" in x for x in pt["mineralogy"]["limitations"])


def test_geomorphology_is_flagged_experimental():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    assert d["geomorphology"]["experimental"] is True
