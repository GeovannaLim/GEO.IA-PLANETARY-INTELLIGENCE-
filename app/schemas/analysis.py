"""Public request/response contract shared by Earth, Moon and Mars.

Design rules
------------
* Every section carries an explicit ``status`` (available / unavailable /
  partial / processing / failed) and, when not available, a ``reason`` code that
  distinguishes provider errors from lack of coverage from lack of compatible
  observations.
* Numeric scientific fields are ``None`` unless they were computed from data
  that is listed in ``data_sources``. There are no defaults that look like
  measurements.
* Every value points back to the source records it came from (``source_ids``).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"

Body = Literal["earth", "moon", "mars"]


class SectionStatus(str, Enum):
    available = "available"
    unavailable = "unavailable"
    partial = "partial"
    processing = "processing"
    failed = "failed"


class Reason(str, Enum):
    """Why a section is not (fully) available."""
    provider_error = "provider_error"            # the remote service failed / timed out
    no_coverage = "no_coverage"                  # no product intersects the region
    no_compatible_observations = "no_compatible_observations"  # products exist but none usable
    insufficient_data = "insufficient_data"      # data found but too sparse for the metric
    not_configured = "not_configured"            # e.g. Earth Engine credentials absent
    not_supported = "not_supported"              # metric not defined for this body/product
    not_attempted = "not_attempted"              # skipped because a prerequisite failed
    invalid_data = "invalid_data"                # data returned but failed validation


class AnalysisStatus(str, Enum):
    processing = "processing"
    completed = "completed"    # pipeline finished; sections may still be unavailable
    failed = "failed"          # pipeline crashed or timed out


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #
class AnalyzeRequest(BaseModel):
    """Region of interest.

    Coordinates are **planetocentric latitude** and **east-positive longitude**.
    By default longitude is expected in [-180, 180]; send
    ``longitude_convention="east_360"`` to pass [0, 360].
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "example": {"latitude": 25.8, "longitude": -15.2, "radius_km": 10}})

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Planetocentric latitude, degrees")
    longitude: float = Field(..., description="East-positive longitude, degrees")
    radius_km: float = Field(10.0, gt=0.0, description="Radius of the circular region, km")
    longitude_convention: Literal["east_180", "east_360"] = "east_180"

    @model_validator(mode="after")
    def _check_longitude(self) -> "AnalyzeRequest":
        lo, hi = (-180.0, 180.0) if self.longitude_convention == "east_180" else (0.0, 360.0)
        if not (lo <= self.longitude <= hi):
            raise ValueError(
                f"longitude {self.longitude} outside [{lo}, {hi}] for convention "
                f"'{self.longitude_convention}'")
        return self


# --------------------------------------------------------------------------- #
# Response building blocks
# --------------------------------------------------------------------------- #
class Coordinates(BaseModel):
    latitude: float
    longitude: float = Field(description="East-positive, normalised to [-180, 180)")
    radius_km: float
    longitude_east_360: float = Field(description="Same longitude in [0, 360) (ODE/GDS/PDS convention)")
    latitude_type: Literal["planetocentric"] = "planetocentric"
    reference_frame: str
    reference_radius_km: float
    bounding_box: dict[str, float] = Field(description="Query bbox in east_360, degrees")


class SourceRecord(BaseModel):
    """Provenance of one external query or product."""
    source_id: str
    provider: str
    service: str
    instrument: str | None = None
    mission: str | None = None
    product_type: str | None = None
    product_id: str | None = None
    url: str | None = None
    observation_start: str | None = None
    observation_end: str | None = None
    spatial_resolution_m: float | None = None
    processing: list[str] = Field(default_factory=list)
    query: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: datetime | None = None
    status: Literal["ok", "empty", "error", "skipped"] = "ok"
    message: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ProblemDetail(BaseModel):
    source_id: str | None = None
    section: str
    reason: Reason
    message: str


