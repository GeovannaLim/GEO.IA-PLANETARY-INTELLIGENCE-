# NASA Space Apps 2026 — Project page texts

**Challenge:** *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

The sections below follow the field order of the official *Project Submission Guide* (2026), ready to paste into
the Project page. Everything is in English, as the guide requires.

Before submitting, fill in these placeholders:
- `[TEAM NAME]`
- `[TEAM MEMBERS]`
- `[DEMO LINK]`
- `[FINAL PROJECT LINK]`

---

## Project Name

GEØ.IA Planetary Intelligence

## High-Level Project Summary

GEØ.IA is an interactive web platform that lets anyone select a region of the Moon or Mars on a 3D globe. It
returns, in about a minute, the documented places on Earth that best help study that region, and explains why.

For each selection, the backend reads open NASA data live:
- laser altimetry (LRO LOLA, MGS MOLA);
- orbital spectroscopy (Chandrayaan-1 M³, MRO CRISM);
- imagery (Moon and Mars Trek);
- for the lunar south pole, where candidate permanent bases are located, LOLA-derived illumination and
  permanent-shadow maps.

The platform turns these data into screening-level mineral evidence. It then matches the evidence to a curated
catalog of terrestrial analog sites documented in the scientific literature. For each site it states what makes it
a good analog, where the analogy fails, and the exact data products used.

At the lunar south pole, where sunlight is too low for mineral spectroscopy, the platform adds two things:
- the modelled illumination and cold-trap context;
- an experimental terrain comparison with real Earth elevation data (Copernicus DEM).

The project matters because analog sites are where astronauts train and where rovers, instruments and
in-situ-resource methods are tested. Choosing them with traceable, honest evidence helps prepare Artemis-era and
Mars exploration.

## Link to Project Demo

`[DEMO LINK]`: 30-second video (English subtitles if spoken in another language) or a deck of up to 7 slides in
English, on a public link with no login.

## Link to Final Project

`[FINAL PROJECT LINK]`: https://geoai-interplanetary.goskip.app.

> Note: this link qualifies only after the Skip closing update
> is published. That update removes the login requirement for analysis and makes English the default. Test the
> link in a private window before submitting.

## Detailed Project Description

### What it does

**1. Select.** The user picks a point and a radius on a 3D Moon or Mars globe, or chooses an example (Jezero,
Gale, Meridiani, Mare Imbrium, Apollo 17).

**2. Analyse.** The backend runs one analysis per request, live, on NASA's public archives. Nothing is
precomputed, and no synthetic value is ever shown as a measurement.

| Section | What it returns |
|---|---|
| Topography | Real laser shots (LOLA RDR / MOLA PEDR) within the circle: elevation statistics, regional and local slope, roughness and coverage |
| Mineralogy (screening) | Moon: M³ band depths at 1 µm and 2 µm. Mars: the CRISM team's summary parameters (olivine, pyroxene, Fe/Mg and Al clays, carbonate, sulfate, ferric oxide, hydration, H₂O/CO₂ ice). Each indicator passes a statistical detection test and a physical floor calibrated on real negative controls. |
| Earth analog sites | Documented terrestrial sites whose published geology explains the mineral families detected in the region, with coordinates and their precision, why the site is an analog, similarities, **differences**, limitations and DOI-verified references. Sites are ordered by the evidence they explain, without any similarity score or percentage. |
| Environment (lunar south pole) | Fraction of time sunlit, area in permanent shadow and Earth visibility, from the LOLA/PGDA illumination models (Mazarico et al., 2011). The section does not claim ice. |
| Moon–Earth geomorphology (experimental) | The lunar terrain (LOLA) and real Earth sites (Copernicus GLO-30) are profiled with the *same* method and scale. Correspondences are reported per exploration purpose: rover mobility, traverse planning and rugged-terrain operations. They are marked experimental and are never presented as recommendations. |
| Sources and provenance | Every value points to its product ID, observation dates and URL |
| PDF report | Downloadable report of the analysis |

**3. Explain honestly.**
- A missing measurement (no sunlight, permanent shadow, no coverage, a NASA service timeout) is reported as such.
  It is never reported as an absence of minerals.
- An inconclusive result produces no recommendation.

### How it works

| Layer | What it does |
|---|---|
| Backend (Python, FastAPI) | Range-reads only the needed bytes of NASA products: M³ and CRISM cubes, LOLA/MOLA through ODE GDS, and the polar illumination maps |
| Science modules | Compute the indicators, apply the detection tests, controls and masks, and match the evidence to the catalog |
| Jobs | Asynchronous jobs with per-step deadlines, so a slow NASA service affects only its own section |
| Caching | Results are cached, but a result affected by a provider failure is not reused |
| Frontend (Skip) | Renders the globes and analysis panels; English and Portuguese |

**Validation**, with expected outcomes written *before* the runs:
- 21 real-data scenarios, from Mars rover landing sites to lunar landing sites and the lunar south pole;
- adversarial tests that try to make the system reach wrong scientific conclusions;
- calibration on one set of real controls and validation on another, never used for calibration;
- 222 automated tests;
- every release was checked again in production against the previous version, value by value.

### Benefits
- **For mission planners, students and the public:** a transparent, explainable link between orbital data of a
  candidate site and real places on Earth where training, instrument testing or resource experiments can be done.
- **Honesty by design:** every analog shows where it **fails** (different chemistry, no space weathering, Earth's
  atmosphere, vegetation, mining). The platform declares its limits instead of inventing confidence.
- **Reproducible:** each result lists the exact NASA products used, so a scientist can verify it.

### What we hope to achieve

