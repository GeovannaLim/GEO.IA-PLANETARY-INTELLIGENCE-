# GEØ.IA Planetary Intelligence — data, resources and references

The Space Apps guide asks for all data, resources, tools, code, text and images used. Every analysis response
also lists its exact product IDs, observation dates and URLs under "Scientific sources".

## NASA data and resources

| Resource | Access used by the platform |
|---|---|
| LRO Lunar Orbiter Laser Altimeter (LOLA) RDR | PDS Geosciences Node, ODE Granular Data System (GDS): https://ode.rsl.wustl.edu/ |
| LOLA/PGDA south polar illumination and permanent-shadow maps (Mazarico et al., 2011) | NASA GSFC Planetary Geodesy Data Archive (PGDA) |
| Chandrayaan-1 Moon Mineralogy Mapper (M³) L2 reflectance, L1B LOC/OBS | PDS Imaging Node (planetarydata.jpl.nasa.gov), found through ODE REST |
| MGS Mars Orbiter Laser Altimeter (MOLA) PEDR | ODE GDS |
| MRO CRISM MTRDR (summary parameters, I/F) | PDS Geosciences Node (pds-geosciences.wustl.edu) |
| ODE REST product search | https://oderest.rsl.wustl.edu/ |
| Moon Trek and Mars Trek WMTS | https://trek.nasa.gov/ |
| PDS Registry/API (LOLA, Diviner discovery) | https://pds.nasa.gov/ |
| EMIT L2A surface reflectance (Earth) | via Google Earth Engine |
| NASA Technical Reports Server (NTRS) | simulant and field-test documentation cited in the catalog |

## Space agency partner data and other data

| Resource | Use |
|---|---|
| ESA / Copernicus DEM GLO-30 (Copernicus programme), AWS Open Data: https://copernicus-dem-30m.s3.amazonaws.com/ | Terrain profiles of the terrestrial analog sites |
| ISRO Chandrayaan-1 mission | Platform that carried NASA's M³ |
| USGS Astrogeology STAC | Data discovery |
| CORINE Land Cover 2012/2018 (Copernicus Land Monitoring Service, EEA) | Validation audit only (Río Tinto mining footprint) |
| OpenStreetMap contributors (ODbL), Overpass API | Validation audit only (Río Tinto mining features) |
| Crossref, DataCite | DOI verification of every catalog reference |

## Software, services and tools

| Component | Items |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, HTTPX, NumPy, ReportLab, SQLite, Docker |
| Tests | pytest, respx |
| Optional Earth endpoint | earthengine-api |
| Hosting | Render |
| Frontend | Skip AI app builder (React), PocketBase |
| Use of Super Intelligence | Claude (Anthropic) wrote the backend code, tests, validation scripts and documentation drafts under the team's direction; the Skip AI app builder generated the web interface. See the project page, "Use of Super Intelligence". |
| Images and textures | 3D globe textures and interface images used by the frontend. **The team must list their sources and licenses here before submitting**, and watermark any SI-generated image. |

## Method references

- Mustard J.F. et al. (2011) JGR 116, E00G12 (definition of the M³ integrated band depths IBD1000/IBD2000).
- Viviano-Beck C.E. et al. (2014) Revised CRISM spectral parameters and summary products based on the currently
  detected mineral diversity on Mars. JGR Planets 119, 1403-1431. https://doi.org/10.1002/2014JE004627
- Mazarico E., Neumann G.A., Smith D.E., Zuber M.T., Torrence M.H. (2011) Illumination conditions of the lunar
  polar regions using LOLA topography. Icarus 211, 1066-1081. https://doi.org/10.1016/j.icarus.2010.10.030
- Bandfield J.L. et al. (2000) A global view of Martian surface compositions from MGS-TES. Science 287, 1626.
  https://doi.org/10.1126/science.287.5458.1626
- Hall D.K. et al. (1995) Remote Sensing of Environment 54 (NDSI snow index).
- McFeeters S.K. (1996) International Journal of Remote Sensing 17 (NDWI water index).
- PDS catalog for the CRISM map projection: `mrocr_4001/catalog/mtr_map.cat`,
  https://pds-geosciences.wustl.edu/mro/mro-m-crism-5-rdr-mptargeted-v1/mrocr_4001/catalog/mtr_map.cat

## Validation references (expected outcomes of the test scenarios)

