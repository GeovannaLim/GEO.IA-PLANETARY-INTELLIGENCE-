"""Regression tests for the 2026-11-14 science fixes: polar CRISM grids, ice magnitude floors,
ice-dominated spectra in analog matching."""

import numpy as np
import pytest

from app import i18n
from app.providers.crism import MapProjection, PolarStereographic, locate
from app.providers.envi import parse_header
from app.schemas.analysis import MineralogySection, SectionStatus, SpectralIndicator, Stats
from app.science import analog_sites, spectral

# Real header values of frt00006535_07_su187j_mtr3 (south polar stereographic, 18 m/px).
SOUTH_HDR = """ENVI
samples = 779
lines   = 699
bands   = 1
data type = 4
interleave = bsq
map info = {Mars South Polar Stereographic [IAU 2000], 1.0000, 1.0000, 132947.7700, -95995.0530, 1.8000000000e+01, 1.8000000000e+01, D_Mars_2000, units=Meters}
projection info = {31, 3396190.0, 3376200.0, -90.000000, 0.000000, 0.0, 0.0, D_Mars_2000, Mars South Polar Stereographic [IAU 2000], units=Meters}
"""


def test_south_polar_grid_matches_pds_label_and_round_trips():
    h = parse_header(SOUTH_HDR)
    p = MapProjection.from_header(h)
    assert isinstance(p, PolarStereographic) and p.south
    rows, cols = np.meshgrid(np.arange(0, h.lines, 50.0), np.arange(0, h.samples, 50.0), indexing="ij")
    lat, lon = p.latlon(rows.ravel(), cols.ravel())
    # PDS label bounds of the product's footprint: lat -87.2501..-86.9363, lon 123.155..129.234 E
    centre_lat, centre_lon = p.latlon(np.array([h.lines / 2]), np.array([h.samples / 2]))
    assert -87.2501 < centre_lat[0] < -86.9363 and 123.155 < centre_lon[0] < 129.234
    assert lat.max() < -86.8 and lat.min() > -87.4
    r, c = locate(p, h, -87.1, 126.0)
    la, lo = p.latlon(np.array([float(r)]), np.array([float(c)]))
    assert abs(la[0] + 87.1) < 0.001 and abs(lo[0] - 126.0) < 0.01


def test_north_polar_orientation_longitude_zero_points_down():
    p = PolarStereographic(south=False, radius_m=PolarStereographic.RP, tie_px=(1.0, 1.0),
                           tie_xy=(-1000.0, 1000.0), pixel_size=(1.0, 1.0))
    x0, y0 = p.xy(89.0, 0.0)
    x90, y90 = p.xy(89.0, 90.0)
    assert abs(x0) < 1e-6 and y0 < 0          # lon 0 straight down from the pole
    assert x90 > 0 and abs(y90) < 1e-6        # lon 90E to the right
    lat, lon = p.latlon(np.array([500.0]), np.array([800.0]))
    r, c = p.pixel(float(lat[0]), float(lon[0]))
    assert r == pytest.approx(500.5, abs=1e-6) and c == pytest.approx(800.5, abs=1e-6)


def test_ice_floor_rejects_tiny_positive_values_seen_on_ice_free_ground():
    rng = np.random.default_rng(0)
    tiny = 0.006 + rng.normal(0, 0.001, 3721)          # like Jezero/Gale BD1435 (~0.005)
    real = 0.24 + rng.normal(0, 0.02, 3721)            # like the north residual cap BD1500_2
    assert spectral.detected(tiny)                     # passes the statistics alone ...
    assert not spectral.crism_detected("BD1435", tiny)  # ... but not the calibrated floor
    assert spectral.crism_detected("BD1500_2", real)
    ind = spectral.crism_indicator("BD1435", tiny)
    assert ind.detected is False and "floor" in ind.interpretation and ind.screening_threshold == 0.02
    assert spectral.crism_detected("D2300", tiny)        # non-ice parameters keep the statistical rule


def _ind(name, det):
    return SpectralIndicator(name=name, value=Stats(mean=0.1), definition="d", reference="r", n_pixels=100,
                             interpretation="i", detected=det)


def test_ice_dominated_spectrum_offers_no_analogs_and_says_why():
    s = MineralogySection(status=SectionStatus.available, indicators=[
        _ind("BD1500_2", True), _ind("SINDEX2", True), _ind("OLINDEX3", True), _ind("BD530_2", True)])
    out = analog_sites.match("mars", s, latitude=85.0)
    assert set(out.masked_evidence) == {"sulfate", "olivine"}
    assert {e["class"] for e in out.region_evidence} == {"ice", "ferric_oxide"}
    assert all("sulfate" not in m and "olivine" not in m for site in out.sites for m in site.matched_classes)
    assert any("ice" in n.lower() and "not used" in n for n in out.notes)
    pt = i18n.localize({"status": "completed", "links": {}, "terrestrial_analogs": out.model_dump(mode="json")},
                       "pt-BR")["terrestrial_analogs"]
    assert any("Gelo exposto" in n for n in pt["notes"])


def test_without_ice_the_same_families_are_matched_normally():
    s = MineralogySection(status=SectionStatus.available, indicators=[
        _ind("BD1500_2", False), _ind("SINDEX2", True), _ind("OLINDEX3", True)])
    out = analog_sites.match("mars", s, latitude=20.0)
    assert out.masked_evidence == [] and {"sulfate", "olivine"} <= {e["class"] for e in out.region_evidence}
