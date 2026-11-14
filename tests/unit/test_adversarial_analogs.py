"""Adversarial regression tests: conditions under which the analog engine could reach a scientifically
wrong conclusion (see scripts/adversarial_analogs.py and docs/RELATORIO_TESTES_CIENTIFICOS.md)."""

import copy
import random

import numpy as np

from app.schemas.analysis import MineralogySection, SectionStatus, SpectralIndicator, Stats
from app.science import analog_sites, spectral

# Window medians measured on a real dust-mantled observation (frt00007c91, Olympus Mons flank).
DUST = {"OLINDEX3": 0.0434, "BDI1000IR": 0.0223, "LCPINDEX2": -0.0073, "HCPINDEX2": -0.0158,
        "D2300": -0.0047, "BD2210_2": 0.0009, "MIN2295_2480": -0.0158, "MIN2345_2537": -0.0058,
        "BD2100_2": 0.0003, "SINDEX2": 0.0058, "BD1900_2": -0.0023, "BD530_2": 0.2629,
        "BD1435": 0.0047, "BD1500_2": -0.007}


def _section(medians: dict, noise: float = 0.002, n: int = 3721, seed: int = 1) -> MineralogySection:
    rng = np.random.default_rng(seed)
    inds = [spectral.crism_indicator(k, v + rng.normal(0, noise, n)) for k, v in medians.items()]
    return MineralogySection(status=SectionStatus.available, indicators=inds)


def test_dust_does_not_produce_mineral_families_or_mineral_analogs():
    out = analog_sites.match("mars", _section(DUST), latitude=17.3)
    fams = {e["class"] for e in out.region_evidence}
    assert fams == {"ferric_oxide"}                       # dust is genuinely ferric; nothing else
    assert not ({"olivine", "sulfate", "al_phyllosilicate_silica", "ice", "mafic"} & fams)
    for s in out.sites:
        assert s.matched_classes == ["ferric_oxide"]


def test_documented_olivine_and_clays_still_detected():
    jezero_like = {**DUST, "OLINDEX3": 0.0708, "D2300": 0.0185, "BD530_2": 0.16}
    fams = {e["class"] for e in analog_sites.match("mars", _section(jezero_like), latitude=18.4).region_evidence}
    assert {"olivine", "fe_mg_phyllosilicate"} <= fams


def test_ranking_does_not_depend_on_catalog_file_order():
    sec = _section({**DUST, "OLINDEX3": 0.07, "D2300": 0.02, "SINDEX2": 0.05})
    base = [s.id for s in analog_sites.match("mars", sec, latitude=18.4).sites]
    original = analog_sites.catalog
    for seed in range(10):
        cat = copy.deepcopy(original())
        random.Random(seed).shuffle(cat["sites"])
        analog_sites.catalog = lambda cat=cat: cat
        try:
            assert [s.id for s in analog_sites.match("mars", sec, latitude=18.4).sites] == base
        finally:
            analog_sites.catalog = original


def test_shared_absence_of_a_band_is_not_a_similarity():
    sec = _section({**DUST, "OLINDEX3": 0.07, "D2300": 0.02})
    legacy_absent = SpectralIndicator(name="legacy_bd2000", value=Stats(median=-0.01),
                                               definition="d", reference="r", n_pixels=100, interpretation="i", detected=False)
    legacy_unknown = legacy_absent.model_copy(update={"detected": None})
    a = analog_sites.match("mars", sec.model_copy(update={"indicators": sec.indicators + [legacy_absent]}), 18.4)
    b = analog_sites.match("mars", sec.model_copy(update={"indicators": sec.indicators + [legacy_unknown]}), 18.4)
    assert [s.id for s in a.sites] == [s.id for s in b.sites]
    for s in a.sites:
        assert not any("2 µm band presence agrees (not detected)" in x for x in s.similarities)


def test_sites_never_cross_bodies():
    cat = {s["id"]: s for s in analog_sites.catalog()["sites"]}
    mars = analog_sites.match("mars", _section({**DUST, "OLINDEX3": 0.07, "D2300": 0.02, "SINDEX2": 0.05}), 18.4)
    for s in mars.sites:
        assert any(a["body"] == "mars" for a in cat[s.id]["analog_for"])


def test_exact_ties_share_a_rank_and_are_announced():
    out = analog_sites.match("mars", _section({**DUST, "OLINDEX3": 0.07, "D2300": 0.02}), 18.4)
    by_id = {s.id: s for s in out.sites}
    assert by_id["samail_bt1b"].rank == by_id["twin_sisters"].rank == 1   # both explain olivine + Fe/Mg clay
    assert any("Tied" in n and "Samail" in n and "Twin Sisters" in n for n in out.notes)
    assert [s.rank for s in out.sites] == sorted(s.rank for s in out.sites)


def test_ubiquitous_ferric_oxide_cannot_tie_with_a_specific_mineral():
    out = analog_sites.match("mars", _section({**DUST, "D2300": 0.024}), 24.0)   # Mawrth-like
    top = {s.id for s in out.sites if s.rank == 1}
    assert top and all("fe_mg_phyllosilicate" in next(x for x in out.sites if x.id == i).matched_classes
                       for i in top)