- Jezero olivine and clays (Mars 2020 site selection): https://authors.library.caltech.edu/87552
- Nili Fossae and Mawrth Vallis: https://meetingorganizer.copernicus.org/EPSC2018/EPSC2018-578.pdf
- Curiosity landing elevation: Vasavada et al. (2014),
  https://deepblue.lib.umich.edu/bitstream/2027.42/108017/1/jgre20266.pdf
- Chang'e-3 landing site: https://www.lroc.asu.edu/images/751 · https://www.lroc.asu.edu/images/811
- Copernicus central-peak olivine: Isaacson et al. (2011),
  https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2010JE003731
- Aram Chaos sulfates: Lichtenberg et al. (2010) JGR Planets, https://doi.org/10.1029/2009JE003353
- Dust regions (low thermal inertia): Putzig et al. (2005) Icarus 173
- Nili Fossae olivine ridges (FRT00003E12): https://essopenarchive.org/doi/full/10.22541/essoar.176235473.32635438/v4
- Regional olivine unit of Nili Fossae: https://www.sciencedirect.com/science/article/abs/pii/S0019103518306031
- Craters of the Moon sample coordinates (Highway Flow, HF16001): Tolometti G. (2021) The Physical Properties of
  Volcanic and Impact Melt. PhD thesis, Western University, Table 2.2,
  https://uwo.scholaris.ca/bitstreams/8a90b505-fda3-46d6-8f08-16ae2d73feaf/download
- Haughton crater centre: Patterson & Ernst (2020) Meteoritics & Planetary Science, https://doi.org/10.1111/maps.13573
- Río Tinto (Peña de Hierro) mine and MARTE project: https://astrobiology.nasa.gov/news/drilling-for-weird-life/ ;
  OpenStreetMap way 208910493; CORINE Land Cover class 131 (EEA)
- Mauna Kea PISCES 2010 ISRU field test (Puʻu Hiwahine): Klingelhöfer et al., NASA NTRS 20140008708

## Terrestrial analog catalog references (DOIs verified on Crossref/DataCite, 2026-11-06)

