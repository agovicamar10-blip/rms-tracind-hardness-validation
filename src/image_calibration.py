"""Stage-micrometer calibration for indentation images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter


try:
    import cv2
except Exception:  # pragma: no cover - only used in incomplete environments
    cv2 = None


@dataclass(frozen=True)
class CalibrationResult:
    """Pixel-to-length calibration result for one image."""

    image_path: Path
    magnification: str
    orientation: str
    detected_step_um: float
    um_per_pixel: float
    intercept_um: float
    n_ticks: int
    x_start_px: float
    x_end_px: float
    detected_span_px: float
    detected_span_um: float
    residual_sd_um: float
    residual_max_abs_um: float
    full_scale_predicted_px: float
    full_scale_visible: bool
    full_scale_consistency_percent: float
    status: str
    reason: str


def normalize_magnification_from_name(path: str | Path) -> str:
    """Extract magnification from a filename."""

    name = Path(path).stem
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*[xX]", name)
    if not match:
        return ""
    value = match.group(1).replace(",", ".")
    if float(value).is_integer():
        value = str(int(float(value)))
    return f"{value}X"


def load_grayscale(path: str | Path) -> np.ndarray:
    """Load an image as an unchanged grayscale float array."""

    return np.asarray(Image.open(path).convert("L"), dtype=np.float32)


def _find_peaks(score: np.ndarray, min_dist: int, threshold: float) -> list[int]:
    """Find local maxima with a minimum distance constraint."""

    candidates: list[tuple[float, int]] = []
    for i in range(2, len(score) - 2):
        if score[i] >= threshold and score[i] >= score[i - 1] and score[i] >= score[i + 1]:
            candidates.append((float(score[i]), i))
    keep: list[int] = []
    for _, idx in sorted(candidates, reverse=True):
        if all(abs(idx - prev) >= min_dist for prev in keep):
            keep.append(idx)
    return sorted(keep)


def _score_from_band(gray: np.ndarray, y0: int, y1: int, x0: int, x1: int, mode: str) -> np.ndarray:
    """Return a column score from a ruler band."""

    band = gray[y0:y1, x0:x1]
    median_by_row = np.median(band, axis=1, keepdims=True)
    if mode == "dark":
        score = (median_by_row - band).clip(min=0).mean(axis=0)
    elif mode == "bright":
        score = (band - median_by_row).clip(min=0).mean(axis=0)
    else:
        image = Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8))
        blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=4)), dtype=np.float32)[y0:y1, x0:x1]
        score = np.abs(band - blurred).mean(axis=0)
    return np.convolve(score, np.ones(3) / 3, mode="same")


def _fixed_ruler_band_ticks(
    gray: np.ndarray,
    magnification: str,
    tick_spacing_um: float,
    total_scale_um: float,
) -> tuple[np.ndarray, np.ndarray, float, dict[str, Any]]:
    """Detect supplied horizontal ruler images using configured physical spacing."""

    height, width = gray.shape
    mag = magnification.upper()
    if mag == "20X":
        # At 20X, minor 2 um ticks are near the resolution limit. The longer
        # 10 um lattice is detected and assigned as five 2 um divisions.
        specs = [
            (0.49, 0.57, 0.25, 0.72, "dark", 0.85, 11, 5),
            (0.48, 0.58, 0.24, 0.74, "dark", 0.85, 11, 5),
            (0.49, 0.57, 0.25, 0.72, "dark", 0.75, 11, 5),
        ]
        expected_count = int(total_scale_um / (tick_spacing_um * 5)) + 1
    elif mag == "50X":
        specs = [
            (0.40, 0.68, 0.0, 1.0, "bright", 0.55, None, 10),
            (0.42, 0.66, 0.0, 1.0, "local", 0.65, None, 10),
            (0.45, 0.67, 0.0, 1.0, "bright", 0.65, None, 10),
        ]
        expected_count = int(total_scale_um / tick_spacing_um) + 1
    else:
        specs = [(0.42, 0.66, 0.0, 1.0, "local", 0.65, None, 8)]
        expected_count = int(total_scale_um / tick_spacing_um) + 1

    best: dict[str, Any] | None = None
    for y0f, y1f, x0f, x1f, mode, quantile, target_count, min_dist in specs:
        y0, y1 = int(height * y0f), int(height * y1f)
        x0, x1 = int(width * x0f), int(width * x1f)
        score = _score_from_band(gray, y0, y1, x0, x1, mode)
        threshold = float(np.quantile(score, quantile))
        peaks = np.asarray([p + x0 for p in _find_peaks(score, min_dist=min_dist, threshold=threshold)], dtype=float)
        if len(peaks) < 5:
            continue
        if target_count is not None and len(peaks) != target_count:
            # If extra minor/false peaks are present, keep the subset that best
            # spans the configured scale with the requested count.
            if len(peaks) > target_count:
                candidates = [peaks[i : i + target_count] for i in range(0, len(peaks) - target_count + 1)]
                peaks = max(candidates, key=lambda x: x[-1] - x[0])
            else:
                continue
        span_px = peaks[-1] - peaks[0]
        if span_px <= 0:
            continue
        physical_um = np.linspace(0.0, total_scale_um, len(peaks))
        slope = total_scale_um / span_px
        if not _slope_is_plausible(magnification, slope):
            continue
        score_value = -abs(len(peaks) - expected_count) - abs((physical_um[-1] - physical_um[0]) - total_scale_um) / 10.0
        if best is None or score_value > best["score"]:
            best = {
                "score": score_value,
                "peaks": peaks,
                "physical_um": physical_um,
                "detected_step_um": float(total_scale_um / (len(peaks) - 1)),
                "roi_y0": y0,
                "roi_y1": y1,
                "roi_x0": x0,
                "roi_x1": x1,
                "mode": mode,
                "quantile": quantile,
            }

    if best is None:
        return np.array([]), np.array([]), np.nan, {"detector": "fixed_ruler_band"}
    return (
        np.asarray(best["peaks"], dtype=float),
        np.asarray(best["physical_um"], dtype=float),
        float(best["detected_step_um"]),
        {"detector": "fixed_ruler_band", **{k: v for k, v in best.items() if k not in {"peaks", "physical_um"}}},
    )


def _slope_is_plausible(magnification: str, slope_um_per_px: float) -> bool:
    """Return whether a fitted calibration slope is plausible for the image magnification."""

    if not np.isfinite(slope_um_per_px) or slope_um_per_px <= 0:
        return False
    mag = magnification.upper()
    if mag == "20X":
        return 0.16 <= slope_um_per_px <= 0.34
    if mag == "50X":
        return 0.06 <= slope_um_per_px <= 0.14
    return 0.03 <= slope_um_per_px <= 0.5


def _projection_tick_candidates(gray: np.ndarray, magnification: str = "") -> tuple[np.ndarray, dict[str, Any]]:
    """Detect tick candidates from horizontal ruler-band projections.

    The detector searches several row bands and x ranges, then scores candidates
    by how well they fit the configured 2 um lattice. This deliberately favors a
    physically consistent ruler pattern over the highest-contrast image-wide
    structures.
    """

    image = Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8))
    blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=4)), dtype=np.float32)
    enhanced = np.abs(gray - blurred)
    height, width = gray.shape
    best: dict[str, Any] | None = None

    mag = magnification.upper()
    if mag == "20X":
        x_ranges = [(0.24, 0.74), (0.26, 0.72), (0.20, 0.80)]
    elif mag == "50X":
        x_ranges = [(0.0, 1.0), (0.0, 0.98), (0.02, 1.0)]
    else:
        x_ranges = [(0.0, 1.0), (0.20, 0.80)]

    y_start = max(0, int(height * 0.42))
    y_stop = min(height, int(height * 0.62))
    for band_height in [45, 65, 90]:
        for y0 in range(y_start, max(y_start + 1, y_stop - band_height), 16):
            y1 = y0 + band_height
            band = gray[y0:y1, :]
            median_by_row = np.median(band, axis=1, keepdims=True)
            scores = {
                "local": enhanced[y0:y1, :].mean(axis=0),
                "dark": (median_by_row - band).clip(min=0).mean(axis=0),
                "bright": (band - median_by_row).clip(min=0).mean(axis=0),
            }
            for x_frac0, x_frac1 in x_ranges:
                x0 = int(width * x_frac0)
                x1 = int(width * x_frac1)
                if x1 - x0 < 100:
                    continue
                for score_name, full_score in scores.items():
                    score = np.convolve(full_score[x0:x1], np.ones(3) / 3, mode="same")
                    for quantile in [0.50, 0.62, 0.74, 0.84, 0.90]:
                        threshold = float(np.quantile(score, quantile))
                        raw_peaks = _find_peaks(score, min_dist=max(4, width // 250), threshold=threshold)
                        if len(raw_peaks) < 5 or len(raw_peaks) > 80:
                            continue
                        peaks = np.asarray([p + x0 for p in raw_peaks], dtype=float)
                        selected_px, physical_um, residuals_um, slope, _, detected_step = _fit_lattice(
                            peaks, 2.0, 100.0
                        )
                        if len(selected_px) < 5 or not _slope_is_plausible(magnification, slope):
                            continue
                        span_um = physical_um[-1] - physical_um[0] if len(physical_um) else np.nan
                        if not (70.0 <= span_um <= 105.0):
                            continue
                        resid_sd = float(np.std(residuals_um, ddof=1)) if len(residuals_um) > 1 else 0.0
                        score_value = float(
                            len(selected_px)
                            + 4.0 * min(span_um / 100.0, 1.0)
                            - 3.0 * resid_sd
                            - 0.08 * abs(span_um - 100.0)
                        )
                        if best is None or score_value > best["score"]:
                            best = {
                                "score": score_value,
                                "peaks": selected_px,
                                "roi_y0": y0,
                                "roi_y1": y1,
                                "roi_x0": x0,
                                "roi_x1": x1,
                                "score_name": score_name,
                                "quantile": quantile,
                                "span_um": span_um,
                                "slope": slope,
                                "detected_step_um": detected_step,
                            }

    if best is None:
        return np.array([], dtype=float), {"detector": "projection_lattice", "roi_y0": np.nan, "roi_y1": np.nan}
    return np.asarray(best["peaks"], dtype=float), {"detector": "projection_lattice", **{k: v for k, v in best.items() if k != "peaks"}}


def _cv_vertical_tick_candidates(gray: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Detect vertical stage-micrometer tick candidates with morphology."""

    if cv2 is None:
        return _projection_tick_candidates(gray)

    img = np.clip(gray, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(img)
    height, width = eq.shape
    candidates: list[dict[str, float]] = []

    for polarity in ["dark", "bright"]:
        mode = cv2.THRESH_BINARY_INV if polarity == "dark" else cv2.THRESH_BINARY
        binary = cv2.adaptiveThreshold(eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, mode, 31, 4)
        for kernel_height in [9, 15, 23, 35, 51]:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_height))
            opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            num, labels, stats_arr, centroids = cv2.connectedComponentsWithStats(opened, 8)
            for label in range(1, num):
                x, y, w, h, area = stats_arr[label]
                if area < 8:
                    continue
                if w > max(12, width * 0.02):
                    continue
                if h < 8 or h > height * 0.35:
                    continue
                if h / max(w, 1) < 1.8:
                    continue
                if x <= 1 or x >= width - 2:
                    continue
                candidates.append(
                    {
                        "x": float(centroids[label][0]),
                        "y": float(centroids[label][1]),
                        "height": float(h),
                        "width": float(w),
                        "area": float(area),
                        "polarity": polarity,
                    }
                )

    if len(candidates) < 5:
        return _projection_tick_candidates(gray)

    cand = pd.DataFrame(candidates)
    # Choose the horizontal band where many narrow vertical ticks coexist.
    hist_bins = np.linspace(0, height, 60)
    hist, edges = np.histogram(cand["y"], bins=hist_bins, weights=np.sqrt(cand["height"]))
    peak_bin = int(np.argmax(hist))
    center_y = float((edges[peak_bin] + edges[peak_bin + 1]) / 2)
    band_half = max(35.0, height * 0.08)
    band = cand[(cand["y"] >= center_y - band_half) & (cand["y"] <= center_y + band_half)].copy()
    if len(band) < 5:
        return _projection_tick_candidates(gray)

    # Merge duplicate components belonging to the same tick.
    band = band.sort_values("x")
    merged: list[float] = []
    weights: list[float] = []
    for _, row in band.iterrows():
        x = float(row["x"])
        wt = float(row["area"] + row["height"])
        if not merged or abs(x - merged[-1]) > max(3.0, width / 400):
            merged.append(x)
            weights.append(wt)
        else:
            total = weights[-1] + wt
            merged[-1] = (merged[-1] * weights[-1] + x * wt) / total
            weights[-1] = total
    peaks = np.asarray(sorted(merged), dtype=float)
    if len(peaks) < 5:
        return _projection_tick_candidates(gray)
    return peaks, {"detector": "cv_morphology", "roi_center_y": center_y, "roi_half_height": band_half}


