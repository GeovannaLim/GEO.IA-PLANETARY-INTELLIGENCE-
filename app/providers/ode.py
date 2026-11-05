"""PDS Geosciences Node — Orbital Data Explorer (ODE) REST and Granular Data
System (GDS) clients.

Verified against the live services and the manuals
(ODE REST V2.1.6, GDS REST V2.0):

* ODE REST  ``https://oderest.rsl.wustl.edu/live2/``
  query=product, results=opmf, output=JSON, IIPT (ihid/iid/pt), bbox
  (minlat/maxlat/westernlon/easternlon, planetocentric, east 0..360),
  loc=f (bbox intersects product footprint).
* ODE GDS   ``https://oderest.rsl.wustl.edu/livegds/``
  query=lolardr (Moon) / molapedr (Mars). Output files are CSV with only valid
  shots (quality flag 0, per the GDS manual §4.5.2). Topography columns:
  LOLA = radius - 1737.4 km sphere; MOLA PEDR = radius - areoid.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.config import get_settings
from app.providers.http import HttpClient, ProviderError, validate_url
from app.science.coordinates import Box
from app.services.cache import metadata_cache

log = logging.getLogger("geoia.ode")

ODE_REST = "https://oderest.rsl.wustl.edu/live2/"
ODE_GDS = "https://oderest.rsl.wustl.edu/livegds/"


def _as_list(x: Any) -> list:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _products(res: dict) -> list[dict]:
    """ODE returns ``"Products": "No Products Found"`` (a string) when empty."""
    prods = res.get("Products")
    if not isinstance(prods, dict):
        return []
    return [p for p in _as_list(prods.get("Product")) if isinstance(p, dict)]


@dataclass
class OdeProduct:
    pdsid: str
    ode_id: str | None
    ihid: str | None
    iid: str | None
    pt: str | None
    data_set_id: str | None
    observation_start: str | None
    observation_end: str | None
    center_lat: float | None
    center_lon: float | None
    footprint_wkt: str | None
    map_scale_m: float | None
    incidence_deg: float | None
    emission_deg: float | None
    phase_deg: float | None
    label_url: str | None
    product_page: str | None
    files: list[dict] = field(default_factory=list)
    raw_keys: list[str] = field(default_factory=list)

    def file_url(self, *, endswith: str) -> str | None:
        for f in self.files:
            name = (f.get("FileName") or "").upper()
            if name.endswith(endswith.upper()) and f.get("URL"):
                return f["URL"]
        return None


def _f(x: Any) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_product(p: dict) -> OdeProduct:
    files = _as_list((p.get("Product_files") or {}).get("Product_file"))
    return OdeProduct(
        pdsid=str(p.get("pdsid") or ""),
        ode_id=str(p.get("ode_id")) if p.get("ode_id") is not None else None,
        ihid=p.get("ihid"), iid=p.get("iid"), pt=p.get("pt"),
        data_set_id=p.get("Data_Set_Id"),
        observation_start=p.get("UTC_start_time"), observation_end=p.get("UTC_stop_time"),
        center_lat=_f(p.get("Center_latitude")), center_lon=_f(p.get("Center_longitude")),
        footprint_wkt=p.get("Footprint_C0_geometry") or p.get("Footprint_geometry"),
        map_scale_m=_f(p.get("Map_scale")),
        incidence_deg=_f(p.get("Incidence_angle")), emission_deg=_f(p.get("Emission_angle")),
        phase_deg=_f(p.get("Phase_angle")),
        label_url=p.get("LabelURL"), product_page=p.get("External_url"),
        files=[f for f in files if isinstance(f, dict)],
        raw_keys=sorted(p.keys()),
    )


async def search_products(http: HttpClient, *, target: str, ihid: str, iid: str, pt: str,
                          box: Box, limit: int = 25, results: str = "opmf",
                          extra: dict | None = None) -> tuple[list[OdeProduct], dict]:
    """Footprint-intersect search. Returns (products, query_params)."""
    products: list[OdeProduct] = []
    queries = []
    for sub in box.split():
        params = {"query": "product", "results": results, "output": "JSON", "target": target,
                  "ihid": ihid, "iid": iid, "pt": pt, "loc": "f", "limit": str(limit),
                  **sub.as_dict(), **(extra or {})}
        queries.append(params)
        key = ("ode", tuple(sorted(params.items())))
        data = await metadata_cache.get_or_set(
            key, get_settings().metadata_cache_ttl_s,
            lambda params=params: http.get_json("ODE REST", ODE_REST, params=params, timeout=60))
        res = (data or {}).get("ODEResults") or {}
        if str(res.get("Status", "")).lower() == "error" or res.get("Error"):
            raise ProviderError("ODE REST", f"query error: {res.get('Error') or res}")
        products.extend(parse_product(p) for p in _products(res))
    seen, unique = set(), []
    for p in products:
        if p.pdsid not in seen:
            seen.add(p.pdsid)
            unique.append(p)
    return unique, {"endpoint": ODE_REST, "requests": queries}


async def product_by_pdsid(http: HttpClient, *, target: str, ihid: str, iid: str, pt: str,
                           pdsid: str) -> OdeProduct | None:
    params = {"query": "product", "results": "opmf", "output": "JSON", "target": target,
              "ihid": ihid, "iid": iid, "pt": pt, "pdsid": pdsid}
    key = ("ode-id", tuple(sorted(params.items())))
    data = await metadata_cache.get_or_set(
        key, get_settings().metadata_cache_ttl_s,
        lambda: http.get_json("ODE REST", ODE_REST, params=params, timeout=60))
    res = (data or {}).get("ODEResults") or {}
    prods = [parse_product(p) for p in _products(res)]
    return prods[0] if prods else None


# --------------------------------------------------------------------------- #
# GDS laser altimetry
# --------------------------------------------------------------------------- #
@dataclass
class AltimetryResult:
    instrument: str
    lon360: np.ndarray
    lat: np.ndarray
    elev_m: np.ndarray
    times: list[str]
    box: Box
    reported_count: int
    files: list[str]
    query: dict
    retrieved_at: datetime
    status_note: str | None = None


GDS_QUERY = {"moon": ("lolardr", "u", "topo_simple_csv.csv"),
             "mars": ("molapedr", "v", "topo_csv.csv")}


class AltimetryTooLarge(Exception):
    pass


def parse_topo_csv(text: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Parse GDS topography CSV (lon, lat, topography[, utc, ...])."""
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return np.array([]), np.array([]), np.array([]), []
    lons, lats, elev, times = [], [], [], []
    for row in reader:
        if len(row) < 3:
            continue
        try:
            lo, la, z = float(row[0]), float(row[1]), float(row[2])
        except ValueError:
            continue
        if not (np.isfinite(lo) and np.isfinite(la) and np.isfinite(z)):
            continue
        lons.append(lo)
        lats.append(la)
        elev.append(z)
        times.append(row[3].strip() if len(row) > 3 else "")
    return np.asarray(lons), np.asarray(lats), np.asarray(elev), times


