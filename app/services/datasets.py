"""Registry of the scientific sources the backend queries (served at
GET /v1/planetary/datasets). Each entry states how the source is used and what
it can NOT be used for."""

from __future__ import annotations

DATASETS = [
    {"id": "lola_rdr", "body": "moon", "role": "topography", "instrument": "LRO LOLA",
     "product": "LOLA RDR shots (quality flag 0)", "service": "ODE GDS query=lolardr",
     "endpoint": "https://oderest.rsl.wustl.edu/livegds/", "longitude_convention": "east_360",
     "datum": "radius - 1737.4 km sphere", "resolution": "~5 m spots, ~57 m along-track; track gaps",
     "use": "elevation statistics, regional/local slope, roughness",
     "not_for": "composition", "docs": "https://oderest.rsl.wustl.edu/GDS_REST_V2.0.pdf"},
    {"id": "m3_l2", "body": "moon", "role": "mineralogy", "instrument": "Chandrayaan-1 M3",
     "product": "L2 reflectance (CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0) + L1B LOC backplane",
     "service": "ODE REST pt=REFIMG / CALIV3; HTTP Range reads at PDS Imaging",
     "endpoint": "https://oderest.rsl.wustl.edu/live2/", "longitude_convention": "east_360",
     "resolution": "~140 or ~280 m/pixel, 85 bands 460-2976 nm",
     "use": "1 and 2 µm band depths, albedo, continuum slope",
     "not_for": "mineral abundances; OH/H2O (thermal-tail affected)", "docs": "https://pds-imaging.jpl.nasa.gov/volumes/m3.html"},
    {"id": "diviner", "body": "moon", "role": "discovery", "instrument": "LRO Diviner",
     "product": "PDS4 gridded/derived products", "service": "PDS Registry API (spatial)",
     "endpoint": "https://pds.nasa.gov/api/search/1/products", "use": "availability of thermal products",
     "not_for": "values are not read in the MVP", "docs": "https://nasa-pds.github.io/pds-api/"},
    {"id": "mola_pedr", "body": "mars", "role": "topography", "instrument": "MGS MOLA",
     "product": "MOLA PEDR shots", "service": "ODE GDS query=molapedr",
     "endpoint": "https://oderest.rsl.wustl.edu/livegds/", "longitude_convention": "east_360",
     "datum": "radius - MOLA areoid", "resolution": "~168 m footprint, ~300 m along-track; track gaps",
     "use": "elevation statistics, slopes, roughness", "not_for": "composition",
     "docs": "https://oderest.rsl.wustl.edu/GDS_REST_V2.0.pdf"},
    {"id": "crism_mtrdr", "body": "mars", "role": "mineralogy", "instrument": "MRO CRISM",
     "product": "MTRDR summary parameters (SU) + corrected I/F (IF)",
     "service": "ODE REST pt=MTRDR; HTTP Range reads at PDS Geosciences",
     "endpoint": "https://oderest.rsl.wustl.edu/live2/", "longitude_convention": "east_360",
     "resolution": "18 or 36 m/pixel; ~10 km targeted footprints",
     "use": "screening of hydration, phyllosilicate, carbonate, sulfate, mafic, ice parameters",
     "not_for": "mineral identification without ratioed spectra; areas outside targeted footprints",
     "docs": "https://pds-geosciences.wustl.edu/missions/mro/crism.htm"},
    {"id": "trek_wmts", "body": "moon,mars", "role": "imagery", "instrument": "various (LROC WAC, Viking MDIM, LOLA/MOLA shaded relief)",
     "product": "WMTS layers", "service": "NASA Trek WMTS + layer catalogue",
     "endpoint": "https://trek.nasa.gov/tiles/apidoc/", "longitude_convention": "east_180",
     "use": "3D-interface basemaps and coverage", "not_for": "physical elevation or composition values",
     "docs": "https://trek.nasa.gov/tiles/apidoc/"},
    {"id": "usgs_stac", "body": "moon,mars", "role": "discovery", "instrument": "Kaguya TC, MRO CTX, MRO HiRISE",
     "product": "USGS high-resolution DTMs (COG)", "service": "USGS Astrogeology STAC",
     "endpoint": "https://stac.astrogeology.usgs.gov/api", "longitude_convention": "east_180",
     "use": "listing local DTMs for follow-up", "not_for": "read by the MVP pipeline",
     "docs": "https://www.usgs.gov/centers/astrogeology-science-center/data"},
    {"id": "earth_engine", "body": "earth", "role": "topography+spectroscopy",
     "instrument": "Copernicus DEM GLO-30, Sentinel-2 L2A, ASTER L1T TIR, EMIT L2A",
     "product": "Earth Engine collections", "service": "Google Earth Engine (service account)",
     "endpoint": "https://earthengine.googleapis.com", "longitude_convention": "east_180",
     "use": "elevation/slope, EMIT band depths, Earth-only context indices",
     "not_for": "Moon/Mars (never required by those endpoints)", "docs": "https://developers.google.com/earth-engine"},
    {"id": "earth_emit_reference_library", "body": "earth", "role": "analog reference",
     "instrument": "EMIT (via Earth Engine)", "product": "app/data/earth_emit_reference_library.json (90 sites)",
     "service": "bundled file derived from the legacy backend (EMIT band depths only)",
     "use": "Earth analog ranking on directly comparable band depths",
     "not_for": "probability of deposits; extraction dates were not archived"},
]


def list_datasets(body: str | None = None) -> list[dict]:
    if not body:
        return DATASETS
    return [d for d in DATASETS if body in d["body"].split(",")]
