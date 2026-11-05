"""NASA Solar System Treks (Moon Trek / Mars Trek) WMTS discovery.

Verified live:
* Layer catalogue  ``https://trek.nasa.gov/{body}/TrekServices/ws/index/eq/searchItems``
  (Solr JSON; ``bbox`` = "west,south,east,north" in east_180 degrees).
* Capabilities     ``https://trek.nasa.gov/tiles/{Body}/EQ/{layer}/1.0.0/WMTSCapabilities.xml``
  (OGC WMTS 1.0.0 RESTful; ResourceURL template, TileMatrixSet, formats).

WMTS tiles are rendered imagery (8-bit, often hillshaded/colourised). They are
returned for visualisation and coverage only and are never used as physical
elevation or composition values.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.providers.http import HttpClient, ProviderError
from app.schemas.analysis import ImageryLayer
from app.science.coordinates import to_east_180
from app.services.cache import metadata_cache

TREK_BODY = {"moon": ("moon", "Moon"), "mars": ("mars", "Mars")}
CATALOG_URL = ("https://trek.nasa.gov/{b}/TrekServices/ws/index/eq/searchItems?start=0&rows=2147483647"
               "&facetKeys=itemType%7CproductCat2%7CserviceTypes%7CthumbnailURLDir"
               "&facetValues=product%7C-%28DEM%20ConfidenceRaw%20Slope%29%7CMosaic%7C%5B%2A%20TO%20%2A%5D")
CAPS_URL = "https://trek.nasa.gov/tiles/{B}/EQ/{layer}/1.0.0/WMTSCapabilities.xml"

CURATED = {
    "moon": [("LRO_WAC_Mosaic_Global_303ppd_v02", "basemap"),
             ("LRO_LOLA_ClrShade_Global_128ppd_v04", "shaded_relief")],
    "mars": [("Mars_Viking_MDIM21_ClrMosaic_global_232m", "basemap"),
             ("Mars_MGS_MOLA_ClrShade_merge_global_463m", "shaded_relief")],
}

NS = {"wmts": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}


async def catalog(http: HttpClient, body: str) -> list[dict]:
    b, _ = TREK_BODY[body]

    async def fetch() -> list[dict]:
        data = await http.get_json("NASA Trek", CATALOG_URL.format(b=b), timeout=60,
                                   max_bytes=15 * 1024 * 1024)
        docs = ((data or {}).get("response") or {}).get("docs")
        if not isinstance(docs, list):
            raise ProviderError("NASA Trek", "catalogue response has no docs")
        return docs

    return await metadata_cache.get_or_set(("trek-cat", body), get_settings().metadata_cache_ttl_s, fetch)


def parse_capabilities(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    layer = root.find(".//wmts:Contents/wmts:Layer", NS)
    if layer is None:
        raise ValueError("no Layer in capabilities")
    res = layer.find("wmts:ResourceURL", NS)
    fmt = layer.find("wmts:Format", NS)
    tms_id = layer.find("wmts:TileMatrixSetLink/wmts:TileMatrixSet", NS)
    tms = root.find(".//wmts:Contents/wmts:TileMatrixSet", NS)
    crs = tms.find("ows:SupportedCRS", NS) if tms is not None else None
    n_levels = len(tms.findall("wmts:TileMatrix", NS)) if tms is not None else None
    return {
        "template": res.get("template") if res is not None else None,
        "format": fmt.text if fmt is not None else None,
        "tile_matrix_set": tms_id.text if tms_id is not None else None,
        "zoom_levels": n_levels,
        "crs": crs.text if crs is not None else None,
    }


async def capabilities(http: HttpClient, body: str, layer: str) -> dict[str, Any]:
    _, B = TREK_BODY[body]
    url = CAPS_URL.format(B=B, layer=layer)

    async def fetch() -> dict[str, Any]:
        text = await http.get_text("NASA Trek", url, timeout=30, max_bytes=2 * 1024 * 1024)
        try:
            caps = parse_capabilities(text)
        except (ET.ParseError, ValueError) as exc:
            raise ProviderError("NASA Trek", f"invalid WMTS capabilities for {layer}: {exc}") from exc
        caps["capabilities_url"] = url
        return caps

    return await metadata_cache.get_or_set(("trek-caps", body, layer), get_settings().metadata_cache_ttl_s, fetch)


def _bbox(doc: dict) -> list[float] | None:
    try:
        w, s, e, n = (float(v) for v in str(doc.get("bbox", "")).split(","))
        return [w, s, e, n]
    except ValueError:
        return None


def covers(doc: dict, lat: float, lon: float) -> bool:
    bb = _bbox(doc)
    if not bb:
        return False
    w, s, e, n = bb
    x = to_east_180(lon)
    in_lon = (w <= x <= e) if w <= e else (x >= w or x <= e)
    return s <= lat <= n and in_lon


async def imagery_for_point(http: HttpClient, body: str, lat: float, lon: float
                            ) -> tuple[list[ImageryLayer], int, dict]:
    """Curated global layers (verified against the catalogue + capabilities)
    and the number of regional Trek products whose bbox covers the point."""
    docs = await catalog(http, body)
    by_label = {d.get("productLabel"): d for d in docs}
    layers: list[ImageryLayer] = []
    for label, role in CURATED[body]:
        doc = by_label.get(label)
        if doc is None:
            continue  # layer withdrawn from catalogue -> simply not offered
        caps = await capabilities(http, body, label)
        layers.append(ImageryLayer(
            layer_id=label, title=doc.get("title") or label, role=role,
            capabilities_url=caps["capabilities_url"], tile_url_template=caps.get("template"),
            image_format=caps.get("format"), tile_matrix_set=caps.get("tile_matrix_set"),
            zoom_levels=caps.get("zoom_levels"), projection=caps.get("crs"),
            bbox_east_180=_bbox(doc), instrument=doc.get("instrument")))
    regional = [d for d in docs if d.get("coverage") != "Global" and covers(d, lat, lon)]
    # A few regional products, highest resolution first when the field is present.
    def res(d: dict) -> float:
        v = d.get("resolution", d.get("Resolution"))
        try:
            return float(v) if v else 1e12
        except (TypeError, ValueError):
            return 1e12
    for d in sorted(regional, key=res)[:3]:
        label = d.get("productLabel")
        if not label:
            continue
        try:
            caps = await capabilities(http, body, label)
        except ProviderError:
            continue
        layers.append(ImageryLayer(
            layer_id=label, title=d.get("title") or label, role="regional_product",
            capabilities_url=caps["capabilities_url"], tile_url_template=caps.get("template"),
            image_format=caps.get("format"), tile_matrix_set=caps.get("tile_matrix_set"),
            zoom_levels=caps.get("zoom_levels"), projection=caps.get("crs"),
            bbox_east_180=_bbox(d), instrument=d.get("instrument")))
    meta = {"catalog_url": CATALOG_URL.format(b=TREK_BODY[body][0]), "catalog_size": len(docs),
            "retrieved_at": datetime.now(timezone.utc)}
    return layers, len(regional), meta
