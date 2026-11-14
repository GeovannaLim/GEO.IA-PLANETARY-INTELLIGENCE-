"""Copernicus DEM GLO-30 (ESA / Copernicus programme) from the AWS Open Data registry.

Product: Copernicus DSM COG 10 (GLO-30, 1 arc-second, EGM2008 heights), 1x1 degree tiles, Float32,
DEFLATE compression with the TIFF floating-point predictor (predictor 3), 1024x1024 internal tiles.
Bucket: https://copernicus-dem-30m.s3.amazonaws.com/ (public, no credentials). Only the internal tiles
that cover the requested window are range-read (assembled across 1-degree tiles when needed); nothing is
cached on disk. Tiles missing from the bucket (open ocean) raise a ProviderError.

It is a surface model (DSM): vegetation and buildings are included. Used here only to characterise
relative terrain (slopes, roughness, relief) of terrestrial sites, never absolute elevation similarity.
"""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass

import numpy as np

from app.providers.http import HttpClient, ProviderError

PROVIDER = "Copernicus DEM GLO-30 (AWS Open Data)"
BASE = "https://copernicus-dem-30m.s3.amazonaws.com/"
PRODUCT = "Copernicus DSM COG 10 (GLO-30), EGM2008"
HEADER_BYTES = 65536


def tile_name(lat_floor: int, lon_floor: int) -> str:
    ns = f"N{lat_floor:02d}" if lat_floor >= 0 else f"S{-lat_floor:02d}"
    ew = f"E{lon_floor:03d}" if lon_floor >= 0 else f"W{-lon_floor:03d}"
    return f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM"


def tile_url(name: str) -> str:
    return f"{BASE}{name}/{name}.tif"


@dataclass
class CogLayout:
    width: int
    height: int
    tile_w: int
    tile_h: int
    offsets: tuple[int, ...]
    counts: tuple[int, ...]
    x0: float            # longitude of the upper-left corner
    y0: float            # latitude of the upper-left corner
    dx: float
    dy: float
    nodata: float | None


def parse_header(data: bytes) -> CogLayout:
    """Minimal TIFF/COG header parser for the first IFD (full-resolution image)."""
    if data[:2] not in (b"II", b"MM"):
        raise ProviderError(PROVIDER, "not a TIFF file")
    bo = "<" if data[:2] == b"II" else ">"
    off = struct.unpack(bo + "I", data[4:8])[0]
    n = struct.unpack(bo + "H", data[off:off + 2])[0]
    size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 11: 4, 12: 8, 16: 8}
    fmt = {3: "H", 4: "I", 11: "f", 12: "d", 16: "Q"}
    tags: dict[int, tuple] = {}
    for i in range(n):
        e = data[off + 2 + 12 * i: off + 14 + 12 * i]
        tag, typ, cnt = struct.unpack(bo + "HHI", e[:8])
        nbytes = size.get(typ, 1) * cnt
        if nbytes <= 4:
            raw = e[8:8 + nbytes]
        else:
            vo = struct.unpack(bo + "I", e[8:12])[0]
            if vo + nbytes > len(data):
                raise ProviderError(PROVIDER, f"TIFF tag {tag} beyond header range")
            raw = data[vo:vo + nbytes]
        tags[tag] = (raw.decode(errors="ignore").strip("\x00") if typ == 2
                     else struct.unpack(bo + fmt[typ] * cnt, raw) if typ in fmt else raw)
    try:
        if tags[259][0] != 8 or tags[317][0] != 3 or tags[258][0] != 32 or tags[339][0] != 3:
            raise ProviderError(PROVIDER, "unexpected encoding (need Float32, DEFLATE, predictor 3)")
        tie, scale = tags[33922], tags[33550]
        nodata = float(tags[42113]) if 42113 in tags and tags[42113] else None
        return CogLayout(width=tags[256][0], height=tags[257][0], tile_w=tags[322][0], tile_h=tags[323][0],
                         offsets=tags[324], counts=tags[325], x0=tie[3], y0=tie[4], dx=scale[0], dy=scale[1],
                         nodata=nodata)
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(PROVIDER, f"incomplete TIFF header: {exc}") from exc


