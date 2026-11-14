# 1. Overview, objective and contribution

**Challenge:** *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

## Summary

GEØ.IA is an interactive web platform that lets anyone select a region of the Moon or Mars on a 3D globe. It
returns, in about a minute, the documented places on Earth that best help study that region, and explains why.

For each selection, the backend reads open NASA data live:
- laser altimetry (LRO LOLA, MGS MOLA);
- orbital spectroscopy (Chandrayaan-1 M³, MRO CRISM);
- imagery (Moon and Mars Trek);
- for the lunar south pole, where candidate permanent bases are located, LOLA-derived illumination and
  permanent-shadow maps.

The platform turns these data into screening-level mineral evidence and matches it to a curated catalog of
terrestrial analog sites documented in the scientific literature. For each site it states what makes it a good
analog, where the analogy fails, and the exact data products used.

At the lunar south pole, where sunlight is too low for mineral spectroscopy, it adds:
- the modelled illumination and cold-trap context;
- an experimental terrain comparison with real Earth elevation data (Copernicus DEM).

## What it does

| Step | What happens |
|---|---|
| Select | The user picks a point and a radius on a 3D Moon or Mars globe, or chooses an example (Jezero, Gale, Meridiani, Mare Imbrium, Apollo 17) |
| Analyse | One analysis per request, live, on NASA's public archives. Nothing is precomputed, and no synthetic value is ever shown as a measurement. |
| Explain | A missing measurement (no sunlight, permanent shadow, no coverage, a NASA service timeout) is reported as such and never as an absence of minerals. An inconclusive result produces no recommendation. |

| Result section | What it returns |
|---|---|
| Topography | Real laser shots (LOLA RDR / MOLA PEDR) within the circle: elevation statistics, regional and local slope, roughness and coverage |
| Mineralogy (screening) | Moon: M³ band depths at 1 µm and 2 µm. Mars: the CRISM team's summary parameters (olivine, pyroxene, Fe/Mg and Al clays, carbonate, sulfate, ferric oxide, hydration, H₂O/CO₂ ice), each with a statistical detection test and a physical floor calibrated on real negative controls |
| Earth analog sites | Documented terrestrial sites whose published geology explains the detected mineral families: coordinates and their precision, why the site is an analog, similarities, **differences**, limitations and DOI-verified references. Ordered by the evidence they explain, without any score or percentage. |
| Environment (lunar south pole) | Fraction of time sunlit, area in permanent shadow and Earth visibility (LOLA/PGDA models, Mazarico et al., 2011). Does not claim ice. |
| Moon–Earth geomorphology (experimental) | Lunar (LOLA) and Earth (Copernicus GLO-30) terrain profiled with the *same* method and scale; correspondences per purpose (rover mobility, traverse planning, rugged-terrain operations), never presented as recommendations |
| Sources and PDF report | Every value points to its product ID, observation dates and URL; downloadable report |

## Objective and contribution

Analog sites are where astronauts train and where rovers, instruments and in-situ-resource methods are tested.
Choosing them with traceable, honest evidence helps prepare Artemis-era and Mars exploration.

- **For mission planners, students and the public:** a transparent, explainable link between orbital data of a
  candidate site and real places on Earth for training, instrument testing or resource experiments.
- **Honesty by design:** every analog shows where it **fails** (different chemistry, no space weathering, Earth's
  atmosphere, vegetation, mining). The platform declares its limits instead of inventing confidence.
- **Reproducible:** each result lists the exact NASA products used, so a scientist can verify it.

**Next steps:**
- a positive plagioclase criterion for lunar highlands;
- thermal (Diviner) and ice data at the poles;
- more terrestrial sites with precise, documented coordinates;
- discovering *new* candidate sites rather than only matching documented ones.

# 2. Architecture, technologies and data sources

```
User
 └─► Skip web app (3D globes, analysis panels, EN/PT)
      └─► GEØ.IA backend (FastAPI on Render)
           └─► NASA PDS / ODE / Trek / PGDA · USGS STAC · AWS Open Data
```

