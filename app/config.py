"""Runtime configuration, read from environment variables (prefix ``GEOIA_``).

Every operational limit lives here so it can be tuned per deployment without
code changes. Nothing secret has a default.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GEOIA_", env_file=".env", extra="ignore")

    app_name: str = "GEØ.IA Planetary Intelligence"
    environment: str = "development"
    log_level: str = "INFO"

    # --- CORS: comma separated list of allowed origins (no wildcard by default)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- persistence (SQLite file; on Render point this at a persistent disk)
    db_path: str = "var/geoia.sqlite3"

    # --- network
    http_timeout_s: float = 30.0
    http_connect_timeout_s: float = 10.0
    http_retries: int = 3
    http_backoff_s: float = 0.8
    http_max_download_bytes: int = 20 * 1024 * 1024  # hard cap per single download
    http_max_concurrency_per_host: int = 6

    # --- jobs
    max_concurrent_jobs: int = 3
    job_timeout_s: float = 240.0
    default_wait_s: float = 0.0
    result_cache_ttl_s: int = 24 * 3600
    metadata_cache_ttl_s: int = 12 * 3600

    # --- operational limits per body (km)
    max_radius_km_moon: float = 25.0
    max_radius_km_mars: float = 50.0
    max_radius_km_earth: float = 25.0
    min_radius_km: float = 0.1

    # --- altimetry (ODE GDS)
    altimetry_max_file_kb: int = 12_000  # skip / shrink when GDS output is larger
    altimetry_shrink_steps: int = 3

    # --- spectral extraction limits (pixels from centre, i.e. window = 2n+1)
    m3_max_half_window_px: int = 20
    crism_max_half_window_px: int = 30
    spectral_max_products_considered: int = 25

    # --- Earth Engine (optional; only the Earth endpoint uses it)
    gee_project: str | None = Field(default=None, validation_alias="GEE_PROJECT")
    gee_service_account_json: str | None = Field(default=None, validation_alias="GEE_SERVICE_ACCOUNT_JSON")
    gee_service_account_key_file: str | None = Field(
        default=None, validation_alias="GEE_SERVICE_ACCOUNT_KEY_FILE")

    # --- live tests (never used by the app itself)
    live_tests: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def max_radius_km(self, body: str) -> float:
        return {"moon": self.max_radius_km_moon, "mars": self.max_radius_km_mars,
                "earth": self.max_radius_km_earth}[body]


@lru_cache
def get_settings() -> Settings:
    return Settings()
