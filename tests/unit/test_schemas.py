from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.pipelines.common import build_coordinates, validate_limits
from app.schemas.analysis import AnalysisResult, AnalyzeRequest, processing_placeholder


def test_request_defaults_and_conventions():
    r = AnalyzeRequest(latitude=25.8, longitude=-15.2, radius_km=10)
    assert r.longitude_convention == "east_180"
    r2 = AnalyzeRequest(latitude=25.8, longitude=344.8, radius_km=10, longitude_convention="east_360")
    assert build_coordinates(r2, "moon").longitude == pytest.approx(-15.2)


@pytest.mark.parametrize("payload", [
    {"latitude": 91, "longitude": 0, "radius_km": 1},
    {"latitude": 0, "longitude": 200, "radius_km": 1},
    {"latitude": 0, "longitude": -1, "radius_km": 1, "longitude_convention": "east_360"},
    {"latitude": 0, "longitude": 0, "radius_km": 0},
    {"latitude": 0, "longitude": 0, "radius_km": 1, "planet": "venus"},
])
def test_invalid_requests_rejected(payload):
    with pytest.raises(ValidationError):
        AnalyzeRequest(**payload)


def test_operational_radius_limits():
    with pytest.raises(ValueError):
        validate_limits(AnalyzeRequest(latitude=0, longitude=0, radius_km=500), "moon")
    validate_limits(AnalyzeRequest(latitude=0, longitude=0, radius_km=10), "mars")


def test_placeholder_contains_no_values():
    req = AnalyzeRequest(latitude=1, longitude=2, radius_km=3)
    p = processing_placeholder("x", "moon", build_coordinates(req, "moon"), datetime.now(timezone.utc))
    d = p.model_dump()
    assert d["status"] == "processing"
    for sec in ("imagery", "topography", "mineralogy", "earth_analogs"):
        assert d[sec]["status"] == "processing"
    assert d["topography"]["elevation_m"] is None and d["mineralogy"]["indicators"] == []
    assert d["confidence"]["level"] == "not_assessed"
    AnalysisResult.model_validate(d)  # round trip
