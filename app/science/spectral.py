"""Spectral attributes computed from real reflectance (M3) or I/F (CRISM).

Only band-depth style quantities are produced: they are ratios of the spectrum
to a local continuum and are therefore insensitive to absolute calibration
offsets. Nothing here returns mineral abundances.

Definitions
-----------
* ``legacy_bd1000`` / ``legacy_bd2000`` — exactly the definition used to build
  the terrestrial EMIT reference library inherited from the previous backend
  (``run_earth_pipeline.extract_gee_indices``):
  ``BD = (C - R_c) / C`` with ``C = (R_left + R_right) / 2`` and bands nearest to
  (1000; 800, 1300) nm and (2000; 1700, 2300) nm. Per-pixel depths are kept
  unclamped (a negative depth is a convex continuum = no absorption). As in the
  library, the clamp at 0 is applied once, to the window mean, when the value
  enters the analog comparison (``legacy_analog_input``). Clamping per pixel
  before averaging would bias noisy windows upwards (mean of max(0, x) > max(0,
  mean x)) and make them incomparable with the library.
  This is the only attribute set that is computed identically on Earth, Moon
  and Mars, which is why it alone is used for cross-body comparison.
* ``IBD1000`` / ``IBD2000`` — integrated band depths after Mustard et al.
  (2011, JGR 116, E00G12): sum of (1 - R/Rc) over 789-1308 nm (continuum
  anchored ~699 and ~1579 nm) and over 1658-2498 nm (continuum ~1579 and
  ~2538 nm), using the M3 bands that fall in those ranges.
* ``R750`` — reflectance at ~750 nm (albedo; affected by maturity).
* ``slope_750_1550`` — (R1550 - R750) / R750 per µm: continuum reddening,
  mainly driven by space weathering on the Moon.
"""

from __future__ import annotations

import math

import numpy as np

from app.schemas.analysis import SpectralIndicator, Stats

DETECTION_SIGMA = 3.0
CORRELATION_PIXELS = 25     # ~5x5 px correlation length (instrument PSF + resampling)
MIN_POSITIVE_FRACTION = 0.6
# Minimum physical magnitude (window median) on top of the statistical test, for the CRISM parameters
# that produced false positives on real negative controls. With thousands of pixels the statistical test
# accepts tiny systematic offsets (calibration/atmospheric residuals). No published detection floors were
# found (Viviano-Beck et al. 2014 define the parameters, not floors), so floors are calibrated on real
# MTRDR controls (data/calibration/crism_controls.json, docs/RELATORIO_TESTES_CIENTIFICOS.md):
#  * negatives: 5 dust-mantled Tharsis/Amazonis observations; 4 ice-free low-latitude sites
#    (Jezero, Nili Fossae, Mawrth, Gale) for the ice parameters;
#  * rule: floor = 2 x the largest negative-control median, rounded;
#  * exception OLINDEX3: 2x would exceed the documented olivine of Jezero/Nili Fossae (0.063-0.071),
#    so the floor is the midpoint between the dust maximum (0.043) and that olivine (thin margin);
#  * ice: positives from the polar caps (BD1500_2 0.051-0.240 north; BD1435 0.41 south).
# Parameters whose negative controls stayed negative (D2300, MIN2295_2480, MIN2345_2537, BD1900_2,
# BD2100_2, LCPINDEX2, HCPINDEX2) keep the statistical rule. BD530_2 (ferric oxide) is real on dust.
MAGNITUDE_FLOOR = {"BD1435": 0.02, "BD1500_2": 0.025, "OLINDEX3": 0.05, "BDI1000IR": 0.045,
                   "BD2210_2": 0.003, "SINDEX2": 0.017}
FLOOR_BASIS = ("window median must also reach {floor} (floor calibrated on real CRISM negative controls "
               "such as dust-covered and ice-free surfaces; see docs/RELATORIO_TESTES_CIENTIFICOS.md)")
# Above this solar incidence the surface is too dimly lit (or unlit) for reflectance band depths.
MAX_USABLE_INCIDENCE_DEG = 85.0
# M3 quality gate: an IBD1000 window median below this marks a convex 1 um region, which silicate surfaces do
# not produce; observed only on observations contradicted by others over the same ground (calibration in
# docs/RELATORIO_TESTES_CIENTIFICOS.md: suspect products -0.11 to -0.36; good mare/olivine +1.3 to +1.8).
M3_CONVEX_1UM = -0.1

