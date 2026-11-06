"""Curated lunar analog sites (source data for app/data/terrestrial_analog_sites.json).

Coordinates from the cited coordinate_source; DOIs resolved on Crossref on 2026-11-06.
"""

KAU_MOON = dict(body="moon", basis="published_analog_general", classes=["pyroxene_basalt"], reference_ids=["neish2017", "hughes2020"],
                rationale_en="Hawaiian basalt lavas are among the terrestrial end-members compared with lunar "
                             "lava surfaces (Neish et al. 2017) and fissure volcanism (Hughes et al. 2020). The "
                             "opened sources name Hawaiian basalts in general, not the Kaʻū Desert itself.",
                rationale_pt="Lavas basálticas havaianas estão entre os membros terrestres comparados a superfícies "
                             "de lava lunares (Neish et al. 2017) e ao vulcanismo fissural (Hughes et al. 2020). As "
                             "fontes consultadas citam basaltos havaianos em geral, não o deserto de Kaʻū em si.")

KAU_MOON_REFS = [
    dict(id="neish2017", doi="10.1016/j.icarus.2016.08.008",
         citation="Neish C.D. et al. (2017) Terrestrial analogues for lunar impact melt flows. Icarus 281, 73-89"),
    dict(id="hughes2020", doi="10.1016/j.pss.2020.105091",
         citation="Hughes S.S. et al. (2020) Basaltic fissure types on Earth: suitable analogs to evaluate the "
                  "origins of volcanic terrains on the Moon and Mars? PSS 193, 105091"),
]

