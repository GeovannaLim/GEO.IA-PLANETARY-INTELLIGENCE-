# GEØ.IA Planetary Intelligence — validation and tests

This document records how the platform was tested and what the tests showed, including the failures. All
scientific tests use **real NASA data**. Synthetic data appears only in the automated unit and integration tests,
and one test guarantees that the application package never imports the test fakes.

Methods are described in [SCIENTIFIC_DOCUMENTATION.md](SCIENTIFIC_DOCUMENTATION.md).

## 1. How we tested

| Kind of test | What it checks |
|---|---|
| Pre-registered scientific scenarios (`scripts/science_tests.py`) | 21 places where the answer is known from the literature or from mission data. The expected outcome and the pass criterion were written **before** running. |
| Adversarial tests (`scripts/adversarial_analogs.py`, `tests/unit/test_adversarial_*`) | Deliberate attempts to make the system reach a wrong scientific conclusion: dust without minerals, regions without ice, no sunlight, bad observations, catalog order, ties, weak evidence, Moon and Mars evidence mixed together |
| Calibration and held-out validation | Every numerical floor was derived from one set of real controls and checked on another set never used for calibration |
| Real-data controls for the geomorphology | The same terrain shifted by 1–6 km (positive control), distinct Earth sites (not assumed false), and a-priori strong contrasts (should not match) |
| Automated suite (pytest) | Unit and integration tests, API contract, provider failures, translations, synthetic terrains |
| Production validation after every deploy | The 21 scenarios, the integration checks with the frontend, and a value-by-value comparison with the previous production version |
| Frontend acceptance tests | The published app tested in a real browser, with the displayed values checked against the API response |

## 2. The 21 pre-registered scientific scenarios

Final run against **production `8df1d61`** (2026-11-14), with real data and no cache: **20 PASS + 1 INCONCLUSIVE**,
identical to the previous production version in values and provenance (Section 6).

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
| M9 | Mars point without CRISM | do not invent | "unavailable" + clearly labelled global context | PASS |
| L1 | Chang'e-3 landing site, Moon | −2630/−2640 m; basalt (LROC) | −2628 m; pyroxene | PASS |
| L2 | Copernicus central peak | olivine (Isaacson et al., 2011) | olivine / volcanic glass | PASS |
| L3 | Mare Imbrium | pyroxene | pyroxene | PASS |
| L4 | Lunar south pole | do not measure in the dark | mineralogy unavailable, 0 sites; environment and geomorphology available | PASS |
| D1–D6 | Martian dust (6 held-out points) | nothing but ferric oxide | only ferric oxide | PASS |
| I1 | North residual cap (held out) | ice; mimicked minerals masked | ice; olivine/sulfate masked | PASS |
| I2 | South residual cap (held out) | ice; mimicked minerals masked | CO₂ ice; olivine/sulfate masked | PASS |

**Additional real-data controls run during development**

| Control | Result |
|---|---|
| CRISM dust, held out | 9/9 clean (0 false minerals) |
| Dust outside Tharsis (8 Elysium + 8 Arabia) | 15/16 clean; the exception led to the olivine coherence rule |
| Olivine study: 59 controls (4 literature positives, 10 regional positives, 45 negatives) + Aram Chaos | 60/60 as expected in production: 14 confident positives, Elysium uncertain, 44 negatives not detected |
| Sulfate positive control (Aram Chaos, Lichtenberg et al., 2010) | detected, with a small margin |
| Lunar permanent-shadow regression | 80°S 30.5°E: 73/73 M³ pixels in permanent shadow excluded, the 3 false anorthosite analogs eliminated. Copernicus (334 pixels) and Imbrium (1,681 pixels) unchanged. |

## 3. Adversarial tests of the analog ranking

| Test | Question | Result |
|---|---|---|
| A1 | Does the catalog file order change the ranking? | No: 20 shuffled orders give the same ranking |
| A2 | Does "neither has the band" count as similarity? | No: only shared presence counts |
| A3 | Can a Moon-only site be offered for Mars, or vice versa? | No |
| A4 | Does dropping one detected family change the top site? | Only when strong detections are removed, which is expected (14 findings documented) |
| A5 | Can broad evidence outrank specific evidence? | No |

