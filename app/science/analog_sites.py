"""Terrestrial analog sites for a lunar or Martian region.

The match is **geological**, not a spectral distance:

1. The region's evidence classes come only from statistically screened detections already
   computed by the Moon / Mars pipelines (M3 IBD1000/IBD2000; CRISM summary parameters).
2. A curated catalog (``app/data/terrestrial_analog_sites.json``) lists real sites with verified
   coordinates, documented lithology and published references that describe them as analogs.
3. A site is offered when its documented analog classes explain the region's evidence. The
   justification is the site's documented geology and reference; spectral data are added only
   where the definition is identical on both bodies (3-band depth presence at 1 and 2 µm on a
   masked EMIT composite) and the terrestrial measurement has enough rock pixels.

Nothing here is a probability, an abundance or a deposit indicator. Terrestrial-only indices
(NDVI, ASTER TIR, Sentinel-2 ratios) are never used as evidence of equivalence.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.analysis import (MineralogySection, Reason, SectionStatus, SpectralIndicator,
                                  TerrestrialAnalogSection, TerrestrialAnalogSite)

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "terrestrial_analog_sites.json"
MAX_SITES = 5
GLOBAL_CONTEXT_MAX_LAT = 60.0
# documentary strength of the analog claim, used only to order sites that explain the same evidence
BASIS_WEIGHT = {"published_analog": 3, "simulant_source": 3, "published_analog_general": 2,
                "mineralogical_reference": 1, "outreach": 0, "candidate": 0}
# minimum masked-EMIT quality before a terrestrial band-presence result is shown as a comparison
EMIT_MIN_ROCK_PIXELS = 200
EMIT_MIN_ROCK_FRACTION = 0.2

# --------------------------------------------------------------------------- #
# Evidence classes: what the region's measurements support, and which documented
# site classes can explain each one. "specific" = a parameter designed for that
# mineral family; "broad" = a generic absorption shared by several families.
# --------------------------------------------------------------------------- #
EVIDENCE: dict[str, dict[str, Any]] = {
    # Moon (M3 integrated band depths, Mustard et al. 2011)
    "lunar_pyroxene": dict(strength="specific", sites={"pyroxene_basalt", "norite"},
                           en="1 µm and 2 µm Fe2+ absorptions (pyroxene-bearing: mare basalt or norite)",
                           pt="absorções de Fe2+ em 1 µm e 2 µm (com piroxênio: basalto de mare ou norito)"),
    "lunar_olivine_or_glass": dict(strength="broad", sites={"olivine_rich", "volcanic_glass"},
                                   en="1 µm absorption without a 2 µm band (olivine- or glass-bearing; ambiguous)",
                                   pt="absorção em 1 µm sem banda em 2 µm (com olivina ou vidro; ambíguo)"),
    "lunar_no_mafic_band": dict(strength="broad", sites={"anorthosite"},
                                en="no significant 1 µm or 2 µm absorption (feldspathic, or mature space-weathered "
                                   "soil; ambiguous)",
                                pt="sem absorção significativa em 1 µm ou 2 µm (feldspático, ou solo maduro "
                                   "intemperizado pelo espaço; ambíguo)"),
    # Mars (CRISM summary parameters, Viviano-Beck et al. 2014)
    "olivine": dict(strength="specific", sites={"olivine_rich"}, en="olivine (OLINDEX3)", pt="olivina (OLINDEX3)"),
    "pyroxene": dict(strength="specific", sites={"pyroxene_basalt"}, en="pyroxene (LCPINDEX2/HCPINDEX2)",
                     pt="piroxênio (LCPINDEX2/HCPINDEX2)"),
    "mafic": dict(strength="broad", sites={"pyroxene_basalt", "olivine_rich"},
                  en="Fe2+ 1 µm absorption of mafic minerals (BDI1000IR)",
                  pt="absorção de Fe2+ em 1 µm de minerais máficos (BDI1000IR)"),
    "fe_mg_phyllosilicate": dict(strength="specific", sites={"fe_mg_phyllosilicate"},
                                 en="Fe/Mg-OH phyllosilicates (D2300)", pt="filossilicatos de Fe/Mg-OH (D2300)"),
    "al_phyllosilicate_silica": dict(strength="specific", sites={"al_phyllosilicate_silica"},
                                     en="Al-OH phyllosilicates or hydrated silica (BD2210_2)",
                                     pt="filossilicatos de Al-OH ou sílica hidratada (BD2210_2)"),
    "carbonate": dict(strength="specific", sites={"carbonate"},
                      en="carbonates (MIN2295_2480/MIN2345_2537)", pt="carbonatos (MIN2295_2480/MIN2345_2537)"),
    "sulfate": dict(strength="specific", sites={"sulfate"}, en="sulfates (BD2100_2/SINDEX2)",
                    pt="sulfatos (BD2100_2/SINDEX2)"),
    "hydrated": dict(strength="broad", sites={"sulfate", "fe_mg_phyllosilicate", "al_phyllosilicate_silica",
                                              "altered_basaltic_soil"},
                     en="H2O in hydrated minerals (BD1900_2; mineral family not resolved)",
                     pt="H2O em minerais hidratados (BD1900_2; família mineral não resolvida)"),
    "ferric_oxide": dict(strength="specific", sites={"ferric_oxide", "altered_basaltic_soil"},
                         en="crystalline ferric oxides (BD530_2)", pt="óxidos férricos cristalinos (BD530_2)"),
    "ice": dict(strength="specific", sites=set(), en="CO2 or H2O ice (BD1435/BD1500_2)",
                pt="gelo de CO2 ou H2O (BD1435/BD1500_2)"),
    "mars_global_basaltic": dict(strength="broad", sites={"pyroxene_basalt", "altered_basaltic_soil"},
                                 en="no regional CRISM measurement; global context only (basaltic crust and "
                                    "altered basaltic soil)",
                                 pt="sem medição CRISM regional; apenas contexto global (crosta basáltica e solo "
                                    "basáltico alterado)"),
}
CRISM_CLASS = {"OLINDEX3": "olivine", "LCPINDEX2": "pyroxene", "HCPINDEX2": "pyroxene", "BDI1000IR": "mafic",
               "D2300": "fe_mg_phyllosilicate", "BD2210_2": "al_phyllosilicate_silica",
               "MIN2295_2480": "carbonate", "MIN2345_2537": "carbonate", "BD2100_2": "sulfate",
               "SINDEX2": "sulfate", "BD1900_2": "hydrated", "BD530_2": "ferric_oxide",
               "BD1435": "ice", "BD1500_2": "ice"}
# a broad class is dropped when a specific class already explains the same absorption
SUBSUMED = {"mafic": {"olivine", "pyroxene"},
            "hydrated": {"sulfate", "fe_mg_phyllosilicate", "al_phyllosilicate_silica", "carbonate"}}

T = {
    "en": dict(
        method="Geological match: the region's screened spectral detections are mapped to mineral families; "
               "curated terrestrial sites whose documented geology (with references) contains those families "
               "are listed. Not a spectral distance or a probability.",
        disclaimer="Terrestrial analogs are documented sites with similar mineral families. They do not "
                   "imply the same origin, abundance, or any mineral occurrence at the selected region.",
        global_basis="No regional spectral measurement is available here; the sites illustrate the global "
                     "basaltic character of the Martian crust (Bandfield et al. 2000, Science 287, 1626; "
                     "doi:10.1126/science.287.5458.1626) and are NOT specific to the selected region.",
        no_evidence="The region's measurements show no screened detection that maps to a documented analog family.",
        no_site="No catalog site documents this family: {labels}.",
        emit_both="Masked EMIT composite of the site ({scenes} scenes, {start}–{end}, {pct}% rock pixels): "
                  "1 µm band {s1}, 2 µm band {s2}; region: 1 µm {r1}, 2 µm {r2}.",
        detected="detected", not_detected="not detected", unknown="not assessed",
        agree="Same 3-band depth definition on both bodies: {band} band presence agrees ({state}).",
        disagree="Same 3-band depth definition on both bodies: {band} band presence differs (region {r}, site {s}).",
        emit_weak="EMIT measurement of the site not used: {why}.",
        emit_none="No masked EMIT measurement of the site is recorded.",
        why_cov="only {pct}% rock pixels after cloud/water/vegetation/snow masks",
        why_status="status {status}",
        two_um="On Earth the 2 µm band shares the window with residual atmospheric CO2 (~2.0 µm); presence only.",
        matched="Explains the region's {label}.",
        weathering="Terrestrial surfaces are chemically weathered and lack space weathering; spectra are "
                   "not expected to match in band strength or slope.",
    ),
    "pt-BR": dict(
        method="Correspondência geológica: as detecções espectrais triadas da região são associadas a famílias "
               "minerais; são listados sítios terrestres curados cuja geologia documentada (com referências) "
               "contém essas famílias. Não é distância espectral nem probabilidade.",
        disclaimer="Análogos terrestres são sítios documentados com famílias minerais semelhantes. Não implicam "
                   "mesma origem, abundância nem ocorrência mineral na região selecionada.",
        global_basis="Não há medição espectral regional aqui; os sítios ilustram o caráter basáltico global da "
                     "crosta marciana (Bandfield et al. 2000, Science 287, 1626; doi:10.1126/science.287.5458.1626) "
                     "e NÃO são específicos da região selecionada.",
        no_evidence="As medições da região não têm detecção triada que corresponda a uma família análoga documentada.",
        no_site="Nenhum sítio do catálogo documenta esta família: {labels}.",
        emit_both="Composto EMIT mascarado do sítio ({scenes} cenas, {start}–{end}, {pct}% de pixels de rocha): "
                  "banda de 1 µm {s1}, banda de 2 µm {s2}; região: 1 µm {r1}, 2 µm {r2}.",
        detected="detectada", not_detected="não detectada", unknown="não avaliada",
        agree="Mesma definição de profundidade de 3 bandas nos dois corpos: presença da banda de {band} "
              "coincide ({state}).",
        disagree="Mesma definição de profundidade de 3 bandas nos dois corpos: presença da banda de {band} "
                 "difere (região {r}, sítio {s}).",
        emit_weak="Medição EMIT do sítio não usada: {why}.",
        emit_none="Não há medição EMIT mascarada registrada para o sítio.",
        why_cov="só {pct}% de pixels de rocha após máscaras de nuvem/água/vegetação/neve",
        why_status="status {status}",
        two_um="Na Terra a banda de 2 µm divide a janela com CO2 atmosférico residual (~2,0 µm); só presença.",
        matched="Explica, na região: {label}.",
        weathering="Superfícies terrestres sofrem intemperismo químico e não têm intemperismo espacial; não se "
                   "espera que os espectros coincidam em intensidade de banda ou inclinação.",
    ),
}


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _ind(min_s: MineralogySection) -> dict[str, SpectralIndicator]:
    return {i.name: i for i in min_s.indicators}


def region_evidence(body: str, min_s: MineralogySection, latitude: float | None = None
                    ) -> tuple[list[dict], str | None]:
    """Evidence classes supported by screened detections, and the basis."""
    usable = min_s.status in (SectionStatus.available, SectionStatus.partial)
    ind = _ind(min_s) if usable else {}
    ev: list[dict] = []
    if body == "moon":
        a, b = ind.get("IBD1000"), ind.get("IBD2000")
        if a is None or b is None or a.detected is None or b.detected is None:
            return [], None
        cls = ("lunar_pyroxene" if a.detected and b.detected else
               "lunar_olivine_or_glass" if a.detected else
               None if b.detected else "lunar_no_mafic_band")
        if cls:
            ev.append({"class": cls, "indicators": ["IBD1000", "IBD2000"]})
        return ev, "regional_spectral_evidence"
    if body == "mars":
        if not usable:
            # global context only when CRISM genuinely has no usable coverage, never after a provider failure
            # and only away from the polar layered deposits / ice caps (|lat| <= 60°)
            if latitude is not None and abs(latitude) > GLOBAL_CONTEXT_MAX_LAT:
                return [], None
            if min_s.status == SectionStatus.unavailable and min_s.reason in (
                    Reason.no_coverage, Reason.no_compatible_observations, Reason.insufficient_data):
                return [{"class": "mars_global_basaltic", "indicators": []}], "global_context"
            return [], None
        hits: dict[str, list[str]] = {}
        for name, cls in CRISM_CLASS.items():
            i = ind.get(name)
            if i is not None and i.detected:
                hits.setdefault(cls, []).append(name)
        for broad, specific in SUBSUMED.items():
            if broad in hits and specific & hits.keys():
                hits.pop(broad)
        ev = [{"class": c, "indicators": v} for c, v in hits.items()]
        return ev, "regional_spectral_evidence"
    return [], None


def _region_band(body: str, min_s: MineralogySection, band: str) -> bool | None:
    i = _ind(min_s).get(f"legacy_bd{band}")
    return None if i is None else i.detected


def _emit_summary(site: dict) -> dict | None:
    m = site.get("emit")
    if not m:
        return None
    rock = (m.get("variants") or {}).get("rock") or {}
    cov = m.get("coverage") or {}
    dates = sorted(s["date"] for s in m.get("scenes", []) if s.get("date"))
    return {"status": m.get("status"), "scenes": m.get("scene_count"),
            "first_date": dates[0] if dates else None, "last_date": dates[-1] if dates else None,
            "rock_fraction": cov.get("rock_fraction"), "rock_pixels": (rock.get("bd1000") or {}).get("n_pixels"),
            "bd1000_detected": m.get("detected", {}).get("bd1000"), "bd2000_detected": m.get("detected", {}).get("bd2000"),
            "measured_at": m.get("measured_at"), "analysis_id": m.get("analysis_id"),
            "radius_km": m.get("radius_km")}


def _emit_usable(e: dict | None) -> tuple[bool, str | None]:
    if not e:
        return False, None
    if e["status"] != "ok":
        return False, "status"
    if (e.get("rock_pixels") or 0) < EMIT_MIN_ROCK_PIXELS or (e.get("rock_fraction") or 0) < EMIT_MIN_ROCK_FRACTION:
        return False, "coverage"
    return True, None


def _texts(site: dict, matched: list[str], comp: dict, lang: str) -> dict[str, list[str] | str]:
    t = T[lang]
    sfx = "_pt" if lang == "pt-BR" else "_en"

    def state(v):
        return t["unknown"] if v is None else t["detected"] if v else t["not_detected"]

    just = [t["matched"].format(label=EVIDENCE[c]["pt" if lang == "pt-BR" else "en"]) for c in matched]
    just += [a["rationale" + sfx] for a in site["analog_for"] if a["body"] == comp["body"]]
    sims, diffs = list(site.get("similarities" + sfx, [])), list(site.get("differences" + sfx, []))
    e = comp.get("emit")
    ok, why = _emit_usable(e)
    if ok:
        r1, r2 = comp["region_bd1000"], comp["region_bd2000"]
        sims.append(t["emit_both"].format(scenes=e["scenes"], start=e["first_date"], end=e["last_date"],
                                          pct=round(100 * e["rock_fraction"]), s1=state(e["bd1000_detected"]),
                                          s2=state(e["bd2000_detected"]), r1=state(r1), r2=state(r2)))
        for band, r, s in (("1 µm", r1, e["bd1000_detected"]), ("2 µm", r2, e["bd2000_detected"])):
            if r is None or s is None:
                continue
            (sims if r == s else diffs).append(
                t["agree"].format(band=band, state=state(r)) if r == s else
                t["disagree"].format(band=band, r=state(r), s=state(s)))
        diffs.append(t["two_um"])
    elif e:
        diffs.append(t["emit_weak"].format(why=t["why_cov"].format(pct=round(100 * (e.get("rock_fraction") or 0)))
                                           if why == "coverage" else t["why_status"].format(status=e["status"])))
    else:
        diffs.append(t["emit_none"])
    diffs.append(t["weathering"])
    return {"setting": site["setting" + sfx], "justification": just, "similarities": sims, "differences": diffs,
            "limitations": list(site.get("limitations" + sfx, []))}


def match(body: str, min_s: MineralogySection, latitude: float | None = None) -> TerrestrialAnalogSection:
    if body not in ("moon", "mars"):
        return TerrestrialAnalogSection(status=SectionStatus.unavailable, reason=Reason.not_supported)
    cat = catalog()
    evidence, basis = region_evidence(body, min_s, latitude)
    if basis is None:
        return TerrestrialAnalogSection(status=SectionStatus.unavailable, reason=Reason.not_attempted,
                                        catalog=f"{cat['name']} v{cat['version']}")
    ev_classes = [e["class"] for e in evidence]
    r1, r2 = _region_band(body, min_s, "1000"), _region_band(body, min_s, "2000")
    scored = []
    for site in cat["sites"]:
        if site.get("verification") != "verified":      # unverified coordinates are never offered
            continue
        docs = set().union(*[set(a["classes"]) for a in site["analog_for"] if a["body"] == body] or [set()])
        if not docs:
            continue
        matched = [c for c in ev_classes if EVIDENCE[c]["sites"] & docs]
        if not matched:
            continue
        n_spec = sum(EVIDENCE[c]["strength"] == "specific" for c in matched)
        e = _emit_summary(site)
        ok, _ = _emit_usable(e)
        agree = 0
        if ok and basis == "regional_spectral_evidence":
            agree = sum(1 for r, s in ((r1, e["bd1000_detected"]), (r2, e["bd2000_detected"]))
                        if r is not None and s is not None and r == s)
        basis_w = max(BASIS_WEIGHT.get(a.get("basis"), 0) for a in site["analog_for"] if a["body"] == body)
        scored.append(((n_spec, len(matched), basis_w, agree, -site["coordinate_precision_km"]), site, matched, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    sites = []
    for _, site, matched, e in scored[:MAX_SITES]:
        comp = {"body": body, "emit": e, "region_bd1000": r1 if basis != "global_context" else None,
                "region_bd2000": r2 if basis != "global_context" else None}
        sites.append(TerrestrialAnalogSite(
            id=site["id"], name=site["name"], country=site["country"], latitude=site["lat"], longitude=site["lon"],
            coordinate_source=site["coordinate_source"], coordinate_precision_km=site["coordinate_precision_km"],
            key_minerals=site["key_minerals"], matched_classes=matched,
            analog_basis=next(a.get("basis") for a in site["analog_for"] if a["body"] == body),
            references=site["references"], emit=e, region_bands={"bd1000": comp["region_bd1000"],
                                                                 "bd2000": comp["region_bd2000"]},
            **_texts(site, matched, comp, "en")))
    explained = {c for _, _, m, _ in scored for c in m}
    unexplained = [c for c in ev_classes if c not in explained]
    notes = []
    if basis == "global_context":
        notes.append(T["en"]["global_basis"])
    if not evidence:
        notes.append(T["en"]["no_evidence"])
    if unexplained:
        notes.append(T["en"]["no_site"].format(labels="; ".join(EVIDENCE[c]["en"] for c in unexplained)))
    status = (SectionStatus.available if sites and basis == "regional_spectral_evidence" else
              SectionStatus.partial if sites else SectionStatus.unavailable)
    return TerrestrialAnalogSection(
        status=status, reason=None if sites else Reason.no_coverage if not evidence else Reason.insufficient_data,
        body=body, basis=basis, method=T["en"]["method"], catalog=f"{cat['name']} v{cat['version']}",
        region_evidence=[{"class": e["class"], "label": EVIDENCE[e["class"]]["en"], "indicators": e["indicators"],
                          "strength": EVIDENCE[e["class"]]["strength"]} for e in evidence],
        unexplained_evidence=unexplained, sites=sites, notes=notes, disclaimer=T["en"]["disclaimer"])


def localize(section: dict, lang: str) -> dict:
    """Rebuild the prose of a serialized section in ``lang`` from the catalog and the structured fields."""
    if lang not in T or not section or not section.get("sites") and not section.get("notes"):
        return section
    t, by_id = T[lang], {s["id"]: s for s in catalog()["sites"]}
    body = section.get("body")
    for s in section.get("sites", []):
        site = by_id.get(s["id"])
        if site is None:
            continue
        rb = s.get("region_bands") or {}
        comp = {"body": body, "emit": s.get("emit"), "region_bd1000": rb.get("bd1000"),
                "region_bd2000": rb.get("bd2000")}
        s.update(_texts(site, s["matched_classes"], comp, lang))
    key = "pt" if lang == "pt-BR" else "en"
    for e in section.get("region_evidence", []):
        if e.get("class") in EVIDENCE:
            e["label"] = EVIDENCE[e["class"]][key]
    unexplained = section.get("unexplained_evidence", [])
    notes = []
    if section.get("basis") == "global_context":
        notes.append(t["global_basis"])
    if not section.get("region_evidence"):
        notes.append(t["no_evidence"])
    if unexplained:
        notes.append(t["no_site"].format(labels="; ".join(EVIDENCE[c][key] for c in unexplained if c in EVIDENCE)))
    section["notes"] = notes
    if section.get("method"):
        section["method"] = t["method"]
    section["disclaimer"] = t["disclaimer"]
    return section