async def query_altimetry(http: HttpClient, body: str, box: Box) -> AltimetryResult:
    """Run one synchronous GDS query (splitting at 0° if needed) and download
    the topography CSV. Raises AltimetryTooLarge when the output exceeds the
    configured size or GDS rejects the area."""
    s = get_settings()
    query, results, suffix = GDS_QUERY[body]
    lon_all, lat_all, z_all, t_all, files, requests = [], [], [], [], [], []
    count, notes = 0, []
    for sub in box.split():
        params = {"query": query, "results": results, "output": "JSON", **sub.as_dict()}
        requests.append(params)
        data = await http.get_json("ODE GDS", ODE_GDS, params=params, timeout=150)
        res = (data or {}).get("GDSResults") or {}
        status = str(res.get("Status", ""))
        if status.lower() != "success":
            err = str(res.get("Error") or res.get("StateSummary") or res)
            if "too large" in err.lower():
                raise AltimetryTooLarge(err)
            raise ProviderError("ODE GDS", f"{query} failed: {err[:300]}")
        try:
            count += int(str(res.get("Count", "0")).replace(",", ""))
        except ValueError:
            pass
        notes.append(str((res.get("StateSummary") or {}).get("StatusNote", "")))
        target = None
        for f in _as_list((res.get("ResultFiles") or {}).get("ResultFile")):
            if str(f.get("URL", "")).endswith(suffix):
                target = f
        if target is None:
            if count == 0:
                continue
            raise ProviderError("ODE GDS", f"{query}: no {suffix} in result files")
        size_kb = _f(target.get("SizeKB")) or 0
        if size_kb > s.altimetry_max_file_kb:
            raise AltimetryTooLarge(f"{suffix} is {size_kb:.0f} KB > {s.altimetry_max_file_kb} KB")
        url = validate_url(str(target["URL"]))
        text = await http.get_text("ODE GDS", url, timeout=120,
                                   max_bytes=int((s.altimetry_max_file_kb + 64) * 1024))
        lo, la, z, t = parse_topo_csv(text)
        lon_all.append(lo)
        lat_all.append(la)
        z_all.append(z)
        t_all.extend(t)
        files.append(url)
    cat = (lambda xs: np.concatenate(xs) if xs else np.array([]))
    return AltimetryResult(
        instrument="LOLA" if body == "moon" else "MOLA",
        lon360=cat(lon_all), lat=cat(lat_all), elev_m=cat(z_all), times=t_all, box=box,
        reported_count=count, files=files, query={"endpoint": ODE_GDS, "requests": requests},
        retrieved_at=datetime.now(timezone.utc), status_note=" | ".join(n for n in notes if n) or None)
