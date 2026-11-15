"""PDF rendering of a stored AnalysisResult (ReportLab).

Layout and palette adapted from the legacy ``report_engine.py``. Every number
in the PDF is read from the stored JSON; absent values print as "—" with the
section's status and reason. No narrative text is generated about the data.

The report follows the requested language (``en`` or ``pt-BR``): the scientific
prose comes from :func:`app.i18n.localize`, exactly as in the JSON response, and
the fixed labels of the layout come from ``_PT`` below.
"""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import i18n

INK = colors.HexColor("#1B1B1D")
FOREST = colors.HexColor("#4C7C59")
PAPER = colors.HexColor("#DFDBD8")
MUTE = colors.HexColor("#6b6b6b")
PLANET_NAME = {"en": {"earth": "Earth", "moon": "Moon", "mars": "Mars"},
               "pt-BR": {"earth": "Terra", "moon": "Lua", "mars": "Marte"}}

# Fixed layout labels in Portuguese, keyed by their English text (English is the default).
_PT = {
    "GEØ.IA PLANETARY INTELLIGENCE — ANALYSIS REPORT": "GEØ.IA PLANETARY INTELLIGENCE — RELATÓRIO DE ANÁLISE",
    "Analysis": "Análise", "status": "estado", "completed": "concluída", "schema": "esquema",
    "Frame": "Referencial", "longitude east-positive": "longitude positiva para leste",
    "Section status": "Estado das seções", "Section": "Seção", "Status": "Estado",
    "Imagery (WMTS)": "Imagens (WMTS)", "Topography": "Topografia",
    "Mineralogy / spectroscopy": "Mineralogia / espectroscopia",
    "Terrestrial analog sites": "Sítios análogos terrestres",
    "Environment — illumination": "Ambiente — iluminação",
    "Moon–Earth geomorphology (experimental)": "Geomorfologia Lua–Terra (experimental)",
    "Spectral comparison (appendix)": "Comparação espectral (apêndice)",
    "Method": "Método", "Datum": "Datum", "Valid shots / samples": "Disparos / amostras válidos",
    "Sampled radius (km)": "Raio amostrado (km)", "Elevation mean / median (m)": "Elevação média / mediana (m)",
    "Elevation p05 – p95 (m)": "Elevação p05 – p95 (m)", "Relief p95-p05 (m)": "Relevo p95-p05 (m)",
    "Regional slope / aspect (°)": "Declividade / orientação regional (°)",
    "Local slope median / p95 (°)": "Declividade local mediana / p95 (°)", "baseline": "linha de base",
    "Roughness RMS (m)": "Rugosidade RMS (m)", "Cell coverage": "Cobertura de células",
    "Instrument": "Instrumento", "Product used": "Produto usado",
    "Products found / containing point": "Produtos encontrados / que contêm o ponto",
    "Valid pixels / window": "Pixels válidos / janela", "Spectral character": "Caráter espectral",
    "Indicator": "Indicador", "Median": "Mediana", "Pixels": "Pixels", "Sensitive to": "Sensível a",
    "Result": "Resultado",
    "Terrestrial analog sites (documented geology)": "Sítios análogos terrestres (geologia documentada)",
    "Basis": "Base", "Region evidence": "Evidência da região",
    "Why": "Por quê", "Similar": "Semelhanças", "Different": "Diferenças", "Limits": "Limites",
    "References": "Referências",
    "Environment — illumination (model-derived)": "Ambiente — iluminação (derivada de modelo)",
    "Fraction of time sunlit": "Fração do tempo iluminada", "Area in permanent shadow": "Área em sombra permanente",
    "Fraction of time Earth is visible": "Fração do tempo com a Terra visível",
    "mean": "média", "range": "faixa",
    "At the centre point": "No ponto central", "Solar illumination": "Iluminação solar",
    "Earth visible": "Terra visível", "Permanent shadow": "Sombra permanente", "yes": "sim", "no": "não",
    "Analysed extent": "Área analisada", "requested": "solicitado", "pixel": "pixel",
    "Products": "Produtos", "Limitations": "Limitações", "Notes": "Notas",
    "Lunar terrain profile": "Perfil do terreno lunar", "Scale": "Escala", "valid windows": "janelas válidas",
    "samples": "amostras", "Metric": "Métrica", "Metrics": "Métricas", "Value": "Valor",
    "Purpose": "Finalidade", "Sites compared": "Sítios comparados",
    "Calculated correspondences": "Correspondências calculadas",
    "No demonstrable correspondence for this purpose.": "Nenhuma correspondência demonstrável para esta finalidade.",
    "Inconclusive": "Inconclusivo",
    "Relief modified by mining (reference only, not a correspondence)":
        "Relevo modificado por mineração (só referência, não é correspondência)",
    "documented lunar analog": "análogo lunar documentado",
    "Median slope": "Declividade mediana", "Slope p90 (steepest slopes)": "Declividade p90 (encostas mais íngremes)",
    "Slope variability (IQR)": "Variabilidade da declividade (IQR)", "Roughness": "Rugosidade",
    "Relief variability (σ)": "Variabilidade do relevo (σ)", "Relief amplitude": "Amplitude do relevo",
    "Confidence": "Confiança", "Criterion": "Critério", "Met": "Atendido", "Detail": "Detalhe",
    "Data sources and provenance": "Fontes de dados e procedência", "ID": "ID",
    "Provider / service": "Provedor / serviço", "Instrument / product": "Instrumento / produto",
    "Observation": "Observação", "Status / note": "Estado / nota", "Problems reported": "Problemas relatados",
    "Appendix — illustrative spectral comparison (2 band-depth attributes)":
        "Apêndice — comparação espectral ilustrativa (2 atributos de profundidade de banda)",
    "Not an analog result: two band depths do not discriminate between library sites, and the library mixes "
    "deposit types. The terrestrial analog sites above are the analog result.":
        "Não é um resultado de análogo: duas profundidades de banda não discriminam os sítios da biblioteca, e a "
        "biblioteca mistura tipos de depósito. Os sítios análogos terrestres acima são o resultado de análogo.",
    "Directly comparable": "Diretamente comparáveis", "Missing": "Ausentes",
    "Library site": "Sítio da biblioteca", "Distance": "Distância", "Similarity (ranking aid)":
        "Similaridade (auxílio de ordenação)",
    "Generated from the stored analysis JSON. Similarity scores are ranking aids, not probabilities of mineral "
    "occurrence; spectral indicators are screening results, not mineral identifications.":
        "Gerado a partir do JSON armazenado da análise. Escores de similaridade são auxílios de ordenação, não "
        "probabilidades de ocorrência mineral; indicadores espectrais são resultados de triagem, não "
        "identificações minerais.",
}