| Component | Role |
|---|---|
| Providers | HTTP clients with timeouts, retries, a host allow-list (protection against server-side request forgery), byte caps and per-host concurrency. They read only the bytes they need (HTTP Range) from multi-GB products. |
| Pipelines | One per body. Steps run concurrently and each is isolated: a failing provider fails only its own section, marked `failed` / `unavailable` with a reason code and a problem message. |
| Deadlines | Altimetry (ODE GDS) 150 s, M³ mineralogy 200 s, inside a 240 s job limit: a slow NASA service never discards the other completed sections |
| Cache | Results cached for 24 h, except results affected by a provider failure, which are recomputed |
| Languages | English and Brazilian Portuguese (`?lang=en` / `?lang=pt-BR`) |
| Coordinates | Planetocentric latitude, east-positive longitude; −180..180 or 0..360 accepted and converted per provider. Circles of `radius_km` (max. 25 km Moon, 50 km Mars). |

**Technologies.**
- Backend: Python 3.12, FastAPI, Pydantic v2, HTTPX, NumPy, ReportLab, SQLite, Docker.
- Tests: pytest, respx.
- Hosting: Render.
- Frontend: Skip AI app builder (React), PocketBase for optional saved history.

## NASA data

| Dataset / resource | How it is used |
|---|---|
| LRO **LOLA RDR** (PDS Geosciences Node, via ODE GDS) | Lunar topography; lunar terrain profiles |
| LOLA/PGDA **south polar illumination and permanent-shadow maps** (NASA GSFC, Mazarico et al., 2011) | Sunlit fraction, Earth visibility, permanent-shadow area; excluding M³ pixels in permanent shadow |
| Chandrayaan-1 **M³** L2 reflectance + L1B location/observation backplanes (PDS Imaging Node, via ODE) | Lunar 1 µm and 2 µm band depths |
| MGS **MOLA PEDR** (via ODE GDS) | Mars topography |
| MRO **CRISM MTRDR** summary-parameter and I/F cubes (PDS Geosciences Node) | Mars mineral screening |
| **ODE REST** product search | Finding M³ and CRISM observations that contain the point |
| **Moon Trek / Mars Trek** WMTS | Imagery layers |
| **PDS Registry/API** | Discovery of LOLA and Diviner products |
| **EMIT** L2A surface reflectance (Earth) | Masked, rock-only band presence at terrestrial analog sites |
| **NASA NTRS** and mission pages | Documentation of simulants and analog field tests (e.g. NU-LHT, PISCES) |

## Space agency partner data and other resources

| Resource | Use |
|---|---|
| ESA / Copernicus DEM GLO-30 (Copernicus programme; AWS Open Data) | Earth side of the geomorphology comparison |
| ISRO Chandrayaan-1 | Mission that carried NASA's M³ |
| USGS Astrogeology STAC | Data discovery |
| Google Earth Engine | EMIT access |
| CORINE Land Cover 2012/2018 (EEA) and OpenStreetMap (ODbL) | Validation audit only (Río Tinto mining footprint) |
| Crossref, DataCite | DOI verification of every catalog reference |

# 3. Methodology: Moon, Mars and terrestrial analogs

**Principles.**
- **Only traceable, real data:** no local copies of lunar data, fixed vectors or precomputed results are used as
  measurements, and synthetic data exists only inside the automated tests.
- **A missing measurement is not a result:** no sunlight, permanent shadow, no coverage, too few pixels or a
  service timeout each get an explicit reason code, and none becomes "no mineral" or an analog.
- **Screening, not identification:** spectral indicators detect a positive absorption, not a mineral or its
  abundance.
- **No artificial confidence:** analog sites are ordered by the evidence they explain, never by a percentage, and
  distances and z-scores are never turned into probabilities.
- **Calibrate on one set, validate on another:** expected test outcomes were written before the runs.

## Topography (LRO LOLA RDR; MGS MOLA PEDR)

| Quantity | How it is computed |
|---|---|
| Data | Individual valid laser shots via ODE GDS; image tiles are never used for numbers |
| Datum | LOLA: radius minus the 1737.4 km sphere. MOLA PEDR: radius minus the areoid. |
| Slope, roughness, coverage | Shots clipped to the circle in a local azimuthal-equidistant projection. Regional slope and aspect: least-squares plane. Local slope: gridded median surface, central differences. Roughness: RMS of residuals from the plane. Coverage: fraction of cells with data. |
| Large areas | If GDS refuses an area, the sampled radius is halved up to 3 times and reported as `sampled_radius_km` (typically 2.5–3 km near the lunar pole) |