The A1–A5 results are identical between the previous production version and the final release.

**Seven ways to reach a wrong scientific conclusion were found and fixed:**
1. false minerals in dust;
2. false equatorial ice;
3. minerals seen through ice;
4. measuring without sunlight;
5. a bad M³ observation deciding the result;
6. absence counted as similarity;
7. meaningless tie-breaking.

The table in Section 8 of the scientific documentation shows each one with its real example.

## 4. Geomorphology validation (real LOLA and Copernicus data)

### 4.1 Lunar regions

| Region | LOLA data | Result at 60 m (9/9 windows) |
|---|---|---|
| Shackleton (interior) | 205,038 shots, 100% coverage | Median slope 12.1 ± 3.5°. Rover mobility: El Tatio, Cuprite, Merriam. Traverse and rugged: Cuprite. Río Tinto is shown only as modified relief. |
| Mons Malapert | 113,543 shots | Median slope 11.0 ± 1.8°. Similar to Shackleton; the El Tatio and Cuprite matches are weak (Earth median slope 2–2.5× lower). |
| Haworth | 75,686 shots, 99.8% coverage | Median slope 15.8 ± 1.1°. Rover mobility: Merriam only. Traverse and rugged: **no demonstrable correspondence**. |
| Copernicus crater, Mare Imbrium | sparse off-polar coverage (54% / 62% at 480 m) | **inconclusive**: no profile is invented |

**Reading these results**
- Merriam (the JSC-1 simulant source) is the only documented lunar analog with a full correspondence (rover
  mobility).
- No Earth site in the catalog is a defensible terrain analog for Haworth's 11–16° walls. A directed search
  (Haughton, Mauna Kea, Haleakalā, Dry Valleys) did not change this: Haughton has a 3° median slope and was
  rejected.

### 4.2 Controls and discrimination

Rates at 60 m. "Families overlap" means the two families of windows share area. Results are per purpose: 3
decisions per pair.

| Control | Correspondence rate |
|---|---|
| Same terrain shifted 1–3 km (families overlap) | 61% |
| Same terrain shifted 4–6 km (no overlap) | 41% |
| Distinct Earth sites (not assumed false) | 23% |
| A-priori strong contrasts (alpine massif × plain or shield) | **0/45** |

- **Sensitivity to the decision threshold:** z ∈ {1, 1.5, 2, 2.5, 3} and k ∈ {1, 2} were evaluated as sensitivity
  analyses only, with no recalibration.
- **Fix found by the controls:** the median-slope gate. It removes the Haworth (15.8°) × Puʻu Nēnē (1.3°) type of
  error, and the 7 named contrasts are now rejected.
- **Alternatives rejected:**
  - Stricter thresholds (k = 2) and a robust spread estimate collapsed the self-match rate.
  - Full slope-distribution distances (W1, KS) were chosen on one half of the sites and evaluated on the other.
    They did not improve separation, so the current method was kept.

### 4.3 Catalog audit (Phase 3A)

| Item | Finding | Decision |
|---|---|---|
| Kaʻū, Dresser, Timanfaya, Stillwater, Sittampundi | No coordinate of the studied unit precise enough to compare at a 2 km scale | Remain excluded |
| Craters of the Moon | GPS sample coordinates found (Tolometti, 2021) | Corrected to the Highway Flow unit |
| Río Tinto | Mixed natural and mining relief | Reported only as modified relief |

## 5. Automated tests

```
pytest -q                                   → 222 passed, 3 skipped (the 3 live-NASA tests)
GEOIA_LIVE_TESTS=1 pytest -m live -q        → 3/3 with normal NASA service
```