DETECTION_BASIS = ("statistical screening: window mean > 3 x standard error (effective n = pixels/25 for "
                   "spatial correlation), median > 0 and >= 60% of pixels positive. Detects a positive band "
                   "depth; not a mineral abundance or identification")


def nearest_band(wavelengths: np.ndarray, target_nm: float, tol_nm: float = 40.0) -> int | None:
    i = int(np.argmin(np.abs(wavelengths - target_nm)))
    return i if abs(wavelengths[i] - target_nm) <= tol_nm else None


def stats(values: np.ndarray) -> Stats:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return Stats()
    p05, med, p95 = np.percentile(v, [5, 50, 95])
    return Stats(mean=float(v.mean()), median=float(med), min=float(v.min()), max=float(v.max()),
                 std=float(v.std(ddof=1)) if v.size > 1 else 0.0, p05=float(p05), p95=float(p95))


def detected_from_stats(mean: float | None, std: float | None, median: float | None, n: int,
                        fraction_positive: float | None) -> bool | None:
    """Same screening as :func:`detected`, from ROI summary statistics (Earth Engine reductions).
    None when the statistics are incomplete."""
    if None in (mean, std, median, fraction_positive) or n < 4:
        return None
    sem = std / math.sqrt(max(2.0, n / CORRELATION_PIXELS))
    return bool(mean > DETECTION_SIGMA * sem and median > 0 and fraction_positive >= MIN_POSITIVE_FRACTION)


def detected(values: np.ndarray) -> bool:
    v = values[np.isfinite(values)]
    if v.size < 4:
        return False
    n_eff = max(2.0, v.size / CORRELATION_PIXELS)
    sem = v.std(ddof=1) / math.sqrt(n_eff)
    return bool(v.mean() > DETECTION_SIGMA * sem and np.median(v) > 0
                and np.mean(v > 0) >= MIN_POSITIVE_FRACTION)


def legacy_band_depth(spec: np.ndarray, wl: np.ndarray, center: float, left: float, right: float
                      ) -> np.ndarray | None:
    """Per-pixel legacy band depth, unclamped; ``spec`` is (n_pixels, n_bands)."""
    ic, il, ir = (nearest_band(wl, x) for x in (center, left, right))
    if None in (ic, il, ir):
        return None
    cont = (spec[:, il] + spec[:, ir]) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        bd = (cont - spec[:, ic]) / cont
    bd[~np.isfinite(bd)] = np.nan
    return bd


def legacy_analog_input(arr: np.ndarray) -> float | None:
    """Window value used for the analog comparison: mean of the unclamped
    per-pixel depths, then clamped at 0 (same order as the EMIT library)."""
    v = arr[np.isfinite(arr)]
    return max(0.0, float(v.mean())) if v.size else None


def window_sem(arr: np.ndarray) -> float | None:
    """Standard error of the window mean with the spatial-correlation correction."""
    v = arr[np.isfinite(arr)]
    if v.size < 2:
        return None
    return float(v.std(ddof=1) / math.sqrt(max(2.0, v.size / CORRELATION_PIXELS)))


LEGACY_NEGATIVE = ("Median depth is negative (convex continuum): no absorption at this wavelength. "
                   "The analog comparison uses 0, as in the reference library.")


def legacy_interpretation(arr: np.ndarray, detailed: bool = True) -> str:
    v = arr[np.isfinite(arr)]
    if detected(arr):
        return f"Positive absorption detected ({DETECTION_BASIS})." if detailed else "Positive absorption detected."
    if v.size and float(np.median(v)) < 0:
        return LEGACY_NEGATIVE
    return "No statistically significant absorption in the window." if detailed else \
        "No statistically significant absorption."


LEGACY_DEF = ("(C - R{c})/C, C = mean(R{l}, R{r}){on}; per-pixel values unclamped (negative = no absorption); "
              "window mean clamped at 0 for the analog comparison")


