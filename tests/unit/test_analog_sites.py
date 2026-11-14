"""Terrestrial analog-site matching: geological basis, no fabrication, language rebuild."""

import json

import pytest

from app import i18n
from app.schemas.analysis import MineralogySection, SectionStatus, SpectralIndicator, Stats
from app.science import analog_sites

REAL_CATALOG = analog_sites.CATALOG_PATH      # captured before the autouse fixture swaps it

FAKE = {
    "name": "test catalog", "version": "0",
    "sites": [
        {"id": "basalt_a", "name": "Basalt A", "country": "X", "lat": 1.0, "lon": 2.0,
         "coordinate_source": "test", "coordinate_precision_km": 0.5, "verification": "verified",
         "setting_en": "flood basalt", "setting_pt": "basalto de derrame", "key_minerals": ["augite"],
         "analog_for": [{"body": "moon", "classes": ["pyroxene_basalt"], "rationale_en": "mare-like basalt",
                         "rationale_pt": "basalto semelhante ao de mare", "reference_ids": ["r1"]},
                        {"body": "mars", "classes": ["pyroxene_basalt"], "rationale_en": "basaltic crust",
                         "rationale_pt": "crosta basáltica", "reference_ids": ["r1"]}],
         "references": [{"id": "r1", "citation": "Ref 1", "doi": "10.0/x"}],
         "differences_en": ["vegetated margins"], "differences_pt": ["bordas vegetadas"],
         "limitations_en": [], "limitations_pt": [],
         "emit": {"status": "ok", "scene_count": 12, "scenes": [{"date": "2023-01-02"}, {"date": "2024-05-06"}],
                  "coverage": {"rock_fraction": 0.8}, "variants": {"rock": {"bd1000": {"n_pixels": 5000}}},
                  "detected": {"bd1000": True, "bd2000": False}, "analysis_id": "a1"}},
        {"id": "anorth", "name": "Anorthosite B", "country": "Y", "lat": -3.0, "lon": 4.0,
         "coordinate_source": "test", "coordinate_precision_km": 1.0, "verification": "verified",
         "setting_en": "anorthosite massif", "setting_pt": "maciço anortosítico", "key_minerals": ["plagioclase"],
         "analog_for": [{"body": "moon", "classes": ["anorthosite"], "rationale_en": "plagioclase-rich",
                         "rationale_pt": "rico em plagioclásio", "reference_ids": []}],
         "references": [], "emit": None},
        {"id": "carb", "name": "Carbonate C", "country": "Z", "lat": 5.0, "lon": 6.0,
         "coordinate_source": "test", "coordinate_precision_km": 0.1, "verification": "verified",
         "setting_en": "ophiolite", "setting_pt": "ofiolito", "key_minerals": ["magnesite"],
         "analog_for": [{"body": "mars", "classes": ["carbonate", "fe_mg_phyllosilicate"],
                         "rationale_en": "carbonated peridotite", "rationale_pt": "peridotito carbonatado",
                         "reference_ids": []}],
         "references": [],
         "emit": {"status": "ok", "scene_count": 3, "scenes": [], "coverage": {"rock_fraction": 0.05},
                  "variants": {"rock": {"bd1000": {"n_pixels": 90}}}, "detected": {"bd1000": True, "bd2000": True}}},
    ]}


@pytest.fixture(autouse=True)
def fake_catalog(monkeypatch, tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps(FAKE))
    monkeypatch.setattr(analog_sites, "CATALOG_PATH", p)
    analog_sites.catalog.cache_clear()
    yield
    analog_sites.catalog.cache_clear()


def ind(name, det):
    return SpectralIndicator(name=name, value=Stats(mean=0.1), definition="d", reference="r", n_pixels=100,
                             interpretation="i", detected=det)


def section(*inds, status=SectionStatus.available):
    return MineralogySection(status=status, indicators=list(inds))


def test_lunar_pyroxene_region_gets_basalt_with_emit_comparison():
    s = analog_sites.match("moon", section(ind("IBD1000", True), ind("IBD2000", True),
                                           ind("legacy_bd1000", True), ind("legacy_bd2000", True)))
    assert s.status == SectionStatus.available and s.basis == "regional_spectral_evidence"
    assert [x.id for x in s.sites] == ["basalt_a"]
    site = s.sites[0]
    assert site.latitude == 1.0 and site.references[0]["doi"] == "10.0/x"
    assert any("1 µm band presence agrees" in t for t in site.similarities)
    assert any("2 µm band presence differs" in t for t in site.differences)
    assert "probab" not in json.dumps(s.model_dump()).lower().replace("or a probability", "")