## Mineral screening

**Moon (Chandrayaan-1 M³ L2).**
1. ODE finds the observations whose footprint contains the point.
2. The L1B location backplane locates the nearest pixel; a pixel more than max(1 km, 3 pixels) away is rejected.
3. A window of up to 41×41 pixels is read in one range request; pixels outside the circle, invalid values and
   wavelengths below 540 nm or above 2600 nm are masked.

Indicators: IBD1000, IBD2000 (after Mustard et al., 2011), 3-point band depths at 1 µm and 2 µm, R750, 750–1550 nm
slope.

| M³ quality control | Rule |
|---|---|
| Sunlight | Solar incidence ≥ 85°: surface unlit or at grazing light, no mineralogy |
| Spectrally suspect observation | IBD1000 median < −0.1 (convex 1 µm region, impossible for silicate rock): the next observation containing the point is used |
| Permanent shadow (lat ≤ −65°) | Each M³ pixel is located on the LOLA/PGDA permanent-shadow map. Pixels in permanent shadow are excluded (scattered light, not sunlight); with fewer than 4 remaining, mineralogy is unavailable. If the map cannot be read, nothing is assumed and the limitation says so. |
| Observation fallback | If the preferred observation cannot be read, the response names the skipped and the used observation |

**Mars (MRO CRISM MTRDR).**
- The CRISM team's summary parameters (Viviano-Beck et al., 2014) are read from the map-projected `SU` cube at the
  analytically computed pixel; the I/F cube provides the 3-point band depths.
- Polar observations use the ellipsoidal polar stereographic projection specified in the PDS catalog, checked
  against the label limits of 3 products (error 0.01–0.03°). The catalog's spherical fallback erred by 3–5 km and
  was rejected.
- The analysed window is about 1.1 × 1.1 km around the point, whatever the radius (stated in
  `mineralogy.analyzed_extent`).

**Detection test (both bodies).** An indicator is "detected" only if:
- the window mean is > 3 × the standard error (effective n = pixels/25, for spatial correlation);
- the median is > 0;
- at least 60% of the pixels are positive;
- on Mars, the median reaches a **physical floor** per parameter. The floors were calibrated on **26 dust-covered
  CRISM controls** and validated on **9 held-out dust controls** (0 false positives), then on 16 more outside
  Tharsis (15/16 clean).

| Specific rule | What it does |
|---|---|
| Olivine spatial coherence (Mars, provisional) | Olivine is "confident" only if ≥ 75% of the window pixels exceed the OLINDEX3 floor; otherwise it is **uncertain** and produces no analog. On 59 real controls (14 positive, 45 negative) this rule separated all of them, while OLINDEX3 × BDI1000IR coherence did not. Provisional because calibrated on the same controls. |
| Ice masking (Mars) | Under confirmed H₂O or CO₂ ice, olivine and sulfate signals that ice can mimic are shown as masked and generate no analogs |
| Broad versus specific evidence | Ferric oxide, ubiquitous in Martian dust, is **broad** evidence and never ties with a specific family |
| Absence is not a composition (Moon) | Lack of both mafic bands is reported as `inconclusive_evidence`; no site is chosen, because there is no positive plagioclase criterion |

## Terrestrial analog sites (the answer to the challenge)

**Catalog.** `app/data/terrestrial_analog_sites.json` holds 18 sites, 16 verified and offered (the unverified Lake Salda and Kunene stay in the file for transparency but are never offered). Each records:
- the coordinate quoted from a cited source, its declared precision and the coordinate source;
- the geology, key minerals and **analog basis** (published analog, official simulant source, regional analog,
  mineralogical reference, outreach);
- similarities, **differences**, limitations, and references with DOIs verified on Crossref/DataCite.

**Matching.** A site is offered when its documented geology explains at least one detected mineral family. The
order is: specific families explained, total families explained, documentary strength, agreement of the masked
EMIT band presence, coordinate precision. Ties share a rank and are announced; at most 5 sites; no score. Families
with no site (e.g. ice) are listed as unexplained. Mars without CRISM coverage (between ±60°) gets a clearly
labelled **global context** (the basaltic crust), never presented as region-specific.

