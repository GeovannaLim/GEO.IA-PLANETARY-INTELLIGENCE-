"""MRO CRISM Map-projected Targeted Reduced Data Records (MTRDR) at a point.

Data path (verified live):
1. ODE REST product search  ihid=MRO iid=CRISM pt=MTRDR (PDS Geosciences
   node, mro-m-crism-5-rdr-mptargeted-v1). Each product has:
   * ``*_SU*_MTR3.IMG`` — 60 summary parameters (Viviano-Beck et al. 2014),
     BSQ float32, ignore 65535;
   * ``*_IF*_MTR3.IMG`` — corrected I/F cube, 489 bands, BSQ float32.
   Both are map-projected (Equirectangular, IAU 2000 Mars sphere, planetocentric,
   east-positive) with an ENVI ``map info`` tie point.
2. The target pixel is computed analytically from the map projection and a
   window of rows is range-read band by band (BSQ).
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field

import numpy as np

from app.config import get_settings
from app.providers import ode
from app.providers.envi import EnviHeader, RemoteCube, open_cube
from app.providers.http import HttpClient, ProviderError
from app.science.coordinates import to_east_180, to_east_360
from app.science.spectral import CRISM_PARAMS

PROVIDER = "PDS Geosciences (CRISM)"

LIMITATIONS = [
    "MTRDR summary parameters are screening products; positive values can arise from noise, "
    "residual atmospheric CO2 or detector artefacts (Viviano-Beck et al. 2014).",
    "CRISM targeted footprints are ~10 km wide; the analysis window covers only the part of the "
    "region imaged by the selected observation.",
    "MTRDR I/F includes CRISM team photometric and volcano-scan atmospheric corrections; legacy band "
    "depths therefore differ in calibration from the terrestrial EMIT surface reflectance.",
]

POLAR_LIMITATION = ("Polar stereographic product: pixel positions use the ellipsoidal equations stated in "
                    "MTR_MAP.CAT; checked against product labels to 0.01-0.03 deg (about 1-2 km near the pole).")

LEGACY_WL = (800.0, 1000.0, 1300.0, 1700.0, 2000.0, 2300.0)


@dataclass
class MapProjection:
    radius_m: float
    std_parallel_deg: float
    central_meridian_deg: float
    tie_px: tuple[float, float]
    tie_xy: tuple[float, float]
    pixel_size: tuple[float, float]

    @classmethod
    def from_header(cls, h: EnviHeader) -> "MapProjection | PolarStereographic":
        mi, pi = h.map_info, h.projection_info
        if len(mi) >= 7 and "polar stereographic" in mi[0].lower():
            return PolarStereographic.from_header(h)
        if len(mi) < 7 or len(pi) < 4 or "equirectangular" not in mi[0].lower():
            raise ProviderError(PROVIDER, "unsupported or missing map projection in header")
        return cls(radius_m=float(pi[1]), std_parallel_deg=float(pi[2]), central_meridian_deg=float(pi[3]),
                   tie_px=(float(mi[1]), float(mi[2])), tie_xy=(float(mi[3]), float(mi[4])),
                   pixel_size=(float(mi[5]), float(mi[6])))

    def xy(self, lat: float, lon: float) -> tuple[float, float]:
        x = self.radius_m * math.radians(lon - self.central_meridian_deg) * math.cos(math.radians(self.std_parallel_deg))
        y = self.radius_m * math.radians(lat)
        return x, y

    def pixel(self, lat: float, lon: float) -> tuple[float, float]:
        """Fractional (row, col), 0-based, of the point."""
        x, y = self.xy(lat, lon)
        col = (x - self.tie_xy[0]) / self.pixel_size[0] + (self.tie_px[0] - 1.0)
        row = (self.tie_xy[1] - y) / self.pixel_size[1] + (self.tie_px[1] - 1.0)
        return row, col

    def latlon(self, row: np.ndarray, col: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Lat/lon of pixel centres (0-based indices)."""
        x = self.tie_xy[0] + (col - (self.tie_px[0] - 1.0) + 0.5) * self.pixel_size[0]
        y = self.tie_xy[1] - (row - (self.tie_px[1] - 1.0) + 0.5) * self.pixel_size[1]
        lat = np.degrees(y / self.radius_m)
        lon = np.degrees(x / (self.radius_m * math.cos(math.radians(self.std_parallel_deg)))) + self.central_meridian_deg
        return lat, lon


