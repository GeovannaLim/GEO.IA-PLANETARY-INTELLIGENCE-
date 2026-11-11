"""pt-BR localisation: every prose field produced by the pipelines must have a rule,
and nothing scientific (numbers, codes, ids, provenance) may change."""
import json
from pathlib import Path

import pytest

from app import i18n
from tests.integration.test_pipelines import _run
from tests.fakes import FakeWorld

EXAMPLES = sorted(Path(__file__).resolve().parents[2].glob("examples/response_*.json"))


def _prose(doc: dict) -> list[tuple[str, str]]:
    """(path, value) for every string under the translated paths."""
    out: list[tuple[str, str]] = []

    def walk(node, parts, label):
        if not parts or node is None or not isinstance(node, dict):
            return
        key, rest = parts[0], parts[1:]
        is_list = key.endswith("[]")
        key = key[:-2] if is_list else key
        val = node.get(key)
        items = val if is_list and isinstance(val, list) else [val] if not is_list else []
        for it in items:
            if rest:
                walk(it, rest, f"{label}.{key}")
            elif isinstance(it, str):
                out.append((f"{label}.{key}", it))
    for p in i18n.PATHS:
        walk(doc, p.split("."), "")
    return out


# Provider-generated text with no fixed template (raw upstream errors, catalogue names) may stay as is.
UNTRANSLATABLE = ("HTTP", "Error", "Exception")


def _docs():
    docs = [d for d in (json.loads(p.read_text()) for p in EXAMPLES) if d["status"] != "processing"]
    docs.append(_run("moon", FakeWorld(10.0, -15.0), 10.0, -15.0))
    docs.append(_run("moon", FakeWorld(10.0, -15.0, m3=False, gds_status=503), 10.0, -15.0))
    docs.append(_run("mars", FakeWorld(18.44, 77.45), 18.44, 77.45, r=0.5))
    docs.append(_run("mars", FakeWorld(-85.0, 150.0, crism=False), -85.0, 150.0, r=5))
    return docs


@pytest.mark.parametrize("doc", _docs(), ids=lambda d: f"{d['planet']}-{d['analysis_id'][:6]}")
def test_every_prose_field_is_translated(doc):
    loc = i18n.localize(doc, "pt-BR")
    missing = [(p, v) for (p, v), (_, t) in zip(_prose(doc), _prose(loc))
               if t == v and not any(k in v for k in UNTRANSLATABLE)]
    assert not missing, missing
    assert loc["language"] == "pt-BR"


@pytest.mark.parametrize("doc", _docs()[:2])
def test_localisation_never_touches_science(doc):
    loc = i18n.localize(doc, "pt-BR")
    for k in ("coordinates", "data_sources", "cache", "report_id", "analysis_id"):
        assert loc.get(k) == doc.get(k)
    for a, b in zip(doc["mineralogy"]["indicators"], loc["mineralogy"]["indicators"]):
        assert a["name"] == b["name"] and a["value"] == b["value"] and a["definition"] == b["definition"]
    assert loc["topography"]["elevation_m"] == doc["topography"]["elevation_m"]
    assert [m["similarity"] for m in loc["earth_analogs"]["matches"]] == \
        [m["similarity"] for m in doc["earth_analogs"]["matches"]]
    assert i18n.localize(doc, "en") is doc                       # canonical form untouched


def test_composite_crism_character_keeps_codes():
    s = ("Positive summary parameters: OLINDEX3 (olivine (broad 1 µm band)); BD1900_2 (H2O in hydrated minerals). "
         "Screening only; mineral identification requires ratioed spectra.")
    t = i18n.translate(s)
    assert t.startswith("Parâmetros-sumário positivos: OLINDEX3 (olivina (banda larga em 1 µm)); BD1900_2 (H₂O")
    assert "Apenas triagem" in t


def test_processing_doc_gets_localised_links():
    doc = {"status": "processing", "analysis_id": "x",
           "links": {"self": "/v1/jobs/x", "report": "/v1/reports/x", "report_pdf": "/v1/reports/x?format=pdf"}}
    loc = i18n.localize(doc, "pt-BR")
    assert loc["links"]["self"] == "/v1/jobs/x?lang=pt-BR"
    assert loc["links"]["report_pdf"] == "/v1/reports/x?format=pdf"   # PDF stays canonical (English)
    assert doc["links"]["self"] == "/v1/jobs/x"


def test_topography_deadline_message_is_translated():
    from app import i18n
    msg = "ODE GDS did not return MOLA altimetry within 150 s; topography not computed (other sections unaffected)"
    assert i18n.translate(msg) == ("O ODE GDS não devolveu a altimetria MOLA em 150 s; topografia não calculada "
                                   "(as demais seções não são afetadas)")