A trustworthy, open starting point for selecting analog sites for Artemis south-polar bases and Mars landing
sites. Next steps:
- a positive plagioclase criterion for lunar highlands;
- thermal (Diviner) and ice data at the poles;
- more terrestrial sites with precise, documented coordinates;
- discovering *new* candidate sites rather than only matching documented ones.

### Tools, languages and services
- **Backend:**
  - language and libraries: Python 3.12, FastAPI, Pydantic, HTTPX, NumPy, ReportLab;
  - storage and packaging: SQLite, Docker;
  - tests: pytest and respx.
- **Hosting:** Render (free plan).
- **Frontend:** built with the Skip AI app builder (React), PocketBase for optional saved history.
- **Data access:** NASA PDS (ODE REST/GDS, Imaging and Geosciences Nodes), NASA Trek WMTS, USGS STAC, AWS Open
  Data (Copernicus DEM).
- **Source code:** https://github.com/GeovannaLim/GEO.IA-PLANETARY-INTELLIGENCE-

## Use of Super Intelligence (SI)

Yes. SI tools were used as accelerators. The team chose the challenge, defined the scientific approach and the
acceptance criteria, and reviewed and approved every change and every deployment.

- **Code and data:**
  - The scientific backend, its tests and validation scripts were written with **Claude (Anthropic)**, a large
    language model, under the team's direction.
  - Claude also helped with literature and coordinate research. Every coordinate and reference used in the
    platform was quoted from an opened source, and DOIs were verified (Crossref/DataCite).
  - This use is acknowledged in the commit metadata (co-author line) and in the platform's "About & Data" page.
- **Frontend:** the web interface was generated with the **Skip AI app builder**, from prompts written by the
  team.
- **Results:** no scientific result is generated by an AI model. All values are computed at request time from the
  NASA and partner data listed below.
- **Images:** any SI-generated image used in the interface or demo must carry a visible "AI-generated" watermark,
  as the guide requires. See the checklist at the end of this document.
- **NASA branding:** no SI-generated content uses or modifies NASA logos, flags or mission identifiers.

## NASA Data

| Dataset / resource | How it is used |
|---|---|
| LRO **LOLA RDR** laser altimetry (PDS Geosciences Node, via ODE GDS) | Lunar topography; lunar terrain profiles for the geomorphology comparison |
| LOLA/PGDA **south polar illumination and permanent-shadow maps** (NASA GSFC, Mazarico et al., 2011) | Sunlit fraction, Earth visibility, permanent-shadow area; excluding M³ pixels in permanent shadow |
| Chandrayaan-1 **Moon Mineralogy Mapper (M³)** L2 reflectance + L1B location/observation backplanes (PDS Imaging Node, via ODE) | Lunar 1 µm and 2 µm band depths (pyroxene, olivine/glass screening) |
| MGS **MOLA PEDR** laser altimetry (via ODE GDS) | Mars topography |
| MRO **CRISM MTRDR** summary-parameter and I/F cubes (PDS Geosciences Node) | Mars mineral screening (olivine, pyroxene, phyllosilicates, carbonate, sulfate, ferric oxide, hydration, ice) |
| **ODE REST** product search (PDS Geosciences Node) | Finding M³ and CRISM observations that contain the point |
| **Moon Trek** and **Mars Trek** WMTS | Imagery layers listed with each analysis |
| **PDS Registry/API** (LOLA, Diviner discovery) | Data discovery listed in the sources |
| **EMIT** L2A surface reflectance (Earth) | Masked, rock-only measurement of the 1 µm and 2 µm band presence at terrestrial analog sites |
| **NASA Technical Reports (NTRS)** and NASA mission pages | Documentation of simulants and analog field tests (e.g. NU-LHT, PISCES) |

## Space Agency Partner Data and Other References

**Partner-agency data**
- **ESA / Copernicus DEM GLO-30** (Copernicus programme; AWS Open Data registry): terrestrial terrain profiles of
  the analog sites. They provide the Earth side of the geomorphology comparison.
- **ISRO Chandrayaan-1**: the mission that carried NASA's M³ instrument.
- **CORINE Land Cover 2012/2018** (Copernicus Land Monitoring, EEA) and **OpenStreetMap**: used only in the
  validation audit, to measure the mining footprint around the Río Tinto site.

**Other data and services**
- USGS Astrogeology STAC (data discovery);
- Google Earth Engine (EMIT access for the Earth endpoint and the site measurements);
- Crossref and DataCite (DOI verification).

**Software**
- Python, FastAPI, Pydantic, HTTPX, NumPy, ReportLab, SQLite, pytest, respx, Docker;
- Render (hosting), Skip (frontend builder), PocketBase (optional history).

**Scientific literature:** the full list is in [REFERENCES.md](REFERENCES.md). It covers the 32 DOI-verified
references of the analog catalog, the method references, and the validation sources.

**Images:** 3D globe textures and interface images. Confirm the source and license of each texture and of any
generated image before submitting (see the checklist).

---

## Checklist before "Submit for Judging" (from the guide)

| Item | What to do |
|---|---|
| Language | All fields above in English |
| Demo link | Public; video ≤ 30 s with English subtitles, or ≤ 7 slides in English. The slides must name the team, the members and the challenge. |
| Final project link | Opens in a **private browser window without login** |
| SI images | The interface currently loads an asset named `chatgpt-image-20-de-jul…png`. If it is AI-generated, it needs a visible "AI-generated" watermark, or it must be replaced. |
| NASA branding | No NASA logos or insignia in the app, slides or video |
| Minors | No images, video or voice of people under 18 |
| Team | All members confirmed at the same Local Event |
| Submission | Accept *Terms and Conditions* and *Confirm All Work is Original*, then **Submit for Judging** before **Sunday, November 15, 11:59 p.m.** (Local Event time) |
| Optional | FortiGuard Web Filter Classification request for the site URL |
