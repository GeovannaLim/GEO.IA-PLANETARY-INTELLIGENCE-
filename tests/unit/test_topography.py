import math

import numpy as np
import pytest

from app.schemas.analysis import Reason, SectionStatus
from app.science.topography import summarize

R_MOON = 1737.4


def _points(n=6000, slope_deg=3.0, lat0=10.0, lon0=20.0, half=0.2, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    lat = rng.uniform(lat0 - half, lat0 + half, n)
    lon = rng.uniform(lon0 - half, lon0 + half, n)
    y = np.radians(lat - lat0) * R_MOON * 1000
    z = 100 + math.tan(math.radians(slope_deg)) * y + noise * rng.standard_normal(n)
    return lat, lon, z


def test_plane_slope_and_aspect_recovered():
    lat, lon, z = _points()
    t = summarize(lat, lon, z, lat0=10, lon0_360=20, roi_radius_km=5, sampled_radius_km=5, body_radius_km=R_MOON,
                  datum="d", method="m", source_ids=["src-01"])
    assert t.status == SectionStatus.available
    assert t.regional_slope_degrees == pytest.approx(3.0, abs=0.05)
    assert t.regional_aspect_degrees == pytest.approx(180.0, abs=1.0)  # rises to the north -> faces south
    assert t.local_slope_degrees.median == pytest.approx(3.0, abs=0.3)
    assert t.roughness_m < 0.1  # only map-projection curvature remains
    assert t.source_ids == ["src-01"] and t.n_points > 1000


def test_points_outside_circle_are_ignored():
    lat, lon, z = _points(half=1.0)
    t = summarize(lat, lon, z, lat0=10, lon0_360=20, roi_radius_km=2, sampled_radius_km=2, body_radius_km=R_MOON,
                  datum="d", method="m", source_ids=[])
    assert t.n_points < lat.size / 10


def test_too_few_points_is_partial_and_no_points_is_no_coverage():
    lat, lon, z = _points(n=10, half=0.01)
    t = summarize(lat, lon, z, lat0=10, lon0_360=20, roi_radius_km=5, sampled_radius_km=5, body_radius_km=R_MOON,
                  datum="d", method="m", source_ids=[])
    assert t.status == SectionStatus.partial and t.reason == Reason.insufficient_data
    assert t.regional_slope_degrees is None
    e = summarize(np.array([]), np.array([]), np.array([]), lat0=0, lon0_360=0, roi_radius_km=1, sampled_radius_km=1,
                  body_radius_km=R_MOON, datum="d", method="m", source_ids=[])
    assert e.status == SectionStatus.unavailable and e.reason == Reason.no_coverage and e.elevation_m is None


def test_reduced_sampling_radius_is_reported():
    lat, lon, z = _points()
    t = summarize(lat, lon, z, lat0=10, lon0_360=20, roi_radius_km=10, sampled_radius_km=5, body_radius_km=R_MOON,
                  datum="d", method="m", source_ids=[])
    assert any("sampled within" in x for x in t.limitations)