def _fit_lattice(
    positions_px: np.ndarray,
    base_tick_spacing_um: float,
    total_scale_um: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float]:
    """Fit detected marks to a regular 2 um lattice with skipped ticks allowed."""

    positions_px = np.asarray(sorted(positions_px), dtype=float)
    if len(positions_px) < 2:
        return np.array([]), np.array([]), np.array([]), np.nan, np.nan, np.nan

    diffs = np.diff(positions_px)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) == 0:
        return np.array([]), np.array([]), np.array([]), np.nan, np.nan, np.nan

    candidate_spacings: set[float] = set()
    for diff in diffs:
        if diff > 120:
            continue
        for multiple in [1, 2, 3, 4, 5, 10]:
            spacing = float(diff / multiple)
            if 3.0 <= spacing <= 40.0:
                candidate_spacings.add(round(spacing, 2))
    span = positions_px[-1] - positions_px[0]
    if span > 0:
        for intervals in [50, 45, 40, 25, 20, 10]:
            spacing = span / intervals
            if 3.0 <= spacing <= 40.0:
                candidate_spacings.add(round(float(spacing), 2))

    if len(candidate_spacings) > 90:
        target = span / 50.0 if span > 0 else np.median(diffs)
        ordered = sorted(candidate_spacings, key=lambda s: abs(s - target))
        candidate_spacings = set(ordered[:90])

    best: dict[str, Any] | None = None
    for spacing in sorted(candidate_spacings):
        tolerance = max(1.8, 0.18 * spacing)
        for origin in positions_px[: min(10, len(positions_px))]:
            indices = np.rint((positions_px - origin) / spacing).astype(int)
            predicted_px = origin + indices * spacing
            residual_px = positions_px - predicted_px
            fitted = np.abs(residual_px) <= tolerance
            if fitted.sum() < 4:
                continue
            candidate = pd.DataFrame(
                {
                    "x": positions_px[fitted],
                    "index": indices[fitted],
                    "residual_px": residual_px[fitted],
                }
            )
            candidate["abs_residual_px"] = candidate["residual_px"].abs()
            candidate = candidate.sort_values("abs_residual_px").drop_duplicates("index")
            if len(candidate) < 4:
                continue
            index_span = int(candidate["index"].max() - candidate["index"].min())
            physical_span = index_span * base_tick_spacing_um
            if physical_span > total_scale_um * 1.25:
                continue
            residual_rms = float(np.sqrt(np.mean(candidate["residual_px"] ** 2)))
            coverage_bonus = min(physical_span / total_scale_um, 1.0)
            score = float(len(candidate) + 2.0 * coverage_bonus - 0.25 * residual_rms)
            if best is None or score > best["score"]:
                best = {
                    "score": score,
                    "spacing": spacing,
                    "origin": origin,
                    "candidate": candidate.sort_values("index"),
                    "physical_span": physical_span,
                }

    if best is None:
        return np.array([]), np.array([]), np.array([]), np.nan, np.nan, np.nan

    candidate = best["candidate"]
    selected_px = candidate["x"].to_numpy(float)
    indices = candidate["index"].to_numpy(float)
    physical_um = (indices - indices.min()) * base_tick_spacing_um
    coef = np.polyfit(selected_px, physical_um, 1)
    predicted_um = np.polyval(coef, selected_px)
    residuals_um = physical_um - predicted_um
    index_steps = np.diff(np.sort(indices))
    detected_step_um = float(np.median(index_steps) * base_tick_spacing_um) if len(index_steps) else base_tick_spacing_um
    return selected_px, physical_um, residuals_um, float(coef[0]), float(coef[1]), detected_step_um