| Body | Mineral family | Sites |
|---|---|---|
| Moon | pyroxene / mare basalt | Merriam Crater (JSC-1 simulant source), Kaʻū Desert, Timanfaya (outreach only) |
| Moon | olivine / volcanic glass | Craters of the Moon (NASA FINESSE), Merriam |
| Moon | norite | Stillwater (NU-LHT feedstock), Sudbury (Apollo 15–17 training) |
| Mars | olivine, serpentine, carbonate | Samail ophiolite BT1B, Twin Sisters dunite |
| Mars | sulfate, ferric oxide | Río Tinto, Kaʻū, Cuprite |
| Mars | hydrated silica / Al-OH | El Tatio, Kaʻū, Cuprite, Dresser |
| Mars | basalt, altered soil | Lonar, Kaʻū, Puʻu Nēnē (JSC Mars-1 source) |

The analogy is of mineral family, not of origin, abundance or formation conditions; terrestrial surfaces have
chemical weathering and no space weathering.

**Earth-side spectral check (NASA EMIT).** The only spectral attribute defined identically on the three bodies is
the **presence** of the 3-point bands at 1 µm and 2 µm.
- EMIT L2A scenes are composited per site, with masks for quality flags, vegetation (NDVI ≥ 0.2), snow
  (NDSI > 0.4) and water (NDWI > 0); scene IDs, dates, real wavelengths and rock-pixel fraction are recorded.
- Presence is compared only with ≥ 200 rock pixels covering ≥ 20% of the area; at 2 µm only presence, never depth
  (residual CO₂ and dry vegetation share that window).
- An earlier 2-band-depth ranking against an older 90-site EMIT library was retired: an audit showed the library
  measured vegetation and moisture more than Fe²⁺ (6 of 7 flood basalts had negative 1 µm depth), and the ranking
  could not separate sites beyond measurement repeatability.

# 4. Lunar south pole and experimental geomorphology

The candidate permanent bases are at the lunar south pole. There, sunlight is too low or absent for M³
mineralogy, so the original platform returned no analog at all. Two sections add evidence that is real at the
pole without pretending to measure minerals.

## Environment — illumination (latitude ≤ −65°)

- Fraction of time sunlit and fraction of time Earth is visible: statistics over the area and at the centre
  pixel, from the 18.6-year averaged illumination models (Mazarico et al., 2011). Permanent-shadow fraction from
  the permanent-shadow map.
- Labelled **model-derived** and independent of the analog ranking (analogs are identical with and without it).
- Flags potential cold traps but **does not measure ice**.

## Moon–Earth geomorphology (experimental)

**Profile.** One procedure for LOLA shots (Moon) and Copernicus GLO-30 pixels (Earth):
- samples projected to a local plane and aggregated on a grid of baseline L (60, 120, 240 or 480 m; the finest
  valid L is used);
- a **terrain unit** is 9 windows of 1 km (centre + 8 offset by 1 km); value = median over windows, uncertainty =
  standard deviation across them (spatial heterogeneity);
- each window needs ≥ 80% cell coverage, and ≥ 5 of 9 windows must be valid. Absolute elevation is never compared.

| Metric | Definition | Purposes using it |
|---|---|---|
| Median slope, slope p90, slope IQR | θ = atan(\|∇z\|), central differences over 2L | Rover mobility (median, p90); traverse (p90, IQR); rugged (IQR) |
| Roughness | RMS departure from local planarity | Rover mobility |
| Relief σ | RMS about the least-squares plane | Traverse; rugged |
| Relief amplitude | p95 − p5 | Rugged-terrain operations |

**Criterion.** A metric corresponds when z = \|Δ\| / √(s₁² + s₂²) ≤ 2, the comparison is **discriminating**
(combined uncertainty ≤ the spread of that metric across reference sites), and the **median slope** also
corresponds. The median-slope gate was added after a real-data audit: without it, a 16° crater wall (Haworth)
"matched" a 1° lava plain through heterogeneity alone. Results are reported as calculated, partial, inconclusive
or not comparable; mining-modified relief (Río Tinto) appears only as a modified-relief reference. The whole
section is flagged `experimental`: z ≤ 2 is an operational criterion, not a test of equivalence.