def decode_tile(blob: bytes, tile_w: int, tile_h: int) -> np.ndarray:
    """DEFLATE + floating-point predictor (Adobe TIFF Tech Note 3) -> float32 (tile_h, tile_w)."""
    raw = np.frombuffer(zlib.decompress(blob), dtype=np.uint8)
    if raw.size != tile_w * tile_h * 4:
        raise ProviderError(PROVIDER, f"tile size mismatch: {raw.size} bytes")
    rows = raw.reshape(tile_h, 4 * tile_w)
    undiff = np.cumsum(rows, axis=1, dtype=np.uint64).astype(np.uint8)       # byte-wise horizontal predictor
    planes = undiff.reshape(tile_h, 4, tile_w).transpose(0, 2, 1)            # MSB plane first
    return np.ascontiguousarray(planes).view(">f4").reshape(tile_h, tile_w).astype(np.float32)


async def _tile_points(http: HttpClient, name: str, lat_min: float, lat_max: float, lon_min: float,
                       lon_max: float) -> dict:
    url = tile_url(name)
    lay = parse_header(await http.get_range(PROVIDER, url, 0, HEADER_BYTES))
    r0 = max(0, int(math.floor((lay.y0 - lat_max) / lay.dy)))
    r1 = min(lay.height - 1, int(math.floor((lay.y0 - lat_min) / lay.dy)))
    c0 = max(0, int(math.floor((lon_min - lay.x0) / lay.dx)))
    c1 = min(lay.width - 1, int(math.floor((lon_max - lay.x0) / lay.dx)))
    tiles_x = math.ceil(lay.width / lay.tile_w)
    rows_out = []
    for tr in range(r0 // lay.tile_h, r1 // lay.tile_h + 1):
        row_blocks = []
        for tc in range(c0 // lay.tile_w, c1 // lay.tile_w + 1):
            k = tr * tiles_x + tc
            blob = await http.get_range(PROVIDER, url, lay.offsets[k], lay.counts[k])
            row_blocks.append(decode_tile(blob, lay.tile_w, lay.tile_h))
        rows_out.append(np.hstack(row_blocks))
    mosaic = np.vstack(rows_out)
    rr0, cc0 = (r0 // lay.tile_h) * lay.tile_h, (c0 // lay.tile_w) * lay.tile_w
    sub = mosaic[r0 - rr0: r1 - rr0 + 1, c0 - cc0: c1 - cc0 + 1].astype(float)
    rows, cols = np.meshgrid(np.arange(r0, r1 + 1), np.arange(c0, c1 + 1), indexing="ij")
    plat = lay.y0 - (rows + 0.5) * lay.dy
    plon = lay.x0 + (cols + 0.5) * lay.dx
    ok = np.isfinite(sub)
    if lay.nodata is not None:
        ok &= sub != lay.nodata
    return {"lat": plat[ok], "lon": plon[ok], "elev": sub[ok], "n": int(sub.size), "url": url,
            "pixel_m": round(lay.dy * 111320.0, 1)}


async def window(http: HttpClient, lat: float, lon: float, radius_km: float) -> dict:
    """Elevation samples (pixel centres) within a square window of half-size radius_km around the point,
    assembled from every 1x1 degree tile the window touches (no antimeridian crossing).

    Returns {'lat', 'lon', 'elev' (1-D arrays), 'tiles', 'urls', 'pixel_m', 'n_window'}."""
    dlat = radius_km / 111.32
    dlon = radius_km / (111.32 * max(1e-6, math.cos(math.radians(lat))))
    lat_min, lat_max, lon_min, lon_max = lat - dlat, lat + dlat, lon - dlon, lon + dlon
    if lon_min < -180 or lon_max >= 180 or abs(lat_max) >= 90 or abs(lat_min) >= 90:
        raise ProviderError(PROVIDER, "window crosses the antimeridian or a pole (not supported)")
    parts, names = [], []
    for la in range(math.floor(lat_min), math.floor(lat_max) + 1):
        for lo in range(math.floor(lon_min), math.floor(lon_max) + 1):
            name = tile_name(la, lo)
            parts.append(await _tile_points(http, name, max(lat_min, la), min(lat_max, la + 1 - 1e-9),
                                            max(lon_min, lo), min(lon_max, lo + 1 - 1e-9)))
            names.append(name)
    return {"lat": np.concatenate([p["lat"] for p in parts]), "lon": np.concatenate([p["lon"] for p in parts]),
            "elev": np.concatenate([p["elev"] for p in parts]), "tiles": names, "url": parts[0]["url"],
            "urls": [p["url"] for p in parts], "pixel_m": parts[0]["pixel_m"],
            "n_window": int(sum(p["n"] for p in parts))}