class ImageryLayer(BaseModel):
    layer_id: str
    title: str
    provider: str = "NASA Trek"
    role: Literal["basemap", "shaded_relief", "regional_product"]
    protocol: Literal["WMTS"] = "WMTS"
    capabilities_url: str
    tile_url_template: str | None = None
    image_format: str | None = None
    tile_matrix_set: str | None = None
    zoom_levels: int | None = None
    projection: str | None = None
    bbox_east_180: list[float] | None = None
    instrument: str | None = None
    note: str = "Visual layer only; pixel values are not physical measurements."


class ImagerySection(BaseModel):
    status: SectionStatus
    reason: Reason | None = None
    layers: list[ImageryLayer] = Field(default_factory=list)
    regional_layers_covering_point: int | None = None
    source_ids: list[str] = Field(default_factory=list)


class Stats(BaseModel):
    mean: float | None = None
    median: float | None = None
    min: float | None = None
    max: float | None = None
    std: float | None = None
    p05: float | None = None
    p95: float | None = None


class TopographySection(BaseModel):
    status: SectionStatus
    reason: Reason | None = None
    method: str | None = None
    datum: str | None = None
    n_points: int | None = None
    sampled_radius_km: float | None = None
    elevation_m: Stats | None = None
    relief_m: float | None = Field(None, description="p95 - p05 of elevation")
    regional_slope_degrees: float | None = Field(None, description="Slope of best-fit plane")
    regional_aspect_degrees: float | None = None
    local_slope_degrees: Stats | None = None
    slope_baseline_m: float | None = None
    roughness_m: float | None = Field(None, description="RMS of residuals about best-fit plane")
    coverage_fraction: float | None = Field(None, description="Fraction of grid cells with data")
    source_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    # spec compatibility shortcuts
    elevation_m_mean: float | None = None
    slope_degrees: float | None = None


class SpectralIndicator(BaseModel):
    name: str
    value: Stats
    unit: str = "dimensionless"
    definition: str
    reference: str
    sensitive_to: str | None = None
    screening_threshold: float | None = None
    threshold_basis: str | None = None
    fraction_above_threshold: float | None = None
    n_pixels: int
    interpretation: str
    comparability: Literal["direct", "proxy", "body_specific"] = "body_specific"
    detected: bool | None = Field(None, description="result of the statistical screening (see threshold_basis); "
                                                    "None for descriptive values")


class MineralogySection(BaseModel):
    status: SectionStatus
    reason: Reason | None = None
    instrument: str | None = None
    method: str | None = None
    products_found: int | None = None
    products_containing_point: int | None = None
    product_used: str | None = None
    pixel_distance_m: float | None = None
    window_pixels: int | None = None
    valid_pixels: int | None = None
    indicators: list[SpectralIndicator] = Field(default_factory=list)
    spectral_character: str | None = None
    mean_spectrum: dict[str, list[float]] | None = Field(
        None, description="{'wavelength_nm': [...], 'reflectance': [...]}")
    source_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AnalogMatch(BaseModel):
    name: str
    country: str | None = None
    setting: str | None = None
    distance: float = Field(description="Euclidean distance in band-depth units (lower = closer)")
    similarity: float = Field(description="1 - distance/max_distance; ranking aid, NOT a probability")
    attributes_used: list[str]
    earth_values: dict[str, float]
    differences: dict[str, float] = Field(default_factory=dict,
                                          description="query value minus terrestrial value, per attribute")