**Earth reference set.** 16 catalog sites measured with real Copernicus GLO-30 (every tile, URL and retrieval time
stored); 11 eligible (coordinate locates the studied unit within 2 km). Excluded for coordinate precision: Kaʻū,
Dresser, Timanfaya, Stillwater, Sittampundi. Catalog audit:
- **Craters of the Moon:** GPS sample coordinates found (Highway Flow, sample HF16001; Tolometti, 2021); now
  measured on that unit, with provenance in `measured_unit` and `catalog_reference_point`.
- **Río Tinto:** catalog point 50 m from the Peña de Hierro mine headframe, 85 m-deep open pit inside the central
  window (OpenStreetMap, CORINE, NASA MARTE project). Masking mapped mining features did not change the result,
  but unmapped spoil cannot be excluded: reclassified as mixed natural/mining relief.

**Lunar results (60 m, 9/9 windows).**

| Region | LOLA data | Result |
|---|---|---|
| Shackleton (interior) | 205,038 shots, 100% coverage | Median slope 12.1 ± 3.5°. Rover mobility: El Tatio, Cuprite, Merriam. Traverse and rugged: Cuprite. Río Tinto only as modified relief. |
| Mons Malapert | 113,543 shots | Median slope 11.0 ± 1.8°. Similar to Shackleton; El Tatio and Cuprite weak (Earth median slope 2–2.5× lower). |
| Haworth | 75,686 shots, 99.8% coverage | Median slope 15.8 ± 1.1°. Rover mobility: Merriam only. Traverse and rugged: **no demonstrable correspondence**. |
| Copernicus crater, Mare Imbrium | sparse off-polar coverage (54% / 62% at 480 m) | **Inconclusive**: no profile is invented |

Merriam (the JSC-1 simulant source) is the only documented lunar analog with a full correspondence. No catalog
site is a defensible terrain analog for Haworth's 11–16° walls; a directed search (Haughton, Mauna Kea,
Haleakalā, Dry Valleys) did not change this (Haughton: 3° median slope, rejected).

**Controls and discrimination (60 m; 3 decisions per pair).**

| Control | Correspondence rate |
|---|---|
| Same terrain shifted 1–3 km (window families overlap) | 61% |
| Same terrain shifted 4–6 km (no overlap) | 41% |
| Distinct Earth sites (not assumed false) | 23% |
| A-priori strong contrasts (alpine massif × plain or shield) | **0/45** |

- z ∈ {1, 1.5, 2, 2.5, 3} and k ∈ {1, 2} were evaluated as sensitivity analyses only, with no recalibration.
- Rejected alternatives: stricter thresholds (k = 2) and a robust spread estimate collapsed the self-match rate.
  Full slope-distribution distances (Wasserstein-1 and KS, window-permutation null), chosen on one half of the
  sites and evaluated on the other, did not discriminate better than the median slope (ranking 0.666 versus 0.649
  at 60 m) and cut true self-matches as much as false ones. The current method was kept.

# 5. Validation, controls and results of the 21 scenarios

| Kind of test | What it checks |
|---|---|
| Pre-registered scenarios | 21 places with known answers; expected outcome and pass criterion written **before** running |
| Adversarial tests | Deliberate attempts to reach a wrong conclusion: dust, no ice, no sunlight, bad observations, catalog order, ties, weak evidence, Moon/Mars mixing |
| Calibration and held-out validation | Every floor derived on one set of real controls and checked on another never used for calibration |
| Automated suite | **222 passed**, 3 skipped (live-NASA tests, 3/3 with normal service): science rules, ranking attacks, geomorphology on synthetic terrains, provider failures and timeouts, API contract, English/Portuguese |
| Production validation | After every deploy: the 21 scenarios, frontend integration, value-by-value comparison with the previous version |

**The 21 scenarios** — final run against production `8df1d61`, real data, no cache: **20 PASS + 1 INCONCLUSIVE**,
identical to the previous production version in values and provenance.

