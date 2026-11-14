"""Build the judge-facing PDF of the submission package (ReportLab, no new dependency).

Source: docs/submission/DOCUMENTATION.md, the consolidated 7-section edition of PROJECT_PAGE, SCIENTIFIC_DOCUMENTATION,
VALIDATION_AND_TESTS and REFERENCES (same facts, repetitions removed). The 32 analog-catalog references are copied
from REFERENCES.md at build time (placeholder @@CATALOG_REFS@@); a line ":::small" switches to compact text.

    .venv/bin/python scripts/build_submission_pdf.py
Writes docs/submission/GEOIA_NASA_Space_Apps_2026_Documentation.pdf.
Team-only material (placeholders, the pre-submission checklist, internal notes) is left out of the PDF; the
markdown files keep it. Supports the markdown used in these files: headings, paragraphs, nested lists, pipe
tables, fenced code, block quotes, rules, **bold**, *italic*, `code` and links.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

SRC = Path("docs/submission")
OUT = SRC / "GEOIA_NASA_Space_Apps_2026_Documentation.pdf"
DOCS = ["DOCUMENTATION.md"]
TITLES = {"PROJECT_PAGE.md": "1. Project overview", "SCIENTIFIC_DOCUMENTATION.md": "2. Scientific documentation",
          "VALIDATION_AND_TESTS.md": "3. Validation and tests", "REFERENCES.md": "4. Data, resources and references"}
FONTS = "/System/Library/Fonts/Supplemental/"

pdfmetrics.registerFont(TTFont("Uni", FONTS + "Arial Unicode.ttf"))
pdfmetrics.registerFont(TTFont("UniB", FONTS + "Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("UniI", FONTS + "Arial Italic.ttf"))
pdfmetrics.registerFont(TTFont("UniBI", FONTS + "Arial Bold Italic.ttf"))
pdfmetrics.registerFont(TTFont("Mono", "/System/Library/Fonts/Menlo.ttc", subfontIndex=0))
pdfmetrics.registerFontFamily("Uni", normal="Uni", bold="UniB", italic="UniI", boldItalic="UniBI")

INK, MUTED, ACCENT, RULE, SHADE = (colors.HexColor(c) for c in ("#1a1d23", "#5b6170", "#1f4e8c", "#d5d9e0", "#f2f4f7"))
BASE = ParagraphStyle("base", fontName="Uni", fontSize=9.5, leading=12.8, textColor=INK, spaceAfter=4)
ST = {
    "h1": ParagraphStyle("h1", parent=BASE, keepWithNext=1, fontName="UniB", fontSize=18, leading=22, textColor=ACCENT,
                         spaceBefore=4, spaceAfter=10),
    "h2": ParagraphStyle("h2", parent=BASE, keepWithNext=1, fontName="UniB", fontSize=13, leading=16, textColor=ACCENT,
                         spaceBefore=12, spaceAfter=6),
    "h3": ParagraphStyle("h3", parent=BASE, keepWithNext=1, fontName="UniB", fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=4),
    "p": BASE,
    "quote": ParagraphStyle("quote", parent=BASE, textColor=MUTED, leftIndent=10, borderPadding=(4, 4, 4, 8),
                            backColor=SHADE),
    "cell": ParagraphStyle("cell", parent=BASE, fontSize=8, leading=10.4, spaceAfter=0),
    "cellh": ParagraphStyle("cellh", parent=BASE, fontName="UniB", fontSize=8, leading=10.4, spaceAfter=0,
                            textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8, leading=9.2, textColor=INK),
}

# Team-only blocks removed from the judge-facing PDF (kept in the markdown files).
DROP_BLOCKS = [
    r"Before submitting, fill in these placeholders:\n(?:- [^\n]*\n)+",
    r"## Link to Project Demo\n\n.*?(?=\n## )",
    r"> Note: this link qualifies only after.*?\n> link in a private window before submitting\.\n",
    r"---\n\n## Checklist before \"Submit for Judging\".*\Z",
]
REPLACE = [
    ("`[FINAL PROJECT LINK]`: https://geoai-interplanetary.goskip.app.", "https://geoai-interplanetary.goskip.app"),
    (" as the guide requires. See the checklist at the end of this document.", " as the guide requires."),
    ("| Images and textures | 3D globe textures and interface images used by the frontend. **The team must list "
     "their sources and licenses here before submitting**, and watermark any SI-generated image. |\n", ""),
    ("**Images:** 3D globe textures and interface images. Confirm the source and license of each texture and of any\n"
     "generated image before submitting (see the checklist).\n", ""),
]
SUBSUP = {"₁": "<sub>1</sub>", "₂": "<sub>2</sub>", "⁺": "<super>+</super>"}
NEED_UNI = "∇∈"   # glyphs missing in the Arial bold/italic faces


def inline(text: str) -> str:
    text = text.replace("\\|", "\x00")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("&lt;br&gt;", "<br/>")
    text = re.sub(r"`([^`]+)`", lambda m: f'<font name="Mono" size="7.8">{m.group(1)}</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)

    def link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("http"):
            return f'<link href="{url}" color="#1f4e8c">{label}</link>'
        return f"<i>{label}</i>"               # internal .md links: the documents are all in this PDF
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    def bare(m):
        url = m.group(1).rstrip(".,;")
        while url.endswith(")") and url.count(")") > url.count("("):
            url = url[:-1]
        return f'<link href="{url}" color="#1f4e8c">{url}</link>' + m.group(1)[len(url):]
    text = re.sub(r"(?<![\"'>=])(https?://[^\s<]+)", bare, text)
    for k, v in SUBSUP.items():
        text = text.replace(k, v)
    for c in NEED_UNI:
        text = text.replace(c, f'<font name="Uni">{c}</font>')
    return text.replace("\x00", "|")


def table(lines: list[str], width: float):
    rows = [[c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))] for ln in lines]
    rows = [r for i, r in enumerate(rows) if not (i == 1 and all(re.fullmatch(r":?-{3,}:?", c) for c in r))]
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    lens = [max(min(len(r[i]), 90) for r in rows) + 6 for i in range(n)]
    widths = [width * l / sum(lens) for l in lens]
    widths = [max(w, 9 * mm) for w in widths]
    widths = [w * width / sum(widths) for w in widths]
    data = [[Paragraph(inline(c), ST["cellh" if i == 0 else "cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SHADE]), ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return [t, Spacer(1, 6)]


SMALL = ParagraphStyle("small", parent=BASE, fontSize=7.8, leading=10, spaceAfter=2)


def render(md: str, width: float) -> list:
    out, lines, i = [], md.split("\n"), 0
    para: list[str] = []
    base = [BASE]

    def flush():
        if para:
            out.append(Paragraph(inline(" ".join(s.strip() for s in para)), ST["p"] if base[0] is BASE else base[0]))
            para.clear()
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == ":::small":
            flush(); base[0] = SMALL; i += 1; continue
        if ln.startswith("```"):
            flush(); j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out += [Preformatted("\n".join(lines[i + 1:j]), ST["code"]), Spacer(1, 6)]
            i = j + 1; continue
        m = re.match(r"^(#{1,3}) (.*)", ln)
        if m:
            flush()
            if len(m.group(1)) == 1 and out:      # each main section starts on a new page
                while out and isinstance(out[-1], Spacer):
                    out.pop()
                out.append(PageBreak())
            out.append(Paragraph(inline(m.group(2)), ST["h" + str(len(m.group(1)))])); i += 1; continue
        if ln.strip() == "---":
            flush(); out.append(Spacer(1, 4)); i += 1; continue
        if ln.lstrip().startswith("|"):
            flush(); j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            out += table(lines[i:j], width); i = j; continue
        if ln.startswith(">"):
            flush(); j = i; q = []
            while j < len(lines) and lines[j].startswith(">"):
                q.append(lines[j].lstrip(">").strip()); j += 1
            out.append(Paragraph(inline(" ".join(q)), ST["quote"])); out.append(Spacer(1, 4)); i = j; continue
        m = re.match(r"^(\s*)([-*]|\d+\.) (.*)", ln)
        if m:
            flush(); j = i
            while j < len(lines) and (re.match(r"^\s*([-*]|\d+\.) ", lines[j]) or
                                      (lines[j].startswith("  ") and lines[j].strip() and not lines[j].lstrip().startswith("|"))):
                mm_ = re.match(r"^(\s*)([-*]|\d+\.) (.*)", lines[j])
                if mm_:
                    level = len(mm_.group(1)) // 2
                    bullet = mm_.group(2) if mm_.group(2)[0].isdigit() else ("•" if level == 0 else "–")
                    items = [mm_.group(3)]
                    k = j + 1
                    while k < len(lines) and lines[k].startswith("  ") and lines[k].strip() and \
                            not re.match(r"^\s*([-*]|\d+\.) ", lines[k]):
                        items.append(lines[k].strip()); k += 1
                    st = ParagraphStyle("li", parent=base[0], leftIndent=12 + 12 * level, bulletIndent=2 + 12 * level,
                                        spaceAfter=1 if base[0] is SMALL else 2)
                    out.append(Paragraph(inline(" ".join(items)), st, bulletText=bullet))
                    j = k
                else:
                    j += 1
            out.append(Spacer(1, 4)); i = j; continue
        if not ln.strip():
            flush(); i += 1; continue
        para.append(ln); i += 1
    flush()
    return out


def page_deco(canvas, doc):
    canvas.saveState()
    canvas.setFont("Uni", 7.5); canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "GEØ.IA Planetary Intelligence — NASA Space Apps Challenge 2026")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(RULE); canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.restoreState()


def cover(width: float) -> list:
    t = ParagraphStyle("t", parent=BASE, fontName="UniB", fontSize=28, leading=34, textColor=ACCENT, alignment=TA_CENTER)
    s = ParagraphStyle("s", parent=BASE, fontSize=12, leading=17, alignment=TA_CENTER, textColor=MUTED)
    c = ParagraphStyle("c", parent=BASE, fontSize=10, leading=15, alignment=TA_CENTER)
    toc = [["Section", "Content"],
           ["1. Overview, objective and contribution", "Summary, what the platform does, why it matters, next steps"],
           ["2. Architecture, technologies and data sources", "Components, NASA data, partner-agency data"],
           ["3. Methodology: Moon, Mars and analogs", "Topography, M³ and CRISM screening, detection tests, analog matching, EMIT"],
           ["4. Lunar south pole and experimental geomorphology", "Illumination, terrain method, results, controls"],
           ["5. Validation and results", "21 pre-registered scenarios, controls, adversarial tests, releases"],
           ["6. Problems, corrections and limitations", "16 problems found and fixed; known limitations"],
           ["7. References, AI transparency and links", "Use of SI, links, method, validation and catalog references"]]
    return [Spacer(1, 45 * mm), Paragraph("GEØ.IA Planetary Intelligence", t), Spacer(1, 6),
            Paragraph("Earth analog sites for the Moon and Mars, from open NASA data", s), Spacer(1, 14 * mm),
            Paragraph("NASA Space Apps Challenge 2026", c),
            Paragraph("<i>Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</i>", c),
            Spacer(1, 8 * mm),
            Paragraph('Platform: <link href="https://geoai-interplanetary.goskip.app" color="#1f4e8c">'
                      'https://geoai-interplanetary.goskip.app</link>', c),
            Paragraph('Scientific API: <link href="https://geoia-planetary-backend.onrender.com/docs" color="#1f4e8c">'
                      'https://geoia-planetary-backend.onrender.com</link>', c),
            Paragraph(f"Release: backend 8df1d61 · Document generated {date.today().isoformat()}", c),
            Spacer(1, 14 * mm)] + \
        table([f"| {toc[0][0]} | {toc[0][1]} |", "|---|---|"] + [f"| {a} | {b} |" for a, b in toc[1:]], width) + \
        [PageBreak()]


def main() -> None:
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="GEØ.IA Planetary Intelligence — NASA Space Apps 2026",
                            author="GEØ.IA team",
                            subject="Project documentation, scientific methods, validation and references",
                            creator="scripts/build_submission_pdf.py (ReportLab); text drafted with Claude (Anthropic) "
                                    "under the team's direction")
    width = A4[0] - 36 * mm
    story = cover(width)
    for k, name in enumerate(DOCS):
        md = (SRC / name).read_text(encoding="utf-8")
        for pat in DROP_BLOCKS:
            md = re.sub(pat, "", md, flags=re.S)
        for a, b in REPLACE:
            md = md.replace(a, b)
        refs = (SRC / "REFERENCES.md").read_text(encoding="utf-8").split("## Terrestrial analog catalog references")[1]
        md = md.replace("@@CATALOG_REFS@@", "\n".join(l for l in refs.splitlines() if l.startswith("- ")))
        story += render(md, width)
        if k < len(DOCS) - 1:
            story.append(PageBreak())
    while story and isinstance(story[-1], Spacer):
        story.pop()
    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=page_deco)
    print(OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
