"""Coordinate conventions and region geometry for Earth, Moon and Mars.

Public API convention: planetocentric latitude, east-positive longitude in
[-180, 180). Providers used here (ODE REST, ODE GDS, CRISM/M3 labels) expect
east-positive [0, 360); Trek catalogue bboxes use [-180, 180]. Conversions are
done only through this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Mean radii used for distance computations (km). Values from the reference
# frames used by each provider's products.
BODY_RADIUS_KM = {
    "moon": 1737.4,     # IAU / LOLA reference sphere (LOLA topography datum)
    "mars": 3396.19,    # IAU 2000 Mars mean equatorial radius (MOLA PEDR uses areoid)
    "earth": 6371.0088, # IUGG mean radius
}
REFERENCE_FRAME = {
    "moon": "MOON_ME (mean Earth/polar axis), planetocentric, east-positive",
    "mars": "IAU 2000 Mars body-fixed, planetocentric, east-positive",
    "earth": "WGS84 (EPSG:4326); latitude treated as geodetic by Earth Engine",
}


def to_east_180(lon: float) -> float:
    """Normalise any longitude to [-180, 180)."""
    x = ((lon + 180.0) % 360.0) - 180.0
    return 0.0 if x == -0.0 else x


def to_east_360(lon: float) -> float:
    """Normalise any longitude to [0, 360)."""
    x = lon % 360.0
    return 0.0 if x == 360.0 else x


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(a)))


@dataclass(frozen=True)
class Box:
    """Lat/lon box in east_360. ``west`` may be > ``east`` when it wraps 0°."""
    south: float
    north: float
    west: float
    east: float

    @property
    def wraps(self) -> bool:
        return self.west > self.east

    def split(self) -> list["Box"]:
        """Non-wrapping boxes in [0, 360] (for providers that cannot wrap)."""
        if not self.wraps:
            return [self]
        return [Box(self.south, self.north, self.west, 360.0),
                Box(self.south, self.north, 0.0, self.east)]

    def as_dict(self) -> dict[str, float]:
        return {"minlat": round(self.south, 6), "maxlat": round(self.north, 6),
                "westernlon": round(self.west, 6), "easternlon": round(self.east, 6)}

    def scaled(self, factor: float, lat: float, lon360: float) -> "Box":
        """Box of the same centre with half-sizes multiplied by ``factor``."""
        half_lat = (self.north - self.south) / 2 * factor
        width = (self.east - self.west) % 360.0 if self.wraps else (self.east - self.west)
        if width >= 359.999:
            return Box(max(-90.0, lat - half_lat), min(90.0, lat + half_lat), 0.0, 360.0)
        half_lon = width / 2 * factor
        return _make_box(lat, lon360, half_lat, half_lon)


def _make_box(lat: float, lon360: float, half_lat: float, half_lon: float) -> Box:
    south, north = lat - half_lat, lat + half_lat
    if north >= 90.0 or south <= -90.0 or half_lon >= 180.0:
        # The circle reaches a pole: the only correct box spans all longitudes.
        return Box(max(-90.0, south), min(90.0, north), 0.0, 360.0)
    west, east = to_east_360(lon360 - half_lon), to_east_360(lon360 + half_lon)
    if east == 0.0:
        east = 360.0
    return Box(south, north, west, east)


def region_box(lat: float, lon: float, radius_km: float, body: str) -> Box:
    """Bounding box (east_360) enclosing a circle of ``radius_km``."""
    r = BODY_RADIUS_KM[body]
    half_lat = math.degrees(radius_km / r)
    coslat = math.cos(math.radians(min(89.999, abs(lat) + half_lat)))
    half_lon = 180.0 if coslat <= 1e-6 else min(180.0, half_lat / coslat)
    return _make_box(lat, to_east_360(lon), half_lat, half_lon)


def point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    """Ray casting; ring vertices are (lon, lat) in the same longitude branch."""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x_cross = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x_cross:
                inside = not inside
    return inside


def parse_wkt_polygons(wkt: str) -> list[list[tuple[float, float]]]:
    """Outer rings of a POLYGON / MULTIPOLYGON WKT string (lon lat order)."""
    if not wkt:
        return []
    body = wkt.strip()
    upper = body.upper()
    if not (upper.startswith("POLYGON") or upper.startswith("MULTIPOLYGON")):
        return []
    rings: list[list[tuple[float, float]]] = []
    depth, buf, ring_depth = 0, "", 3 if upper.startswith("MULTIPOLYGON") else 2
    ring_index_at_depth = 0
    for ch in body[body.index("("):]:
        if ch == "(":
            depth += 1
            if depth == ring_depth:
                buf = ""
            elif depth == ring_depth - 1:
                ring_index_at_depth = 0
            continue
        if ch == ")":
            if depth == ring_depth:
                if ring_index_at_depth == 0:  # keep outer ring only
                    pts = []
                    for pair in buf.split(","):
                        parts = pair.split()
                        if len(parts) >= 2:
                            pts.append((float(parts[0]), float(parts[1])))
                    if len(pts) >= 3:
                        rings.append(pts)
                ring_index_at_depth += 1
            depth -= 1
            continue
        if depth == ring_depth:
            buf += ch
    return rings


def footprint_contains(wkt: str, lat: float, lon: float) -> bool | None:
    """True/False if the footprint polygon contains the point; None if unparsable.

    Tries the point in both longitude branches so footprints written in
    [-180, 180] (ODE ``Footprint_C0_geometry``) or [0, 360] both work.
    """
    rings = parse_wkt_polygons(wkt)
    if not rings:
        return None
    candidates = {to_east_180(lon), to_east_360(lon)}
    return any(point_in_ring(x, lat, ring) for ring in rings for x in candidates)
