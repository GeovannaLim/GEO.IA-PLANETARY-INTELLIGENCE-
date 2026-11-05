import pytest

from app.science.coordinates import (Box, footprint_contains, haversine_km, parse_wkt_polygons, region_box,
                                     to_east_180, to_east_360)


@pytest.mark.parametrize("lon,e180,e360", [(0, 0, 0), (-15.2, -15.2, 344.8), (180, -180, 180), (-180, -180, 180),
                                           (359.9, -0.1, 359.9), (360, 0, 0), (725, 5, 5)])
def test_longitude_normalisation(lon, e180, e360):
    assert to_east_180(lon) == pytest.approx(e180)
    assert to_east_360(lon) == pytest.approx(e360)


def test_equatorial_box_is_symmetric_and_converted():
    b = region_box(0.0, -15.2, 10, "moon")
    assert not b.wraps
    assert b.west < 344.8 < b.east
    assert b.north == pytest.approx(-b.south)
    # 10 km on the Moon ~ 0.33 deg
    assert b.north == pytest.approx(10 / 1737.4 * 57.2958, rel=1e-6)


def test_box_crossing_prime_meridian_wraps_and_splits():
    b = region_box(0.0, 0.02, 5, "moon")
    assert b.wraps
    parts = b.split()
    assert len(parts) == 2 and parts[0].east == 360.0 and parts[1].west == 0.0


def test_antimeridian_is_not_a_wrap_in_east360():
    b = region_box(0.5, 179.95, 3, "moon")
    assert not b.wraps and b.west < 179.95 < b.east and b.east > 180


@pytest.mark.parametrize("lat", [89.95, -89.95])
def test_polar_box_spans_all_longitudes(lat):
    b = region_box(lat, 30.0, 5, "moon")
    assert (b.west, b.east) == (0.0, 360.0)
    assert -90 <= b.south and b.north <= 90


def test_haversine_quarter_circumference():
    assert haversine_km(0, 0, 0, 90, 1737.4) == pytest.approx(1737.4 * 3.14159265 / 2, rel=1e-6)


def test_wkt_parsing_and_containment_both_branches():
    wkt = "POLYGON ((-15.5 34.5, -14.5 34.5, -14.5 35.5, -15.5 35.5, -15.5 34.5))"
    assert len(parse_wkt_polygons(wkt)[0]) == 5
    assert footprint_contains(wkt, 35.0, -15.0) is True
    assert footprint_contains(wkt, 35.0, 345.0) is True          # same point, east_360
    assert footprint_contains(wkt, 36.0, -15.0) is False
    multi = "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)), ((359 0, 360 0, 360 1, 359 1, 359 0)))"
    assert footprint_contains(multi, 0.5, -0.5) is True
    assert footprint_contains("", 0, 0) is None
    assert footprint_contains("POINT (1 2)", 0, 0) is None


def test_box_as_dict_keys_match_ode_parameters():
    assert set(Box(0, 1, 2, 3).as_dict()) == {"minlat", "maxlat", "westernlon", "easternlon"}