| Area | Examples |
|---|---|
| Science | Detection test and floors, olivine coherence, ice masking, convex-1 µm filter, illumination cut, permanent-shadow control, absence ≠ anorthosite |
| Analog ranking | Adversarial attacks A1–A5, ties, broad versus specific evidence, body separation |
| Geomorphology | Same method on irregular (LOLA-like) and gridded (DEM-like) data, scale never mixed, partial coverage gives "insufficient", heterogeneous reference is non-discriminating, slope gate, mining-modified relief never shown as a natural correspondence, Mars has no section |
| Resilience | M³ timeout fails only mineralogy (not an absence), observation fallback declared, provider-failure results not replayed from cache, LOLA 503, ODE failure, illumination map unavailable |
| API | Contract and schema backward compatibility, async jobs (202 → 200), restart resumption, CORS restricted to configured origins, English/Portuguese |

## 6. Production releases and their validation

Every release was compared with the previous production version before it was published. The previous commit was
kept as the rollback target.

| Release | Main change | Automated tests | Scenario result | Comparison with the previous version |
|---|---|---|---|---|
| `dc4e267` | First production deploy on Render | — | Production validation script: 27/27 | — |
| `abb10cb` | Calibrated CRISM floors (26 dust controls), polar CRISM projection, the 7 adversarial fixes | 114 | 20 PASS + 1 inconclusive | Integration with the frontend: 33/34 (the one failure passed on rerun) |
| `46f3a88` | Olivine spatial-coherence rule (provisional), analysed CRISM extent | 182 | 20 + 1, unchanged | Olivine controls 60/60; integration 34/34 |
| `ed1ee18` | Lunar south polar illumination; permanent-shadow control of M³ | 198 | 20 + 1 | 21/21 identical to `46f3a88` in mineralogy, products, families, sites, ranks and altitude |
| **`8df1d61`** (current) | Experimental Moon–Earth geomorphology; Río Tinto and Craters of the Moon audit; M³ timeout resilience | **222** | **20 + 1 on the first production run, no retries** | **21/21 identical to `ed1ee18`** in values and provenance, with source IDs resolved to their products |

**Final release checks**
- 21/21 responses are schema-valid.
- They contain no local paths, stack traces or credentials.
- Mars returns no geomorphology section.
- Experimental Earth candidates never appear in the API.

**External incident during validation.** NASA's PDS Imaging Node was intermittently slow on 2026-11-14, with 73
read timeouts.
- **Diagnosis:** the same case run on the *stable* code (`ed1ee18`) also timed out, so the cause was external.
- **Fix:** the M³ deadline. During slow periods the affected scenarios returned mineralogy as `provider_error` with
  no analogs and no invented value. They were rerun with the same pre-registered criteria once the service
  recovered, and they passed.
- **Timing measured per provider:** M³ dominates (up to 249 range reads, single reads up to 67 s). CRISM reads stay
  under 2 s each.

## 7. Frontend acceptance tests (published app, real browser)

| Version | Result |
|---|---|
| 0.0.74 | **Rejected:** the lunar south pole produced a blank screen, because `comparisons` was read as a list. Imbrium, Mars and the history passed. |
| 0.0.75 | **Accepted:** environment and geomorphology values identical to the API. One provenance defect found: the radius displayed differed from the radius analysed. |
| 0.0.76 | The panel correctly shows the radius from the API response. This revealed the root cause: the auto-start request sent 10 km while the field showed 5 km. |
| Final | **Accepted:** a never-analysed polar point (−88.5°, 30°). The backend received `radius_km = 5.0`; the panel and the history show 5 km; the environment and geomorphology sections match the API. |

## 8. Evidence

- Raw outputs (JSON and logs) of every validation run are kept by the team under `var/` (not versioned). They can
  be shared on request.
- Reproducible scripts are in `scripts/`:
  - `science_tests.py` and `science_tests_retry.py`;
  - `final_regression.py`;
  - `adversarial_analogs.py`;
  - `geomorph_controls.py` and `geomorph_dist_study.py`;
  - `geomorph_candidates_compare.py`, `geomorph_rio_tinto_mask.py` and `provider_timing.py`.
- Detailed reports, in Portuguese, are in `docs/`. This English set summarises them for the submission.
