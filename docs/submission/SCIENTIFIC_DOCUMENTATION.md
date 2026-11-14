# GEØ.IA Planetary Intelligence — scientific documentation

**NASA Space Apps Challenge 2026.** Challenge: *Identify Earth Locations that Analog the Permanent Moon Base
Locations and Mars*. Production backend: commit `8df1d61` (https://geoia-planetary-backend.onrender.com).

This document describes **what the platform measures, how, why, and where it stops being reliable**. It also
records the scientific process: the problems found and how each was solved. The tests and their results are in
[VALIDATION_AND_TESTS.md](VALIDATION_AND_TESTS.md); the references are in [REFERENCES.md](REFERENCES.md).

> **SI disclosure.** The backend code, tests and validation scripts were written with Claude (Anthropic) under the
> team's direction and review. No result shown by the platform is produced by an AI model: every value is computed
> at request time from the data sources below.

---

## 1. Principles that guided every decision

1. **Only traceable, real data.**
   - Every value points to its source product, observation dates and URL.
   - No local copies of lunar data, no fixed vectors and no precomputed results are used as measurements.
   - Synthetic data exists only inside the automated tests.
2. **A missing measurement is not a result.**
   - No sunlight, permanent shadow, no coverage, too few pixels or a NASA service timeout are each reported
     explicitly, with a reason code.
   - None of them is ever converted into "no mineral" or into an analog.
3. **Screening, not identification.** Spectral indicators detect a positive absorption. They do not identify a
   mineral or measure its abundance, and the platform says so.
4. **No artificial confidence.**
   - Analog sites are ordered by the evidence they explain, never by a similarity percentage.
   - Distances and z-scores are never turned into probabilities.
5. **Calibrate on one set, validate on another.**
   - Every numerical floor was derived from one group of real controls and checked on a group never used for
     calibration.
   - Expected test outcomes were written before the runs.
6. **Declare the limits.** Each section carries its limitations, and every analog site lists where the analogy
   **fails**.

## 2. Architecture

```
User ─► Skip web app (3D globes, panels, EN/PT) ─► GEØ.IA backend (FastAPI on Render) ─► NASA PDS / ODE / Trek / PGDA,
                                                                                         USGS STAC, AWS Open Data
```

| Component | Role |
|---|---|
| **Providers** | HTTP clients with:<br>• timeouts and retries;<br>• a host allow-list (protection against server-side request forgery);<br>• byte caps and per-host concurrency.<br>They read only the bytes they need (HTTP Range) from multi-GB products. |
| **Pipelines** | One per body (Moon, Mars, Earth). Steps run concurrently and each is isolated: a failing provider fails only its own section, which is marked `failed` / `unavailable` with a reason and a problem message. |
| **Deadlines** | Altimetry (ODE GDS) has a 150 s budget and M³ mineralogy a 200 s budget, inside a 240 s job limit. A slow NASA service therefore never discards the other completed sections. |
| **Cache** | Results are cached for 24 h, except results affected by a provider failure, which are recomputed on the next request. |
| **Languages** | English and Brazilian Portuguese (`?lang=en` / `?lang=pt-BR`). |

**Coordinate conventions**
- Latitude is planetocentric and longitude is east-positive.
- The API accepts −180..180 or 0..360 and converts to each provider's convention.
- Regions are circles of `radius_km`, with a maximum of 25 km on the Moon and 50 km on Mars.

## 3. Topography (Moon: LRO LOLA RDR; Mars: MGS MOLA PEDR)

**Data.** Individual valid laser shots retrieved through ODE GDS. Image tiles are never used for numbers.

| Quantity | How it is computed |
|---|---|
| Datum | LOLA: radius minus the 1737.4 km sphere. MOLA PEDR: radius minus the areoid. |
| Geometry | Shots are clipped to the circle in a local azimuthal-equidistant projection |
| Regional slope and aspect | Least-squares plane |
| Local slope | Gridded median surface, central differences |
| Roughness | RMS of residuals from the plane |
| Coverage | Fraction of grid cells that contain data |

If GDS refuses an area, the sampled radius is halved up to 3 times. This is reported as `sampled_radius_km`; near
the lunar pole it is typically 2.5–3 km.

## 4. Mineral screening

### 4.1 Moon — Chandrayaan-1 M³ L2

**Steps**
1. ODE finds the M³ observations whose footprint contains the point.
2. The L1B location backplane locates the nearest pixel. A pixel more than max(1 km, 3 pixels) away is rejected.
3. A window of up to 41×41 pixels is read in a single range request.
4. Pixels outside the circle are masked, and so are invalid values and wavelengths below 540 nm or above 2600 nm.

**Indicators:** IBD1000, IBD2000 (after Mustard et al., 2011), 3-point band depths at 1 µm and 2 µm, R750 and the
750–1550 nm slope.

**Quality controls**, each added after it was shown to be necessary (Section 8):

| Control | Rule |
|---|---|
| Sunlight | Solar incidence ≥ 85° means the surface is unlit or at grazing light: no mineralogy. |
| Spectrally suspect observation | An IBD1000 median < −0.1 (a convex 1 µm region, impossible for silicate rock) marks the observation as suspect, and the next observation containing the point is used. |
| Permanent shadow (lat ≤ −65°) | Each valid M³ pixel is located on the LOLA/PGDA permanent-shadow map (Mazarico et al., 2011). Pixels in permanent shadow are excluded: their reflectance is scattered light, not direct sunlight. With fewer than 4 remaining pixels, mineralogy is unavailable. If the shadow map cannot be read, nothing is assumed and the limitation says so. |
| Observation fallback | If the preferred observation cannot be read, the response states which one was skipped and why, and which one was used |

### 4.2 Mars — MRO CRISM MTRDR

- The platform uses the CRISM team's summary parameters (Viviano-Beck et al., 2014), read from the map-projected
  `SU` cube at the analytically computed pixel.
- The I/F cube provides the 3-point band depths.
- Polar observations use the ellipsoidal polar stereographic projection specified in the PDS catalog. It was
  implemented and checked against the label limits of 3 products (error 0.01–0.03°). The catalog's spherical
  fallback equations erred by 3–5 km and were rejected.
- The analysed window is about 1.1 × 1.1 km around the point, whatever the requested radius. This is stated in
  `mineralogy.analyzed_extent`.

### 4.3 Detection test (both bodies)

An indicator is "detected" only if all of the following hold:
- the window mean is > 3 × the standard error, with an effective n of pixels/25 to account for spatial
  correlation;
- the median is > 0;
- at least 60% of the pixels are positive;
- on Mars, the window median reaches a **physical floor** per parameter.

**How the floors were set**
- They were calibrated on **26 dust-covered CRISM controls**, where no hydrated or mafic mineral is expected.
- They were validated on **9 held-out dust controls** (0 false positives) and later on 16 more outside Tharsis
  (Elysium and Arabia), with 15/16 clean.
- The single exception, an Elysium olivine at 0.052, led to the spatial-coherence rule in Section 4.4.

### 4.4 Specific rules

| Rule | What it does |
|---|---|
| Olivine spatial coherence (Mars, provisional) | Olivine is "confident" only if at least 75% of the window pixels exceed the OLINDEX3 floor. Otherwise it is shown as **uncertain** and produces no analog. Study on 59 real controls (14 positive, 45 negative): this rule separated all of them, while OLINDEX3 × BDI1000IR coherence did not. It is declared provisional because it was calibrated on the same controls. |
| Ice masking (Mars) | When H₂O or CO₂ ice is confirmed, olivine and sulfate signals that ice bands can mimic are shown as masked and generate no analogs |
| Broad versus specific evidence | Ferric oxide, ubiquitous in Martian dust, counts as **broad** evidence and never ties with a specific mineral family |
| Absence is not a composition (Moon) | The lack of both mafic bands no longer implies anorthosite. It is reported as `inconclusive_evidence` and no site is chosen, because there is no positive plagioclase criterion. |

## 5. Terrestrial analog sites (the answer to the challenge)

**Catalog**
- `app/data/terrestrial_analog_sites.json` holds 18 sites, of which 16 are verified and offered.
- Each site records:
  - the coordinate quoted from a cited source, its declared precision and the coordinate source;
  - the geology, the key minerals and the **analog basis**, i.e. the strength of the documented link (published
    analog, official simulant source, regional analog, mineralogical reference, outreach);
  - similarities, **differences** and limitations;
  - references, with DOIs verified on Crossref/DataCite.
- Unverified sites (Lake Salda, Kunene) stay in the file for transparency but are never offered.

**Matching**
- A site is offered when its documented geology explains at least one mineral family detected in the region.
- The order follows, in this priority:
  1. specific families explained;
  2. total families explained;
  3. documentary strength;
  4. agreement of the masked EMIT rock-only band presence (Section 6);
  5. coordinate precision.
- Ties share a rank and are announced. There is no score, and at most 5 sites are offered.
- Families with no site in the catalog (for example ice) are listed as unexplained, never filled in.
- Mars without CRISM coverage (between ±60°) receives a clearly labelled **global context** (the basaltic crust),
  never presented as region-specific.

| Body | Mineral family | Sites |
|---|---|---|
| Moon | pyroxene / mare basalt | Merriam Crater (JSC-1 simulant source), Kaʻū Desert, Timanfaya (outreach only) |
| Moon | olivine / volcanic glass | Craters of the Moon (NASA FINESSE), Merriam |
| Moon | norite | Stillwater (NU-LHT feedstock), Sudbury (Apollo 15–17 training) |
| Mars | olivine, serpentine, carbonate | Samail ophiolite BT1B, Twin Sisters dunite |
| Mars | sulfate, ferric oxide | Río Tinto, Kaʻū, Cuprite |
| Mars | hydrated silica / Al-OH | El Tatio, Kaʻū, Cuprite, Dresser |
| Mars | basalt, altered soil | Lonar, Kaʻū, Puʻu Nēnē (JSC Mars-1 source) |

**What the analogy means.** It is an analogy of mineral family, not of origin, abundance or formation conditions.
Every result recalls that terrestrial surfaces have chemical weathering and no space weathering, and that their
spectra are not expected to match in band strength.

## 6. Earth-side spectral check (NASA EMIT)

The only spectral attribute defined identically on the three bodies is the **presence** of the 3-point bands at
1 µm and 2 µm.

**Measurement at each site**
- EMIT L2A scenes are composited per site.
- Masks remove bad pixels (EMIT quality flags), vegetation (NDVI ≥ 0.2), snow (NDSI > 0.4) and water (NDWI > 0).
- Provenance is recorded: scene IDs, dates, real wavelengths and rock-pixel fraction.

**Use in the comparison**
- Presence is compared only when the site has at least 200 rock pixels covering at least 20% of the area.
- At 2 µm only presence is compared, never depth, because residual atmospheric CO₂ and dry vegetation share that
  window.

**Lesson from the process.** An earlier ranking compared two band depths against an older 90-site EMIT library
and returned similarity scores. An audit found that this library measured vegetation and moisture more than Fe²⁺
(6 of 7 flood basalts had negative 1 µm depth). The ranking also could not separate sites beyond the measurement
repeatability. That ranking is no longer shown anywhere in the interface.

## 7. Lunar south pole: environment and terrain

**Why this section exists.** The candidate permanent bases are at the lunar south pole. There, sunlight is too low
or absent for M³ mineralogy, so the original platform returned no analog at all. The following two sections add
evidence that is real at the pole, without pretending to measure minerals.

### 7.1 Environment — illumination (LOLA/PGDA, latitude ≤ −65°)

| Quantity | Source |
|---|---|
| Fraction of time sunlit and fraction of time Earth is visible | Statistics over the area plus the centre pixel, from the 18.6-year averaged illumination models (Mazarico et al., 2011) |
| Permanent-shadow fraction | Permanent-shadow map, read with byte-range requests |

- The section is labelled **model-derived** and is independent of the analog ranking: a test shows that analogs
  are identical with and without it.
- It flags potential cold traps but **does not measure ice**.

### 7.2 Moon–Earth geomorphology (experimental)

**Goal.** Compare the lunar terrain with Earth terrain for operational purposes, with *one* method for both
bodies.

**Profile.** The same procedure is applied to LOLA shots on the Moon and to Copernicus GLO-30 pixels on Earth.
- Samples are projected to a local plane and aggregated on a grid of horizontal baseline L (60, 120, 240 or 480 m;
  the finest valid L is used).
- A **terrain unit** is described by 9 windows of 1 km: the centre plus 8 windows offset by 1 km.
- Each metric's value is the median over the windows, and its uncertainty is the standard deviation across them,
  i.e. the spatial heterogeneity.
- A window needs at least 80% cell coverage, and at least 5 of the 9 windows must be valid.

**Metrics**

| Metric | Definition |
|---|---|
| Median slope, slope p90, slope IQR | Slope θ = atan(\|∇z\|), from central differences over 2L |
| Roughness | RMS departure from local planarity |
| Relief σ | RMS about the least-squares plane |
| Relief amplitude | p95 − p5 |

Absolute elevation is never compared.

**Comparison by purpose**

| Purpose | Metrics compared |
|---|---|
| Rover mobility | median slope, slope p90, roughness |
| Traverse planning | slope p90, slope IQR, relief σ |
| Rugged-terrain operations | relief amplitude, relief σ, slope IQR |

**Correspondence criterion.** A metric corresponds when all of the following hold:
- z = \|Δ\| / √(s₁² + s₂²) ≤ 2;
- the comparison is **discriminating**: the combined uncertainty must not exceed the spread of that metric across
  the reference sites;
- the **median slope** also corresponds (median-slope gate).

The median-slope gate was added after a real-data audit. Without it, a 16° crater wall (Haworth) "matched" a 1°
lava plain because of heterogeneity alone. The gate can only remove correspondences.

**How results are reported**
- Correspondences are reported as **calculated correspondences**, kept separate from partial ones, inconclusive
  ones and sites without precise coordinates.
- Sites whose relief is documented as mining-modified (Río Tinto) are listed only as **modified-relief
  references**.
- The whole section is flagged `experimental`. z ≤ 2 is an operational criterion, not a test of equivalence.

**Earth reference set**
- 16 catalog sites were measured with real Copernicus GLO-30 data; every DEM tile, URL and retrieval time is
  stored.
- 11 sites are eligible for comparison: their coordinate locates the studied unit to within 2 km.
- Excluded for coordinate precision: Kaʻū, Dresser, Timanfaya, Stillwater and Sittampundi.

**Phase 3A improvements**
- A literature audit found GPS sample coordinates for **Craters of the Moon**: Highway Flow, sample HF16001
  (Tolometti, 2021). The site is now measured on that documented unit, and the provenance is kept in
  `measured_unit` and `catalog_reference_point`.
- A **Río Tinto** audit (OpenStreetMap, CORINE Land Cover, NASA MARTE project) found the catalog point 50 m from
  the Peña de Hierro mine headframe, with an 85 m-deep open pit inside the central window. Masking the mapped
  mining features did not change the result, but unmapped spoil cannot be excluded. The site was therefore
  reclassified as mixed natural/mining relief.

**Tested alternative, not adopted.** Comparing the full slope distribution (Wasserstein-1 and KS distances with a
window-permutation null) was evaluated. It did not discriminate better than the median slope (ranking 0.666
versus 0.649 at 60 m). It also cut true self-matches as much as false ones. The current method was kept.

## 8. The scientific process: problems found and how each was solved

Each finding comes from a real-data test, an adversarial test or an audit. The fix was validated on real data
before any deployment.

| # | Problem found | Real example | Fix |
|---|---|---|---|
| 1 | Clipping band depths to zero per pixel before averaging biased values upward and made queries incomparable with the library | All lunar and Martian queries | Clip once, after the mean, as the library does; show unclipped values with an interpretation |
| 2 | The old EMIT library measured vegetation and moisture, not Fe²⁺; the 2-depth ranking could not discriminate | Basalt sites with negative 1 µm depth | New catalog matched by documented mineral family; EMIT used only as masked, rock-only band presence; old ranking removed from the interface |
| 3 | False minerals in dust: thousands of pixels made tiny calibration noise "significant" | Olympus Mons dust "showed" olivine, Al clay, sulfate and ice | Physical floors calibrated on 26 dust controls; 9 held-out controls: 0 false positives |
| 4 | False ice near the equator | Jezero, Nili, Mawrth, Gale | Same calibration; the real polar caps keep their ice (0.05–0.41) |
| 5 | Minerals "seen" through ice | Polar cap "sulfate" and "olivine" | Masked under confirmed ice, with an explanation |
| 6 | Measuring without sunlight | Lunar south pole: IBD1000 = −4.4 marked "available" | Incidence ≥ 85° means no mineralogy |
| 7 | A bad observation decided the result | Copernicus peak: one M³ observation "no band", another strong olivine | Convex-1 µm filter: Copernicus now finds its documented olivine (Isaacson et al., 2011) |
| 8 | Absence counted as similarity | "Neither has a 2 µm band" changed the 1st place at Mawrth | Only shared **presence** counts |
| 9 | Ties broken by meaningless details | File order or coordinate precision deciding Samail versus Río Tinto | Shared rank plus a notice; ferric oxide treated as broad evidence |
| 10 | Mars above about 65° never had mineralogy (polar projection unsupported) | Polar caps | Ellipsoidal polar stereographic projection from the PDS catalog |
| 11 | Olivine false positive in Elysium dust (0.052 versus floor 0.05) | Elysium | Spatial-coherence rule (≥ 75% of pixels), provisional |
| 12 | Permanent shadow produced a false anorthosite analog | 80°S 30.5°E: 73/73 M³ pixels in permanent shadow, yet Shawmere, Sittampundi and Stillwater were offered | Shadow control per pixel; absence of bands is inconclusive, never anorthosite |
| 13 | South pole had no analog dimension at all | Shackleton, Haworth, Malapert | Illumination section and experimental geomorphology section |
| 14 | Terrain "matches" between strongly contrasting terrains | Haworth (15.8°) versus Puʻu Nēnē (1.3°) | Median-slope gate |
| 15 | Mining-modified relief presented as a natural analog | Río Tinto | Modified-relief references |
| 16 | A slow NASA PDS lost whole lunar analyses (240 s timeout), even on the stable version | 73 PDS timeouts during validation | 200 s M³ deadline: only mineralogy fails, as `provider_error`, "not evidence of absence"; degraded results are not cached |

## 9. Known limitations (shown to users)

**Spectral indicators**
- They are screening indicators, not identification or abundance.
- The floors come from real controls, not from published thresholds, and the olivine margin is small (dust up to
  0.043 or 0.052, documented olivine 0.063–0.071).
- The CRISM window covers about 1 km² around the point, whatever the radius. M³ pixels are about 140–280 m.
- There is no positive plagioclase criterion, so lunar highlands with good data come out inconclusive, and
  anorthosite sites are not offered.
- Apollo 17 gets no satisfactory identification. A systematic M³ effect over bright highlands is possible.
- Sulfate was detected at Aram Chaos only just above its floor.

**Lunar south pole**
- Illumination is model-derived, and transient shadow at observation time is not detected.
- Ice is not measured.

**Analog catalog**
- It is a curated catalog of documented sites. The platform does not discover new sites.

**Geomorphology**
- It is experimental. Discrimination is modest: the same terrain 4–6 km away corresponds in 41% of cases, against
  23% for distinct terrains and 0/45 for strong contrasts.
- Earth elevations are a surface model that includes vegetation and buildings.
- Copernicus crater and Mare Imbrium are inconclusive because LOLA coverage is sparse there.

**Earth side of every analogy**
- Gravity, vacuum, radiation, temperature and space weathering differ, and each site lists its own differences.

**Operations**
- Results depend on NASA services; when one is slow or down, the affected section says so.
