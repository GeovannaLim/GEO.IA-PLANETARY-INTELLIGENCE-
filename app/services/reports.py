"""PDF rendering of a stored AnalysisResult (ReportLab).

Layout and palette adapted from the legacy ``report_engine.py``. Every number
in the PDF is read from the stored JSON; absent values print as "—" with the
section's status and reason. No narrative text is generated about the data.
"""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor("#1B1B1D")
FOREST = colors.HexColor("#4C7C59")
PAPER = colors.HexColor("#DFDBD8")
MUTE = colors.HexColor("#6b6b6b")
PLANET_NAME = {"earth": "Terra / Earth", "moon": "Lua / Moon", "mars": "Marte / Mars"}


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Title"], textColor=INK, fontSize=18, leading=22, spaceAfter=2),
        "eyebrow": ParagraphStyle("eb", parent=ss["Normal"], textColor=FOREST, fontSize=8, leading=10,
                                  spaceAfter=8, fontName="Helvetica-Bold"),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], textColor=INK, fontSize=11, leading=14,
                             spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("b", parent=ss["Normal"], textColor=INK, fontSize=8.5, leading=11.5),
        "small": ParagraphStyle("s", parent=ss["Normal"], textColor=MUTE, fontSize=7.2, leading=9.5),
    }


def _fmt(v, nd=3) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


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


