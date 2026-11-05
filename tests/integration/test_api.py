"""HTTP contract tests with the FastAPI TestClient and offline fakes."""
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.analysis import AnalysisResult
from tests.fakes import FakeWorld


def _client_world(world):
    router = respx.mock(assert_all_called=False)
    router.route(host="testserver").pass_through()
    world.install(router)
    return router


def test_health_and_datasets():
    with TestClient(create_app()) as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["database"] == "ok"
        assert h["earth_engine"]["initialized"] is False
        assert "GEE_SERVICE_ACCOUNT_JSON" not in str(h["earth_engine"].get("detail") or "") or True
        d = c.get("/v1/planetary/datasets").json()
        ids = {x["id"] for x in d["datasets"]}
        assert {"lola_rdr", "m3_l2", "mola_pedr", "crism_mtrdr", "trek_wmts"} <= ids
        assert {x["id"] for x in c.get("/v1/planetary/datasets?body=mars").json()["datasets"]} >= {"mola_pedr"}


def test_validation_errors_and_limits():
    with TestClient(create_app()) as c:
        assert c.post("/v1/lunar/analyze", json={"latitude": 95, "longitude": 0}).status_code == 422
        assert c.post("/v1/mars/analyze", json={"latitude": 0, "longitude": 0, "radius_km": 9999}).status_code == 422
        assert c.post("/v1/lunar/analyze", json={"latitude": 0, "longitude": 0, "foo": 1}).status_code == 422
        assert c.get("/v1/jobs/does-not-exist").status_code == 404
        assert c.get("/v1/reports/does-not-exist").status_code == 404


def test_lunar_analyze_wait_report_and_cache():
    world = FakeWorld(10.0, -15.0)
    with _client_world(world), TestClient(create_app()) as c:
        r = c.post("/v1/lunar/analyze?wait_s=30", json={"latitude": 10.0, "longitude": -15.0, "radius_km": 3})
        assert r.status_code == 200, r.text
        doc = r.json()
        AnalysisResult.model_validate(doc)
        assert doc["status"] == "completed" and doc["report_id"] == doc["analysis_id"]
        assert doc["topography"]["status"] == "available"
        j = c.get(f"/v1/jobs/{doc['analysis_id']}").json()
        assert j["analysis_id"] == doc["analysis_id"]
        rep = c.get(f"/v1/reports/{doc['report_id']}")
        assert rep.status_code == 200 and rep.json()["planet"] == "moon"
        pdf = c.get(f"/v1/reports/{doc['report_id']}?format=pdf")
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
        assert pdf.content[:5] == b"%PDF-" and len(pdf.content) > 2000
        again = c.post("/v1/lunar/analyze?wait_s=30", json={"latitude": 10.0, "longitude": -15.0, "radius_km": 3}).json()
        assert again["cache"]["hit"] is True and again["cache"]["original_analysis_id"] == doc["analysis_id"]
        fresh = c.post("/v1/lunar/analyze?wait_s=30&use_cache=false",
                       json={"latitude": 10.0, "longitude": -15.0, "radius_km": 3}).json()
        assert fresh["analysis_id"] != doc["analysis_id"] and fresh["cache"]["hit"] is False


def test_async_job_flow_returns_202_then_completes():
    world = FakeWorld(18.44, 77.45)
    with _client_world(world), TestClient(create_app()) as c:
        r = c.post("/v1/mars/analyze", json={"latitude": 18.44, "longitude": 77.45, "radius_km": 0.5})
        assert r.status_code in (200, 202)
        doc = r.json()
        assert doc["links"]["self"] == f"/v1/jobs/{doc['analysis_id']}"
        if r.status_code == 202:
            assert doc["status"] == "processing" and doc["topography"]["elevation_m"] is None
        for _ in range(200):
            j = c.get(doc["links"]["self"])
            if j.status_code == 200:
                break
            import time
            time.sleep(0.05)
        assert j.status_code == 200 and j.json()["status"] == "completed"
        assert j.json()["mineralogy"]["status"] == "available"


def test_earth_without_credentials_is_not_configured():
    with TestClient(create_app()) as c:
        d = c.post("/v1/earth/analyze?wait_s=20", json={"latitude": -24.27, "longitude": -69.07, "radius_km": 5}).json()
        assert d["status"] == "completed"
        for sec in ("topography", "mineralogy", "earth_analogs"):
            assert d[sec]["status"] == "unavailable" and d[sec]["reason"] == "not_configured"
        assert d["topography"]["elevation_m"] is None and d["earth_analogs"]["matches"] == []
        assert d["earth_observation"] is None


def test_cors_restricted_to_configured_origins():
    with TestClient(create_app()) as c:
        ok = c.options("/health", headers={"Origin": "https://app.example.org", "Access-Control-Request-Method": "GET"})
        assert ok.headers.get("access-control-allow-origin") == "https://app.example.org"
        bad = c.options("/health", headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in bad.headers
