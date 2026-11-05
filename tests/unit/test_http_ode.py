import httpx
import pytest
import respx

from app.providers import ode
from app.providers.http import HttpClient, ProviderError, UnsafeURLError, validate_url
from tests.conftest import run


@pytest.mark.parametrize("url", ["https://127.0.0.1/x", "https://evil.example.com/x", "file:///etc/passwd",
                                 "https://user:pw@trek.nasa.gov/", "https://trek.nasa.gov:8443/x",
                                 "https://169.254.169.254/latest/meta-data", "gopher://trek.nasa.gov/"])
def test_ssrf_guard_rejects(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_ssrf_guard_accepts_and_upgrades():
    assert validate_url("http://pds-imaging.jpl.nasa.gov/a").startswith("https://")


def test_retry_then_success_and_redirect_revalidated():
    async def go():
        with respx.mock() as r:
            route = r.get("https://trek.nasa.gov/x").mock(side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": 1})])
            r.get("https://pds.nasa.gov/r").mock(return_value=httpx.Response(307, headers={"location": "https://evil.example.com/"}))
            http = HttpClient()
            try:
                assert await http.get_json("t", "https://trek.nasa.gov/x") == {"ok": 1}
                assert route.call_count == 2
                with pytest.raises(UnsafeURLError):
                    await http.get_json("t", "https://pds.nasa.gov/r")
            finally:
                await http.aclose()
    run(go())


def test_persistent_failure_and_size_cap_raise_provider_error():
    async def go():
        with respx.mock() as r:
            r.get("https://trek.nasa.gov/down").mock(return_value=httpx.Response(503))
            r.get("https://trek.nasa.gov/big").mock(return_value=httpx.Response(200, content=b"x" * 5000))
            r.get("https://trek.nasa.gov/norange").mock(return_value=httpx.Response(200, content=b"abcd"))
            http = HttpClient()
            try:
                with pytest.raises(ProviderError):
                    await http.get_json("t", "https://trek.nasa.gov/down")
                with pytest.raises(ProviderError, match="exceeded|too large"):
                    await http.get_text("t", "https://trek.nasa.gov/big", max_bytes=1000)
                with pytest.raises(ProviderError, match="Range"):
                    await http.get_range("t", "https://trek.nasa.gov/norange", 0, 2)
            finally:
                await http.aclose()
    run(go())


def test_gds_csv_parsing_skips_bad_rows():
    lo, la, z, t = ode.parse_topo_csv("LONG_EAST,LAT_NORTH, TOPOGRAPHY, UTC\n000.03,0.003,-1520.9,2000-05-19\nbad,row\n1,2,nan\n")
    assert list(z) == [-1520.9] and t == ["2000-05-19"]
    assert ode.parse_topo_csv("")[0].size == 0


def test_product_with_incomplete_metadata_parses():
    p = ode.parse_product({"pdsid": "X"})
    assert p.pdsid == "X" and p.footprint_wkt is None and p.files == [] and p.file_url(endswith=".IMG") is None
    assert ode._products({"Products": "No Products Found"}) == []
