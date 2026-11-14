"""M3 mineralogy vs permanent shadow (2026-11-14 correction). Synthetic M3 cubes and a synthetic
illumination archive (tests/fakes.py): permanently shadowed quadrant = longitudes 0-90E near the pole.
Real-data validation is in docs/VALIDACAO_SOMBRA_MINERALOGIA_LUNAR.md."""

from tests.fakes import FakeWorld
from tests.integration.test_pipelines import _run


def _sites(d):
    return (d["terrestrial_analogs"] or {}).get("sites") or []


def test_permanent_shadow_blocks_any_mineral_inference():
    d = _run("moon", FakeWorld(-89.9, 45.0), -89.9, 45.0, r=1.0)
    m = d["mineralogy"]
    assert m["status"] == "unavailable" and m["reason"] == "insufficient_data"
    assert m["indicators"] == [] and m["valid_pixels"] < 4
    assert any("permanent shadow" in x and "excluded" in x for x in m["limitations"])
    assert any(p["section"] == "mineralogy" and "Mineralogy is not inferred" in p["message"] for p in d["problems"])
    assert _sites(d) == []                                           # no analog from a shadowed window


def test_partial_shadow_keeps_only_sunlit_pixels():
    full = _run("moon", FakeWorld(-89.9, 0.2, illum_status=503), -89.9, 0.2, r=1.0)   # no map: nothing removed
    part = _run("moon", FakeWorld(-89.9, 0.2), -89.9, 0.2, r=1.0)
    assert 4 <= part["mineralogy"]["valid_pixels"] < full["mineralogy"]["valid_pixels"]
    msg = next(x for x in part["mineralogy"]["limitations"] if "permanent shadow" in x)
    assert "were excluded" in msg


def test_missing_map_is_not_read_as_shadow_or_as_sunlight():
    d = _run("moon", FakeWorld(-89.9, 45.0, illum_status=503), -89.9, 45.0, r=1.0)
    m = d["mineralogy"]
    assert any("could not be checked" in x for x in m["limitations"])          # declared, not presumed
    assert not any("were excluded" in x for x in m["limitations"])             # no shadow claimed
    assert d["environment"]["status"] == "failed" and d["environment"]["permanent_shadow_fraction"] is None
    assert any(p["section"] == "mineralogy" and "permanent-shadow check failed" in p["message"]
               for p in d["problems"])


def test_non_polar_detections_are_unchanged():
    d = _run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0)
    assert d["mineralogy"]["status"] == "available"
    assert not any("permanent shadow" in x for x in d["mineralogy"]["limitations"])
    assert d["environment"]["reason"] == "not_supported"


def test_shadow_messages_are_translated():
    from app import i18n
    d = _run("moon", FakeWorld(-89.9, 45.0), -89.9, 45.0, r=1.0)
    pt = i18n.localize(d, "pt-BR")
    assert any("estão em sombra permanente" in x for x in pt["mineralogy"]["limitations"])
    assert any("A mineralogia não é inferida" in p["message"] for p in pt["problems"])
