"""Offline fakes of every external service, for automated tests ONLY.

Synthetic cubes and altimetry are generated here so tests exercise the real
parsing, range-read, projection and statistics code without network access.
Nothing in this module is importable by the application.
"""

from __future__ import annotations

import json
import math
import re

import httpx
import numpy as np
import respx

from app.science.coordinates import to_east_360

ODE = "https://oderest.rsl.wustl.edu/live2/"
GDS = "https://oderest.rsl.wustl.edu/livegds/"
M3_BASE = "https://planetarydata.jpl.nasa.gov/img/data/m3/FAKE"
CRISM_BASE = "https://pds-geosciences.wustl.edu/mro/FAKE"

M3_WL = np.round(np.arange(460.0, 2980.0, 30.0), 2)          # 84 bands
M3_LINES, M3_SAMPLES = 200, 20
CRISM_PARAMS = ["R770", "OLINDEX3", "LCPINDEX2", "HCPINDEX2", "BDI1000IR", "BD1900_2", "D2300", "BD2210_2"]
CRISM_IF_WL = [700.0, 800.0, 1000.0, 1300.0, 1500.0, 1700.0, 2000.0, 2300.0]
MARS_R = 3394839.8


def ranged(content: bytes):
    def handler(request: httpx.Request) -> httpx.Response:
        rng = request.headers.get("Range")
        if not rng:
            return httpx.Response(200, content=content)
        a, b = (int(x) for x in re.match(r"bytes=(\d+)-(\d+)", rng).groups())
        return httpx.Response(206, content=content[a:b + 1])
    return handler


# --------------------------------------------------------------------------- #
# synthetic products
# --------------------------------------------------------------------------- #
def m3_cubes(lat0: float, lon0: float, depth1: float = 0.15, depth2: float = 0.10):
    lines, samples = np.meshgrid(np.arange(M3_LINES), np.arange(M3_SAMPLES), indexing="ij")
    lat = lat0 + (lines - 100) * 0.004
    lon = to_east_360(lon0) + (samples - 10) * 0.004 / max(0.05, math.cos(math.radians(lat0)))
    loc = np.zeros((M3_LINES, 3, M3_SAMPLES), dtype="<f8")
    loc[:, 0, :], loc[:, 1, :], loc[:, 2, :] = lon, lat, 1737400.0
    wl = M3_WL
    cont = 0.08 + 0.00003 * (wl - 460)
    spec = cont * (1 - depth1 * np.exp(-((wl - 1000) / 90) ** 2) - depth2 * np.exp(-((wl - 2000) / 180) ** 2))
    rng = np.random.default_rng(0)
    rfl = np.empty((M3_LINES, wl.size, M3_SAMPLES), dtype="<f4")
    for i in range(M3_LINES):
        rfl[i] = (spec[:, None] * (1 + 0.002 * rng.standard_normal((wl.size, M3_SAMPLES)))).astype("<f4")
    rfl[0, :, 0] = -999.0
    obs = np.full((M3_LINES, 10, M3_SAMPLES), 35.0, dtype="<f4")
    return loc.tobytes(), rfl.tobytes(), obs.tobytes()


def m3_headers():
    wl = ",\n ".join(f"{w:.2f}" for w in M3_WL)
    rfl = (f"ENVI\nsamples = {M3_SAMPLES}\nlines = {M3_LINES}\nbands = {M3_WL.size}\nheader offset = 0\n"
           f"data type = 4\ninterleave = bil\nbyte order = 0\ndata ignore value = -999.0\nwavelength = {{\n {wl}}}\n")
    loc = (f"ENVI\nsamples = {M3_SAMPLES}\nlines = {M3_LINES}\nbands = 3\nheader offset = 0\ndata type = 5\n"
           "interleave = bil\nbyte order = 0\nband names = {\n Longitude, Latitude, Radius}\n")
    obs = (f"ENVI\nsamples = {M3_SAMPLES}\nlines = {M3_LINES}\nbands = 10\nheader offset = 0\ndata type = 4\n"
           "interleave = bil\nbyte order = 0\nband names = {\n To-Sun Azimuth (deg), To-Sun Zenith (deg), "
           "To-M3 Azimuth (deg),\n To-M3 Zenith (deg), Phase (deg), a, b, c, d, e}\n")
    return rfl, loc, obs


