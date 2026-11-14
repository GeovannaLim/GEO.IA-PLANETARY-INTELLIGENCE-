"""Chandrayaan-1 Moon Mineralogy Mapper (M3) Level 2 reflectance at a point.

Data path (all verified live):
1. ODE REST product search  ihid=CH1-ORB iid=M3 pt=REFIMG  (L2 reflectance,
   CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0, PDS Imaging node).
2. The L2 label names its pixel-location backplane
   (``CH1:PIXEL_LOCATION_FILE_NAME = M3G..._V03_LOC.IMG``), which lives in the
   L1B product (ODE pt=CALIV3, pdsid ``M3G..._V03_RDN``).
3. LOC.IMG is BIL float64 (longitude, latitude, radius) with the same
   lines x samples as the L2 RFL cube. The pixel nearest the target is found by
   a coarse-to-fine search that range-reads single LOC lines (~5 KB each).
4. A window of RFL lines (BIL float32, 85 global-mode bands, ignore = -999)
   is range-read in one request; pixels farther than the ROI radius or with
   invalid values are masked.

L2 RFL is "pixel located, thermal corrected, photometry corrected reflectance"
(label). Known limitations are listed in the returned object.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from app.config import get_settings
from app.providers import ode
from app.providers.envi import EnviHeader, RemoteCube, open_cube, parse_pds3_label
from app.providers.http import HttpClient, ProviderError
from app.science.coordinates import BODY_RADIUS_KM, to_east_360

PROVIDER = "PDS Imaging (M3)"

LIMITATIONS = [
    "M3 L2 reflectance includes an empirical thermal correction; residual thermal emission can "
    "affect the 2 µm region on warm, low-latitude terrain.",
    "M3 global-mode spatial sampling is ~140 m/pixel (100 km orbit) or ~280 m/pixel (200 km orbit).",
    "L2 photometric correction uses a lunar topography model; steep slopes and high incidence "
    "angles degrade the correction.",
    "Pixels within the window are spatially correlated, so the detection test is optimistic.",
]


@dataclass
class M3Extraction:
    product_id: str
    rfl_url: str
    loc_url: str
    observation_start: str | None
    observation_end: str | None
    line: int
    sample: int
    pixel_distance_m: float
    pixel_size_m: float | None
    half_window: int
    wavelengths: np.ndarray
    spectra: np.ndarray          # (n_valid, n_bands)
    n_window: int
    n_valid: int
    incidence_deg: float | None
    pixel_lat: np.ndarray | None = None     # (n_valid,) planetocentric latitude of each valid pixel
    pixel_lon: np.ndarray | None = None     # (n_valid,) east longitude 0-360 of each valid pixel
    processing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=lambda: list(LIMITATIONS))


def _angular_dist(lat: np.ndarray, lon: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    p1, p2 = math.radians(lat0), np.radians(lat)
    dl = np.radians(lon - lon0)
    a = np.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


class LocReader:
    def __init__(self, cube: RemoteCube):
        self.cube = cube
        self.h: EnviHeader = cube.h
        self._cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    async def line(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        if i not in self._cache:
            arr = await self.cube.bil_lines(i, i, bands=slice(0, 2))
            self._cache[i] = (arr[0, 0, :].astype(float), arr[0, 1, :].astype(float))
        return self._cache[i]

    async def best_in_lines(self, lines: list[int], lat0: float, lon0: float) -> tuple[float, int, int]:
        import asyncio
        res = await asyncio.gather(*(self.line(i) for i in lines))
        best = (math.inf, -1, -1)
        for i, (lon, lat) in zip(lines, res):
            ok = np.isfinite(lon) & np.isfinite(lat) & (np.abs(lat) <= 90)
            if not ok.any():
                continue
            d = _angular_dist(lat, to_east_360_arr(lon), lat0, lon0)
            d[~ok] = np.inf
            j = int(np.argmin(d))
            if d[j] < best[0]:
                best = (float(d[j]), i, j)
        return best


def to_east_360_arr(lon: np.ndarray) -> np.ndarray:
    return np.mod(lon, 360.0)


async def find_pixel(loc: LocReader, lat0: float, lon0: float, coarse: int = 48) -> tuple[float, int, int]:
    n = loc.h.lines
    step = max(1, n // coarse)
    lines = list(range(0, n, step)) + [n - 1]
    best = await loc.best_in_lines(lines, lat0, lon0)
    while step > 1 and best[1] >= 0:
        centre = best[1]
        new_step = max(1, step // 8)
        lines = sorted({min(n - 1, max(0, centre + k * new_step)) for k in range(-8, 9)})
        cand = await loc.best_in_lines(lines, lat0, lon0)
        if cand[0] <= best[0]:
            best = cand
        step = new_step
    return best


async def extract(http: HttpClient, product: ode.OdeProduct, lat: float, lon: float,
                  radius_km: float) -> M3Extraction:
    s = get_settings()
    lon360 = to_east_360(lon)
    rfl_img = product.file_url(endswith="_RFL.IMG")
    rfl_hdr = product.file_url(endswith="_RFL.HDR")
    lbl_url = product.file_url(endswith="_L2.LBL") or product.label_url
    if not (rfl_img and rfl_hdr and lbl_url):
        raise ProviderError(PROVIDER, f"{product.pdsid}: incomplete file list (RFL.IMG/HDR/L2.LBL)")
    label = parse_pds3_label(await http.get_text(PROVIDER, lbl_url, timeout=30, max_bytes=256 * 1024))
    loc_name = label.get("CH1:PIXEL_LOCATION_FILE_NAME")
    if not loc_name or not loc_name.upper().endswith("_LOC.IMG"):
        raise ProviderError(PROVIDER, f"{product.pdsid}: label has no pixel-location file")
    l1b_id = loc_name[: -len("_LOC.IMG")] + "_RDN"
    l1b = await ode.product_by_pdsid(http, target="moon", ihid="CH1-ORB", iid="M3", pt="CALIV3", pdsid=l1b_id)
    if l1b is None:
        raise ProviderError(PROVIDER, f"L1B product {l1b_id} not found in ODE")
    loc_img, loc_hdr = l1b.file_url(endswith="_LOC.IMG"), l1b.file_url(endswith="_LOC.HDR")
    if not (loc_img and loc_hdr):
        raise ProviderError(PROVIDER, f"{l1b_id}: LOC backplane files missing")

    rfl = await open_cube(http, PROVIDER, rfl_img, rfl_hdr)
    loc_cube = await open_cube(http, PROVIDER, loc_img, loc_hdr)
    if (loc_cube.h.lines, loc_cube.h.samples) != (rfl.h.lines, rfl.h.samples):
        raise ProviderError(PROVIDER, "LOC and RFL dimensions differ; cannot co-register")
    if not rfl.h.wavelengths or len(rfl.h.wavelengths) != rfl.h.bands:
        raise ProviderError(PROVIDER, "RFL header lacks a complete wavelength table")

    loc = LocReader(loc_cube)
    ang, line, sample = await find_pixel(loc, lat, lon360)
    if line < 0:
        raise ProviderError(PROVIDER, "LOC backplane contains no valid coordinates")
    R = BODY_RADIUS_KM["moon"] * 1000
    dist_m = ang * R
    lon_l, lat_l = await loc.line(line)
    pix = None
    if 0 < sample < loc.h.samples - 1:
        d = _angular_dist(lat_l[sample - 1:sample + 2], to_east_360_arr(lon_l[sample - 1:sample + 2]),
                          lat_l[sample], to_east_360_arr(lon_l[sample:sample + 1])[0])
        pix = float(np.mean([d[0], d[2]]) * R)
    tol = max(1000.0, 3 * (pix or 300.0))
    if dist_m > tol:
        raise NoPixelNearPoint(f"nearest M3 pixel is {dist_m:.0f} m away (> {tol:.0f} m); footprint edge or gap")

    half = s.m3_max_half_window_px
    if pix:
        half = int(min(half, max(1, math.ceil(radius_km * 1000 / pix))))
    l0, l1 = max(0, line - half), min(rfl.h.lines - 1, line + half)
    c0, c1 = max(0, sample - half), min(rfl.h.samples - 1, sample + half)
    block = await rfl.bil_lines(l0, l1)                     # (lines, bands, samples)
    loc_block = await loc_cube.bil_lines(l0, l1)            # (lines, 3, samples)
    cube = block[:, :, c0:c1 + 1].astype(float)              # (L, B, S)
    lons = to_east_360_arr(loc_block[:, 0, c0:c1 + 1].astype(float))
    lats = loc_block[:, 1, c0:c1 + 1].astype(float)
    within = _angular_dist(lats, lons, lat, lon360) * R <= radius_km * 1000
    spectra = np.transpose(cube, (0, 2, 1)).reshape(-1, rfl.h.bands)
    within = within.reshape(-1)
    wl = np.asarray(rfl.h.wavelengths, dtype=float)
    use = (wl >= 540) & (wl <= 2600)   # drop the two shortest (noisy) bands and the thermal tail
    ignore = rfl.h.ignore_value if rfl.h.ignore_value is not None else -999.0
    sub = spectra[:, use]
    valid = within & np.all(np.isfinite(sub), axis=1) & np.all(sub != ignore, axis=1) \
        & np.all(sub > 0, axis=1) & np.all(sub < 1.5, axis=1)

    incidence = None
    try:
        obs_img, obs_hdr = l1b.file_url(endswith="_OBS.IMG"), l1b.file_url(endswith="_OBS.HDR")
        if obs_img and obs_hdr:
            obs = await open_cube(http, PROVIDER, obs_img, obs_hdr)
            names = [n.lower() for n in obs.h.band_names]
            bi = next((k for k, n in enumerate(names) if "sun" in n and "zenith" in n), None)
            if bi is not None and obs.h.interleave == "bil":
                row = await obs.bil_lines(line, line, bands=slice(bi, bi + 1))
                v = float(row[0, 0, sample])
                incidence = v if 0 <= v <= 180 else None
    except ProviderError:
        incidence = None  # optional geometry; absence is reported as null

    return M3Extraction(
        product_id=product.pdsid, rfl_url=rfl_img, loc_url=loc_img,
        observation_start=product.observation_start, observation_end=product.observation_end,
        line=line, sample=sample, pixel_distance_m=dist_m, pixel_size_m=pix, half_window=half,
        wavelengths=wl[use], spectra=sub[valid], n_window=int(within.sum()), n_valid=int(valid.sum()),
        incidence_deg=incidence, pixel_lat=lats.reshape(-1)[valid], pixel_lon=lons.reshape(-1)[valid],
        processing=[
            f"pixel located via L1B LOC backplane ({l1b_id}); nearest pixel line {line}, sample {sample}",
            f"window {l1 - l0 + 1}x{c1 - c0 + 1} px range-read from L2 RFL; "
            f"pixels > {radius_km} km from target masked",
            "bands < 540 nm and > 2600 nm excluded; values <= 0, >= 1.5, -999 or non-finite masked",
        ])


class NoPixelNearPoint(Exception):
    pass