SITES = [
    dict(id="merriam_jsc1", name="Merriam Crater cinder quarry, San Francisco Volcanic Field (JSC-1 source)",
         country="USA (Arizona)", lat=35.3333, lon=-111.2833, coordinate_precision_km=2,
         coordinate_source="Lunarpedia transcription of McKay et al. (1994): 35°20'N, 111°17'W",
         verification="verified", measurement_radius_km=2,
         setting_en="Basaltic ash and cinder: plagioclase, pyroxene and olivine with ~50% basaltic glass.",
         setting_pt="Cinza e escória basálticas: plagioclásio, piroxênio e olivina com ~50% de vidro basáltico.",
         key_minerals=["plagioclase", "pyroxene", "olivine", "basaltic glass", "ilmenite"],
         analog_for=[dict(body="moon", basis="simulant_source", classes=["pyroxene_basalt", "volcanic_glass"],
                          reference_ids=["mckay1994", "willman1995", "ray2010"],
                          rationale_en="NASA JSC made the JSC-1 simulant from this ash to approximate a low-Ti mare "
                                       "soil (Apollo 14 sample 14163) in chemistry, mineralogy and grain size.",
                          rationale_pt="A NASA JSC fez o simulante JSC-1 com esta cinza para aproximar um solo de "
                                       "mare com baixo Ti (amostra 14163 da Apollo 14) em química, mineralogia e "
                                       "granulometria.")],
         similarities_en=["Pyroxene + plagioclase + olivine with abundant glass, like low-Ti mare soil."],
         similarities_pt=["Piroxênio + plagioclásio + olivina com muito vidro, como solo de mare com baixo Ti."],
         differences_en=["No agglutinates, no nanophase iron and no space weathering; terrestrial oxidation and "
                         "clay traces."],
         differences_pt=["Sem aglutinados, sem ferro nanofásico e sem intemperismo espacial; oxidação terrestre e "
                         "traços de argila."],
         limitations_en=["Active cinder quarry; sparse juniper and grass around; pit within 1–2 km of the point."],
         limitations_pt=["Pedreira de escória ativa; zimbro e capim esparsos em volta; cava a 1–2 km do ponto."],
         references=[dict(id="mckay1994", doi=None, url="https://lunarpedia.org/w/JSC-1",
                          citation="McKay D.S. et al. (1994) JSC-1: a new lunar soil simulant. Engineering, "
                                   "Construction, and Operations in Space IV, ASCE, 857-866"),
                     dict(id="willman1995", doi="10.1061/(ASCE)0893-1321(1995)8:2(77)",
                          citation="Willman B.M. et al. (1995) Properties of lunar soil simulant JSC-1. J. Aerosp. "
                                   "Eng. 8, 77-87"),
                     dict(id="ray2010", doi="10.1016/j.jnoncrysol.2010.04.049",
                          citation="Ray C.S. et al. (2010) JSC-1A lunar soil simulant: characterization, glass "
                                   "formation, and selected glass properties. J. Non-Cryst. Solids 356, 2369-2374")]),
    dict(id="craters_of_the_moon", name="Craters of the Moon lava field (Snake River Plain)", country="USA (Idaho)",
         lat=43.46167, lon=-113.56271, coordinate_precision_km=5,
         coordinate_source="Wikipedia (monument reference point inside the Holocene lava field)",
         verification="verified", measurement_radius_km=5,
         setting_en="Holocene Great Rift lavas, basalt to trachyte; Fe-rich olivine, plagioclase, rare pyroxene, "
                    "glassy crusts.",
         setting_pt="Lavas holocênicas da Great Rift, de basalto a traquito; olivina rica em Fe, plagioclásio, "
                    "piroxênio raro, crostas vítreas.",
         key_minerals=["Fe-rich olivine", "plagioclase", "Fe-Ti oxides", "glass"],
         analog_for=[dict(body="moon", basis="published_analog", classes=["olivine_rich", "volcanic_glass"],
                          reference_ids=["neish2017", "stout1994"],
                          rationale_en="NASA FINESSE used these lavas as analogs for lunar lava-flow surfaces "
                                       "(Neish et al. 2017); Stout et al. (1994) document Fe-rich olivine and "
                                       "glassy crusts with rare pyroxene.",
                          rationale_pt="O projeto FINESSE da NASA usou estas lavas como análogos de superfícies de "
                                       "derrames lunares (Neish et al. 2017); Stout et al. (1994) documentam "
                                       "olivina rica em Fe e crostas vítreas com piroxênio raro.")],
         differences_en=["Alkaline, Fe-Ti-P-rich lavas, not low-Ti mare tholeiite: mainly a morphological analog. "
                         "Neish et al. found no terrestrial flow matching lunar melt-flow properties."],
         differences_pt=["Lavas alcalinas ricas em Fe-Ti-P, não toleíto de mare com baixo Ti: análogo sobretudo "
                         "morfológico. Neish et al. não acharam derrame terrestre com as propriedades lunares."],
         limitations_en=["Point is ±5 km within a 1,600 km² field; sagebrush and lichen on older flows."],
         limitations_pt=["Ponto com ±5 km num campo de 1.600 km²; artemísia e líquen nos derrames mais antigos."],
         references=[KAU_MOON_REFS[0],
                     dict(id="stout1994", doi="10.1093/petrology/35.6.1681",
                          citation="Stout M.Z. et al. (1994) Petrological and mineralogical variations in 2500-2000 "
                                   "yr B.P. lava flows, Craters of the Moon lava field, Idaho. J. Petrol. 35, "
                                   "1681-1715")]),
    dict(id="timanfaya", name="Timanfaya lava field (1730–1736), Lanzarote", country="Spain",
         lat=28.99417, lon=-13.79333, coordinate_precision_km=3, coordinate_source="Wikipedia (national park)",
         verification="verified", measurement_radius_km=3,
         setting_en="Basaltic fissure-eruption lavas and tephra, basanite evolving to tholeiite.",
         setting_pt="Lavas e tefra de erupção fissural basáltica, de basanito a toleíto.",
         key_minerals=["basalt"],
         analog_for=[dict(body="moon", basis="outreach", classes=["pyroxene_basalt"], reference_ids=["esa2017", "muller2024"],
                          rationale_en="ESA's PANGAEA astronaut course trains here because the arid climate "
                                       "preserves lava plains resembling lunar maria (ESA, not peer reviewed); "
                                       "Muller & Longpré (2024) document the basaltic composition.",
                          rationale_pt="O curso PANGAEA da ESA treina astronautas aqui porque o clima árido preserva "
                                       "planícies de lava parecidas com os mares lunares (ESA, sem revisão por "
                                       "pares); Muller & Longpré (2024) documentam a composição basáltica.")],
         similarities_en=["Fresh, arid basalt plains with little vegetation."],
         similarities_pt=["Planícies de basalto recente e árido, com pouca vegetação."],
         differences_en=["Alkaline-transitional Canary basalt, not mare chemistry; the lunar link is from ESA "
                         "outreach only."],
         differences_pt=["Basalto alcalino-transicional das Canárias, não química de mare; o vínculo lunar vem só "
                         "de divulgação da ESA."],
         limitations_en=["National park (restricted); lichen on lava; agriculture on tephra."],
         limitations_pt=["Parque nacional (acesso restrito); líquen na lava; agricultura sobre a tefra."],
         references=[dict(id="esa2017", doi=None,
                          url="https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/CAVES_and_"
                              "Pangaea/Astronaut_meets_volcano", citation="ESA (2017) Astronaut meets volcano"),
                     dict(id="muller2024", doi="10.1007/s00445-024-01729-5",
                          citation="Muller J.K., Longpré M.-A. (2024) Tephra dispersal and composition reveal the "
                                   "explosive onset of a large basaltic fissure eruption: Timanfaya, Lanzarote, "
                                   "1730-1736 CE. Bull. Volcanol. 86")]),
    dict(id="stillwater", name="Stillwater Complex, Beartooth Mountains (NU-LHT simulant source)",
         country="USA (Montana)", lat=45.3861, lon=-109.9031, coordinate_precision_km=5,
         coordinate_source="Wikipedia (complex reference point); anorthosite bands a few km away",
         verification="verified", measurement_radius_km=5,
         setting_en="Layered mafic–ultramafic intrusion; Banded Series of norite, gabbro and anorthosite.",
         setting_pt="Intrusão máfica–ultramáfica acamadada; Série Bandada de norito, gabro e anortosito.",
         key_minerals=["calcic plagioclase", "orthopyroxene", "clinopyroxene"],
         analog_for=[dict(body="moon", basis="published_analog", classes=["anorthosite", "norite"],
                          reference_ids=["salpas1983", "carli2014", "rickman2024"],
                          rationale_en="Salpas et al. (1983) test Stillwater anorthosites as lunar analogs; Carli et "
                                       "al. (2014) use their VNIR spectra to map lunar highlands; Stillwater "
                                       "anorthosite and norite are the feedstock of the NU-LHT highland simulants.",
                          rationale_pt="Salpas et al. (1983) testam os anortositos de Stillwater como análogos "
                                       "lunares; Carli et al. (2014) usam seus espectros VNIR para mapear as terras "
                                       "altas; anortosito e norito de Stillwater são a matéria-prima dos "
                                       "simulantes NU-LHT.")],
         similarities_en=["Plagioclase-dominated anorthosite and plagioclase–orthopyroxene norite, as in the "
                          "lunar highland crust."],
         similarities_pt=["Anortosito dominado por plagioclásio e norito de plagioclásio–ortopiroxênio, como na "
                          "crosta das terras altas."],
         differences_en=["Not shocked or space weathered; plagioclase less calcic than lunar ferroan anorthosite."],
         differences_pt=["Sem choque nem intemperismo espacial; plagioclásio menos cálcico que o anortosito "
                         "ferroano lunar."],
         limitations_en=["Mountain forest, winter snow and lichen; active Pt-Pd mining."],
         limitations_pt=["Floresta de montanha, neve no inverno e líquen; mineração ativa de Pt-Pd."],
         references=[dict(id="salpas1983", doi="10.1029/JB088iS01p00B27",
                          citation="Salpas P.A., Haskin L.A., McCallum I.S. (1983) Stillwater anorthosites: a lunar "
                                   "analog? JGR 88, B27-B39"),
                     dict(id="carli2014", doi="10.2138/am-2014-4808",
                          citation="Carli C., Serventi G., Sgavetti M. (2014) VNIR spectral variability of the "
                                   "igneous stratified Stillwater Complex: a tool to map lunar highlands. Am. "
                                   "Mineral. 99, 1834-1848"),
                     dict(id="rickman2024", doi=None, url="https://ntrs.nasa.gov/citations/20240007991",
                          citation="Rickman D.L. et al. (2024) Characterization of NUW-LHT-5M, a lunar highland "
                                   "simulant. NASA TP")]),
    dict(id="shawmere", name="Shawmere Anorthosite, Kapuskasing Structural Zone (OB-1 simulant source)",
         country="Canada (Ontario)", lat=48.1324, lon=-82.7886, coordinate_precision_km=0.5,
         coordinate_source="Ontario Geological Survey MDI record MDI42B02NW00001", verification="verified",
         measurement_radius_km=3,
         setting_en="Coarse Archean anorthosite, plagioclase ~An78 with 2–5% diopside, hypersthene, hornblende.",
         setting_pt="Anortosito arqueano grosso, plagioclásio ~An78 com 2–5% de diopsídio, hiperstênio, "
                    "hornblenda.",
         key_minerals=["plagioclase (~An78)", "diopside", "hypersthene", "hornblende"],
         analog_for=[dict(body="moon", basis="simulant_source", classes=["anorthosite"], reference_ids=["battler2009"],
                          rationale_en="Battler & Spray (2009) chose the Shawmere for its calcic, homogeneous "
                                       "plagioclase as the anorthosite component of the OB-1 highland simulant.",
                          rationale_pt="Battler & Spray (2009) escolheram o Shawmere pelo plagioclásio cálcico e "
                                       "homogêneo como componente anortosítico do simulante OB-1 das terras altas.")],
         similarities_en=["Nearly monomineralic calcic plagioclase, like lunar highland anorthosite."],
         similarities_pt=["Plagioclásio cálcico quase monomineral, como o anortosito das terras altas lunares."],
         differences_en=["Metamorphosed and hornblende-bearing; plagioclase less calcic than lunar anorthosite."],
         differences_pt=["Metamorfizado e com hornblenda; plagioclásio menos cálcico que o anortosito lunar."],
         limitations_en=["Boreal forest, lakes and till cover most of the area: few bare-rock pixels."],
         limitations_pt=["Floresta boreal, lagos e till cobrem a maior parte da área: poucos pixels de rocha nua."],
         references=[dict(id="battler2009", doi="10.1016/j.pss.2009.09.003",
                          citation="Battler M.M., Spray J.G. (2009) The Shawmere anorthosite and OB-1 as lunar "
                                   "highland regolith simulants. PSS 57, 2128-2131")]),
    dict(id="sittampundi", name="Sittampundi Anorthosite Complex (LSS-ISAC-1 simulant source)",
         country="India (Tamil Nadu)", lat=11.275, lon=77.917, coordinate_precision_km=15,
         coordinate_source="Centre of the study-area box in Naidu, MSA Special Paper 1, pp. 116-123",
         verification="verified", measurement_radius_km=5,
         setting_en="Neoarchean layered anorthosite–gabbro complex at granulite facies; anorthite-rich plagioclase.",
         setting_pt="Complexo acamadado neoarqueano de anortosito–gabro em fácies granulito; plagioclásio rico em "
                    "anortita.",
         key_minerals=["calcic plagioclase", "amphibole", "garnet", "pyroxene", "Cr-spinel"],
         analog_for=[dict(body="moon", basis="published_analog", classes=["anorthosite"], reference_ids=["anbazhagan2010", "anbazhagan2021"],
                          rationale_en="Anbazhagan & Arivazhagan (2010) use its anorthosites as lunar highland "
                                       "spectral analogs; ISRO quarried it for the LSS-ISAC-1 simulant "
                                       "(Anbazhagan et al. 2021).",
                          rationale_pt="Anbazhagan & Arivazhagan (2010) usam seus anortositos como análogos "
                                       "espectrais das terras altas; a ISRO o extraiu para o simulante LSS-ISAC-1 "
                                       "(Anbazhagan et al. 2021).")],
         differences_en=["High-grade metamorphism; tropical weathering."],
         differences_pt=["Metamorfismo de alto grau; intemperismo tropical."],
         limitations_en=["Coordinate is the centre of a ~15 km study box; the anorthosite band is narrow; "
                         "farmland and vegetation."],
         limitations_pt=["A coordenada é o centro de uma área de estudo de ~15 km; a faixa de anortosito é "
                         "estreita; lavoura e vegetação."],
         references=[dict(id="anbazhagan2010", doi="10.1016/j.pss.2009.12.002",
                          citation="Anbazhagan S., Arivazhagan S. (2010) Reflectance spectra of analog "
                                   "anorthosites: implications for lunar highland mapping. PSS 58, 752-760"),
                     dict(id="anbazhagan2021", doi="10.1016/j.icarus.2021.114511",
                          citation="Anbazhagan S. et al. (2021) A lunar soil simulant (LSS-ISAC-1) for the lunar "
                                   "exploration programme of ISRO. Icarus 366, 114511")]),
    dict(id="sudbury_creighton", name="Sudbury Igneous Complex norite, South Range (Creighton)",
         country="Canada (Ontario)", lat=46.46389, lon=-81.17472, coordinate_precision_km=2,
         coordinate_source="Wikipedia (Creighton Mine; norite base within 1–2 km)", verification="verified",
         measurement_radius_km=3,
         setting_en="~1.85 Ga differentiated impact melt sheet: quartz norite, norite, gabbro, granophyre; breccias.",
         setting_pt="Lençol de fusão de impacto diferenciado de ~1,85 Ga: quartzo-norito, norito, gabro, "
                    "granófiro; brechas.",
         key_minerals=["plagioclase", "orthopyroxene", "quartz"],
         analog_for=[dict(body="moon", basis="published_analog", classes=["norite"], reference_ids=["norman1992", "therriault2002"],
                          rationale_en="Norman (1992) discusses the Sudbury melt sheet as a model for lunar noritic "
                                       "crust; Therriault et al. (2002) document its differentiation. Apollo 15–17 "
                                       "crews trained here.",
                          rationale_pt="Norman (1992) discute o lençol de fusão de Sudbury como modelo para a crosta "
                                       "norítica lunar; Therriault et al. (2002) documentam sua diferenciação. As "
                                       "tripulações das Apollo 15–17 treinaram aqui.")],
         differences_en=["Quartz-bearing, crust-contaminated norite, unlike pristine lunar norite."],
         differences_pt=["Norito com quartzo e contaminado pela crosta, diferente do norito lunar primitivo."],
         limitations_en=["Boreal forest, lakes; a century of mining and smelting (slag, tailings, regreening)."],
         limitations_pt=["Floresta boreal, lagos; um século de mineração e fundição (escória, rejeito, "
                         "reflorestamento)."],
         references=[dict(id="norman1992", doi="10.1130/SPE293-p331",
                          citation="Norman M.D. (1992) Sudbury Igneous Complex: impact melt or endogenous magma? "
                                   "Implications for lunar crustal evolution. GSA Spec. Pap. 293, 331-342"),
                     dict(id="therriault2002", doi="10.2113/gsecongeo.97.7.1521",
                          citation="Therriault A.M., Fowler A.D., Grieve R.A.F. (2002) The Sudbury Igneous Complex: "
                                   "a differentiated impact melt sheet. Econ. Geol. 97, 1521-1540")]),
    dict(id="kunene_zebra", name="Kunene Complex, Zebra Mountains lobe", country="Namibia",
         lat=-17.12322, lon=13.49802, coordinate_precision_km=0.2,
         coordinate_source="GPS of sample Ku-97-93, Table A.1.1, Drüppel (2003) Würzburg dissertation appendix",
         verification="unverified: no published lunar-analog reference (lithology and coordinate verified)",
         measurement_radius_km=3,
         setting_en="Mesoproterozoic massif anorthosite and leucotroctolite in an arid setting.",
         setting_pt="Anortosito maciço e leucotroctolito mesoproterozoicos em ambiente árido.",
         key_minerals=["plagioclase (~An57–76)", "pyroxene", "olivine", "ilmenite"],
         analog_for=[dict(body="moon", basis="candidate", classes=["anorthosite"], reference_ids=["lehmann2023"],
                          rationale_en="Candidate only: well-exposed arid anorthosite, but no paper uses it as a "
                                       "lunar analog.",
                          rationale_pt="Apenas candidato: anortosito árido bem exposto, mas nenhum artigo o usa "
                                       "como análogo lunar.")],
         limitations_en=["Excluded from matching until a lunar-analog reference exists; measured for the library."],
         limitations_pt=["Fora da correspondência até existir referência como análogo lunar; medido para a "
                         "biblioteca."],
         references=[dict(id="lehmann2023", doi="10.1016/j.gsf.2023.101620",
                          citation="Lehmann J. et al. (2023) Landsat 8 and Alos DEM geological mapping reveals the "
                                   "architecture of the giant Mesoproterozoic Kunene Complex anorthosite suite. "
                                   "Geosci. Front. 14, 101620")]),
]