@dataclass
class PolarStereographic:
    """MTRDR polar stereographic grid (observations poleward of +/-65 deg).

    catalog/MTR_MAP.CAT (mrocr_4001): polar products use the IAU 2000 ellipsoid (Re 3396.19 km,
    Rp 3376.2 km), true scale at the pole, planetocentric latitude, east longitude; south: longitude 0
    points up and 90E right; north: longitude 0 points down and 90E right. The catalog states the
    products were generated with the ELLIPSOID form of the equations (its spherical equations are
    only a fallback). Checked against product labels (MINIMUM/MAXIMUM_LATITUDE): the ellipsoidal
    form applied to the planetocentric latitude reproduces the label footprint to 0.01-0.03 deg,
    the spherical fallback is 0.05-0.08 deg off (docs/RELATORIO_TESTES_CIENTIFICOS.md).
    Formulas: Snyder (1987), USGS Professional Paper 1395, polar aspect, k0 = 1 at the pole.
    The grid comes from the ENVI ``map info`` tie point (upper-left corner of pixel 1,1).
    """
    south: bool
    radius_m: float
    tie_px: tuple[float, float]
    tie_xy: tuple[float, float]
    pixel_size: tuple[float, float]

    A = 3396190.0
    RP = 3376200.0

    @classmethod
    def from_header(cls, h: EnviHeader) -> "PolarStereographic":
        mi = h.map_info
        name = mi[0].lower()
        if "south" not in name and "north" not in name:
            raise ProviderError(PROVIDER, "polar stereographic header without hemisphere")
        return cls(south="south" in name, radius_m=cls.RP, tie_px=(float(mi[1]), float(mi[2])),
                   tie_xy=(float(mi[3]), float(mi[4])), pixel_size=(float(mi[5]), float(mi[6])))

    @classmethod
    def _e(cls) -> float:
        return math.sqrt(1.0 - (cls.RP / cls.A) ** 2)

    @classmethod
    def _k(cls) -> float:
        e = cls._e()
        return 2.0 * cls.A / math.sqrt((1 + e) ** (1 + e) * (1 - e) ** (1 - e))

    def xy(self, lat, lon):
        e = self._e()
        phi = np.radians(-np.asarray(lat, float) if self.south else np.asarray(lat, float))
        t = np.tan(np.pi / 4 - phi / 2) / ((1 - e * np.sin(phi)) / (1 + e * np.sin(phi))) ** (e / 2)
        rho = self._k() * t
        lam = np.radians(lon)
        return rho * np.sin(lam), (rho * np.cos(lam) if self.south else -rho * np.cos(lam))

    def pixel(self, lat: float, lon: float) -> tuple[float, float]:
        """Fractional (row, col), 0-based, of the point."""
        x, y = self.xy(lat, lon)
        col = (x - self.tie_xy[0]) / self.pixel_size[0] + (self.tie_px[0] - 1.0)
        row = (self.tie_xy[1] - y) / self.pixel_size[1] + (self.tie_px[1] - 1.0)
        return float(row), float(col)

    def latlon(self, row: np.ndarray, col: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Lat/lon of pixel centres (0-based indices); longitude east 0-360."""
        x = self.tie_xy[0] + (col - (self.tie_px[0] - 1.0) + 0.5) * self.pixel_size[0]
        y = self.tie_xy[1] - (row - (self.tie_px[1] - 1.0) + 0.5) * self.pixel_size[1]
        e, t = self._e(), np.hypot(x, y) / self._k()
        phi = np.pi / 2 - 2 * np.arctan(t)
        for _ in range(12):                      # converges to < 1e-12 rad well before 12 iterations
            phi = np.pi / 2 - 2 * np.arctan(t * ((1 - e * np.sin(phi)) / (1 + e * np.sin(phi))) ** (e / 2))
        lat = -np.degrees(phi) if self.south else np.degrees(phi)
        lon = np.degrees(np.arctan2(x, y if self.south else -y)) % 360.0
        return lat, lon


@dataclass
class CrismExtraction:
    product_id: str
    su_url: str
    if_url: str | None
    observation_start: str | None
    observation_end: str | None
    row: int
    col: int
    pixel_size_m: float
    half_window: int
    params: dict[str, np.ndarray]            # parameter -> valid pixel values
    legacy_spectra: np.ndarray | None        # (n_valid, 6) at LEGACY_WL
    legacy_wavelengths: np.ndarray | None
    n_window: int
    n_valid: int
    incidence_deg: float | None
    emission_deg: float | None
    processing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=lambda: list(LIMITATIONS))


class OutsideImage(Exception):
    pass


def locate(proj: MapProjection, h: EnviHeader, lat: float, lon: float) -> tuple[int, int]:
    for lon_branch in (to_east_360(lon), to_east_180(lon)):
        r, c = proj.pixel(lat, lon_branch)
        if 0 <= r < h.lines and 0 <= c < h.samples:
            return int(math.floor(r)), int(math.floor(c))
    raise OutsideImage("point falls outside the map-projected cube")


async def _read_window(cube: RemoteCube, band: int, r0: int, r1: int, c0: int, c1: int) -> np.ndarray:
    rows = await cube.bsq_rows(band, r0, r1)
    return rows[:, c0:c1 + 1].astype(float)


async def extract(http: HttpClient, product: ode.OdeProduct, lat: float, lon: float,
                  radius_km: float) -> CrismExtraction:
    s = get_settings()
    su_img = next((f["URL"] for f in product.files
                   if "_SU" in (f.get("FileName") or "").upper() and f["FileName"].upper().endswith(".IMG")), None)
    su_hdr = next((f["URL"] for f in product.files
                   if "_SU" in (f.get("FileName") or "").upper() and f["FileName"].upper().endswith(".HDR")), None)
    if_img = next((f["URL"] for f in product.files
                   if "_IF" in (f.get("FileName") or "").upper() and f["FileName"].upper().endswith("_MTR3.IMG")), None)
    if_hdr = next((f["URL"] for f in product.files
                   if "_IF" in (f.get("FileName") or "").upper() and f["FileName"].upper().endswith("_MTR3.HDR")), None)
    if not (su_img and su_hdr):
        raise ProviderError(PROVIDER, f"{product.pdsid}: summary-parameter (SU) files missing")

    su = await open_cube(http, PROVIDER, su_img, su_hdr)
    if su.h.interleave != "bsq":
        raise ProviderError(PROVIDER, f"SU cube interleave {su.h.interleave} not supported")
    proj = MapProjection.from_header(su.h)
    row, col = locate(proj, su.h, lat, lon)
    px = abs(proj.pixel_size[0])
    half = int(min(s.crism_max_half_window_px, max(1, math.ceil(radius_km * 1000 / px))))
    r0, r1 = max(0, row - half), min(su.h.lines - 1, row + half)
    c0, c1 = max(0, col - half), min(su.h.samples - 1, col + half)

    rr, cc = np.meshgrid(np.arange(r0, r1 + 1), np.arange(c0, c1 + 1), indexing="ij")
    plat, plon = proj.latlon(rr.astype(float), cc.astype(float))
    R = proj.radius_m
    p1, p2 = math.radians(lat), np.radians(plat)
    dl = np.radians(plon - (to_east_360(lon) if abs(plon.mean() - to_east_360(lon)) < 180 else to_east_180(lon)))
    a = np.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    within = (2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))) <= radius_km * 1000

    names = {n.upper(): i for i, n in enumerate(su.h.band_names)}
    wanted = [n for n in CRISM_PARAMS if n in names]
    if not wanted:
        raise ProviderError(PROVIDER, "SU header lists none of the expected summary parameters")
    windows = await asyncio.gather(*(_read_window(su, names[n], r0, r1, c0, c1) for n in wanted))
    ignore = su.h.ignore_value if su.h.ignore_value is not None else 65535.0
    stack = np.stack(windows)                       # (P, rows, cols)
    finite = np.isfinite(stack) & (stack != ignore) & (np.abs(stack) < 1e3)
    valid = within & finite.all(axis=0)
    params = {n: stack[i][valid] for i, n in enumerate(wanted)}

    legacy, legacy_wl = None, None
    processing = [
        (f"map projection from SU header (Polar Stereographic, {'south' if proj.south else 'north'}, IAU 2000 "
         f"ellipsoid per MTR_MAP.CAT); target pixel row {row}, col {col}"
         if isinstance(proj, PolarStereographic) else
         f"map projection from SU header (Equirectangular, R={R:.1f} m, std parallel {proj.std_parallel_deg}°); "
         f"target pixel row {row}, col {col}"),
        f"window {r1 - r0 + 1}x{c1 - c0 + 1} px ({px:.0f} m/px); pixels > {radius_km} km masked; "
        f"ignore value {ignore:g} and non-finite masked",
    ]
    if if_img and if_hdr:
        ifc = await open_cube(http, PROVIDER, if_img, if_hdr)
        if ifc.h.interleave == "bsq" and ifc.h.wavelengths and (ifc.h.lines, ifc.h.samples) == (su.h.lines, su.h.samples):
            wl = np.asarray(ifc.h.wavelengths, dtype=float)
            idx = [int(np.argmin(np.abs(wl - w))) for w in LEGACY_WL]
            if all(abs(wl[i] - w) <= 20 for i, w in zip(idx, LEGACY_WL)):
                bands = await asyncio.gather(*(_read_window(ifc, i, r0, r1, c0, c1) for i in idx))
                st = np.stack(bands)                                   # (6, rows, cols)
                ign = ifc.h.ignore_value if ifc.h.ignore_value is not None else 65535.0
                ok = valid & (np.isfinite(st) & (st != ign) & (st > 0) & (st < 2)).all(axis=0)
                legacy = st[:, ok].T                                   # (n, 6)
                legacy_wl = wl[idx]
                processing.append(f"I/F bands nearest {', '.join(str(int(w)) for w in LEGACY_WL)} nm read "
                                  f"(actual {', '.join(f'{wl[i]:.0f}' for i in idx)} nm) for legacy band depths")

    return CrismExtraction(
        product_id=product.pdsid, su_url=su_img, if_url=if_img,
        observation_start=product.observation_start, observation_end=product.observation_end,
        row=row, col=col, pixel_size_m=px, half_window=half, params=params,
        legacy_spectra=legacy, legacy_wavelengths=legacy_wl,
        n_window=int(within.sum()), n_valid=int(valid.sum()),
        incidence_deg=product.incidence_deg, emission_deg=product.emission_deg, processing=processing,
        limitations=list(LIMITATIONS) + ([POLAR_LIMITATION] if isinstance(proj, PolarStereographic) else []))