class EarthAnalogSection(BaseModel):
    status: SectionStatus
    reason: Reason | None = None
    method: str | None = None
    reference_library: str | None = None
    directly_comparable: list[str] = Field(default_factory=list)
    approximate_proxies: list[str] = Field(default_factory=list)
    not_comparable: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    query_values: dict[str, float] = Field(default_factory=dict)
    query_uncertainty: dict[str, float] = Field(
        default_factory=dict, description="standard error of each query value (spatially corrected); empty if unknown")
    matches: list[AnalogMatch] = Field(default_factory=list)
    discrimination: Literal["low", "moderate", "adequate"] | None = Field(
        None, description="how well the ranking separates the top sites (see docs/CIENCIA.md#análogos)")
    discrimination_note: str | None = None
    top5_distance_spread: float | None = None
    indistinguishable_sites: int | None = Field(
        None, description="library sites whose distance is within 2 sigma (query uncertainty) of the best match")
    disclaimer: str = ("Similarity of a few band-depth attributes. It is not a probability "
                       "of mineral occurrence and does not indicate a deposit.")


class TerrestrialAnalogSite(BaseModel):
    id: str
    name: str
    country: str
    latitude: float
    longitude: float
    coordinate_source: str
    coordinate_precision_km: float | None = None
    setting: str
    key_minerals: list[str] = Field(default_factory=list)
    matched_classes: list[str] = Field(description="region evidence classes this site's documented geology explains")
    analog_basis: str | None = Field(None, description="published_analog | simulant_source | published_analog_general"
                                                       " | mineralogical_reference | outreach")
    justification: list[str] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    emit: dict[str, Any] | None = Field(None, description="masked EMIT remeasurement of the site (provenance)")
    region_bands: dict[str, bool | None] = Field(default_factory=dict)


class TerrestrialAnalogSection(BaseModel):
    status: SectionStatus
    reason: Reason | None = None
    body: Literal["moon", "mars"] | None = None
    basis: Literal["regional_spectral_evidence", "global_context"] | None = None
    method: str | None = None
    catalog: str | None = None
    region_evidence: list[dict[str, Any]] = Field(default_factory=list)
    unexplained_evidence: list[str] = Field(default_factory=list)
    sites: list[TerrestrialAnalogSite] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    disclaimer: str | None = None


class Criterion(BaseModel):
    criterion: str
    met: bool
    detail: str


class ConfidenceSection(BaseModel):
    level: Literal["not_assessed", "low", "moderate", "high"] = "not_assessed"
    basis: str = "Rule-based; see docs/CIENCIA.md#confiança"
    criteria: list[Criterion] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CacheInfo(BaseModel):
    hit: bool = False
    original_analysis_id: str | None = None
    computed_at: datetime | None = None


class AnalysisResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    analysis_id: str
    planet: Body
    status: AnalysisStatus
    created_at: datetime
    completed_at: datetime | None = None
    progress: list[str] = Field(default_factory=list, description="Completed pipeline steps")
    coordinates: Coordinates
    data_sources: list[SourceRecord] = Field(default_factory=list)
    imagery: ImagerySection
    topography: TopographySection
    mineralogy: MineralogySection
    earth_analogs: EarthAnalogSection
    terrestrial_analogs: TerrestrialAnalogSection | None = Field(
        None, description="Moon/Mars: documented terrestrial analog sites matched by mineral family")
    earth_observation: dict[str, Any] | None = Field(
        None, description="Earth only: Sentinel-2/ASTER/EMIT indices with provenance")
    confidence: ConfidenceSection
    problems: list[ProblemDetail] = Field(default_factory=list)
    cache: CacheInfo = Field(default_factory=CacheInfo)
    report_id: str | None = None
    links: dict[str, str] = Field(default_factory=dict)


def processing_placeholder(analysis_id: str, planet: Body, coords: Coordinates,
                           created_at: datetime) -> AnalysisResult:
    """Initial state returned while a job runs. Contains no values at all."""
    p = SectionStatus.processing
    return AnalysisResult(
        analysis_id=analysis_id, planet=planet, status=AnalysisStatus.processing,
        created_at=created_at, coordinates=coords,
        imagery=ImagerySection(status=p), topography=TopographySection(status=p),
        mineralogy=MineralogySection(status=p), earth_analogs=EarthAnalogSection(status=p),
        confidence=ConfidenceSection())