| # | Place | Expected (source) | Obtained | Verdict |
|---|---|---|---|---|
| M1 | Jezero crater, Mars | olivine + Fe/Mg clay (Ehlmann et al.; Mars 2020 site selection) | olivine, Fe/Mg phyllosilicate, ferric oxide | PASS |
| M2 | Jezero, repeated | identical values and product | identical | PASS |
| M3 | Jezero shifted 1 km | nearly identical | same families, 100% overlap | PASS |
| M4 | Nili Fossae trough | olivine / clays | olivine, Fe/Mg clay, carbonate | PASS |
| M5 | Mawrth Vallis (0–360° input) | clays | Fe/Mg clay | PASS |
| M6 | Mawrth Vallis (−180..180° input) | identical to M5 | identical (east 341.1°) | PASS |
| M7 | Curiosity landing site | −4501 m (Vasavada et al., 2014) | −4506 m | PASS |
| M8 | Olympus Mons (dust, negative control) | no hydrated minerals | no CRISM coverage: cannot be judged | INCONCLUSIVE |
| M9 | Mars point without CRISM | do not invent | "unavailable" + labelled global context | PASS |
| L1 | Chang'e-3 landing site, Moon | −2630/−2640 m; basalt (LROC) | −2628 m; pyroxene | PASS |
| L2 | Copernicus central peak | olivine (Isaacson et al., 2011) | olivine / volcanic glass | PASS |
| L3 | Mare Imbrium | pyroxene | pyroxene | PASS |
| L4 | Lunar south pole | do not measure in the dark | mineralogy unavailable, 0 sites; environment and geomorphology available | PASS |
| D1–D6 | Martian dust (6 held-out points) | nothing but ferric oxide | only ferric oxide | PASS |
| I1 | North residual cap (held out) | ice; mimicked minerals masked | ice; olivine/sulfate masked | PASS |
| I2 | South residual cap (held out) | ice; mimicked minerals masked | CO₂ ice; olivine/sulfate masked | PASS |

**Additional real-data controls.**

| Control | Result |
|---|---|
| CRISM dust, held out | 9/9 clean (0 false minerals) |
| Dust outside Tharsis (8 Elysium + 8 Arabia) | 15/16 clean; the exception led to the olivine coherence rule |
| Olivine study: 59 controls (4 literature, 10 regional positives, 45 negatives) + Aram Chaos | 60/60 as expected in production: 14 confident, Elysium uncertain, 44 negatives not detected |
| Sulfate positive control (Aram Chaos; Lichtenberg et al., 2010) | detected, with a small margin |
| Lunar permanent shadow (80°S 30.5°E) | 73/73 M³ pixels in permanent shadow excluded; 3 false anorthosite analogs eliminated; Copernicus (334 pixels) and Imbrium (1,681 pixels) unchanged |

**Adversarial tests of the analog ranking** (identical before and after the final release):
- A1: the catalog file order does not change the ranking (20 shuffled orders);
- A2: "neither has the band" never counts as similarity;
- A3: a Moon-only site is never offered for Mars, or vice versa;
- A4: dropping one family changes the top site only when strong detections are removed (14 findings documented);
- A5: broad evidence never outranks specific evidence.

**Release history.** Each release was compared with the previous production version before publication (rollback
target kept):

| Release | Main change | Tests | Check against previous version |
|---|---|---|---|
| `dc4e267` | First production deploy | — | production validation 27/27 |
| `abb10cb` | Calibrated CRISM floors, polar CRISM projection, adversarial fixes | 114 | 20 + 1; frontend integration 33/34 (rerun passed) |
| `46f3a88` | Olivine coherence rule, analysed CRISM extent | 182 | 20 + 1; olivine controls 60/60; integration 34/34 |
| `ed1ee18` | South polar illumination; permanent-shadow control of M³ | 198 | 21/21 identical to `46f3a88` |
| **`8df1d61`** | Experimental geomorphology; catalog audit; M³ timeout resilience | **222** | **21/21 identical to `ed1ee18`** (source IDs resolved to products); 20 + 1 on the first production run |

Final checks: 21/21 responses schema-valid, with no local paths, stack traces or credentials; Mars returns no
geomorphology section; experimental Earth candidates never appear in the API. The published web app was also
tested in a real browser: displayed values match the API, and a never-analysed polar point confirmed that the
radius shown is the radius analysed (5 km).

# 6. Problems identified, corrections and limitations

Each finding comes from a real-data test, an adversarial test or an audit; each fix was validated on real data
before deployment.

