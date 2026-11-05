"""NASA PDS Registry API (``https://pds.nasa.gov/api/search/1/products``).

Verified live behaviour that shapes this client:
* The endpoint answers 307 -> ``pds.mcp.nasa.gov`` (redirect is followed and
  re-validated against the allow-list).
* ``keywords=`` is effectively ignored (returns the full registry), so only
  structured ``q=`` filters are used.
* Spatial filtering works on PDS4 ``cart:Bounding_Coordinates`` fields.
* PDS3-only holdings (e.g. MRO CRISM TRDR/MTRDR, Chandrayaan-1 M3) are NOT
  indexed: an empty answer is therefore reported as "not indexed in the PDS
  registry", never as "no coverage". ODE remains the authoritative discovery
  service for those instruments.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.providers.http import HttpClient, ProviderError
from app.science.coordinates import Box
from app.services.cache import metadata_cache

PDS_SEARCH = "https://pds.nasa.gov/api/search/1/products"

FIELDS = ",".join([
    "lid", "title", "pds:Time_Coordinates.pds:start_date_time",
    "pds:Time_Coordinates.pds:stop_date_time", "ref_lid_instrument",
    "cart:Bounding_Coordinates.cart:west_bounding_coordinate",
    "cart:Bounding_Coordinates.cart:east_bounding_coordinate",
    "cart:Bounding_Coordinates.cart:north_bounding_coordinate",
    "cart:Bounding_Coordinates.cart:south_bounding_coordinate",
])

INSTRUMENT_LID = {
    "lola": "urn:nasa:pds:context:instrument:lro.lola",
    "diviner": "urn:nasa:pds:context:instrument:lro.dlre",
    "crism": "urn:nasa:pds:context:instrument:mro.crism",
    "mola": "urn:nasa:pds:context:instrument:mgs.mola",
}


def _first(v: Any) -> Any:
    return v[0] if isinstance(v, list) and v else v


async def search_spatial(http: HttpClient, *, instrument: str, lat: float, lon360: float,
                         limit: int = 5) -> dict:
    """PDS4 products of ``instrument`` whose bounding box contains the point."""
    lid = INSTRUMENT_LID[instrument]
    q = (f'(ref_lid_instrument eq "{lid}" and '
         f'cart:Bounding_Coordinates.cart:west_bounding_coordinate le {lon360:.4f} and '
         f'cart:Bounding_Coordinates.cart:east_bounding_coordinate ge {lon360:.4f} and '
         f'cart:Bounding_Coordinates.cart:south_bounding_coordinate le {lat:.4f} and '
         f'cart:Bounding_Coordinates.cart:north_bounding_coordinate ge {lat:.4f})')
    params = {"q": q, "limit": str(limit), "fields": FIELDS}

    async def fetch() -> dict:
        return await http.get_json("PDS API", PDS_SEARCH, params=params, timeout=45)

    data = await metadata_cache.get_or_set(("pds", instrument, round(lat, 3), round(lon360, 3)),
                                           get_settings().metadata_cache_ttl_s, fetch)
    if not isinstance(data, dict) or "summary" not in data:
        raise ProviderError("PDS API", "unexpected response shape")
    items = []
    for d in data.get("data") or []:
        props = d.get("properties") or {}
        items.append({
            "lid": d.get("id"), "title": d.get("title"),
            "start": _first(props.get("pds:Time_Coordinates.pds:start_date_time")),
            "stop": _first(props.get("pds:Time_Coordinates.pds:stop_date_time")),
        })
    return {"hits": (data.get("summary") or {}).get("hits"), "items": items,
            "query": {"endpoint": PDS_SEARCH, "params": params}}


async def instrument_indexed(http: HttpClient, instrument: str) -> int | None:
    """Total products registered for an instrument (cheap, cached)."""
    lid = INSTRUMENT_LID[instrument]
    params = {"q": f'ref_lid_instrument eq "{lid}"', "limit": "0"}

    async def fetch() -> int | None:
        data = await http.get_json("PDS API", PDS_SEARCH, params=params, timeout=45)
        return int(((data or {}).get("summary") or {}).get("hits") or 0)

    return await metadata_cache.get_or_set(("pds-count", instrument), 24 * 3600, fetch)


async def resolve(http: HttpClient, lidvid: str) -> dict:
    """Resolve a PDS4 identifier to its registry metadata."""
    url = f"{PDS_SEARCH}/{lidvid}"
    return await http.get_json("PDS API", url, timeout=45)


def box_center(box: Box) -> tuple[float, float]:
    lat = (box.south + box.north) / 2
    if box.wraps:
        lon = ((box.west + box.east + 360.0) / 2) % 360.0
    else:
        lon = (box.west + box.east) / 2
    return lat, lon