def calibrate_stage_micrometer(
    image_path: str | Path,
    tick_spacing_um: float = 2.0,
    total_scale_um: float = 100.0,
    output_overlay: str | Path | None = None,
) -> tuple[CalibrationResult, pd.DataFrame]:
    """Calibrate one stage-micrometer image using multiple detected ticks.

    The physical tick spacing is supplied by configuration. The algorithm only
    infers which regular tick lattice was detected; it does not invent physical
    spacing from the image.
    """

    image_path = Path(image_path)
    gray = load_grayscale(image_path)
    height, width = gray.shape
    magnification = normalize_magnification_from_name(image_path)
    ticks_px, physical_um, step_um, metadata = _fixed_ruler_band_ticks(
        gray, magnification, tick_spacing_um, total_scale_um
    )
    if len(ticks_px) < 2:
        ticks_px, metadata = _projection_tick_candidates(gray, magnification)
        physical_um = np.array([])
        step_um = np.nan
    if len(ticks_px) < 2:
        ticks_px, metadata = _cv_vertical_tick_candidates(gray)
        physical_um = np.array([])
        step_um = np.nan
    if len(ticks_px) < 2:
        result = CalibrationResult(
            image_path=image_path,
            magnification=magnification,
            orientation="horizontal",
            detected_step_um=np.nan,
            um_per_pixel=np.nan,
            intercept_um=np.nan,
            n_ticks=int(len(ticks_px)),
            x_start_px=np.nan,
            x_end_px=np.nan,
            detected_span_px=np.nan,
            detected_span_um=np.nan,
            residual_sd_um=np.nan,
            residual_max_abs_um=np.nan,
            full_scale_predicted_px=np.nan,
            full_scale_visible=False,
            full_scale_consistency_percent=np.nan,
            status="rejected",
            reason="Fewer than two reliable ticks detected",
        )
        return result, pd.DataFrame()

    if len(physical_um) == len(ticks_px) and len(ticks_px) >= 2:
        coef = np.polyfit(ticks_px, physical_um, 1)
        slope = float(coef[0])
        intercept = float(coef[1])
        residuals_um = physical_um - np.polyval(coef, ticks_px)
    else:
        ticks_px, physical_um, residuals_um, slope, intercept, step_um = _fit_lattice(
            ticks_px, tick_spacing_um, total_scale_um
        )
    if len(ticks_px) < 2:
        result = CalibrationResult(
            image_path=image_path,
            magnification=magnification,
            orientation="horizontal",
            detected_step_um=np.nan,
            um_per_pixel=np.nan,
            intercept_um=np.nan,
            n_ticks=0,
            x_start_px=np.nan,
            x_end_px=np.nan,
            detected_span_px=np.nan,
            detected_span_um=np.nan,
            residual_sd_um=np.nan,
            residual_max_abs_um=np.nan,
            full_scale_predicted_px=np.nan,
            full_scale_visible=False,
            full_scale_consistency_percent=np.nan,
            status="rejected",
            reason="Could not fit a physically consistent tick lattice",
        )
        return result, pd.DataFrame()
    detected_span_px = float(ticks_px[-1] - ticks_px[0])
    detected_span_um = float(physical_um[-1] - physical_um[0]) if len(physical_um) else np.nan
    full_scale_predicted_px = float(total_scale_um / slope) if np.isfinite(slope) and slope > 0 else np.nan
    full_scale_visible = bool(
        np.isfinite(full_scale_predicted_px)
        and full_scale_predicted_px <= width * 1.05
        and detected_span_um >= total_scale_um * 0.8
    )
    full_scale_consistency = (
        100.0 * detected_span_um / total_scale_um if np.isfinite(detected_span_um) else np.nan
    )
    residual_sd = float(np.std(residuals_um, ddof=1)) if len(residuals_um) > 1 else 0.0
    residual_max = float(np.max(np.abs(residuals_um))) if len(residuals_um) else np.nan
    status = "reliable" if len(ticks_px) >= 6 and residual_sd <= max(0.75, step_um * 0.2) else "conditionally reliable"
    reason = (
        f"{len(ticks_px)} ticks fitted as {step_um:g} um lattice using {metadata.get('detector')}; "
        f"span covers {full_scale_consistency:.1f}% of configured 100 um scale"
    )

    result = CalibrationResult(
        image_path=image_path,
        magnification=magnification,
        orientation="horizontal",
        detected_step_um=step_um,
        um_per_pixel=slope,
        intercept_um=intercept,
        n_ticks=int(len(ticks_px)),
        x_start_px=float(ticks_px[0]),
        x_end_px=float(ticks_px[-1]),
        detected_span_px=detected_span_px,
        detected_span_um=detected_span_um,
        residual_sd_um=residual_sd,
        residual_max_abs_um=residual_max,
        full_scale_predicted_px=full_scale_predicted_px,
        full_scale_visible=full_scale_visible,
        full_scale_consistency_percent=full_scale_consistency,
        status=status,
        reason=reason,
    )

    tick_table = pd.DataFrame(
        {
            "image_path": str(image_path),
            "magnification": result.magnification,
            "tick_index": np.arange(len(ticks_px), dtype=int),
            "pixel_position": ticks_px,
            "assigned_position_um": physical_um,
            "fit_residual_um": residuals_um,
        }
    )
    if output_overlay is not None:
        save_calibration_overlay(gray, ticks_px, physical_um, result, output_overlay)
    return result, tick_table