| # | Problem found | Real example | Fix |
|---|---|---|---|
| 1 | Clipping band depths to zero per pixel before averaging biased values and made queries incomparable with the library | All lunar and Martian queries | Clip once, after the mean; show unclipped values with an interpretation |
| 2 | The old EMIT library measured vegetation and moisture, not Fe²⁺; the 2-depth ranking could not discriminate | Basalt sites with negative 1 µm depth | Catalog matched by documented mineral family; EMIT only as rock-only band presence; old ranking removed |
| 3 | False minerals in dust: thousands of pixels made calibration noise "significant" | Olympus Mons dust "showed" olivine, Al clay, sulfate, ice | Physical floors on 26 dust controls; 9 held-out: 0 false positives |
| 4 | False ice near the equator | Jezero, Nili, Mawrth, Gale | Same calibration; real polar caps keep their ice (0.05–0.41) |
| 5 | Minerals "seen" through ice | Polar cap "sulfate" and "olivine" | Masked under confirmed ice, with an explanation |
| 6 | Measuring without sunlight | Lunar south pole: IBD1000 = −4.4 marked "available" | Incidence ≥ 85°: no mineralogy |
| 7 | A bad observation decided the result | Copernicus peak: one M³ observation "no band", another strong olivine | Convex-1 µm filter: Copernicus finds its documented olivine |
| 8 | Absence counted as similarity | "Neither has a 2 µm band" changed the 1st place at Mawrth | Only shared **presence** counts |
| 9 | Ties broken by meaningless details | File order deciding Samail versus Río Tinto | Shared rank plus a notice; ferric oxide as broad evidence |
| 10 | Mars above about 65° never had mineralogy | Polar caps | Ellipsoidal polar stereographic projection from the PDS catalog |
| 11 | Olivine false positive in Elysium dust (0.052 versus floor 0.05) | Elysium | Spatial-coherence rule (≥ 75% of pixels), provisional |
| 12 | Permanent shadow produced a false anorthosite analog | 80°S 30.5°E: 73/73 pixels in permanent shadow, yet 3 anorthosite sites offered | Per-pixel shadow control; absence of bands is inconclusive |
| 13 | South pole had no analog dimension at all | Shackleton, Haworth, Malapert | Illumination section and experimental geomorphology |
| 14 | Terrain "matches" between strongly contrasting terrains | Haworth (15.8°) versus Puʻu Nēnē (1.3°) | Median-slope gate |
| 15 | Mining-modified relief presented as a natural analog | Río Tinto | Modified-relief references |
| 16 | A slow NASA PDS lost whole lunar analyses (240 s timeout), even on the stable version | 73 PDS read timeouts on 2026-11-14; the stable `ed1ee18` code also timed out | 200 s M³ deadline: only mineralogy fails, as `provider_error` ("not evidence of absence"); degraded results not cached; affected scenarios rerun with the same criteria and passed. Measured per provider: M³ up to 249 range reads, single reads up to 67 s; CRISM < 2 s. |

## Known limitations (shown to users)

**Spectral indicators**
- Screening indicators, not identification or abundance.
- Floors come from real controls, not published thresholds; the olivine margin is small (dust up to 0.043 or
  0.052, documented olivine 0.063–0.071); the coherence rule is provisional.
- The CRISM window covers about 1 km² around the point whatever the radius; M³ pixels are about 140–280 m.
- No positive plagioclase criterion: lunar highlands with good data come out inconclusive and anorthosite sites
  are not offered. Apollo 17 gets no satisfactory identification; a systematic M³ effect over bright highlands is
  possible.
- Sulfate was detected at Aram Chaos only just above its floor.

**Lunar south pole:** illumination is model-derived; transient shadow at observation time is not detected; ice is
not measured.

**Analog catalog:** a curated catalog of documented sites; the platform does not discover new sites.

**Geomorphology:** experimental, with modest discrimination (41% same-terrain versus 23% distinct terrains);
Earth elevations are a surface model that includes vegetation and buildings; Copernicus crater and Mare Imbrium
are inconclusive.

**Earth side of every analogy:** gravity, vacuum, radiation, temperature and space weathering differ; each site
lists its own differences.

**Operations:** results depend on NASA services; when one is slow or down, the affected section says so.

# 7. References, transparency on AI use and links

## Use of Super Intelligence (SI)

SI tools were used as accelerators. The team chose the challenge, defined the scientific approach and the
acceptance criteria, and reviewed and approved every change and deployment.
- **Code and data:** the scientific backend, its tests and validation scripts were written with **Claude
  (Anthropic)**, a large language model, under the team's direction. Claude also helped with literature and
  coordinate research; every coordinate and reference used was quoted from an opened source, and DOIs were
  verified. Acknowledged in the commit metadata (co-author line) and in the platform's "About & Data" page.