def crism_cubes(lat0: float, lon0: float, olivine: float = 0.08):
    lines, samples = 100, 80
    std = 15.0
    x_tie = MARS_R * math.radians(to_east_360(lon0) - 0.02) * math.cos(math.radians(std))
    y_tie = MARS_R * math.radians(lat0 + 0.02)
    map_info = (f"{{MRO Mars Equirectangular [IAU 2000], 1.0000, 1.0000, {x_tie:.4f}, {y_tie:.4f}, 3.6e+01, "
                f"3.6e+01, D_Mars, units=Meters}}")
    proj = f"{{17, {MARS_R}, {std}, 0.000000, 0.0, 0.0, D_Mars, MRO Mars Equirectangular, units=Meters}}"
    rng = np.random.default_rng(1)
    su = np.empty((len(CRISM_PARAMS), lines, samples), dtype="<f4")
    for i, name in enumerate(CRISM_PARAMS):
        base = {"R770": 0.2, "OLINDEX3": olivine}.get(name, 0.0)
        su[i] = base + 0.002 * rng.standard_normal((lines, samples))
    su[:, 0, 0] = 65535.0
    ifc = np.empty((len(CRISM_IF_WL), lines, samples), dtype="<f4")
    for i, w in enumerate(CRISM_IF_WL):
        ifc[i] = 0.2 * (1 - (0.12 if w == 1000.0 else 0.0)) + 0.001 * rng.standard_normal((lines, samples))
    names = ",\n ".join(CRISM_PARAMS)
    su_hdr = (f"ENVI\nsamples = {samples}\nlines = {lines}\nbands = {len(CRISM_PARAMS)}\nheader offset = 0\n"
              f"data type = 4\ninterleave = bsq\nbyte order = 0\nmap info = {map_info}\nprojection info = {proj}\n"
              f"data ignore value = 6.55350000e+04\nband names = {{\n {names}}}\n")
    wl = ", ".join(f"{w:.2f}" for w in CRISM_IF_WL)
    if_hdr = (f"ENVI\nsamples = {samples}\nlines = {lines}\nbands = {len(CRISM_IF_WL)}\nheader offset = 0\n"
              f"data type = 4\ninterleave = bsq\nbyte order = 0\nmap info = {map_info}\nprojection info = {proj}\n"
              f"data ignore value = 6.55350000e+04\nwavelength = {{\n {wl}}}\n")
    return su.tobytes(), ifc.tobytes(), su_hdr, if_hdr


def footprint_around(lat: float, lon: float, d: float = 0.3) -> str:
    x = to_east_360(lon)
    return f"POLYGON (({x - d} {lat - d}, {x + d} {lat - d}, {x + d} {lat + d}, {x - d} {lat + d}, {x - d} {lat - d}))"


def ode_product(pdsid: str, lat: float, lon: float, files: list[tuple[str, str]], **extra) -> dict:
    p = {"pdsid": pdsid, "ode_id": "1", "ihid": "X", "iid": "Y", "pt": "Z", "Data_Set_Id": "FAKE",
         "UTC_start_time": "2009-06-09T18:32:54", "UTC_stop_time": "2009-06-09T18:50:00",
         "Center_latitude": str(lat), "Center_longitude": str(to_east_360(lon)),
         "Footprint_C0_geometry": footprint_around(lat, lon),
         "Product_files": {"Product_file": [{"FileName": n, "URL": u, "Type": "Product"} for n, u in files]}}
    p.update(extra)
    return p


def gds_points(body: str, box: dict, slope_deg: float = 2.0, density: int = 4000) -> str:
    rng = np.random.default_rng(2)
    lat = rng.uniform(box["minlat"], box["maxlat"], density)
    w, e = box["westernlon"], box["easternlon"]
    lon = rng.uniform(w, e if e >= w else e + 360, density) % 360
    lat0 = (box["minlat"] + box["maxlat"]) / 2
    R = 1737400.0 if body == "moon" else 3396190.0
    y = np.radians(lat - lat0) * R
    z = -2000.0 + math.tan(math.radians(slope_deg)) * y
    head = "Pt_Longitude, Pt_Latitude, Topography\n" if body == "moon" else "LONG_EAST,LAT_NORTH, TOPOGRAPHY, UTC\n"
    rows = [f"{a:.7f}, {b:.7f}, {c:.2f}" + ("" if body == "moon" else ",2000-05-19T16:30:30.077")
            for a, b, c in zip(lon, lat, z)]
    return head + "\n".join(rows) + "\n"