- Allen C.C. et al. (1998) Martian soil simulant available for scientific, educational study. Eos 79, 405-409. https://doi.org/10.1029/98EO00309
- Allen C.C., Morris R.V. (1999) Reply. Eos 80, 169. https://doi.org/10.1029/99EO00123
- Anbazhagan S. et al. (2021) A lunar soil simulant (LSS-ISAC-1) for the lunar exploration programme of ISRO. Icarus 366, 114511. https://doi.org/10.1016/j.icarus.2021.114511
- Anbazhagan S., Arivazhagan S. (2010) Reflectance spectra of analog anorthosites: implications for lunar highland mapping. PSS 58, 752-760. https://doi.org/10.1016/j.pss.2009.12.002
- Battler M.M., Spray J.G. (2009) The Shawmere anorthosite and OB-1 as lunar highland regolith simulants. PSS 57, 2128-2131. https://doi.org/10.1016/j.pss.2009.09.003
- Carli C., Serventi G., Sgavetti M. (2014) VNIR spectral variability of the igneous stratified Stillwater Complex: a tool to map lunar highlands. Am. Mineral. 99, 1834-1848. https://doi.org/10.2138/am-2014-4808
- Chemtob S.M. et al. (2010) Silica coatings in the Kaʻū Desert, Hawaii, a Mars analog terrain. JGR Planets 115, E04001. https://doi.org/10.1029/2009JE003473
- Curtis S. et al. (2021) Spectral variability in weathered ultramafic terrestrial analogs for Martian rocks. GSA Abstracts with Programs 53(6). https://doi.org/10.1130/abs/2021AM-370626
- Djokic T. et al. (2017) Earliest signs of life on land preserved in ca. 3.5 Ga hot spring deposits. Nat. Commun. 8, 15263. https://doi.org/10.1038/ncomms15263
- ESA (2017) Astronaut meets volcano. https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/CAVES_and_Pangaea/Astronaut_meets_volcano
- Fernández-Remolar D.C. et al. (2005) The Río Tinto Basin, Spain: mineralogy, sedimentary geobiology, and implications for interpretation of outcrop rocks at Meridiani Planum, Mars. EPSL 240, 149-167. https://doi.org/10.1016/j.epsl.2005.09.043
- Gunes Y. et al. (2024) Morphological and microbial diversity of hydromagnesite microbialites in Lake Salda: a Mars analog alkaline lake. Geobiology 22. https://doi.org/10.1111/gbi.12619
- Hughes S.S. et al. (2020) Basaltic fissure types on Earth: suitable analogs to evaluate the origins of volcanic terrains on the Moon and Mars? PSS 193, 105091. https://doi.org/10.1016/j.pss.2020.105091
- King T.V.V., Ridley W.I. (1987) Relation of the spectroscopic reflectance of olivine to mineral chemistry and some remote sensing implications. JGR 92, 11457-11469. https://doi.org/10.1029/JB092iB11p11457
- Lafay R. et al. (2020) Electron microprobe data for Hole BT1B, Oman Drilling Project. PANGAEA. https://doi.org/10.1594/PANGAEA.915753
- Leask E.K. et al. (2021) Tracing carbonate formation, serpentinization, and biological materials with micro-/meso-scale infrared imaging spectroscopy in a Mars analog system, Samail Ophiolite, Oman. Earth and Space Science 8, e2021EA001637. https://doi.org/10.1029/2021EA001637
- Lehmann J. et al. (2023) Landsat 8 and Alos DEM geological mapping reveals the architecture of the giant Mesoproterozoic Kunene Complex anorthosite suite. Geosci. Front. 14, 101620. https://doi.org/10.1016/j.gsf.2023.101620
- Maloof A.C. et al. (2010) Geology of Lonar Crater, India. GSA Bull. 122, 109-126. https://doi.org/10.1130/B26474.1
- McKay D.S. et al. (1994) JSC-1: a new lunar soil simulant. Engineering, Construction, and Operations in Space IV, ASCE, 857-866. https://lunarpedia.org/w/JSC-1
- Muller J.K., Longpré M.-A. (2024) Tephra dispersal and composition reveal the explosive onset of a large basaltic fissure eruption: Timanfaya, Lanzarote, 1730-1736 CE. Bull. Volcanol. 86. https://doi.org/10.1007/s00445-024-01729-5
- Neish C.D. et al. (2017) Terrestrial analogues for lunar impact melt flows. Icarus 281, 73-89. https://doi.org/10.1016/j.icarus.2016.08.008
- Norman M.D. (1992) Sudbury Igneous Complex: impact melt or endogenous magma? Implications for lunar crustal evolution. GSA Spec. Pap. 293, 331-342. https://doi.org/10.1130/SPE293-p331
- Ray C.S. et al. (2010) JSC-1A lunar soil simulant: characterization, glass formation, and selected glass properties. J. Non-Cryst. Solids 356, 2369-2374. https://doi.org/10.1016/j.jnoncrysol.2010.04.049
- Rickman D.L. et al. (2024) Characterization of NUW-LHT-5M, a lunar highland simulant. NASA TP. https://ntrs.nasa.gov/citations/20240007991
- Ruff S.W., Farmer J.D. (2016) Silica deposits on Mars with features resembling hot spring biosignatures at El Tatio in Chile. Nat. Commun. 7, 13554. https://doi.org/10.1038/ncomms13554
- Russell M.J. et al. (1999) Search for signs of ancient life on Mars: expectations from hydromagnesite microbialites, Salda Lake, Turkey. J. Geol. Soc. 156, 869-888. https://doi.org/10.1144/gsjgs.156.5.0869
- Salpas P.A., Haskin L.A., McCallum I.S. (1983) Stillwater anorthosites: a lunar analog? JGR 88, B27-B39. https://doi.org/10.1029/JB088iS01p00B27
- Seelos K.D. et al. (2010) Silica in a Mars analog environment: Kaʻū Desert, Kīlauea Volcano, Hawaii. JGR Planets 115, E00D15. https://doi.org/10.1029/2009JE003347
- Stout M.Z. et al. (1994) Petrological and mineralogical variations in 2500-2000 yr B.P. lava flows, Craters of the Moon lava field, Idaho. J. Petrol. 35, 1681-1715. https://doi.org/10.1093/petrology/35.6.1681
- Swayze G.A. et al. (2014) Mapping advanced argillic alteration at Cuprite, Nevada, using imaging spectroscopy. Econ. Geol. 109, 1179-1221. https://doi.org/10.2113/econgeo.109.5.1179
- Therriault A.M., Fowler A.D., Grieve R.A.F. (2002) The Sudbury Igneous Complex: a differentiated impact melt sheet. Econ. Geol. 97, 1521-1540. https://doi.org/10.2113/gsecongeo.97.7.1521
- Willman B.M. et al. (1995) Properties of lunar soil simulant JSC-1. J. Aerosp. Eng. 8, 77-87. https://doi.org/10.1061/(ASCE)0893-1321(1995)8:2(77)
