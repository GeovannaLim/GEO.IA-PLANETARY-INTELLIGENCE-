"""Response localisation (English canonical -> Brazilian Portuguese).

Results are computed, cached and stored in English (the canonical form used by
tests, provenance and the PDF). ``localize(doc, "pt-BR")`` returns a translated
copy for display. Only human-readable prose is translated; numbers, units,
instrument and product names, parameter codes (IBD1000, BD2210_2...), URLs,
identifiers and provenance records are never touched.

Translation is a list of substring substitutions applied in order (longest and
most specific first), so composed sentences ("A. B. C.") translate piecewise.
Anything without a rule stays in English (e.g. raw provider error text).
"""

from __future__ import annotations

import copy
import re
from typing import Any, Callable

SUPPORTED = ("en", "pt-BR")
DEFAULT = "en"

_BASIS_EN = ("statistical screening: window mean > 3 x standard error (effective n = pixels/25 for spatial "
             "correlation), median > 0 and >= 60% of pixels positive. Detects a positive band depth; not a "
             "mineral abundance or identification")
_BASIS_PT = ("triagem estatística: média da janela > 3 × erro-padrão (n efetivo = pixels/25 pela correlação "
             "espacial), mediana > 0 e ≥ 60% dos pixels positivos. Detecta uma profundidade de banda positiva; "
             "não é abundância nem identificação mineral")

# What each spectral parameter is sensitive to (CRISM summary parameters, M3 and legacy indices).
SENSITIVE_TO = {
    "olivine (broad 1 µm band)": "olivina (banda larga em 1 µm)",
    "low-Ca pyroxene": "piroxênio de baixo Ca",
    "high-Ca pyroxene": "piroxênio de alto Ca",
    "Fe2+ 1 µm absorption (mafic minerals)": "absorção de Fe²⁺ em 1 µm (minerais máficos)",
    "H2O in hydrated minerals": "H₂O em minerais hidratados",
    "Fe/Mg-OH (Fe/Mg phyllosilicates)": "Fe/Mg-OH (filossilicatos de Fe/Mg)",
    "Al-OH (Al phyllosilicates, hydrated silica)": "Al-OH (filossilicatos de Al, sílica hidratada)",
    "Mg/Fe-OH; CO2 ice": "Mg/Fe-OH; gelo de CO₂",
    "Mg carbonate": "carbonato de Mg",
    "Fe/Ca carbonate": "carbonato de Fe/Ca",
    "monohydrated sulfates": "sulfatos mono-hidratados",
    "polyhydrated sulfates (convexity at 2.29 µm)": "sulfatos poli-hidratados (convexidade em 2,29 µm)",
    "crystalline ferric oxides": "óxidos férricos cristalinos",
    "CO2 ice": "gelo de CO₂",
    "H2O ice": "gelo de H₂O",
    "albedo at 770 nm (descriptive)": "albedo em 770 nm (descritivo)",
    "Fe2+ crystal-field absorptions near 1 µm (pyroxene, olivine, Fe-bearing glass)":
        "absorções de campo cristalino do Fe²⁺ perto de 1 µm (piroxênio, olivina, vidro com Fe)",
    "Fe2+ absorption near 2 µm (pyroxene; absent in olivine)":
        "absorção de Fe²⁺ perto de 2 µm (piroxênio; ausente na olivina)",
    "1 µm Fe2+ absorption (coarse, 3-band)": "absorção de Fe²⁺ em 1 µm (grosseira, 3 bandas)",
    "2 µm Fe2+ absorption (coarse, 3-band)": "absorção de Fe²⁺ em 2 µm (grosseira, 3 bandas)",
    "Fe2+ absorption (coarse)": "absorção de Fe²⁺ (grosseira)",
    "albedo; space-weathering maturity": "albedo; maturidade por intemperismo espacial",
    "space weathering / maturity": "intemperismo espacial / maturidade",
}

_Rule = tuple[re.Pattern, str | Callable[[re.Match], str]]


def _lit(en: str, pt: str) -> _Rule:
    return re.compile(re.escape(en)), pt


