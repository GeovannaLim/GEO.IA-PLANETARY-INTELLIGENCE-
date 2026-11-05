"""GEØ.IA Planetary Intelligence — FastAPI application."""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.providers.http import close_http
from app.services import jobs
from app.services.store import get_store


class JsonFormatter(logging.Formatter):
    STD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
               "logger": record.name, "msg": record.getMessage()}
        out.update({k: v for k, v in vars(record).items() if k not in self.STD})
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def configure_logging() -> None:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(get_settings().log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    n = get_store().mark_interrupted()
    if n:
        logging.getLogger("geoia").warning("marked interrupted jobs as failed", extra={"count": n})
    yield
    await jobs.shutdown()
    await close_http()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version=__version__, lifespan=lifespan,
                  description="Coordinate-based analysis of the Earth, the Moon and Mars from traceable "
                              "scientific sources (NASA PDS/ODE, Trek, USGS, Earth Engine).")
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])
    app.include_router(router)
    return app


app = create_app()