METRIC_NAME = {"slope_median_deg": "Median slope", "slope_p90_deg": "Slope p90 (steepest slopes)",
               "slope_iqr_deg": "Slope variability (IQR)", "roughness_m": "Roughness",
               "relief_sigma_m": "Relief variability (σ)", "relief_amplitude_m": "Relief amplitude"}


def _lang(lang: str | None) -> str:
    return lang if lang in i18n.SUPPORTED else i18n.DEFAULT


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Title"], textColor=INK, fontSize=18, leading=22, spaceAfter=2),
        "eyebrow": ParagraphStyle("eb", parent=ss["Normal"], textColor=FOREST, fontSize=8, leading=10,
                                  spaceAfter=8, fontName="Helvetica-Bold"),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], textColor=INK, fontSize=11, leading=14,
                             spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"),
        "h3": ParagraphStyle("h3", parent=ss["Normal"], textColor=INK, fontSize=8.5, leading=11.5,
                             spaceBefore=5, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("b", parent=ss["Normal"], textColor=INK, fontSize=8.5, leading=11.5),
        "small": ParagraphStyle("s", parent=ss["Normal"], textColor=MUTE, fontSize=7.2, leading=9.5),
    }


def _fmt(v, nd=3) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def _pct(v, nd=1) -> str:
    return "—" if v is None else f"{100 * v:.{nd}f}%"