def test_lunar_no_band_is_inconclusive_not_anorthosite():
    """Absence of mafic bands alone must not select anorthosite sites (2026-11-14 correction: shadowed /
    dark M3 windows lack bands too)."""
    s = analog_sites.match("moon", section(ind("IBD1000", False), ind("IBD2000", False)))
    assert s.sites == [] and s.region_evidence == []
    assert s.inconclusive_evidence == ["lunar_no_mafic_band"]
    assert s.status == SectionStatus.unavailable and s.reason.value == "insufficient_data"
    assert any("not evidence of anorthosite" in n for n in s.notes)
    pt = i18n.localize({"status": "completed", "links": {}, "terrestrial_analogs": s.model_dump(mode="json")},
                       "pt-BR")["terrestrial_analogs"]
    assert any("não é evidência de anortosito" in n for n in pt["notes"])


def test_mars_specific_class_and_low_emit_coverage_is_not_used():
    s = analog_sites.match("mars", section(ind("MIN2295_2480", True), ind("BD1900_2", True)))
    assert [e["class"] for e in s.region_evidence] == ["carbonate"]        # hydrated subsumed by carbonate
    assert s.sites[0].id == "carb"
    assert any("not used" in t for t in s.sites[0].differences)
    assert not any("agrees" in t for t in s.sites[0].similarities)


def test_mars_without_crism_is_global_context_partial():
    from app.schemas.analysis import Reason
    failed = analog_sites.match("mars", MineralogySection(status=SectionStatus.failed, reason=Reason.provider_error))
    assert failed.sites == [] and failed.basis is None
    s = analog_sites.match("mars", MineralogySection(status=SectionStatus.unavailable, reason=Reason.no_coverage))
    assert s.basis == "global_context" and s.status == SectionStatus.partial
    assert s.notes and "NOT specific" in s.notes[0]
    assert all(v is None for v in s.sites[0].region_bands.values())
    polar = analog_sites.match("mars", MineralogySection(status=SectionStatus.unavailable, reason=Reason.no_coverage),
                               latitude=-85.0)
    assert polar.sites == [] and polar.basis is None


def test_unexplained_evidence_is_reported_not_filled():
    s = analog_sites.match("mars", section(ind("BD2100_2", True)))
    assert s.sites == [] and s.unexplained_evidence == ["sulfate"]
    assert s.status == SectionStatus.unavailable and "sulfates" in s.notes[0]


def test_no_lunar_measurement_gives_nothing():
    s = analog_sites.match("moon", MineralogySection(status=SectionStatus.unavailable))
    assert s.status == SectionStatus.unavailable and s.sites == []


def test_pt_br_rebuilds_prose_and_keeps_structure():
    s = analog_sites.match("moon", section(ind("IBD1000", True), ind("IBD2000", True),
                                           ind("legacy_bd1000", True), ind("legacy_bd2000", True)))
    doc = {"status": "completed", "links": {}, "terrestrial_analogs": s.model_dump(mode="json")}
    pt = i18n.localize(doc, "pt-BR")["terrestrial_analogs"]
    site = pt["sites"][0]
    assert site["setting"] == "basalto de derrame"
    assert any("coincide" in t for t in site["similarities"])
    assert "basalto semelhante ao de mare" in site["justification"]
    assert site["latitude"] == 1.0 and site["matched_classes"] == ["lunar_pyroxene"]
    assert pt["disclaimer"].startswith("Análogos terrestres")
    assert doc["terrestrial_analogs"]["sites"][0]["setting"] == "flood basalt"   # original untouched


