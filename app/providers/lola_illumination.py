"""LOLA-derived lunar south-polar illumination maps (Mazarico et al. 2011, Icarus 211, 1066-1081,
doi:10.1016/j.icarus.2010.10.030), as published by the LOLA team / NASA GSFC PGDA (product 69).

Products (PDS IMG, int16 LSB, polar stereographic on the 1737.4 km sphere, true scale at the pole):
* AVGVISIB_*        fraction of time the solar disc is (partly) visible, 0..1   (DN*0.00004)
* LPSR_*            permanent shadow: 1 = permanently shadowed, 0 = not        (DN*0.000025 + 0.5)
* AVGVISIB_*_EARTH  fraction of time the Earth disc is visible (communications) (DN*0.00004)
Grids: 85S 60 m/px (to 82.9S), 75S 120 m/px (to 75S), 65S 240 m/px (to 55.2S); the finest grid that
covers the point is used. These are MODEL products computed over the LOLA topography (18.6-year
nutation cycle, 1-hour step), not direct observations.

Access: HTTP byte ranges of whole image rows (https://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG/,
the LOLA team mirror linked from https://pgda.gsfc.nasa.gov/products/69). South pole only: the
orientation was validated against known features (Shackleton interior permanently shadowed, Mons
Malapert illuminated); the north grids were not validated and are not used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.config import get_settings
from app.providers.envi import parse_pds3_label
from app.providers.http import HttpClient, ProviderError
from app.services.cache import metadata_cache

PROVIDER = "NASA GSFC PGDA / LOLA team (illumination maps)"
BASE = "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG/"
VERSION = "201608"
GRIDS = ((-85.0, "85S_060M"), (-75.0, "75S_120M"), (-65.0, "65S_240M"))   # finest first
LAYERS = {"sun": "AVGVISIB_{g}_" + VERSION, "psr": "LPSR_{g}_" + VERSION,
          "earth": "AVGVISIB_{g}_" + VERSION + "_EARTH"}
MAX_HALF_WINDOW_KM = 3.0          # bounded byte ranges: at most ~2*3 km of rows per layer
REFERENCE = ("Mazarico, E., Neumann, G.A., Smith, D.E., Zuber, M.T., Torrence, M.H. (2011). Illumination "
             "conditions of the lunar polar regions using LOLA topography. Icarus 211, 1066-1081, "
             "doi:10.1016/j.icarus.2010.10.030")
LIMITATIONS = [
    "Model product: illumination computed over the LOLA topography (Mazarico et al. 2011), not a direct "
    "observation; terrain smaller than the grid spacing is not resolved.",
    "Long-term averages over the 18.6-year lunar nutation cycle; they do not describe any particular date.",
    "Sunlit fraction counts any visible part of the solar disc; it is not an energy or temperature estimate.",
]


class NotApplicable(Exception):
    """Point outside the validated south-polar grids."""


@dataclass
class Grid:
    name: str
    lines: int
    samples: int
    record_bytes: int
    scale_m: float
    line_offset: float
    sample_offset: float
    radius_m: float
    factor: float
    offset: float


def grid_for(lat: float) -> str:
    if lat > -65.0:
        raise NotApplicable("illumination maps are used only for the lunar south polar region (lat <= -65)")
    return next(g for lim, g in GRIDS if lat <= lim)


def _num(v: str) -> float:
    return float(str(v).split("<")[0].strip())


def parse_label(text: str, name: str) -> Grid:
    k = parse_pds3_label(text)
    try:
        if k.get("SAMPLE_TYPE") != "LSB_INTEGER" or int(k.get("SAMPLE_BITS", 0)) != 16:
            raise ValueError("unexpected sample type")
        if _num(k["CENTER_LATITUDE"]) != -90.0:
            raise ValueError("not a south polar grid")
        return Grid(name=name, lines=int(k["LINES"]), samples=int(k["LINE_SAMPLES"]),
                    record_bytes=int(k["RECORD_BYTES"]), scale_m=_num(k["MAP_SCALE"]),
                    line_offset=_num(k["LINE_PROJECTION_OFFSET"]), sample_offset=_num(k["SAMPLE_PROJECTION_OFFSET"]),
                    radius_m=_num(k["A_AXIS_RADIUS"]) * 1000.0, factor=_num(k["SCALING_FACTOR"]),
                    offset=_num(k["OFFSET"]))
    except (KeyError, ValueError) as exc:
        raise ProviderError(PROVIDER, f"bad label for {name}: {exc}") from exc


def to_pixel(g: Grid, lat: float, lon: float) -> tuple[float, float]:
    """0-based fractional (row, col) of a planetocentric point (south polar stereographic, sphere).

    PDS convention: 1-based line = LINE_PROJECTION_OFFSET - y/scale, sample = SAMPLE_PROJECTION_OFFSET +
    x/scale, with x = rho sin(lon), y = rho cos(lon) and longitude 0 pointing up (validated, see module doc)."""
    rho = 2.0 * g.radius_m * math.tan(math.radians(90.0 + lat) / 2.0)
    lam = math.radians(lon)
    x, y = rho * math.sin(lam), rho * math.cos(lam)
    return g.line_offset - y / g.scale_m - 1.0, g.sample_offset + x / g.scale_m - 1.0


def window_latlon(g: Grid, rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = (g.line_offset - (rows + 1.0)) * g.scale_m
    x = (cols + 1.0 - g.sample_offset) * g.scale_m
    c = 2.0 * np.arctan(np.hypot(x, y) / (2.0 * g.radius_m))
    return np.degrees(c) - 90.0, np.degrees(np.arctan2(x, y)) % 360.0


async def _label(http: HttpClient, name: str) -> Grid:
    async def fetch() -> Grid:
        text = await http.get_text(PROVIDER, BASE + name + ".LBL", timeout=30, max_bytes=64 * 1024)
        return parse_label(text, name)
    return await metadata_cache.get_or_set(("lola-illum-label", name), get_settings().metadata_cache_ttl_s, fetch)


async def _rows(http: HttpClient, g: Grid, r0: int, r1: int) -> np.ndarray:
    data = await http.get_range(PROVIDER, BASE + g.name + ".IMG", r0 * g.record_bytes,
                                (r1 - r0 + 1) * g.record_bytes)
    arr = np.frombuffer(data, "<i2").reshape(r1 - r0 + 1, g.record_bytes // 2)[:, :g.samples]
    return arr.astype(float) * g.factor + g.offset


@dataclass
class Illumination:
    grid: str
    scale_m: float
    products: dict[str, str]
    values: dict[str, np.ndarray]       # layer -> pixel values inside the analysis circle
    centre: dict[str, float]            # layer -> value at the pixel containing the point
    n_pixels: int
    half_window_km: float
    requested_radius_km: float


async def sample(http: HttpClient, lat: float, lon: float, radius_km: float) -> Illumination:
    gname = grid_for(lat)
    grids = {k: await _label(http, v.format(g=gname)) for k, v in LAYERS.items()}
    g = grids["sun"]
    row_f, col_f = to_pixel(g, lat, lon)
    row, col = int(round(row_f)), int(round(col_f))
    if not (0 <= row < g.lines and 0 <= col < g.samples):
        raise NotApplicable("point outside the polar illumination grid")
    half_km = min(radius_km, MAX_HALF_WINDOW_KM)
    half = max(1, int(math.ceil(half_km * 1000.0 / g.scale_m)))
    r0, r1 = max(0, row - half), min(g.lines - 1, row + half)
    c0, c1 = max(0, col - half), min(g.samples - 1, col + half)
    rr, cc = np.meshgrid(np.arange(r0, r1 + 1), np.arange(c0, c1 + 1), indexing="ij")
    dist_km = np.hypot((rr - row_f) * g.scale_m, (cc - col_f) * g.scale_m) / 1000.0
    inside = dist_km <= max(half_km, g.scale_m / 1000.0)
    values, centre = {}, {}
    for layer, gl in grids.items():
        if (gl.lines, gl.samples, gl.scale_m) != (g.lines, g.samples, g.scale_m):
            raise ProviderError(PROVIDER, f"{gl.name}: grid differs from {g.name}")
        block = (await _rows(http, gl, r0, r1))[:, c0:c1 + 1]
        values[layer] = block[inside]
        centre[layer] = float(block[row - r0, col - c0])
    return Illumination(grid=gname, scale_m=g.scale_m, products={k: v.name for k, v in grids.items()},
                        values=values, centre=centre, n_pixels=int(inside.sum()), half_window_km=half_km,
                        requested_radius_km=radius_km)


MAX_LOOKUP_ROWS = 600     # bounded byte range for per-pixel lookups (~6 MB at the 60 m grid)


async def permanent_shadow_at(http: HttpClient, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Per-point permanent-shadow flag from the LPSR map: 1.0 = permanently shadowed, 0.0 = not,
    NaN = outside the grid (not verifiable). Raises NotApplicable outside the south polar region and
    ProviderError on archive failure; never guesses."""
    lats, lons = np.asarray(lats, float), np.asarray(lons, float)
    gname = grid_for(float(np.nanmax(lats)))          # finest grid that covers every point
    g = await _label(http, LAYERS["psr"].format(g=gname))
    rows = np.empty(lats.shape)
    cols = np.empty(lats.shape)
    for i, (la, lo) in enumerate(zip(lats.ravel(), lons.ravel())):
        rows.flat[i], cols.flat[i] = to_pixel(g, float(la), float(lo))
    ri, ci = np.rint(rows).astype(int), np.rint(cols).astype(int)
    inside = (ri >= 0) & (ri < g.lines) & (ci >= 0) & (ci < g.samples)
    out = np.full(lats.shape, np.nan)
    if not inside.any():
        return out
    r0, r1 = int(ri[inside].min()), int(ri[inside].max())
    if r1 - r0 + 1 > MAX_LOOKUP_ROWS:
        raise ProviderError(PROVIDER, f"shadow lookup would read {r1 - r0 + 1} rows (> {MAX_LOOKUP_ROWS})")
    block = await _rows(http, g, r0, r1)
    out[inside] = (block[ri[inside] - r0, ci[inside]] > 0.5).astype(float)
    return out