def _p(text, style) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _table(rows, widths, st, header=False) -> Table:
    data = [[_p(c, st["small"] if header and i == 0 else st["body"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, PAPER),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1EFED")))
    t.setStyle(TableStyle(style))
    return t


def _status(sec: dict) -> str:
    s = sec.get("status", "—")
    return f"{s}" + (f" ({sec['reason']})" if sec.get("reason") else "")


def _environment(env: dict, T, st, W) -> list:
    out = [_p(T("Environment — illumination (model-derived)"), st["h2"])]
    if env.get("status") != "available":
        out.append(_p(f"{T('Status')}: {_status(env)}.", st["body"]))
    else:
        sun, earth = env.get("sunlit_fraction") or {}, env.get("earth_visible_fraction") or {}
        ctr, ext = env.get("centre") or {}, env.get("analyzed_extent") or {}
        shadow = ctr.get("permanent_shadow")
        rows = [
            [T("Fraction of time sunlit"), f"{T('mean')} {_pct(sun.get('mean'))} · {T('range')} "
                                           f"{_pct(sun.get('p05'))} – {_pct(sun.get('p95'))} (p05 – p95)"],
            [T("Area in permanent shadow"), _pct(env.get("permanent_shadow_fraction"))],
            [T("Fraction of time Earth is visible"), f"{T('mean')} {_pct(earth.get('mean'))} · {T('range')} "
                                                     f"{_pct(earth.get('p05'))} – {_pct(earth.get('p95'))} (p05 – p95)"],
            [f"{T('At the centre point')}: {T('Solar illumination')}", _pct(ctr.get("sunlit_fraction"))],
            [f"{T('At the centre point')}: {T('Earth visible')}", _pct(ctr.get("earth_visible_fraction"))],
            [f"{T('At the centre point')}: {T('Permanent shadow')}",
             "—" if shadow is None else (T("yes") if shadow else T("no"))],
            [T("Analysed extent"), f"r = {_fmt(ext.get('radius_km'), 2)} km ({T('requested')} "
                                   f"{_fmt(ext.get('requested_radius_km'), 2)} km) · {_fmt(ext.get('area_km2'), 2)} km² · "
                                   f"{T('pixel')} {_fmt(ext.get('pixel_size_m'), 0)} m"],
            [T("Products"), ", ".join(env.get("products") or []) or "—"],
            [T("Method"), _fmt(env.get("method"))],
        ]
        out.append(_table(rows, [60 * mm, W - 60 * mm], st))
    for key in ("limitations", "notes"):
        for x in env.get(key) or []:
            out.append(_p(f"• {x}", st["small"]))
    return out


def _geomorphology(g: dict, T, st, W) -> list:
    out = [_p(T("Moon–Earth geomorphology (experimental)"), st["h2"])]
    notes = list(g.get("notes") or [])
    if notes:                                     # the "experimental, not a recommendation" note comes first
        out.append(_p(notes.pop(0), st["body"]))
    if g.get("status") != "available":
        out.append(_p(f"{T('Status')}: {_status(g)}.", st["body"]))
    mp = g.get("moon_profile") or {}
    if mp:
        out.append(_p(f"{T('Lunar terrain profile')}: {T('Scale')} {_fmt(mp.get('baseline_m'), 0)} m · "
                      f"{T('valid windows')} {_fmt(mp.get('windows_valid'))}/{_fmt(mp.get('windows_total'))} · "
                      f"{T('samples')} {_fmt(mp.get('samples'))}", st["h3"]))
        rows = [[T("Metric"), T("Value")]]
        for key, m in (mp.get("metrics") or {}).items():
            rows.append([T(METRIC_NAME.get(key, key)),
                         f"{_fmt(m.get('value'), 2)} ± {_fmt(m.get('uncertainty'), 2)} {m.get('unit') or ''}"])
        if len(rows) > 1:
            out.append(_table(rows, [70 * mm, W - 70 * mm], st, header=True))
    for comp in (g.get("comparisons") or {}).values():
        out.append(_p(f"{T('Purpose')}: {comp.get('label')}", st["h3"]))
        metrics = ", ".join(T(METRIC_NAME.get(m, m)) for m in comp.get("metrics") or [])
        out.append(_p(f"{T('Metrics')}: {metrics} · {T('Sites compared')}: {_fmt(comp.get('sites_compared'))}",
                      st["small"]))
        matches = comp.get("matches") or []
        if matches:
            names = "; ".join(f"{m.get('name')} ({m.get('country')})"
                              + (f" — {T('documented lunar analog')}" if m.get("documented_lunar_analog") else "")
                              for m in matches)
            out.append(_p(f"{T('Calculated correspondences')}: {names}", st["body"]))
        elif comp.get("result") == "inconclusive":
            out.append(_p(T("Inconclusive"), st["body"]))
        else:
            out.append(_p(T("No demonstrable correspondence for this purpose."), st["body"]))
        mod = comp.get("modified_relief_references") or []
        if mod:
            out.append(_p(f"{T('Relief modified by mining (reference only, not a correspondence)')}: "
                          + "; ".join(m.get("name", "") for m in mod), st["small"]))
    for x in notes + list(g.get("limitations") or []):
        out.append(_p(f"• {x}", st["small"]))
    return out


def render_pdf(doc: dict, lang: str | None = None) -> bytes:
    lang = _lang(lang)
    doc = i18n.localize(doc, lang)          # same scientific prose as the JSON response in that language

    def T(text: str) -> str:
        return _PT.get(text, text) if lang == "pt-BR" else text

    st = _styles()
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"GEØ.IA report {doc.get('analysis_id')}")
    W = A4[0] - 32 * mm
    c = doc.get("coordinates", {})
    planet = PLANET_NAME[lang].get(doc.get("planet"), doc.get("planet"))
    story = [
        Paragraph(escape(T("GEØ.IA PLANETARY INTELLIGENCE — ANALYSIS REPORT")), st["eyebrow"]),
        _p(f"{planet} — "
           f"{_fmt(c.get('latitude'), 4)}°, {_fmt(c.get('longitude'), 4)}° (r = {_fmt(c.get('radius_km'), 2)} km)",
           st["h1"]),
        _p(f"{T('Analysis')} {doc.get('analysis_id')} · {T('status')} {doc.get('status')} · "
           f"{T('completed')} {doc.get('completed_at')} · {T('schema')} {doc.get('schema_version')}", st["small"]),
        _p(f"{T('Frame')}: {c.get('reference_frame')}; latitude {c.get('latitude_type')}; "
           f"{T('longitude east-positive')} (east_360 = {_fmt(c.get('longitude_east_360'), 4)}°).", st["small"]),
        Spacer(1, 4),
    ]

    env, geo = doc.get("environment") or {}, doc.get("geomorphology") or {}
    sections = [("Imagery (WMTS)", "imagery"), ("Topography", "topography"), ("Mineralogy / spectroscopy", "mineralogy"),
                ("Terrestrial analog sites", "terrestrial_analogs")]
    if env:
        sections.append(("Environment — illumination", "environment"))
    if geo:
        sections.append(("Moon–Earth geomorphology (experimental)", "geomorphology"))
    sections.append(("Spectral comparison (appendix)", "earth_analogs"))
    story.append(_p(T("Section status"), st["h2"]))
    story.append(_table([[T("Section"), T("Status")]] + [
        [T(name), _status(doc.get(key) or {})] for name, key in sections], [60 * mm, W - 60 * mm], st, header=True))

    t = doc.get("topography", {})
    story.append(_p(T("Topography"), st["h2"]))
    e, ls = t.get("elevation_m") or {}, t.get("local_slope_degrees") or {}
    story.append(_table([
        [T("Method"), _fmt(t.get("method"))], [T("Datum"), _fmt(t.get("datum"))],
        [T("Valid shots / samples"), _fmt(t.get("n_points"))],
        [T("Sampled radius (km)"), _fmt(t.get("sampled_radius_km"), 2)],
        [T("Elevation mean / median (m)"), f"{_fmt(e.get('mean'), 1)} / {_fmt(e.get('median'), 1)}"],
        [T("Elevation p05 – p95 (m)"), f"{_fmt(e.get('p05'), 1)} – {_fmt(e.get('p95'), 1)}"],
        [T("Relief p95-p05 (m)"), _fmt(t.get("relief_m"), 1)],
        [T("Regional slope / aspect (°)"),
         f"{_fmt(t.get('regional_slope_degrees'), 2)} / {_fmt(t.get('regional_aspect_degrees'), 0)}"],
        [T("Local slope median / p95 (°)"), f"{_fmt(ls.get('median'), 2)} / {_fmt(ls.get('p95'), 2)} "
                                            f"({T('baseline')} {_fmt(t.get('slope_baseline_m'), 0)} m)"],
        [T("Roughness RMS (m)"), _fmt(t.get("roughness_m"), 1)], [T("Cell coverage"), _fmt(t.get("coverage_fraction"), 2)],
    ], [60 * mm, W - 60 * mm], st))

    m = doc.get("mineralogy", {})
    story.append(_p(T("Mineralogy / spectroscopy"), st["h2"]))
    story.append(_table([
        [T("Instrument"), _fmt(m.get("instrument"))], [T("Product used"), _fmt(m.get("product_used"))],
        [T("Products found / containing point"),
         f"{_fmt(m.get('products_found'))} / {_fmt(m.get('products_containing_point'))}"],
        [T("Valid pixels / window"), f"{_fmt(m.get('valid_pixels'))} / {_fmt(m.get('window_pixels'))}"],
        [T("Spectral character"), _fmt(m.get("spectral_character"))],
    ], [60 * mm, W - 60 * mm], st))
    inds = m.get("indicators") or []
    if inds:
        rows = [[T("Indicator"), T("Median"), "p95", T("Pixels"), T("Sensitive to"), T("Result")]]
        for i in inds:
            v = i.get("value") or {}
            rows.append([i["name"], _fmt(v.get("median"), 4), _fmt(v.get("p95"), 4), _fmt(i.get("n_pixels")),
                         _fmt(i.get("sensitive_to")), _fmt(i.get("interpretation"))])
        story.append(Spacer(1, 3))
        story.append(_table(rows, [24 * mm, 16 * mm, 16 * mm, 13 * mm, 45 * mm, W - 114 * mm], st, header=True))

    ta = doc.get("terrestrial_analogs") or {}
    if ta:
        story.append(_p(T("Terrestrial analog sites (documented geology)"), st["h2"]))
        ev = "; ".join(e.get("label", "") for e in ta.get("region_evidence") or []) or "—"
        story.append(_p(f"{T('Status')}: {_status(ta)}. {T('Basis')}: {ta.get('basis') or '—'}. "
                        f"{T('Region evidence')}: {ev}.", st["body"]))
        for n in ta.get("notes") or []:
            story.append(_p(n, st["small"]))
        for s in ta.get("sites") or []:
            refs = "; ".join(f"{r.get('citation')}" + (f" doi:{r['doi']}" if r.get("doi") else "")
                             for r in s.get("references") or [])
            story.append(_p(f"{s['name']} ({s['country']}) — {s['latitude']:.4f}, {s['longitude']:.4f} "
                            f"(±{_fmt(s.get('coordinate_precision_km'), 2)} km). {s.get('setting', '')}", st["body"]))
            for label, key in (("Why", "justification"), ("Similar", "similarities"), ("Different", "differences"),
                               ("Limits", "limitations")):
                if s.get(key):
                    story.append(_p(f"{T(label)}: " + " ".join(s[key]), st["small"]))
            if refs:
                story.append(_p(f"{T('References')}: {refs}", st["small"]))
        if ta.get("disclaimer"):
            story.append(_p(ta["disclaimer"], st["small"]))

    if env:
        story += _environment(env, T, st, W)
    if geo:
        story += _geomorphology(geo, T, st, W)

    conf = doc.get("confidence", {})
    story.append(_p(f"{T('Confidence')}: {conf.get('level')}", st["h2"]))
    if conf.get("criteria"):
        story.append(_table([[T("Criterion"), T("Met"), T("Detail")]] + [
            [x["criterion"], T("yes") if x["met"] else T("no"), x["detail"]] for x in conf["criteria"]],
            [60 * mm, 12 * mm, W - 72 * mm], st, header=True))
    for lim in conf.get("limitations") or []:
        story.append(_p(f"• {lim}", st["small"]))

    story.append(_p(T("Data sources and provenance"), st["h2"]))
    rows = [[T("ID"), T("Provider / service"), T("Instrument / product"), T("Observation"), T("Status / note")]]
    for s in doc.get("data_sources") or []:
        rows.append([s["source_id"], f"{s['provider']} — {s['service']}",
                     f"{s.get('instrument') or '—'} {s.get('product_type') or ''} {s.get('product_id') or ''}",
                     f"{s.get('observation_start') or '—'} → {s.get('observation_end') or '—'}",
                     f"{s.get('status')}: {s.get('message') or ''}"[:400]])
    story.append(_table(rows, [13 * mm, 42 * mm, 45 * mm, 34 * mm, W - 134 * mm], st, header=True))

    if doc.get("problems"):
        story.append(_p(T("Problems reported"), st["h2"]))
        for pb in doc["problems"]:
            story.append(_p(f"• [{pb['section']}/{pb['reason']}] {pb['message']}", st["small"]))

    # The 2-attribute spectral ranking does not discriminate sites (docs/CIENCIA.md); it is kept for
    # transparency as an appendix, after the documented terrestrial analog sites.
    a = doc.get("earth_analogs", {})
    story.append(_p(T("Appendix — illustrative spectral comparison (2 band-depth attributes)"), st["h2"]))
    story.append(_p(T("Not an analog result: two band depths do not discriminate between library sites, and the "
                      "library mixes deposit types. The terrestrial analog sites above are the analog result."),
                    st["small"]))
    story.append(_p(f"{T('Status')}: {_status(a)}. "
                    f"{T('Directly comparable')}: {', '.join(a.get('directly_comparable') or []) or '—'}. "
                    f"{T('Missing')}: {', '.join(a.get('missing') or []) or '—'}.", st["body"]))
    if a.get("matches"):
        rows = [[T("Library site"), T("Distance"), T("Similarity (ranking aid)")]]
        rows += [[x["name"], _fmt(x["distance"], 4), _fmt(x["similarity"], 3)] for x in a["matches"]]
        story.append(_table(rows, [90 * mm, 30 * mm, W - 120 * mm], st, header=True))
    story.append(_p(a.get("disclaimer", ""), st["small"]))

    story.append(Spacer(1, 8))
    story.append(_p(T("Generated from the stored analysis JSON. Similarity scores are ranking aids, not probabilities of "
                      "mineral occurrence; spectral indicators are screening results, not mineral identifications."),
                    st["small"]))
    pdf.build(story)
    return buf.getvalue()