def render_pdf(doc: dict) -> bytes:
    st = _styles()
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"GEØ.IA report {doc.get('analysis_id')}")
    W = A4[0] - 32 * mm
    c = doc.get("coordinates", {})
    story = [
        Paragraph("GEØ.IA PLANETARY INTELLIGENCE — RELATÓRIO DE ANÁLISE", st["eyebrow"]),
        _p(f"{PLANET_NAME.get(doc.get('planet'), doc.get('planet'))} — "
           f"{_fmt(c.get('latitude'), 4)}°, {_fmt(c.get('longitude'), 4)}° (r = {_fmt(c.get('radius_km'), 2)} km)",
           st["h1"]),
        _p(f"Analysis {doc.get('analysis_id')} · status {doc.get('status')} · completed {doc.get('completed_at')} · "
           f"schema {doc.get('schema_version')}", st["small"]),
        _p(f"Frame: {c.get('reference_frame')}; latitude {c.get('latitude_type')}; longitude east-positive "
           f"(east_360 = {_fmt(c.get('longitude_east_360'), 4)}°).", st["small"]),
        Spacer(1, 4),
    ]

    story.append(_p("Section status", st["h2"]))
    story.append(_table([["Section", "Status"]] + [
        [name, _status(doc.get(key) or {})] for name, key in
        (("Imagery (WMTS)", "imagery"), ("Topography", "topography"), ("Mineralogy / spectroscopy", "mineralogy"),
         ("Terrestrial analog sites", "terrestrial_analogs"),
         ("Spectral comparison (appendix)", "earth_analogs"))], [60 * mm, W - 60 * mm], st, header=True))

    t = doc.get("topography", {})
    story.append(_p("Topography", st["h2"]))
    e, ls = t.get("elevation_m") or {}, t.get("local_slope_degrees") or {}
    story.append(_table([
        ["Method", _fmt(t.get("method"))], ["Datum", _fmt(t.get("datum"))],
        ["Valid shots / samples", _fmt(t.get("n_points"))], ["Sampled radius (km)", _fmt(t.get("sampled_radius_km"), 2)],
        ["Elevation mean / median (m)", f"{_fmt(e.get('mean'), 1)} / {_fmt(e.get('median'), 1)}"],
        ["Elevation p05 – p95 (m)", f"{_fmt(e.get('p05'), 1)} – {_fmt(e.get('p95'), 1)}"],
        ["Relief p95-p05 (m)", _fmt(t.get("relief_m"), 1)],
        ["Regional slope / aspect (°)", f"{_fmt(t.get('regional_slope_degrees'), 2)} / {_fmt(t.get('regional_aspect_degrees'), 0)}"],
        ["Local slope median / p95 (°)", f"{_fmt(ls.get('median'), 2)} / {_fmt(ls.get('p95'), 2)} "
                                        f"(baseline {_fmt(t.get('slope_baseline_m'), 0)} m)"],
        ["Roughness RMS (m)", _fmt(t.get("roughness_m"), 1)], ["Cell coverage", _fmt(t.get("coverage_fraction"), 2)],
    ], [60 * mm, W - 60 * mm], st))

    m = doc.get("mineralogy", {})
    story.append(_p("Mineralogy / spectroscopy", st["h2"]))
    story.append(_table([
        ["Instrument", _fmt(m.get("instrument"))], ["Product used", _fmt(m.get("product_used"))],
        ["Products found / containing point", f"{_fmt(m.get('products_found'))} / {_fmt(m.get('products_containing_point'))}"],
        ["Valid pixels / window", f"{_fmt(m.get('valid_pixels'))} / {_fmt(m.get('window_pixels'))}"],
        ["Spectral character", _fmt(m.get("spectral_character"))],
    ], [60 * mm, W - 60 * mm], st))
    inds = m.get("indicators") or []
    if inds:
        rows = [["Indicator", "Median", "p95", "Pixels", "Sensitive to", "Result"]]
        for i in inds:
            v = i.get("value") or {}
            rows.append([i["name"], _fmt(v.get("median"), 4), _fmt(v.get("p95"), 4), _fmt(i.get("n_pixels")),
                         _fmt(i.get("sensitive_to")), _fmt(i.get("interpretation"))])
        story.append(Spacer(1, 3))
        story.append(_table(rows, [24 * mm, 16 * mm, 16 * mm, 13 * mm, 45 * mm, W - 114 * mm], st, header=True))

    ta = doc.get("terrestrial_analogs") or {}
    if ta:
        story.append(_p("Terrestrial analog sites (documented geology)", st["h2"]))
        ev = "; ".join(e.get("label", "") for e in ta.get("region_evidence") or []) or "—"
        story.append(_p(f"Status: {_status(ta)}. Basis: {ta.get('basis') or '—'}. Region evidence: {ev}.", st["body"]))
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
                    story.append(_p(f"{label}: " + " ".join(s[key]), st["small"]))
            if refs:
                story.append(_p(f"References: {refs}", st["small"]))
        if ta.get("disclaimer"):
            story.append(_p(ta["disclaimer"], st["small"]))

    conf = doc.get("confidence", {})
    story.append(_p(f"Confidence: {conf.get('level')}", st["h2"]))
    if conf.get("criteria"):
        story.append(_table([["Criterion", "Met", "Detail"]] + [
            [x["criterion"], "yes" if x["met"] else "no", x["detail"]] for x in conf["criteria"]],
            [60 * mm, 12 * mm, W - 72 * mm], st, header=True))
    for lim in conf.get("limitations") or []:
        story.append(_p(f"• {lim}", st["small"]))

    story.append(_p("Data sources and provenance", st["h2"]))
    rows = [["ID", "Provider / service", "Instrument / product", "Observation", "Status / note"]]
    for s in doc.get("data_sources") or []:
        rows.append([s["source_id"], f"{s['provider']} — {s['service']}",
                     f"{s.get('instrument') or '—'} {s.get('product_type') or ''} {s.get('product_id') or ''}",
                     f"{s.get('observation_start') or '—'} → {s.get('observation_end') or '—'}",
                     f"{s.get('status')}: {s.get('message') or ''}"[:400]])
    story.append(_table(rows, [13 * mm, 42 * mm, 45 * mm, 34 * mm, W - 134 * mm], st, header=True))

    if doc.get("problems"):
        story.append(_p("Problems reported", st["h2"]))
        for pb in doc["problems"]:
            story.append(_p(f"• [{pb['section']}/{pb['reason']}] {pb['message']}", st["small"]))

    # The 2-attribute spectral ranking does not discriminate sites (docs/CIENCIA.md); it is kept for
    # transparency as an appendix, after the documented terrestrial analog sites.
    a = doc.get("earth_analogs", {})
    story.append(_p("Appendix — illustrative spectral comparison (2 band-depth attributes)", st["h2"]))
    story.append(_p("Not an analog result: two band depths do not discriminate between library sites, and the "
                    "library mixes deposit types. The terrestrial analog sites above are the analog result.",
                    st["small"]))
    story.append(_p(f"Status: {_status(a)}. Directly comparable: {', '.join(a.get('directly_comparable') or []) or '—'}. "
                    f"Missing: {', '.join(a.get('missing') or []) or '—'}.", st["body"]))
    if a.get("matches"):
        rows = [["Library site", "Distance", "Similarity (ranking aid)"]]
        rows += [[x["name"], _fmt(x["distance"], 4), _fmt(x["similarity"], 3)] for x in a["matches"]]
        story.append(_table(rows, [90 * mm, 30 * mm, W - 120 * mm], st, header=True))
    story.append(_p(a.get("disclaimer", ""), st["small"]))

    story.append(Spacer(1, 8))
    story.append(_p("Generated from the stored analysis JSON. Similarity scores are ranking aids, not probabilities of "
                    "mineral occurrence; spectral indicators are screening results, not mineral identifications.",
                    st["small"]))
    pdf.build(story)
    return buf.getvalue()
