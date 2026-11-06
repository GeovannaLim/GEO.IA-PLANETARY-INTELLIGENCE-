"""Curated Mars analog sites (source data for app/data/terrestrial_analog_sites.json).

Every coordinate comes from the cited coordinate_source; every DOI was resolved on Crossref or
DataCite on 2026-11-06. Texts summarise the cited references; nothing is extrapolated.
"""

BASALT_NOTE_EN = ("Basalt (pyroxene + plagioclase by definition); the opened sources do not document the "
                  "pyroxene composition.")
BASALT_NOTE_PT = ("Basalto (piroxênio + plagioclásio por definição); as fontes consultadas não documentam a "
                  "composição do piroxênio.")

SITES = [
    dict(id="samail_bt1b", name="Samail Ophiolite — Wadi Mansah listvenite (OmanDP Hole BT1B)", country="Oman",
         lat=23.364496, lon=58.182396, coordinate_precision_km=0.5,
         coordinate_source="PANGAEA dataset doi:10.1594/PANGAEA.915753 (Oman Drilling Project Hole BT1B collar)",
         verification="verified", measurement_radius_km=2,
         setting_en="Mantle peridotite of the Samail ophiolite altered to serpentinite and listvenite "
                    "(magnesite, dolomite).",
         setting_pt="Peridotito do manto do ofiolito de Samail alterado para serpentinito e listvenito "
                    "(magnesita, dolomita).",
         key_minerals=["serpentine", "magnesite", "dolomite", "olivine (relict)", "spinel"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["carbonate", "fe_mg_phyllosilicate", "olivine_rich"],
                          reference_ids=["leask2021", "lafay2020"],
                          rationale_en="Leask et al. (2021) treat the Samail ophiolite as a Mars analog system: "
                                       "ultramafic rocks with serpentine and Mg-carbonate alteration exposed in a "
                                       "semi-arid setting, the assemblage seen from orbit at Nili Fossae and Jezero.",
                          rationale_pt="Leask et al. (2021) tratam o ofiolito de Samail como sistema análogo de "
                                       "Marte: rochas ultramáficas com alteração para serpentina e carbonato de Mg "
                                       "expostas em clima semiárido, o conjunto visto da órbita em Nili Fossae e "
                                       "Jezero.")],
         similarities_en=["Olivine → serpentine → Mg-carbonate alteration sequence documented on both bodies."],
         similarities_pt=["Sequência de alteração olivina → serpentina → carbonato de Mg documentada nos dois "
                          "corpos."],
         differences_en=["Leask et al. found carbonate and serpentine in mixtures separable only at cm-scale "
                         "pixels; Fe2+ in magnesite can mimic the 1 µm olivine band."],
         differences_pt=["Leask et al. só separaram carbonato e serpentina em mistura com pixels de escala "
                         "centimétrica; Fe2+ na magnesita pode imitar a banda de olivina em 1 µm."],
         limitations_en=["Point is a borehole collar; listvenite outcrops are hundreds of metres across "
                         "(a few 60 m pixels). Wadi gravels and travertine nearby."],
         limitations_pt=["O ponto é a boca de um furo de sondagem; os afloramentos de listvenito têm centenas de "
                         "metros (poucos pixels de 60 m). Cascalho de wadi e travertino por perto."],
         references=[dict(id="leask2021", doi="10.1029/2021EA001637",
                          citation="Leask E.K. et al. (2021) Tracing carbonate formation, serpentinization, and "
                                   "biological materials with micro-/meso-scale infrared imaging spectroscopy in a "
                                   "Mars analog system, Samail Ophiolite, Oman. Earth and Space Science 8, "
                                   "e2021EA001637"),
                     dict(id="lafay2020", doi="10.1594/PANGAEA.915753",
                          citation="Lafay R. et al. (2020) Electron microprobe data for Hole BT1B, Oman Drilling "
                                   "Project. PANGAEA")]),
    dict(id="lake_salda", name="Lake Salda (Salda Gölü)", country="Turkey", lat=37.550, lon=29.683,
         coordinate_precision_km=4, coordinate_source="Wikipedia (lake centroid)",
         verification="unverified: no published coordinate on the hydromagnesite unit; lake centroid is open water",
         measurement_radius_km=3,
         setting_en="Alkaline lake with hydromagnesite beaches and microbialites.",
         setting_pt="Lago alcalino com praias e microbialitos de hidromagnesita.",
         key_minerals=["hydromagnesite"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["carbonate"], reference_ids=["russell1999", "gunes2024"],
                          rationale_en="Hydromagnesite microbialites proposed as a model for Mars carbonates "
                                       "(Russell et al. 1999); compared with Jezero carbonates.",
                          rationale_pt="Microbialitos de hidromagnesita propostos como modelo para carbonatos de "
                                       "Marte (Russell et al. 1999); comparados aos carbonatos de Jezero.")],
         limitations_en=["Excluded from matching until an on-unit coordinate is verified."],
         limitations_pt=["Fora da correspondência até que uma coordenada sobre a unidade seja verificada."],
         references=[dict(id="russell1999", doi="10.1144/gsjgs.156.5.0869",
                          citation="Russell M.J. et al. (1999) Search for signs of ancient life on Mars: "
                                   "expectations from hydromagnesite microbialites, Salda Lake, Turkey. J. Geol. "
                                   "Soc. 156, 869-888"),
                     dict(id="gunes2024", doi="10.1111/gbi.12619",
                          citation="Gunes Y. et al. (2024) Morphological and microbial diversity of hydromagnesite "
                                   "microbialites in Lake Salda: a Mars analog alkaline lake. Geobiology 22")]),
    dict(id="rio_tinto", name="Río Tinto headwaters — Peña de Hierro", country="Spain", lat=37.72512, lon=-6.55643,
         coordinate_precision_km=0.5, coordinate_source="Waymarking record WM19T97 (Peña de Hierro mine)",
         verification="verified", measurement_radius_km=2,
         setting_en="Iberian Pyrite Belt massive sulfides with a gossan cap; acid (pH ~2) river precipitating "
                    "jarosite and schwertmannite; goethite converting to hematite on terraces.",
         setting_pt="Sulfetos maciços da Faixa Piritosa Ibérica com chapéu de gossan; rio ácido (pH ~2) que "
                    "precipita jarosita e schwertmannita; goethita que vira hematita nos terraços.",
         key_minerals=["jarosite", "schwertmannite", "goethite", "hematite"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["sulfate", "ferric_oxide"], reference_ids=["fernandez2005"],
                          rationale_en="Fernández-Remolar et al. (2005) use Río Tinto to interpret the jarosite- "
                                       "and hematite-bearing outcrop of Meridiani Planum: evaporitic jarosite and "
                                       "goethite-to-hematite conversion.",
                          rationale_pt="Fernández-Remolar et al. (2005) usam o Río Tinto para interpretar o "
                                       "afloramento com jarosita e hematita de Meridiani Planum: jarosita "
                                       "evaporítica e conversão de goethita em hematita.")],
         similarities_en=["Acid-sulfate mineralogy (jarosite) with ferric oxides, as at Meridiani."],
         similarities_pt=["Mineralogia ácido-sulfatada (jarosita) com óxidos férricos, como em Meridiani."],
         differences_en=["Driven by sulfide mining waste and microbial activity; heavy anthropogenic disturbance."],
         differences_pt=["Controlado por rejeito de mineração de sulfetos e atividade microbiana; forte "
                         "perturbação humana."],
         limitations_en=["Open pit, spoil and channels mixed in each pixel; Mediterranean vegetation around."],
         limitations_pt=["Cava, rejeito e canais misturados em cada pixel; vegetação mediterrânea em volta."],
         references=[dict(id="fernandez2005", doi="10.1016/j.epsl.2005.09.043",
                          citation="Fernández-Remolar D.C. et al. (2005) The Río Tinto Basin, Spain: mineralogy, "
                                   "sedimentary geobiology, and implications for interpretation of outcrop rocks "
                                   "at Meridiani Planum, Mars. EPSL 240, 149-167")]),
    dict(id="el_tatio", name="El Tatio geyser field", country="Chile", lat=-22.33139, lon=-68.01028,
         coordinate_precision_km=2, coordinate_source="Wikipedia (field reference point)", verification="verified",
         measurement_radius_km=2,
         setting_en="Hot-spring siliceous sinter (opal-A) over ~30 km² at ~4,300 m.",
         setting_pt="Sínter silicoso de fontes termais (opala-A) em ~30 km² a ~4.300 m.",
         key_minerals=["opal-A"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["al_phyllosilicate_silica"], reference_ids=["ruff2016"],
                          rationale_en="Ruff & Farmer (2016) compare opaline silica at Home Plate (Gusev, Spirit "
                                       "rover) with biomediated sinter textures at El Tatio.",
                          rationale_pt="Ruff & Farmer (2016) comparam a sílica opalina de Home Plate (Gusev, "
                                       "rover Spirit) com texturas de sínter biomediadas de El Tatio.")],
         similarities_en=["Hydrated (opaline) silica of hydrothermal origin."],
         similarities_pt=["Sílica hidratada (opalina) de origem hidrotermal."],
         differences_en=["BD2210_2 also responds to Al-OH clays; the site matches only the silica branch."],
         differences_pt=["BD2210_2 também responde a argilas de Al-OH; o sítio só corresponde ao ramo da sílica."],
         limitations_en=["Coordinate is the field reference point; sinter aprons (0.1–1 km) mix with volcanic "
                         "soils; tourist and drilling scars."],
         limitations_pt=["A coordenada é o ponto de referência do campo; os leques de sínter (0,1–1 km) se "
                         "misturam a solos vulcânicos; marcas de turismo e perfuração."],
         references=[dict(id="ruff2016", doi="10.1038/ncomms13554",
                          citation="Ruff S.W., Farmer J.D. (2016) Silica deposits on Mars with features resembling "
                                   "hot spring biosignatures at El Tatio in Chile. Nat. Commun. 7, 13554")]),
    dict(id="cuprite", name="Cuprite mining district", country="USA (Nevada)", lat=37.55, lon=-117.21389,
         coordinate_precision_km=1, coordinate_source="USGS MRDS record via westernmininghistory.com/10009264",
         verification="verified", measurement_radius_km=3,
         setting_en="Acid-sulfate (advanced argillic) alteration of Tertiary volcanics: alunite, kaolinite, "
                    "dickite, opal, silicified rock.",
         setting_pt="Alteração ácido-sulfatada (argílica avançada) de vulcânicas terciárias: alunita, caulinita, "
                    "dickita, opala, rocha silicificada.",
         key_minerals=["alunite", "kaolinite", "dickite", "opal", "muscovite"],
         analog_for=[dict(body="mars", basis="mineralogical_reference", classes=["al_phyllosilicate_silica", "sulfate"], reference_ids=["swayze2014"],
                          rationale_en="Mineralogical reference rather than a published Mars analog: Swayze et "
                                       "al. (2014) map alunite, kaolinite and opal here with imaging spectroscopy, "
                                       "the mineral families CRISM BD2210_2 and sulfate parameters target.",
                          rationale_pt="Referência mineralógica, não um análogo de Marte publicado: Swayze et "
                                       "al. (2014) mapeiam alunita, caulinita e opala aqui com espectroscopia de "
                                       "imageamento, as famílias que BD2210_2 e os parâmetros de sulfato do CRISM "
                                       "buscam.")],
         similarities_en=["Al-OH and sulfate (alunite) absorptions near 2.2 µm and 1.76 µm are well characterised."],
         similarities_pt=["Absorções de Al-OH e de sulfato (alunita) perto de 2,2 µm e 1,76 µm bem caracterizadas."],
         differences_en=["The cited paper does not frame Cuprite as a Mars analog."],
         differences_pt=["O artigo citado não apresenta Cuprite como análogo de Marte."],
         limitations_en=["Small historic pits; US-95 crosses the district; sparse shrubs."],
         limitations_pt=["Pequenas cavas históricas; a rodovia US-95 cruza o distrito; arbustos esparsos."],
         references=[dict(id="swayze2014", doi="10.2113/econgeo.109.5.1179",
                          citation="Swayze G.A. et al. (2014) Mapping advanced argillic alteration at Cuprite, "
                                   "Nevada, using imaging spectroscopy. Econ. Geol. 109, 1179-1221")]),
    dict(id="puu_nene", name="Puʻu Nēnē cinder cone (JSC Mars-1 source)", country="USA (Hawaiʻi)",
         lat=19.69743, lon=-155.49697, coordinate_precision_km=0.3,
         coordinate_source="Colorado School of Mines sample list (mars.mines.edu, PNeHIBc)", verification="verified",
         measurement_radius_km=1,
         setting_en="Palagonitic basaltic tephra, largely X-ray amorphous, minor plagioclase and magnetite.",
         setting_pt="Tefra basáltica palagonítica, em grande parte amorfa aos raios X, com pouco plagioclásio e "
                    "magnetita.",
         key_minerals=["palagonite", "plagioclase", "magnetite"],
         analog_for=[dict(body="mars", basis="simulant_source", classes=["altered_basaltic_soil"], reference_ids=["allen1998"],
                          rationale_en="Allen et al. (1998) quarried this tephra as JSC Mars-1, a simulant of "
                                       "Martian bright-region soil.",
                          rationale_pt="Allen et al. (1998) extraíram esta tefra como JSC Mars-1, simulante do "
                                       "solo das regiões claras de Marte.")],
         similarities_en=["Poorly crystalline Fe-bearing alteration of basaltic glass, as in Martian dust."],
         similarities_pt=["Alteração pouco cristalina de vidro basáltico com Fe, como na poeira marciana."],
         differences_en=["Its suitability as a simulant was debated (Allen & Morris 1999)."],
         differences_pt=["Sua adequação como simulante foi debatida (Allen & Morris 1999)."],
         limitations_en=["Cone is a few hundred metres across (2–5 EMIT pixels); grassland around."],
         limitations_pt=["O cone tem poucas centenas de metros (2–5 pixels EMIT); pasto em volta."],
         references=[dict(id="allen1998", doi="10.1029/98EO00309",
                          citation="Allen C.C. et al. (1998) Martian soil simulant available for scientific, "
                                   "educational study. Eos 79, 405-409"),
                     dict(id="allen1999", doi="10.1029/99EO00123",
                          citation="Allen C.C., Morris R.V. (1999) Reply. Eos 80, 169")]),
    dict(id="kau_desert", name="Kaʻū Desert, Kīlauea", country="USA (Hawaiʻi)", lat=19.40861, lon=-155.29667,
         coordinate_precision_km=3, coordinate_source="Wikipedia (Crater Rim Drive trailhead, NE edge)",
         verification="verified", measurement_radius_km=3,
         setting_en="Basaltic flows and tephra altered by SO2-acidified rain: opaline silica coatings, jarosite.",
         setting_pt="Derrames e tefra basálticos alterados por chuva acidificada por SO2: películas de sílica "
                    "opalina, jarosita.",
         key_minerals=["basalt", "opaline silica", "jarosite", "Fe-Ti oxide"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["al_phyllosilicate_silica", "sulfate", "altered_basaltic_soil",
                                                "pyroxene_basalt"], reference_ids=["seelos2010", "chemtob2010"],
                          rationale_en="Seelos et al. (2010) map opaline silica with AVIRIS and Chemtob et al. "
                                       "(2010) link the coatings to acid-sulfate leaching like that proposed for "
                                       "Gusev silica.",
                          rationale_pt="Seelos et al. (2010) mapeiam sílica opalina com AVIRIS e Chemtob et al. "
                                       "(2010) ligam as películas a lixiviação ácido-sulfatada como a proposta "
                                       "para a sílica de Gusev.")],
         similarities_en=[BASALT_NOTE_EN],
         similarities_pt=[BASALT_NOTE_PT],
         differences_en=["Coatings are ~10 µm thick: weak orbital signal mixed with fresh basalt."],
         differences_pt=["As películas têm ~10 µm: sinal orbital fraco misturado a basalto fresco."],
         limitations_en=["Coordinate is a trailhead on the desert's NE edge; the interior extends km to the SW."],
         limitations_pt=["A coordenada é um início de trilha na borda NE do deserto; o interior se estende por km "
                         "a SW."],
         references=[dict(id="seelos2010", doi="10.1029/2009JE003347",
                          citation="Seelos K.D. et al. (2010) Silica in a Mars analog environment: Kaʻū Desert, "
                                   "Kīlauea Volcano, Hawaii. JGR Planets 115, E00D15"),
                     dict(id="chemtob2010", doi="10.1029/2009JE003473",
                          citation="Chemtob S.M. et al. (2010) Silica coatings in the Kaʻū Desert, Hawaii, a Mars "
                                   "analog terrain. JGR Planets 115, E04001")]),
    dict(id="dresser", name="Dresser Formation, North Pole Dome, Pilbara", country="Australia",
         lat=-21.151759, lon=119.437252, coordinate_precision_km=5, coordinate_source="Wikipedia (formation)",
         verification="verified", measurement_radius_km=3,
         setting_en="~3.48 Ga hydrothermally altered chert, barite, hematitic chert, geyserite and sinter.",
         setting_pt="Chert alterado hidrotermalmente de ~3,48 Ga, barita, chert hematítico, geiserito e sínter.",
         key_minerals=["chert (quartz)", "barite", "hematite", "kaolinite"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["ferric_oxide", "al_phyllosilicate_silica"], reference_ids=["djokic2017"],
                          rationale_en="Djokic et al. (2017) propose the Dresser hot-spring deposits as an analog "
                                       "for fossil-life searches in ancient Martian hot springs.",
                          rationale_pt="Djokic et al. (2017) propõem os depósitos de fontes termais de Dresser como "
                                       "análogo para a busca de vida fóssil em fontes termais antigas de Marte.")],
         differences_en=["Silica is recrystallised chert, not hydrated opal: the analogy is geological and "
                         "biological, weak for BD2210_2."],
         differences_pt=["A sílica é chert recristalizado, não opala hidratada: a analogia é geológica e "
                         "biológica, fraca para BD2210_2."],
         limitations_en=["Coordinate is for the formation, ±5 km; narrow ridges, spinifex and laterite cover."],
         limitations_pt=["Coordenada da formação, ±5 km; cristas estreitas, cobertura de spinifex e laterita."],
         references=[dict(id="djokic2017", doi="10.1038/ncomms15263",
                          citation="Djokic T. et al. (2017) Earliest signs of life on land preserved in ca. 3.5 Ga "
                                   "hot spring deposits. Nat. Commun. 8, 15263")]),
    dict(id="lonar", name="Lonar Crater", country="India", lat=19.975, lon=76.5075, coordinate_precision_km=1,
         coordinate_source="Wikipedia (crater centre; lake)", verification="verified", measurement_radius_km=2,
         setting_en="~1.8 km simple impact crater formed entirely in Deccan flood basalt, with breccia and ejecta.",
         setting_pt="Cratera de impacto simples de ~1,8 km formada inteiramente em basalto de derrame do Deccan, "
                    "com brecha e ejecta.",
         key_minerals=["basalt"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["pyroxene_basalt"], reference_ids=["maloof2010"],
                          rationale_en="Maloof et al. (2010) describe Lonar as the only well-preserved terrestrial "
                                       "impact crater formed entirely in basalt, an analog for craters in Martian "
                                       "basaltic plains.",
                          rationale_pt="Maloof et al. (2010) descrevem Lonar como a única cratera de impacto "
                                       "terrestre bem preservada formada inteiramente em basalto, análoga às "
                                       "crateras das planícies basálticas de Marte.")],
         similarities_en=[BASALT_NOTE_EN],
         similarities_pt=[BASALT_NOTE_PT],
         differences_en=["Crater floor and rim are forested and surrounded by farmland; a lake fills the centre."],
         differences_pt=["Fundo e borda da cratera são florestados e cercados de lavoura; um lago ocupa o centro."],
         limitations_en=["Vegetation strongly masks the basalt in optical data."],
         limitations_pt=["A vegetação encobre fortemente o basalto nos dados ópticos."],
         references=[dict(id="maloof2010", doi="10.1130/B26474.1",
                          citation="Maloof A.C. et al. (2010) Geology of Lonar Crater, India. GSA Bull. 122, "
                                   "109-126")]),
    dict(id="twin_sisters", name="Twin Sisters dunite", country="USA (Washington)", lat=48.7045599,
         lon=-121.9873731, coordinate_precision_km=2, coordinate_source="Wikipedia / GNIS (summit)",
         verification="verified", measurement_radius_km=2,
         setting_en="Relatively unaltered dunite (olivine ~Fo91) with local serpentinite; USGS olivine standard "
                    "GDS71 locality.",
         setting_pt="Dunito pouco alterado (olivina ~Fo91) com serpentinito local; localidade do padrão de "
                    "olivina GDS71 do USGS.",
         key_minerals=["olivine (Fo91)", "enstatite", "chromite", "serpentine"],
         analog_for=[dict(body="mars", basis="published_analog", classes=["olivine_rich", "fe_mg_phyllosilicate"],
                          reference_ids=["curtis2021", "king1987"],
                          rationale_en="Curtis et al. (2021) study weathered Twin Sisters dunite as an analog for "
                                       "Martian ultramafic rocks; King & Ridley (1987) use its olivine to relate "
                                       "reflectance to composition.",
                          rationale_pt="Curtis et al. (2021) estudam o dunito intemperizado de Twin Sisters como "
                                       "análogo de rochas ultramáficas de Marte; King & Ridley (1987) usam sua "
                                       "olivina para relacionar reflectância e composição.")],
         similarities_en=["Olivine-dominated rock with the broad 1 µm olivine band."],
         similarities_pt=["Rocha dominada por olivina, com a banda larga de olivina em 1 µm."],
         differences_en=["Olivine is far more Mg-rich (Fo91) than typical Martian olivine."],
         differences_pt=["A olivina é muito mais rica em Mg (Fo91) que a olivina típica de Marte."],
         limitations_en=["Alpine terrain: seasonal snow, forest on lower slopes, steep shadows."],
         limitations_pt=["Terreno alpino: neve sazonal, floresta nas encostas baixas, sombras fortes."],
         references=[dict(id="curtis2021", doi="10.1130/abs/2021AM-370626",
                          citation="Curtis S. et al. (2021) Spectral variability in weathered ultramafic "
                                   "terrestrial analogs for Martian rocks. GSA Abstracts with Programs 53(6)"),
                     dict(id="king1987", doi="10.1029/JB092iB11p11457",
                          citation="King T.V.V., Ridley W.I. (1987) Relation of the spectroscopic reflectance of "
                                   "olivine to mineral chemistry and some remote sensing implications. JGR 92, "
                                   "11457-11469")]),
]
