"""Provisional spatial-coverage criterion for Mars olivine (OLINDEX3), approved as experimental 2026-11-14.

The 75% criterion was calibrated on the same 59 controls used here and has NOT been validated on an
independent set (docs/DIAGNOSTICO_OLIVINA.md). These tests freeze the expected behaviour on those controls
and document the known blind spot (small outcrops filling part of the ~2 km CRISM window)."""

import json
from pathlib import Path

import numpy as np
import pytest

from app import i18n
from app.schemas.analysis import MineralogySection, SectionStatus
from app.science import analog_sites, spectral

FLOOR = spectral.MAGNITUDE_FLOOR["OLINDEX3"]
CONTROLS = json.loads((Path(__file__).parent.parent / "data" / "olivine_controls.json").read_text())["controls"]


def window(median: float, coverage: float, n: int = 3721, seed: int = 0) -> np.ndarray:
    """Synthetic OLINDEX3 window with the given window median and fraction of pixels >= the floor."""
    rng = np.random.default_rng(seed)
    k = int(round(coverage * n))
    below = FLOOR - 0.01 - rng.uniform(0, 0.005, n - k)              # positive, just under the floor
    if median >= FLOOR and k > n // 2:
        j = n // 2 - (n - k)                                           # rank of the median inside 'above'
        top = FLOOR + (median - FLOOR) * (k - 1) / max(j, 1)
        above = np.linspace(FLOOR, max(top, FLOOR), k)
    else:
        above = FLOOR + rng.uniform(0, 0.01, k)
        below = median + rng.normal(0, 0.002, n - k)
    return np.concatenate([below, above])


def status(arr: np.ndarray) -> str:
    ind = spectral.crism_indicator("OLINDEX3", arr)
    if not ind.detected:
        return "not_detected"
    return "uncertain" if ind.uncertain else "confident"


@pytest.mark.parametrize("c", CONTROLS, ids=lambda c: f"{c['group']}:{c['lat']},{c['lon']}")
def test_all_59_real_controls(c):
    got = status(window(c["olindex3"], c["frac_ol_floor"]))
    if c["group"].startswith("positive"):
        assert got == "confident", c
    elif c["olindex3"] >= FLOOR:                                       # the only one: Elysium 27.44N 143.34E
        assert got == "uncertain", c
    else:
        assert got == "not_detected", c


def _control(lat, lon):
    return next(c for c in CONTROLS if abs(c["lat"] - lat) < 1e-3 and abs(c["lon"] - lon) < 1e-3)


def test_jezero_and_nili_fossae_stay_confident():
    for lat, lon in ((18.4386, 77.5031), (21.0, 74.5)):
        c = _control(lat, lon)
        assert status(window(c["olindex3"], c["frac_ol_floor"])) == "confident"


def test_elysium_becomes_uncertain_but_stays_visible():
    c = _control(27.4387, 143.3358)
    arr = window(c["olindex3"], c["frac_ol_floor"])
    ind = spectral.crism_indicator("OLINDEX3", arr)
    assert ind.detected is True and ind.uncertain is True               # visible ...
    assert ind.spatial_coverage == pytest.approx(c["frac_ol_floor"], abs=0.01)
    assert "Uncertain detection" in ind.interpretation
    sec = MineralogySection(status=SectionStatus.available, indicators=[ind])
    out = analog_sites.match("mars", sec, latitude=27.44)
    assert out.uncertain_evidence == ["olivine"]                        # ... but not matched
    assert not any("olivine" in s.matched_classes for s in out.sites)
    assert any("Uncertain detection" in n for n in out.notes)
    pt = i18n.localize({"status": "completed", "links": {}, "mineralogy": sec.model_dump(mode="json"),
                        "terrestrial_analogs": out.model_dump(mode="json")}, "pt-BR")
    assert any("Detecção incerta" in n for n in pt["terrestrial_analogs"]["notes"])
    assert pt["mineralogy"]["indicators"][0]["interpretation"].startswith("Detecção incerta")


@pytest.mark.parametrize("share,expected", [
    (0.40, "not_detected"),   # outcrop in 40% of the window: window median below the floor -> MISSED
    (0.60, "uncertain"),      # 60%: passes the floor, fails 75% coverage -> visible, uncertain
    (0.85, "confident"),
])
def test_small_outcrop_blind_spot_is_documented(share, expected):
    """Strong olivine (0.12) filling only part of the window over a 0.01 background.
    Known limitation of a window statistic: partial outcrops are reported as uncertain or missed."""
    n = 3721
    k = int(share * n)
    arr = np.concatenate([0.12 + np.random.default_rng(1).normal(0, 0.005, k),
                          0.01 + np.random.default_rng(2).normal(0, 0.003, n - k)])
    assert status(arr) == expected


def test_rule_applies_only_to_olivine_and_never_to_m3():
    other = spectral.crism_indicator("D2300", np.full(400, 0.02) + np.random.default_rng(3).normal(0, 1e-3, 400))
    assert other.uncertain is None and other.spatial_coverage is None
    assert set(spectral.SPATIAL_COVERAGE_MIN) == {"OLINDEX3"}


def test_analyzed_extent_reports_the_real_window():
    from app.providers.crism import analyzed_extent
    e = analyzed_extent(61, 61, 3721, 18.0, 10.0)                      # Jezero-like: 18 m pixels, 10 km asked
    assert e["window_km"] == [1.1, 1.1] and e["requested_radius_km"] == 10.0
    assert e["fraction_of_requested_area"] < 0.01                      # ~1.2 km² of a 314 km² circle
