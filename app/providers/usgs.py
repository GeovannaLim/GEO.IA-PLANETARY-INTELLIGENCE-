"""USGS Astrogeology Science Center — STAC catalogue of analysis-ready products.

Verified live: ``https://stac.astrogeology.usgs.gov/api/collections`` lists
high-resolution DTM collections (Kaguya TC DTMs for the Moon; CTX and HiRISE
DTMs for Mars). We use STAC ``/search`` (intersects a point) to report which
local high-resolution terrain products exist for the region. These COG DTMs
are not read by the MVP pipeline; they are returned as discoverable,
georeferenced follow-up products with their asset links.
"""

from __future__ import annotations

from app.config import get_settings
from app.providers.http import HttpClient, ProviderError
from app.science.coordinates import to_east_180
from app.services.cache import metadata_cache

STAC = "https://stac.astrogeology.usgs.gov/api"

DTM_COLLECTIONS = {
    "moon": ["kaguya_terrain_camera_usgs_dtms_v2", "kaguya_terrain_camera_usgs_dtms_v2_northpolar",
             "kaguya_terrain_camera_usgs_dtms_v2_southpolar"],
    "mars": ["mro_ctx_controlled_usgs_dtms", "mro_hirise_socet_dtms"],
}

WMS = {
    "moon": "https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/earth/moon_simp_cyl.map",
    "mars": "https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/mars/mars_simp_cyl.map",
}


async def dtms_at_point(http: HttpClient, body: str, lat: float, lon: float, limit: int = 5) -> dict:
    x = to_east_180(lon)
    params = {"collections": ",".join(DTM_COLLECTIONS[body]),
              "intersects": f'{{"type":"Point","coordinates":[{x:.6f},{lat:.6f}]}}',
              "limit": str(limit)}

    async def fetch() -> dict:
        return await http.get_json("USGS STAC", f"{STAC}/search", params=params, timeout=45)

    data = await metadata_cache.get_or_set(("stac", body, round(lat, 4), round(x, 4)),
                                           get_settings().metadata_cache_ttl_s, fetch)
    if not isinstance(data, dict) or "features" not in data:
        raise ProviderError("USGS STAC", "unexpected search response")
    items = []
    for f in data.get("features") or []:
        props = f.get("properties") or {}
        assets = f.get("assets") or {}
        dtm = next((a for k, a in assets.items() if "dem" in k.lower() or "dtm" in k.lower()), None)
        items.append({
            "id": f.get("id"), "collection": f.get("collection"),
            "datetime": props.get("datetime") or props.get("start_datetime"),
            "gsd_m": props.get("gsd"),
            "asset_href": (dtm or {}).get("href"),
        })
    matched = (data.get("context") or {}).get("matched") or data.get("numberMatched")
    return {"items": items, "matched": matched, "query": {"endpoint": f"{STAC}/search", "params": params}}