def integrated_band_depth(spec: np.ndarray, wl: np.ndarray, lo: float, hi: float,
                          anchor_l: float, anchor_r: float) -> np.ndarray | None:
    il, ir = nearest_band(wl, anchor_l), nearest_band(wl, anchor_r)
    idx = np.where((wl >= lo - 1) & (wl <= hi + 1))[0]
    if il is None or ir is None or idx.size < 3:
        return None
    wl_l, wl_r = wl[il], wl[ir]
    rl, rr = spec[:, il:il + 1], spec[:, ir:ir + 1]
    frac = (wl[idx] - wl_l) / (wl_r - wl_l)
    cont = rl + (rr - rl) * frac[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        ibd = np.sum(1.0 - spec[:, idx] / cont, axis=1)
    ibd[~np.isfinite(ibd)] = np.nan
    return ibd


def m3_indicators(spec: np.ndarray, wl: np.ndarray) -> tuple[list[SpectralIndicator], dict[str, np.ndarray]]:
    """Indicators from valid M3 L2 pixels ``spec`` (n_pixels, n_bands)."""
    out: list[SpectralIndicator] = []
    values: dict[str, np.ndarray] = {}
    n = spec.shape[0]
    ref_m3 = "Mustard et al. (2011) JGR 116, E00G12 (M3 integrated band depths)"

    def add(name, arr, definition, reference, sensitive, comparability, unit="dimensionless",
            with_detection=True):
        if arr is None:
            return
        values[name] = arr
        det = detected(arr) if with_detection else None
        if name.startswith("legacy_"):
            interp = legacy_interpretation(arr)
        elif with_detection:
            interp = (f"Positive absorption detected ({DETECTION_BASIS})." if det else
                      "No statistically significant absorption in the window.")
        else:
            interp = "Descriptive value; no detection test applies."
        out.append(SpectralIndicator(
            name=name, value=stats(arr), unit=unit, definition=definition, reference=reference,
            sensitive_to=sensitive, screening_threshold=0.0 if with_detection else None,
            threshold_basis=DETECTION_BASIS if with_detection else None,
            fraction_above_threshold=float(np.mean(arr[np.isfinite(arr)] > 0)) if with_detection and np.isfinite(arr).any() else None,
            n_pixels=int(np.isfinite(arr).sum()), interpretation=interp, comparability=comparability, detected=det))

    add("IBD1000", integrated_band_depth(spec, wl, 789, 1308, 699, 1579),
        "Integrated band depth 789-1308 nm, linear continuum ~699-1579 nm", ref_m3,
        "Fe2+ crystal-field absorptions near 1 µm (pyroxene, olivine, Fe-bearing glass)", "body_specific")
    add("IBD2000", integrated_band_depth(spec, wl, 1658, 2498, 1579, 2538),
        "Integrated band depth 1658-2498 nm, linear continuum ~1579-2538 nm", ref_m3,
        "Fe2+ absorption near 2 µm (pyroxene; absent in olivine)", "body_specific")
    add("legacy_bd1000", legacy_band_depth(spec, wl, 1000, 800, 1300),
        LEGACY_DEF.format(c=1000, l=800, r=1300, on=""), "GEØ.IA terrestrial EMIT library definition",
        "1 µm Fe2+ absorption (coarse, 3-band)", "direct")
    add("legacy_bd2000", legacy_band_depth(spec, wl, 2000, 1700, 2300),
        LEGACY_DEF.format(c=2000, l=1700, r=2300, on=""), "GEØ.IA terrestrial EMIT library definition",
        "2 µm Fe2+ absorption (coarse, 3-band)", "direct")
    i750, i1550 = nearest_band(wl, 750), nearest_band(wl, 1550)
    if i750 is not None:
        add("R750", spec[:, i750].astype(float), "Reflectance at the band nearest 750 nm",
            "Lucey et al. (2000) JGR 105 (750 nm albedo for lunar maturity/FeO work)",
            "albedo; space-weathering maturity", "body_specific", unit="reflectance", with_detection=False)
    if i750 is not None and i1550 is not None:
        with np.errstate(divide="ignore", invalid="ignore"):
            slope = (spec[:, i1550] - spec[:, i750]) / spec[:, i750] / ((wl[i1550] - wl[i750]) / 1000.0)
        add("slope_750_1550", slope, "(R1550 - R750) / R750 per µm", "Continuum slope (space weathering reddening)",
            "space weathering / maturity", "body_specific", unit="per µm", with_detection=False)
    _ = n
    return out, values


def m3_character(values: dict[str, np.ndarray]) -> str | None:
    a, b = values.get("IBD1000"), values.get("IBD2000")
    if a is None or b is None:
        return None
    d1, d2 = detected(a), detected(b)
    if d1 and d2:
        return ("1 µm and 2 µm absorptions both detected: consistent with pyroxene-bearing material "
                "(e.g. mare basalt or noritic material). Not a mineral identification.")
    if d1:
        return ("1 µm absorption without a significant 2 µm band: consistent with olivine-, glass- or "
                "Fe-bearing plagioclase-rich material; ambiguous without band-centre analysis.")
    if d2:
        return "Only the 2 µm region shows a positive depth: atypical; possibly thermal-correction residual."
    return ("No significant 1/2 µm absorption: consistent with mature, space-weathered or feldspathic "
            "surface; ambiguous.")


# --------------------------------------------------------------------------- #
# CRISM summary parameters (computed by the CRISM team, Viviano-Beck et al. 2014)
# --------------------------------------------------------------------------- #
VB14 = "Viviano-Beck et al. (2014) JGR Planets 119, 1403-1431 (CRISM summary products)"
CRISM_PARAMS = {
    "OLINDEX3": "olivine (broad 1 µm band)",
    "LCPINDEX2": "low-Ca pyroxene",
    "HCPINDEX2": "high-Ca pyroxene",
    "BDI1000IR": "Fe2+ 1 µm absorption (mafic minerals)",
    "BD1900_2": "H2O in hydrated minerals",
    "D2300": "Fe/Mg-OH (Fe/Mg phyllosilicates)",
    "BD2210_2": "Al-OH (Al phyllosilicates, hydrated silica)",
    "BD2290": "Mg/Fe-OH; CO2 ice",
    "MIN2295_2480": "Mg carbonate",
    "MIN2345_2537": "Fe/Ca carbonate",
    "BD2100_2": "monohydrated sulfates",
    "SINDEX2": "polyhydrated sulfates (convexity at 2.29 µm)",
    "BD530_2": "crystalline ferric oxides",
    "BD1435": "CO2 ice",
    "BD1500_2": "H2O ice",
    "R770": "albedo at 770 nm (descriptive)",
}


def crism_detected(name: str, arr: np.ndarray) -> bool:
    """Statistical screening plus, for the ice parameters, the calibrated magnitude floor."""
    if not detected(arr):
        return False
    floor = MAGNITUDE_FLOOR.get(name)
    if floor is None:
        return True
    v = arr[np.isfinite(arr)]
    return bool(v.size and float(np.median(v)) >= floor)


def crism_indicator(name: str, arr: np.ndarray) -> SpectralIndicator:
    descriptive = name.startswith("R")
    det = None if descriptive else crism_detected(name, arr)
    floor = MAGNITUDE_FLOOR.get(name)
    basis = DETECTION_BASIS + ("; " + FLOOR_BASIS.format(floor=floor) if floor is not None else "")
    if descriptive:
        interp = "Descriptive I/F value; no detection test applies."
    elif det:
        interp = (f"Positive parameter value detected ({basis}). Sensitive to "
                  f"{CRISM_PARAMS[name]}; confirmation requires ratioed-spectrum analysis.")
    elif floor is not None and detected(arr):
        interp = (f"Small positive value below the {floor} floor: not counted as a detection "
                  f"(dust-covered or ice-free control surfaces reach similar values).")
    else:
        interp = "No statistically significant positive value in the window."
    finite = arr[np.isfinite(arr)]
    return SpectralIndicator(
        name=name, value=stats(arr), unit="I/F" if descriptive else "dimensionless",
        definition=f"CRISM MTRDR summary parameter {name} (computed by the CRISM team)",
        reference=VB14, sensitive_to=CRISM_PARAMS.get(name),
        screening_threshold=None if descriptive else (floor if floor is not None else 0.0),
        threshold_basis=None if descriptive else basis,
        fraction_above_threshold=None if descriptive or finite.size == 0 else float(np.mean(finite > 0)),
        n_pixels=int(finite.size), interpretation=interp, comparability="body_specific", detected=det)


def crism_character(indicators: list[SpectralIndicator], values: dict[str, np.ndarray]) -> str | None:
    if not values:
        return None
    hits = [i.name for i in indicators
            if i.name in values and not i.name.startswith("R") and crism_detected(i.name, values[i.name])]
    if not hits:
        return "No summary parameter shows a statistically significant positive value in the window."
    parts = [f"{h} ({CRISM_PARAMS.get(h, '?')})" for h in hits]
    return ("Positive summary parameters: " + "; ".join(parts) +
            ". Screening only; mineral identification requires ratioed spectra.")
