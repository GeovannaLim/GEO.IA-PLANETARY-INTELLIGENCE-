import numpy as np
import pytest

from app.schemas.analysis import Reason, SectionStatus
from app.science import similarity, spectral

WL = np.arange(460.0, 2980.0, 20.0)


def _spec(d1=0.15, d2=0.10, n=200, noise=0.002, seed=0):
    cont = 0.1 + 0.00002 * (WL - 460)
    s = cont * (1 - d1 * np.exp(-((WL - 1000) / 90) ** 2) - d2 * np.exp(-((WL - 2000) / 180) ** 2))
    rng = np.random.default_rng(seed)
    return s[None, :] * (1 + noise * rng.standard_normal((n, WL.size)))


def test_legacy_band_depth_matches_definition_exactly():
    spec = np.zeros((1, WL.size)) + 0.2
    i = lambda w: int(np.argmin(np.abs(WL - w)))  # noqa: E731
    spec[0, i(1000)] = 0.15
    bd = spectral.legacy_band_depth(spec, WL, 1000, 800, 1300)
    assert bd[0] == pytest.approx((0.2 - 0.15) / 0.2)
    spec[0, i(1000)] = 0.25                        # convexity: kept negative per pixel (= no absorption)
    assert spectral.legacy_band_depth(spec, WL, 1000, 800, 1300)[0] == pytest.approx(-0.25)


def test_analog_input_clamps_after_the_mean_like_the_library():
    """Library entries are max(0, mean(depth)); clamping per pixel first would bias noise upwards."""
    noise = np.random.default_rng(3).normal(0.0, 0.03, 2000)       # no absorption, only noise
    assert spectral.legacy_analog_input(noise) == pytest.approx(max(0.0, noise.mean()))
    biased = float(np.mean(np.clip(noise, 0, None)))                # the previous behaviour
    assert biased > 0.01 and spectral.legacy_analog_input(noise) < 0.003
    assert spectral.legacy_analog_input(np.array([np.nan])) is None


def test_negative_legacy_depth_is_explained_not_hidden():
    arr = np.random.default_rng(4).normal(-0.03, 0.005, 500)
    assert spectral.legacy_interpretation(arr) == spectral.LEGACY_NEGATIVE
    assert spectral.stats(arr).median < 0                           # displayed with its sign


def test_pyroxene_like_spectrum_detects_both_bands():
    ind, vals = spectral.m3_indicators(_spec(), WL)
    names = {i.name for i in ind}
    assert {"IBD1000", "IBD2000", "legacy_bd1000", "legacy_bd2000", "R750", "slope_750_1550"} <= names
    assert spectral.detected(vals["IBD1000"]) and spectral.detected(vals["IBD2000"])
    assert "pyroxene" in spectral.m3_character(vals)


def test_flat_spectrum_detects_nothing():
    ind, vals = spectral.m3_indicators(_spec(0, 0, noise=0.01), WL)
    assert not spectral.detected(vals["IBD1000"]) and not spectral.detected(vals["IBD2000"])
    assert "No significant" in spectral.m3_character(vals)


def test_detection_needs_majority_and_correlation_aware_sem():
    tiny = np.full(4000, 0.001) + np.random.default_rng(0).normal(0, 0.02, 4000)
    assert not spectral.detected(tiny)             # many pixels, tiny mean: not a detection
    assert not spectral.detected(np.array([0.1, 0.1, -0.2]))  # too few pixels


def test_crism_indicator_has_reference_and_no_abundance():
    ind = spectral.crism_indicator("OLINDEX3", np.full(100, 0.08) + np.random.default_rng(1).normal(0, 0.002, 100))
    assert "Viviano-Beck" in ind.reference and ind.sensitive_to.startswith("olivine")
    assert "abundance" not in ind.interpretation.lower() or "not" in ind.interpretation.lower()
    assert ind.comparability == "body_specific"


def test_similarity_requires_direct_attributes_only():
    sec = similarity.compare("moon", {"legacy_bd1000": 0.1})
    assert sec.status == SectionStatus.unavailable and sec.reason == Reason.insufficient_data
    assert sec.missing == ["legacy_bd2000"] and sec.matches == []
    # extra, non-comparable keys are ignored, never scored
    sec = similarity.compare("moon", {"legacy_bd1000": 0.1, "legacy_bd2000": 0.02, "IBD1000": 9.0, "R750": 0.05})
    assert sec.status == SectionStatus.available
    assert all(m.attributes_used == ["legacy_bd1000", "legacy_bd2000"] for m in sec.matches)
    d = [m.distance for m in sec.matches]
    assert d == sorted(d) and all(0 <= m.similarity <= 1 for m in sec.matches)
    assert "not a probability" in sec.disclaimer
    m = sec.matches[0]
    assert m.differences == {a: pytest.approx(sec.query_values[a] - m.earth_values[a], abs=1e-5)
                             for a in m.attributes_used}


def test_discrimination_uses_measurement_uncertainty():
    q = {"legacy_bd1000": 0.05, "legacy_bd2000": 0.01}
    precise = similarity.compare("moon", {**q, "_sem": {"legacy_bd1000": 1e-5, "legacy_bd2000": 1e-5}})
    noisy = similarity.compare("moon", {**q, "_sem": {"legacy_bd1000": 0.05, "legacy_bd2000": 0.05}})
    assert precise.query_uncertainty and noisy.indistinguishable_sites > precise.indistinguishable_sites >= 1
    assert noisy.discrimination == "low" and "cannot be distinguished" in noisy.disclaimer
    assert precise.matches == noisy.matches or [m.name for m in precise.matches] == [m.name for m in noisy.matches]
    unknown = similarity.compare("moon", q)                         # no uncertainty -> not claimed
    assert unknown.indistinguishable_sites is None and unknown.discrimination in ("low", "moderate", "adequate")
    assert similarity.LIBRARY_CAVEAT in unknown.disclaimer
    assert similarity.LIBRARY_CAVEAT not in similarity.compare("earth", q).disclaimer


def test_reference_library_provenance():
    lib = similarity.load_library()
    assert lib["n_entries"] == len(lib["entries"]) > 50
    assert "EMIT" in lib["measurement"] and lib["derived_from"]["sha256"]
    for e in lib["entries"]:
        assert e["legacy_bd1000"] >= 0 and e["legacy_bd2000"] >= 0