TREK_CAPS = """<?xml version="1.0"?><Capabilities xmlns="http://www.opengis.net/wmts/1.0"
 xmlns:ows="http://www.opengis.net/ows/1.1"><Contents><Layer><ows:Identifier>L</ows:Identifier>
 <Format>image/jpeg</Format><TileMatrixSetLink><TileMatrixSet>default028mm</TileMatrixSet></TileMatrixSetLink>
 <ResourceURL format="image/jpeg" resourceType="tile" template="https://trek.nasa.gov/tiles/X/{TileMatrix}/{TileRow}/{TileCol}.jpg"/>
 </Layer><TileMatrixSet><ows:Identifier>default028mm</ows:Identifier><ows:SupportedCRS>urn:ogc:def:crs:EPSG::104903</ows:SupportedCRS>
 <TileMatrix><ows:Identifier>0</ows:Identifier></TileMatrix><TileMatrix><ows:Identifier>1</ows:Identifier></TileMatrix>
 </TileMatrixSet></Contents></Capabilities>"""


def trek_catalog(body: str) -> dict:
    from app.providers.trek import CURATED
    docs = [{"productLabel": lab, "title": lab, "coverage": "Global", "bbox": "-180,-90,180,90"}
            for lab, _ in CURATED[body]]
    return {"response": {"docs": docs}}