- **Frontend:** generated with the **Skip AI app builder**, from prompts written by the team.
- **Results:** no scientific result is generated by an AI model; all values are computed at request time from the
  NASA and partner data listed in Section 2.
- **NASA branding:** no SI-generated content uses or modifies NASA logos, flags or mission identifiers.

## Links

| Resource | Link |
|---|---|
| Platform | https://geoai-interplanetary.goskip.app |
| Scientific API (OpenAPI at `/docs`) | https://geoia-planetary-backend.onrender.com |
| Source code (backend) | https://github.com/GeovannaLim/GEO.IA-PLANETARY-INTELLIGENCE- |
| ODE (LOLA, MOLA, M³, CRISM search) | https://ode.rsl.wustl.edu/ |
| Moon Trek / Mars Trek | https://trek.nasa.gov/ |
| Copernicus DEM GLO-30 (AWS) | https://copernicus-dem-30m.s3.amazonaws.com/ |

:::small

## Method references

- Mustard J.F. et al. (2011) JGR 116, E00G12 (definition of the M³ integrated band depths IBD1000/IBD2000).
- Viviano-Beck C.E. et al. (2014) Revised CRISM spectral parameters and summary products based on the currently detected mineral diversity on Mars. JGR Planets 119, 1403-1431. https://doi.org/10.1002/2014JE004627
- Mazarico E., Neumann G.A., Smith D.E., Zuber M.T., Torrence M.H. (2011) Illumination conditions of the lunar polar regions using LOLA topography. Icarus 211, 1066-1081. https://doi.org/10.1016/j.icarus.2010.10.030
- Bandfield J.L. et al. (2000) A global view of Martian surface compositions from MGS-TES. Science 287, 1626. https://doi.org/10.1126/science.287.5458.1626
- Hall D.K. et al. (1995) Remote Sensing of Environment 54 (NDSI snow index). McFeeters S.K. (1996) International Journal of Remote Sensing 17 (NDWI water index).
- PDS catalog for the CRISM map projection: https://pds-geosciences.wustl.edu/mro/mro-m-crism-5-rdr-mptargeted-v1/mrocr_4001/catalog/mtr_map.cat

## Validation references

- Jezero olivine and clays (Mars 2020 site selection): https://authors.library.caltech.edu/87552
- Nili Fossae and Mawrth Vallis: https://meetingorganizer.copernicus.org/EPSC2018/EPSC2018-578.pdf
- Curiosity landing elevation: Vasavada et al. (2014), https://deepblue.lib.umich.edu/bitstream/2027.42/108017/1/jgre20266.pdf
- Chang'e-3 landing site: https://www.lroc.asu.edu/images/751 · https://www.lroc.asu.edu/images/811
- Copernicus central-peak olivine: Isaacson et al. (2011), https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2010JE003731
- Aram Chaos sulfates: Lichtenberg et al. (2010) JGR Planets, https://doi.org/10.1029/2009JE003353 · Dust regions: Putzig et al. (2005) Icarus 173
- Nili Fossae olivine ridges (FRT00003E12): https://essopenarchive.org/doi/full/10.22541/essoar.176235473.32635438/v4 · Regional olivine unit: https://www.sciencedirect.com/science/article/abs/pii/S0019103518306031
- Craters of the Moon sample coordinates: Tolometti G. (2021) The Physical Properties of Volcanic and Impact Melt. PhD thesis, Western University, Table 2.2, https://uwo.scholaris.ca/bitstreams/8a90b505-fda3-46d6-8f08-16ae2d73feaf/download
- Haughton crater centre: Patterson & Ernst (2020) Meteoritics & Planetary Science, https://doi.org/10.1111/maps.13573 · Mauna Kea PISCES 2010 field test: Klingelhöfer et al., NASA NTRS 20140008708
- Río Tinto (Peña de Hierro) and the MARTE project: https://astrobiology.nasa.gov/news/drilling-for-weird-life/ · OpenStreetMap way 208910493; CORINE Land Cover class 131 (EEA)

## Terrestrial analog catalog references (DOIs verified on Crossref/DataCite, 2026-11-06)

@@CATALOG_REFS@@
