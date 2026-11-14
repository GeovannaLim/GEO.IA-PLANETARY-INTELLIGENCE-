"""Real-network smoke tests. Skipped unless GEOIA_LIVE_TESTS=1.

    GEOIA_LIVE_TESTS=1 pytest -m live -q
"""
import os
import uuid
from datetime import datetime, timezone

import pytest

from app.pipelines import lunar, mars
from app.providers import ode, pds, trek, usgs
from app.providers.http import get_http
from app.schemas.analysis import AnalyzeRequest
from app.science.coordinates import region_box
from tests.conftest import run

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(os.getenv("GEOIA_LIVE_TESTS") != "1", reason="set GEOIA_LIVE_TESTS=1")]


async def _noop(_):
    return None


def test_live_connectors_respond():
    async def go():
        http = get_http()
        moon = await trek.catalog(http, "moon")
        caps = await trek.capabilities(http, "mars", "Mars_MGS_MOLA_ClrShade_merge_global_463m")
        prods, _ = await ode.search_products(http, target="moon", ihid="CH1-ORB", iid="M3", pt="REFIMG",
                                             box=region_box(35, -15, 0.5, "moon"), limit=5)
        alt = await ode.query_altimetry(http, "mars", region_box(0.0, 0.0, 2, "mars"))
        p = await pds.search_spatial(http, instrument="lola", lat=35.0, lon360=345.0)
        s = await usgs.dtms_at_point(http, "mars", 18.44, 77.45)
        return moon, caps, prods, alt, p, s
    moon, caps, prods, alt, p, s = run(go())
    assert len(moon) > 100 and caps["template"]
    assert prods and all(x.pdsid.startswith("M3") for x in prods)
    assert alt.elev_m.size > 0
    assert p["hits"] is not None and isinstance(s["items"], list)


def test_live_lunar_imbrium():
    async def go():
        return await lunar.run(AnalyzeRequest(latitude=35.0, longitude=-15.0, radius_km=3), get_http(),
                               uuid.uuid4().hex, datetime.now(timezone.utc), _noop)
    d = run(go()).model_dump(mode="json")
    assert d["topography"]["status"] in ("available", "partial") and d["topography"]["n_points"] > 100
    m = d["mineralogy"]
    # a slow PDS may exhaust the M3 deadline: that must be a declared provider failure, never a scientific result
    assert m["status"] in ("available", "partial", "unavailable") or (
        m["status"] == "failed" and m["reason"] == "provider_error"
        and any("not evidence that minerals are absent" in x for x in m["limitations"]))


def test_live_mars_jezero():
    async def go():
        return await mars.run(AnalyzeRequest(latitude=18.44, longitude=77.45, radius_km=3), get_http(),
                              uuid.uuid4().hex, datetime.now(timezone.utc), _noop)
    d = run(go()).model_dump(mode="json")
    assert d["topography"]["n_points"] and d["mineralogy"]["products_found"] >= 1