# --------------------------------------------------------------------------- #
# router
# --------------------------------------------------------------------------- #
class FakeWorld:
    """Configurable fake of ODE/GDS/Trek/PDS/STAC/M3/CRISM."""

    def __init__(self, lat: float, lon: float, *, m3: bool = True, crism: bool = True, gds_status: int = 200,
                 trek_status: int = 200, pds_status: int = 200, ode_status: int = 200, gds_empty: bool = False,
                 crism_incidence: str = "40"):
        self.lat, self.lon = lat, lon
        self.crism_incidence = crism_incidence
        self.m3, self.crism = m3, crism
        self.gds_status, self.trek_status, self.pds_status, self.ode_status = gds_status, trek_status, pds_status, ode_status
        self.gds_empty = gds_empty
        self.loc, self.rfl, self.obs = m3_cubes(lat, lon)
        self.su, self.ifc, self.su_hdr, self.if_hdr = crism_cubes(lat, lon)
        self.gds_boxes: list[dict] = []

    # ODE REST
    def ode(self, request: httpx.Request) -> httpx.Response:
        if self.ode_status != 200:
            return httpx.Response(self.ode_status)
        q = dict(request.url.params)
        pt = q.get("pt")
        prods = []
        if pt == "REFIMG" and self.m3:
            prods = [ode_product("M3GFAKE_V01_RFL", self.lat, self.lon, [
                ("M3GFAKE_V01_L2.LBL", f"{M3_BASE}/M3GFAKE_V01_L2.LBL"),
                ("M3GFAKE_V01_RFL.HDR", f"{M3_BASE}/M3GFAKE_V01_RFL.HDR"),
                ("M3GFAKE_V01_RFL.IMG", f"{M3_BASE}/M3GFAKE_V01_RFL.IMG")])]
        elif pt == "CALIV3":
            prods = [ode_product("M3GFAKE_V03_RDN", self.lat, self.lon, [
                ("M3GFAKE_V03_LOC.HDR", f"{M3_BASE}/M3GFAKE_V03_LOC.HDR"),
                ("M3GFAKE_V03_LOC.IMG", f"{M3_BASE}/M3GFAKE_V03_LOC.IMG"),
                ("M3GFAKE_V03_OBS.HDR", f"{M3_BASE}/M3GFAKE_V03_OBS.HDR"),
                ("M3GFAKE_V03_OBS.IMG", f"{M3_BASE}/M3GFAKE_V03_OBS.IMG")])]
        elif pt == "MTRDR" and self.crism:
            prods = [ode_product("frtfake_07_if000j_mtr3", self.lat, self.lon, [
                ("FRTFAKE_07_SU000J_MTR3.HDR", f"{CRISM_BASE}/su.hdr"),
                ("FRTFAKE_07_SU000J_MTR3.IMG", f"{CRISM_BASE}/su.img"),
                ("FRTFAKE_07_IF000J_MTR3.HDR", f"{CRISM_BASE}/if.hdr"),
                ("FRTFAKE_07_IF000J_MTR3.IMG", f"{CRISM_BASE}/if.img")], Map_scale="36", Incidence_angle=self.crism_incidence)]
        body = {"ODEResults": {"Status": "Success", "Products": {"Product": prods} if prods else "No Products Found"}}
        return httpx.Response(200, json=body)

    def gds(self, request: httpx.Request) -> httpx.Response:
        if self.gds_status != 200:
            return httpx.Response(self.gds_status)
        q = dict(request.url.params)
        box = {k: float(q[k]) for k in ("minlat", "maxlat", "westernlon", "easternlon")}
        self.gds_boxes.append(box)
        name = "topo_simple_csv.csv" if q["query"] == "lolardr" else "topo_csv.csv"
        idx = len(self.gds_boxes) - 1
        res = {"GDSResults": {"Status": "Success", "Count": "0" if self.gds_empty else "4000",
                              "StateSummary": {"StatusNote": "fake"},
                              "ResultFiles": {"ResultFile": [] if self.gds_empty else [
                                  {"SizeKB": "120", "URL": f"https://oderest.rsl.wustl.edu/output/fake{idx}/X_{name}"}]}}}
        return httpx.Response(200, json=res)

    def gds_file(self, request: httpx.Request) -> httpx.Response:
        idx = int(re.search(r"/fake(\d+)/", str(request.url)).group(1))
        body = "moon" if "topo_simple" in str(request.url) else "mars"
        return httpx.Response(200, text=gds_points(body, self.gds_boxes[idx]))

    def install(self, router: respx.MockRouter) -> None:
        rfl_hdr, loc_hdr, obs_hdr = m3_headers()
        router.get(url__startswith=ODE).mock(side_effect=self.ode)
        router.get(url__startswith=GDS).mock(side_effect=self.gds)
        router.get(url__startswith="https://oderest.rsl.wustl.edu/output/").mock(side_effect=self.gds_file)
        router.get(f"{M3_BASE}/M3GFAKE_V01_L2.LBL").mock(return_value=httpx.Response(
            200, text='PDS_VERSION_ID = PDS3\nCH1:PIXEL_LOCATION_FILE_NAME = "M3GFAKE_V03_LOC.IMG"\nEND\n'))
        router.get(f"{M3_BASE}/M3GFAKE_V01_RFL.HDR").mock(return_value=httpx.Response(200, text=rfl_hdr))
        router.get(f"{M3_BASE}/M3GFAKE_V03_LOC.HDR").mock(return_value=httpx.Response(200, text=loc_hdr))
        router.get(f"{M3_BASE}/M3GFAKE_V03_OBS.HDR").mock(return_value=httpx.Response(200, text=obs_hdr))
        router.get(f"{M3_BASE}/M3GFAKE_V01_RFL.IMG").mock(side_effect=ranged(self.rfl))
        router.get(f"{M3_BASE}/M3GFAKE_V03_LOC.IMG").mock(side_effect=ranged(self.loc))
        router.get(f"{M3_BASE}/M3GFAKE_V03_OBS.IMG").mock(side_effect=ranged(self.obs))
        router.get(f"{CRISM_BASE}/su.hdr").mock(return_value=httpx.Response(200, text=self.su_hdr))
        router.get(f"{CRISM_BASE}/if.hdr").mock(return_value=httpx.Response(200, text=self.if_hdr))
        router.get(f"{CRISM_BASE}/su.img").mock(side_effect=ranged(self.su))
        router.get(f"{CRISM_BASE}/if.img").mock(side_effect=ranged(self.ifc))

        def trek_cat(request):
            if self.trek_status != 200:
                return httpx.Response(self.trek_status)
            body = "moon" if "/moon/" in str(request.url) else "mars"
            return httpx.Response(200, json=trek_catalog(body))
        router.get(url__regex=r"https://trek\.nasa\.gov/(moon|mars)/TrekServices/.*").mock(side_effect=trek_cat)
        router.get(url__regex=r"https://trek\.nasa\.gov/tiles/.*WMTSCapabilities\.xml").mock(
            return_value=httpx.Response(200, text=TREK_CAPS))
        router.get(url__startswith="https://pds.nasa.gov/api/").mock(
            side_effect=lambda r: httpx.Response(self.pds_status, json={"summary": {"hits": 0}, "data": []}))
        router.get(url__startswith="https://stac.astrogeology.usgs.gov/").mock(
            return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []}))


def dumps(x) -> str:
    return json.dumps(x, default=str)