def _sens(m: re.Match) -> str:
    return SENSITIVE_TO.get(m.group(1), m.group(1))


RULES: list[_Rule] = [
    # ---- detection basis and interpretations --------------------------------------------------
    _lit(_BASIS_EN, _BASIS_PT),
    (re.compile(r"Positive parameter value detected \((.+?)\)\. Sensitive to (.+?); confirmation requires "
                r"ratioed-spectrum analysis\."),
     lambda m: (f"Valor positivo do parâmetro detectado ({m.group(1)}). Sensível a "
                f"{SENSITIVE_TO.get(m.group(2), m.group(2))}; a confirmação exige análise de espectros em razão.")),
    (re.compile(r"Positive absorption detected \((.+?)\)\."), r"Absorção positiva detectada (\1)."),
    _lit("Positive absorption detected.", "Absorção positiva detectada."),
    _lit("No statistically significant absorption in the window.",
         "Nenhuma absorção estatisticamente significativa na janela."),
    _lit("No statistically significant absorption.", "Nenhuma absorção estatisticamente significativa."),
    _lit("No statistically significant positive value in the window.",
         "Nenhum valor positivo estatisticamente significativo na janela."),
    _lit("Descriptive I/F value; no detection test applies.", "Valor descritivo de I/F; não há teste de detecção."),
    _lit("Descriptive value; no detection test applies.", "Valor descritivo; não há teste de detecção."),
    _lit("Median depth is negative (convex continuum): no absorption at this wavelength. "
         "The analog comparison uses 0, as in the reference library.",
         "Profundidade mediana negativa (contínuo convexo): sem absorção neste comprimento de onda. "
         "A comparação com análogos usa 0, como na biblioteca de referência."),
    _lit("ROI-mean value is negative (convex continuum): no absorption at this wavelength. "
         "The analog comparison uses 0, as in the reference library.",
         "Média da região negativa (contínuo convexo): sem absorção neste comprimento de onda. "
         "A comparação com análogos usa 0, como na biblioteca de referência."),
    _lit("ROI-mean value; per-pixel distribution not retrieved",
         "Valor médio da região; distribuição por pixel não obtida"),
    # ---- spectral character ---------------------------------------------------------------
    _lit("1 µm and 2 µm absorptions both detected: consistent with pyroxene-bearing material "
         "(e.g. mare basalt or noritic material). Not a mineral identification.",
         "Absorções em 1 µm e 2 µm detectadas: compatível com material contendo piroxênio "
         "(p. ex. basalto de mare ou material norítico). Não é identificação mineral."),
    _lit("1 µm absorption without a significant 2 µm band: consistent with olivine-, glass- or "
         "Fe-bearing plagioclase-rich material; ambiguous without band-centre analysis.",
         "Absorção em 1 µm sem banda significativa em 2 µm: compatível com material rico em olivina, vidro "
         "ou plagioclásio com Fe; ambíguo sem análise do centro de banda."),
    _lit("Only the 2 µm region shows a positive depth: atypical; possibly thermal-correction residual.",
         "Só a região de 2 µm mostra profundidade positiva: atípico; possivelmente resíduo da correção térmica."),
    _lit("No significant 1/2 µm absorption: consistent with mature, space-weathered or feldspathic "
         "surface; ambiguous.",
         "Sem absorção significativa em 1/2 µm: compatível com superfície madura, intemperizada pelo espaço "
         "ou feldspática; ambíguo."),
    _lit("No summary parameter shows a statistically significant positive value in the window.",
         "Nenhum parâmetro-sumário mostra valor positivo estatisticamente significativo na janela."),
    (re.compile(r"Positive summary parameters: (.+?)\. Screening only; mineral identification requires ratioed "
                r"spectra\."),
     lambda m: ("Parâmetros-sumário positivos: "
                + re.sub(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", lambda n: f"({SENSITIVE_TO.get(n.group(1), n.group(1))})",
                         m.group(1))
                + ". Apenas triagem; a identificação mineral exige espectros em razão.")),
    # ---- analog section ---------------------------------------------------------------------
    _lit("Similarity of a few band-depth attributes. It is not a probability of mineral occurrence and does "
         "not indicate a deposit.",
         "Similaridade de poucos atributos de profundidade de banda. Não é probabilidade de ocorrência mineral "
         "e não indica jazida."),
    (re.compile(r"Low discrimination: the top (\d+) sites lie within ([\d.]+) band-depth units of each other\."),
     lambda m: (f"Baixa discriminação: os {m.group(1)} primeiros sítios ficam a menos de "
                f"{m.group(2).replace('.', ',')} unidades de profundidade de banda entre si.")),
    _lit("Only two attributes are compared; many geologically unrelated sites can match equally well "
         "(the library is dominated by hydrothermal ore systems).",
         "Só dois atributos são comparados; muitos sítios sem relação geológica podem coincidir igualmente "
         "(a biblioteca é dominada por sistemas minerais hidrotermais)."),
    (re.compile(r"(\d+) of the (\d+) library sites are within the measurement uncertainty of the best match "
                r"and cannot be distinguished from it\."),
     r"\1 dos \2 sítios da biblioteca estão dentro da incerteza de medida do melhor resultado e não podem "
     r"ser distinguidos dele."),
    _lit("Many library sites have a negative 1 µm and a large 2 µm depth, a pattern typical of vegetation and "
         "soil moisture rather than Fe2+ in mafic minerals; low-depth (arid, sparsely vegetated) sites therefore "
         "dominate the matches for the Moon and Mars.",
         "Muitos sítios da biblioteca têm profundidade negativa em 1 µm e grande em 2 µm, padrão típico de "
         "vegetação e umidade do solo, e não de Fe²⁺ em minerais máficos; por isso sítios de baixa "
         "profundidade (áridos, pouco vegetados) dominam os resultados para a Lua e Marte."),
    _lit("Low discrimination: the order of the top matches is not meaningful.",
         "Discriminação baixa: a ordem dos primeiros resultados não é significativa."),
    _lit("Moderate discrimination: the first matches are only partly separated.",
         "Discriminação moderada: os primeiros resultados estão só parcialmente separados."),
    _lit("Adequate discrimination for a two-attribute comparison.",
         "Discriminação adequada para uma comparação de dois atributos."),
    _lit("Euclidean distance over directly comparable band depths (legacy definition)",
         "Distância euclidiana sobre profundidades de banda diretamente comparáveis (definição legada)"),
    _lit("IBD1000 (vs EMIT 1 µm depth: same absorption, different integration)",
         "IBD1000 (vs. profundidade EMIT em 1 µm: mesma absorção, integração diferente)"),
    _lit("IBD2000 (vs EMIT 2 µm depth: same absorption, different integration)",
         "IBD2000 (vs. profundidade EMIT em 2 µm: mesma absorção, integração diferente)"),
    _lit("BDI1000IR / LCPINDEX2 / HCPINDEX2 (Fe2+ absorptions; CRISM-specific definitions)",
         "BDI1000IR / LCPINDEX2 / HCPINDEX2 (absorções de Fe²⁺; definições próprias do CRISM)"),
    _lit("R750 / slope_750_1550 (lunar space weathering has no terrestrial analogue)",
         "R750 / slope_750_1550 (o intemperismo espacial lunar não tem análogo terrestre)"),
    _lit("ASTER TIR silica/mafic indices (thermal infrared, not measured on the Moon here)",
         "índices ASTER TIR de sílica/máficos (infravermelho térmico, não medido na Lua aqui)"),
    _lit("Sentinel-2 ferric ratio, NDVI (aqueous alteration / vegetation; absent on the Moon)",
         "razão férrica Sentinel-2, NDVI (alteração aquosa / vegetação; ausentes na Lua)"),
    _lit("Sentinel-2 ferric ratio, NDVI and ASTER TIR indices (reported as Earth context only)",
         "razão férrica Sentinel-2, NDVI e índices ASTER TIR (apenas contexto terrestre)"),
    _lit("BD1900_2, D2300, BD2210_2, carbonate and sulfate parameters (no equivalent attribute in the "
         "terrestrial reference library)",
         "BD1900_2, D2300, BD2210_2, parâmetros de carbonatos e sulfatos (sem atributo equivalente na "
         "biblioteca terrestre)"),
    _lit("CO2/H2O ice parameters (no terrestrial counterpart in the library)",
         "parâmetros de gelo de CO₂/H₂O (sem correspondente terrestre na biblioteca)"),
    _lit("ASTER TIR indices, NDVI (not measured on Mars here)", "índices ASTER TIR, NDVI (não medidos em Marte aqui)"),
    # ---- methods and datums -------------------------------------------------------------------
    (re.compile(r"\b(LOLA|MOLA) laser altimeter shots via ODE GDS"), r"disparos do altímetro laser \1 via ODE GDS"),
    (re.compile(r"\b(LOLA|MOLA) shots\b"), r"disparos \1"),
    _lit("radius minus 1737.4 km reference sphere (LOLA RDR topography)",
         "raio menos esfera de referência de 1737,4 km (topografia LOLA RDR)"),
    _lit("radius minus MOLA areoid (PEDR topography)", "raio menos areoide MOLA (topografia PEDR)"),
    _lit("Copernicus GLO-30 DEM statistics (Earth Engine)", "estatísticas do MDE Copernicus GLO-30 (Earth Engine)"),
    _lit("EGM2008 geoid", "geoide EGM2008"),
    _lit("M3 L2 reflectance window; band depths over valid pixels (see indicator definitions)",
         "janela de reflectância M3 L2; profundidades de banda sobre pixels válidos (ver definições dos indicadores)"),
    _lit("CRISM MTRDR summary parameters (CRISM team) over a pixel window",
         "parâmetros-sumário CRISM MTRDR (equipe CRISM) sobre uma janela de pixels"),
    _lit("EMIT L2A surface reflectance band depths", "profundidades de banda da reflectância de superfície EMIT L2A"),
    # ---- limitations -------------------------------------------------------------------------
    _lit("M3 L2 reflectance includes an empirical thermal correction; residual thermal emission can affect the "
         "2 µm region on warm, low-latitude terrain.",
         "A reflectância M3 L2 inclui correção térmica empírica; emissão térmica residual pode afetar a região "
         "de 2 µm em terrenos quentes de baixa latitude."),
    _lit("M3 global-mode spatial sampling is ~140 m/pixel (100 km orbit) or ~280 m/pixel (200 km orbit).",
         "A amostragem espacial do M3 no modo global é ~140 m/pixel (órbita de 100 km) ou ~280 m/pixel "
         "(órbita de 200 km)."),
    _lit("L2 photometric correction uses a lunar topography model; steep slopes and high incidence angles "
         "degrade the correction.",
         "A correção fotométrica L2 usa um modelo de topografia lunar; encostas íngremes e ângulos de incidência "
         "altos degradam a correção."),
    _lit("Pixels within the window are spatially correlated, so the detection test is optimistic.",
         "Os pixels da janela são espacialmente correlacionados, então o teste de detecção é otimista."),
    _lit("MTRDR summary parameters are screening products; positive values can arise from noise, residual "
         "atmospheric CO2 or detector artefacts (Viviano-Beck et al. 2014).",
         "Os parâmetros-sumário MTRDR são produtos de triagem; valores positivos podem vir de ruído, CO₂ "
         "atmosférico residual ou artefatos do detector (Viviano-Beck et al. 2014)."),
    _lit("CRISM targeted footprints are ~10 km wide; the analysis window covers only the part of the region "
         "imaged by the selected observation.",
         "As observações direcionadas do CRISM têm ~10 km de largura; a janela de análise cobre só a parte da "
         "região imageada pela observação escolhida."),
    _lit("MTRDR I/F includes CRISM team photometric and volcano-scan atmospheric corrections; legacy band "
         "depths therefore differ in calibration from the terrestrial EMIT surface reflectance.",
         "O I/F MTRDR inclui correções fotométrica e atmosférica (volcano-scan) da equipe CRISM; por isso as "
         "profundidades legadas diferem em calibração da reflectância de superfície EMIT terrestre."),
    _lit("CRISM I/F and terrestrial EMIT reflectance differ in atmospheric/photometric correction; band-depth "
         "comparison is a shape comparison, not a compositional match.",
         "O I/F do CRISM e a reflectância EMIT terrestre diferem na correção atmosférica/fotométrica; a "
         "comparação de profundidades de banda compara forma, não composição."),
    (re.compile(r"(LOLA|MOLA) shot spacing leaves gaps between ground tracks"),
     r"o espaçamento dos disparos \1 deixa lacunas entre as trilhas"),
    (re.compile(r"only (\d+) valid altimeter shots inside the sampled circle \(minimum (\d+) for slope metrics\)"),
     r"apenas \1 disparos válidos do altímetro no círculo amostrado (mínimo de \2 para métricas de declividade)"),
    (re.compile(r"altimetry sampled within ([\d.]+) km of the centre \(requested ([\d.]+) km\) to respect GDS "
                r"query-size limits"),
     r"altimetria amostrada a até \1 km do centro (pedido: \2 km) para respeitar o limite de consulta do GDS"),
    (re.compile(r"sparse shot coverage \((\d+)% of (\d+) m cells\); local slopes describe track-adjacent terrain only"),
     r"cobertura esparsa de disparos (\1% das células de \2 m); declividades locais descrevem só o terreno junto "
     r"às trilhas"),
    _lit("too few adjacent grid cells for a robust local-slope distribution",
         "poucas células vizinhas para uma distribuição robusta de declividade local"),
    (re.compile(r"high solar incidence at the pixel \((\d+)°\)"), r"incidência solar alta no pixel (\1°)"),
    (re.compile(r"high solar incidence \((\d+)°\)"), r"incidência solar alta (\1°)"),
    _lit("EMIT coverage is limited to arid regions within ±52° latitude",
         "a cobertura do EMIT se limita a regiões áridas entre ±52° de latitude"),
    _lit("WMTS tiles are rendered imagery for visualisation; not physical values",
         "os tiles WMTS são imagens renderizadas para visualização; não são valores físicos"),
    _lit("Visual layer only; pixel values are not physical measurements.",
         "Camada apenas visual; os valores dos pixels não são medidas físicas."),
    _lit("discovery only; products are not downloaded", "apenas descoberta; os produtos não são baixados"),
    _lit("listed for follow-up analysis; not read by the MVP pipeline",
         "listado para análise posterior; não é lido pelo pipeline atual"),
    _lit("Earth Engine credentials not configured on this host",
         "credenciais do Earth Engine não configuradas neste servidor"),
    _lit("Earth-only context indices; not compared with lunar or Martian data.",
         "Índices de contexto apenas terrestres; não comparados com dados lunares ou marcianos."),
    # ---- problems / coverage messages ------------------------------------------------------
    _lit("no M3 L2 observation intersects the point", "nenhuma observação M3 L2 cobre o ponto"),
    _lit("M3 footprints intersect the search box but none contains the point",
         "há observações M3 na área de busca, mas nenhuma contém o ponto"),
    (re.compile(r"(\d+) valid M3 pixels in the window of (\S+)"), r"\1 pixels M3 válidos na janela de \2"),
    (re.compile(r"(\d+) valid CRISM pixels"), r"\1 pixels CRISM válidos"),
    _lit("no CRISM targeted observation covers the point", "nenhuma observação direcionada do CRISM cobre o ponto"),
    _lit("MTRDR footprints intersect the box but none contains the point",
         "há observações MTRDR na área de busca, mas nenhuma contém o ponto"),
    (re.compile(r"No map-projected CRISM MTRDR covers the point, but (\d+) unprojected targeted TRDR observation\(s\) "
                r"exist; processing TRDRs \(geometry \+ atmospheric correction\) is outside the MVP\."),
     r"Nenhum MTRDR do CRISM projetado cobre o ponto, mas existem \1 observações TRDR não projetadas; "
     r"processar TRDRs (geometria + correção atmosférica) está fora do escopo atual."),
    _lit("no valid altimeter shots in the region", "nenhum disparo válido do altímetro na região"),
    # ---- confidence ------------------------------------------------------------------------
    _lit("Rule-based; see docs/CIENCIA.md#confiança", "Baseada em regras; ver docs/CIENCIA.md#confiança"),
    _lit("Rule-based; see docs/SCIENCE.md#confidence", "Baseada em regras; ver docs/CIENCIA.md#confiança"),
    _lit("Earth analogs use only band depths with identical definitions; Moon and Earth surfaces differ "
         "(space weathering, no water or vegetation, regolith grain size).",
         "Os análogos terrestres usam só profundidades de banda com definição idêntica; as superfícies da Lua "
         "e da Terra diferem (intemperismo espacial, ausência de água e vegetação, granulometria do regolito)."),
    (re.compile(r"^(\d+|None) valid shots in the sampled circle$"), r"\1 disparos válidos no círculo amostrado"),
    (re.compile(r"^coverage (.+)$"), r"cobertura \1"),
    (re.compile(r"^sampled radius (.+) km$"), r"raio amostrado \1 km"),
    (re.compile(r"^nearest pixel (.+) m from target$"), r"pixel mais próximo a \1 m do alvo"),
    (re.compile(r"^(\d+|None) valid pixels$"), r"\1 pixels válidos"),
    (re.compile(r"^incidence (.+)°$"), r"incidência \1°"),
]