def test_earth_pipeline_records_masked_emit_without_substitution(monkeypatch):
    """Earth pipeline with a stand-in for Earth Engine: masked EMIT stats become rock_* indicators
    with detection, the full provenance record is kept, missing values stay missing."""
    import asyncio
    import uuid
    from datetime import datetime, timezone

    from app.pipelines import earth
    from app.providers import earth_engine as gee
    from app.schemas.analysis import AnalyzeRequest

    masked = {"status": "ok", "scene_count": 2, "scale_m": 60, "mask_rules": gee.MASK_RULES,
              "scenes": [{"id": "EMIT_A", "date": "2023-03-01", "solar_zenith": "30"},
                         {"id": "EMIT_B", "date": "2024-02-01", "solar_zenith": "35"}],
              "band_wavelengths_nm": {"b1000": 1000.1},
              "variants": {"raw": {"bd1000": {"mean": 0.02, "std": 0.01, "median": 0.02, "n_pixels": 9000,
                                              "fraction_positive": 0.9},
                                   "bd2000": {"mean": 0.3, "std": 0.1, "median": 0.3, "n_pixels": 9000,
                                              "fraction_positive": 1.0}},
                           "quality": {}, "rock": {"bd1000": {"mean": 0.03, "std": 0.01, "median": 0.03,
                                                              "n_pixels": 4000, "fraction_positive": 0.95},
                                                   "bd2000": {"mean": None, "std": None, "median": None,
                                                              "n_pixels": 0, "fraction_positive": None}}},
              "coverage": {"roi_pixels": 9000, "rock_fraction": 0.44}}
    fake = {"core": {"ndvi": 0.1}, "topography": {"elev_mean": 100.0}, "counts": {"s2_images": 3},
            "emit": {"status": "ok", "scene_count": 2, "hyp_bd_1000": 0.02, "hyp_bd_2000": 0.3},
            "emit_masked": masked}
    monkeypatch.setattr(gee, "initialize", lambda: {"initialized": True})
    monkeypatch.setattr(gee, "extract", lambda lat, lon, r: fake)

    async def noop(_):
        return None
    res = asyncio.run(earth.run(AnalyzeRequest(latitude=-24.27, longitude=-69.07, radius_km=5), None,
                                uuid.uuid4().hex, datetime.now(timezone.utc), noop))
    d = res.model_dump(mode="json")
    names = {i["name"]: i for i in d["mineralogy"]["indicators"]}
    assert names["rock_bd1000"]["detected"] is True and names["rock_bd1000"]["n_pixels"] == 4000
    assert "rock_bd2000" not in names                              # no rock pixels -> absent, not zero
    assert d["earth_observation"]["emit_masked"]["scenes"][1]["id"] == "EMIT_B"
    src = {s["source_id"]: s for s in d["data_sources"]}
    assert src[d["earth_observation"]["emit_masked_source_id"]]["status"] == "ok"
    pt = i18n.localize(d, "pt-BR")
    assert {i["name"]: i for i in pt["mineralogy"]["indicators"]}["rock_bd1000"]["interpretation"] == \
        "Absorção positiva detectada."
    assert d["terrestrial_analogs"] is None


def test_real_catalog_countries_and_minerals_have_pt_br_names():
    cat = json.loads(REAL_CATALOG.read_text(encoding="utf-8"))
    for site in cat["sites"]:
        assert site["country"] in analog_sites.COUNTRY_PT, site["country"]
        for k in site["key_minerals"]:
            assert k in analog_sites.MINERAL_PT, k


def test_pt_br_translates_country_and_minerals_from_catalog_only(monkeypatch):
    monkeypatch.setattr(analog_sites, "CATALOG_PATH", REAL_CATALOG)
    analog_sites.catalog.cache_clear()
    real = json.loads(REAL_CATALOG.read_text(encoding="utf-8"))
    samail = next(s for s in real["sites"] if s["country"] == "Oman")
    section = {"body": "mars", "basis": "regional_spectral_evidence", "region_evidence": [], "notes": [],
               "unexplained_evidence": [], "disclaimer": "x",
               "sites": [{"id": samail["id"], "name": samail["name"], "country": "Oman",
                          "key_minerals": list(samail["key_minerals"]), "matched_classes": [],
                          "region_bands": {}, "emit": None}]}
    out = analog_sites.localize(section, "pt-BR")["sites"][0]
    assert out["country"] == "Omã" and out["name"] == samail["name"]
    assert out["key_minerals"] == [analog_sites.MINERAL_PT[k] for k in samail["key_minerals"]]
    again = analog_sites.localize(section, "pt-BR")["sites"][0]     # idempotent
    assert again["country"] == "Omã"
