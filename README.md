# GEØ.IA Planetary Intelligence — scientific backend

**NASA Space Apps Challenge 2026** · Challenge: *Identify Earth Locations that Analog the Permanent Moon Base
Locations and Mars*

GEØ.IA lets anyone select a region of the Moon or Mars on a 3D globe. It returns the documented places on Earth
that best help study that region, explains why, and states where the analogy fails. This repository is the
scientific backend: a FastAPI service that reads open NASA data live, computes screening-level mineral evidence,
lunar south-polar illumination and an experimental terrain comparison, and matches the evidence to a curated catalog
of terrestrial analog sites.

| | |
|---|---|
| Live platform | https://geoai-interplanetary.goskip.app |
| Scientific API | https://geoia-planetary-backend.onrender.com (OpenAPI at `/docs`) |
| Project documentation (PDF, 14 pages) | [docs/submission/GEOIA_NASA_Space_Apps_2026_Documentation.pdf](docs/submission/GEOIA_NASA_Space_Apps_2026_Documentation.pdf) |
| Scientific documentation | [docs/submission/SCIENTIFIC_DOCUMENTATION.md](docs/submission/SCIENTIFIC_DOCUMENTATION.md) |
| Validation and tests | [docs/submission/VALIDATION_AND_TESTS.md](docs/submission/VALIDATION_AND_TESTS.md) |
| Data, resources and references | [docs/submission/REFERENCES.md](docs/submission/REFERENCES.md) |

## Use of AI (Super Intelligence)

This project was developed with the assistance of generative AI tools, under the team's direction:

- **Backend code, tests, validation scripts and documentation drafts:** written with **Claude (Anthropic)**. The
  team chose the challenge, defined the scientific approach and acceptance criteria, and reviewed and approved
  every change and deployment. Every commit carries a `Co-Authored-By: Claude` line in its metadata.
- **Literature and coordinate research:** assisted by Claude. Every coordinate and reference used was quoted from
  an opened source, and DOIs were verified on Crossref/DataCite.
- **Web interface:** generated with the **Skip AI app builder**, from prompts written by the team.
- **Results:** no scientific result is produced by an AI model. Every value is computed at request time from the
  NASA and partner data listed below.

## What the API returns

`POST /v1/{lunar,mars}/analyze` with `{"latitude", "longitude", "radius_km"}` returns:

| Section | Content |
|---|---|
| `topography` | LRO LOLA RDR / MGS MOLA PEDR laser shots: elevation statistics, slopes, roughness, coverage |
| `mineralogy` | Moon: Chandrayaan-1 M³ band depths. Mars: MRO CRISM summary parameters. Each indicator has a statistical detection test, and on Mars a physical floor calibrated on real negative controls. Screening, not identification. |
| `terrestrial_analogs` | Documented Earth analog sites whose published geology explains the detected mineral families, with coordinates, similarities, **differences**, limitations and DOI-verified references. No similarity score. |
| `environment` | Lunar south pole: sunlit fraction, permanent-shadow area and Earth visibility (LOLA/PGDA models) |
| `geomorphology` | Lunar south pole, **experimental**: LOLA and Copernicus GLO-30 terrain profiled with the same method; correspondences per exploration purpose, never presented as recommendations |
| `data_sources`, `problems` | Product IDs, observation dates and URLs of every value; explicit reasons for every unavailable section |

A missing measurement (no sunlight, permanent shadow, no coverage, a NASA service timeout) is reported with a
reason code and is never turned into "no mineral" or into an analog. Other endpoints: `GET /v1/jobs/{id}`,
`GET /v1/reports/{id}` (`?format=pdf`), `GET /v1/planetary/datasets`, `GET /health`. Prose fields are available in
English and Portuguese (`?lang=en` / `?lang=pt-BR`).

## Data sources

| Body | Topography | Spectroscopy | Other |
|---|---|---|---|
| Moon | LRO LOLA RDR (ODE GDS) | Chandrayaan-1 M³ L2 (PDS Imaging Node, HTTP range reads) | LOLA/PGDA south polar illumination and permanent-shadow maps; Moon Trek WMTS |
| Mars | MGS MOLA PEDR (ODE GDS) | MRO CRISM MTRDR (PDS Geosciences Node) | Mars Trek WMTS |
| Earth | Copernicus DEM GLO-30 (ESA, AWS Open Data) | NASA EMIT L2A (Google Earth Engine) | USGS Astrogeology STAC |

Full list, with how each source is used: [docs/submission/REFERENCES.md](docs/submission/REFERENCES.md).

## Repository layout

```
app/
  main.py, config.py   FastAPI app, configuration (GEOIA_* environment variables)
  api/                 endpoints
  schemas/             single response contract for Moon/Mars/Earth (status + reason per section)
  providers/           HTTP clients: ODE REST/GDS, Trek, PDS, USGS STAC, M³, CRISM, LOLA illumination,
                       Copernicus DEM, Earth Engine
  pipelines/           orchestration per body, with per-step deadlines
  science/             coordinates, topography, spectral indicators, analog matching, geomorphology
  services/            async jobs, SQLite store, PDF reports, cache
  data/                curated analog catalog, Earth terrain profiles, EMIT reference library (with provenance)
scripts/               reproducible validation: 21 pre-registered scenarios, adversarial tests, controls
tests/                 unit and integration tests (synthetic data only here), live tests (opt-in)
docs/submission/       English project documentation for the NASA Space Apps submission
docs/                  the team's internal working reports for each development phase (in Portuguese)
```

## Run locally

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
.venv/bin/python -m pytest -q                                 # 222 offline tests (synthetic fakes only in tests/)
GEOIA_LIVE_TESTS=1 .venv/bin/python -m pytest -m live -q      # live calls to NASA services
PYTHONPATH=. .venv/bin/python scripts/science_tests.py https://geoia-planetary-backend.onrender.com   # 21 scenarios
```

A test guarantees that the `app` package never imports the test fakes. Validation results for every release are
summarised in [docs/submission/VALIDATION_AND_TESTS.md](docs/submission/VALIDATION_AND_TESTS.md).

## Deployment

Docker and a Render blueprint (`render.yaml`, free plan). Secrets live only in the Render dashboard or in a local
`.env` (never committed, never logged, never returned by the API). See [docs/DEPLOY.md](docs/DEPLOY.md).

## Main limitations

- Spectral indicators are screening parameters, not mineral identifications or abundances.
- Analog sites come from a curated catalog of documented sites; the platform does not discover new sites.
- The geomorphology comparison is experimental and its discrimination is modest.
- Lunar illumination is model-derived; ice is not measured.
- Results depend on the availability of NASA services; when one fails, the affected section says so.

The complete list is in the scientific documentation. The Portuguese version of this README is
[README.pt-BR.md](README.pt-BR.md).