# Paths (dot notation, [] = every list item) whose string values are prose to translate.
PATHS = (
    "imagery.layers[].note", "imagery.limitations[]",
    "topography.method", "topography.datum", "topography.limitations[]",
    "mineralogy.method", "mineralogy.spectral_character", "mineralogy.limitations[]",
    "mineralogy.indicators[].interpretation", "mineralogy.indicators[].sensitive_to",
    "mineralogy.indicators[].threshold_basis",
    "earth_analogs.method", "earth_analogs.disclaimer", "earth_analogs.discrimination_note",
    "earth_analogs.approximate_proxies[]", "earth_analogs.not_comparable[]",
    "confidence.basis", "confidence.limitations[]", "confidence.criteria[].detail",
    "problems[].message", "earth_observation.note",
)


def translate(text: str, lang: str = "pt-BR") -> str:
    if lang != "pt-BR" or not isinstance(text, str):
        return text
    exact = SENSITIVE_TO.get(text)
    if exact:
        return exact
    for pattern, repl in RULES:
        text = pattern.sub(repl, text)
    return text


def _walk(node: Any, parts: list[str], lang: str) -> None:
    if not parts or node is None:
        return
    key, rest = parts[0], parts[1:]
    is_list = key.endswith("[]")
    key = key[:-2] if is_list else key
    if not isinstance(node, dict) or key not in node:
        return
    val = node[key]
    if is_list:
        if not isinstance(val, list):
            return
        for i, item in enumerate(val):
            if rest:
                _walk(item, rest, lang)
            elif isinstance(item, str):
                val[i] = translate(item, lang)
    elif rest:
        _walk(val, rest, lang)
    elif isinstance(val, str):
        node[key] = translate(val, lang)


def localize(doc: dict, lang: str | None) -> dict:
    """Return a translated deep copy of an analysis document (``doc`` is left untouched)."""
    lang = lang or DEFAULT
    if lang == DEFAULT:
        return doc
    out = copy.deepcopy(doc)
    links = out.get("links") or {}
    for k in ("self", "report"):          # keep the language while the client polls / fetches JSON
        if isinstance(links.get(k), str) and "lang=" not in links[k]:
            links[k] += ("&" if "?" in links[k] else "?") + f"lang={lang}"
    out["language"] = lang
    if out.get("status") != "processing":
        for path in PATHS:
            _walk(out, path.split("."), lang)
    return out