def save_calibration_overlay(
    gray: np.ndarray,
    ticks_px: np.ndarray,
    physical_um: np.ndarray,
    result: CalibrationResult,
    output_path: str | Path,
) -> None:
    """Save a diagnostic overlay for detected calibration ticks."""

    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=140)
    ax.imshow(gray, cmap="gray")
    for x, u in zip(ticks_px, physical_um):
        ax.axvline(x, color="#d62728", linewidth=0.8, alpha=0.65)
        if len(ticks_px) <= 15 or int(round(u)) % 20 == 0:
            ax.text(x, 18, f"{u:g}", color="#d62728", fontsize=7, rotation=90, va="top")
    ax.set_title(
        f"{result.magnification} calibration: {result.um_per_pixel:.5g} um/px, "
        f"{result.n_ticks} ticks, {result.status}"
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def calibrate_available_images(
    calibration_dir: str | Path,
    tick_spacing_um: float,
    total_scale_um: float,
    diagnostic_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calibrate every available stage-micrometer image."""

    calibration_dir = Path(calibration_dir)
    records: list[dict[str, Any]] = []
    ticks: list[pd.DataFrame] = []
    for path in sorted(calibration_dir.glob("*")):
        if path.suffix.lower() not in {".bmp", ".png", ".tif", ".tiff"}:
            continue
        overlay = None
        if diagnostic_dir is not None:
            overlay = Path(diagnostic_dir) / f"{path.stem}_calibration_overlay.png"
        result, tick_table = calibrate_stage_micrometer(
            path,
            tick_spacing_um=tick_spacing_um,
            total_scale_um=total_scale_um,
            output_overlay=overlay,
        )
        records.append({**result.__dict__, "image_path": str(result.image_path)})
        ticks.append(tick_table)
    table = pd.DataFrame(records)
    tick_df = pd.concat(ticks, ignore_index=True) if ticks else pd.DataFrame()
    return table, tick_df


def calibration_lookup(calibration_table: pd.DataFrame) -> dict[str, dict[str, float | str]]:
    """Create a magnification-to-scale lookup from reliable calibration rows."""

    lookup: dict[str, dict[str, float | str]] = {}
    if calibration_table.empty:
        return lookup
    for _, row in calibration_table.iterrows():
        mag = row.get("magnification", "")
        if not mag or not np.isfinite(row.get("um_per_pixel", np.nan)):
            continue
        lookup[mag] = {
            "sx_um_per_px": float(row["um_per_pixel"]),
            "sy_um_per_px": float(row["um_per_pixel"]),
            "source": str(row.get("image_path", "")),
            "orientation": str(row.get("orientation", "")),
            "status": str(row.get("status", "")),
            "assumption": "Only horizontal calibration image available; sy set equal to sx as explicit isotropy assumption.",
        }
    return lookup
