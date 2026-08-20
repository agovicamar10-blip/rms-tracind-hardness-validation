"""Automatic indentation image analysis for Vickers, Micro-Vickers and Brinell."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


try:
    import cv2
except Exception:  # pragma: no cover - only used in incomplete environments
    cv2 = None


@dataclass(frozen=True)
class ImageMeasurementConfig:
    """Configurable thresholds for rule-based image classification."""

    min_edge_strength: float = 8.0
    max_vickers_diagonal_ratio: float = 1.45
    reject_vickers_diagonal_ratio: float = 2.0
    min_corner_angle_deg: float = 35.0
    min_brinnell_circularity: float = 0.55
    max_brinnell_axis_ratio: float = 1.35
    max_radial_cv: float = 0.12
    conditional_relative_difference_percent: float = 2.0
    reject_relative_difference_percent: float = 5.0


def require_cv2() -> None:
    """Raise a clear error if OpenCV is unavailable."""

    if cv2 is None:
        raise ImportError("opencv-python is required for automatic image analysis.")


def load_gray_uint8(path: str | Path) -> np.ndarray:
    """Load an image without resizing as a grayscale uint8 array."""

    return np.asarray(Image.open(path).convert("L"), dtype=np.uint8)


def calibrated_distance(p1: np.ndarray, p2: np.ndarray, sx: float, sy: float) -> float:
    """Distance between two image points using anisotropic calibration."""

    delta = np.asarray(p2, dtype=float) - np.asarray(p1, dtype=float)
    return float(np.sqrt((delta[0] * sx) ** 2 + (delta[1] * sy) ** 2))


def _preprocess(gray: np.ndarray) -> np.ndarray:
    require_cv2()
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(gray)
    return cv2.GaussianBlur(eq, (5, 5), 0)


def _candidate_contours(gray: np.ndarray, kind: str) -> list[np.ndarray]:
    require_cv2()
    proc = _preprocess(gray)
    height, width = proc.shape
    masks: list[np.ndarray] = []

    edges = cv2.Canny(proc, 35, 100)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
    masks.append(edges)

    local = cv2.absdiff(proc, cv2.GaussianBlur(proc, (0, 0), 21))
    _, otsu = cv2.threshold(local, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    otsu = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    masks.append(otsu)

    # The pyramid or Brinell impression often has a broad intensity shift whose
    # interior is locally smooth. Global masks catch this body, while the edge
    # and local-contrast masks above catch irregular boundaries.
    _, dark = cv2.threshold(proc, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    masks.append(dark)
    _, bright = cv2.threshold(proc, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    masks.append(bright)

    contours: list[np.ndarray] = []
    for mask in masks:
        found, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for contour in found:
            area = abs(cv2.contourArea(contour))
            min_area_fraction = 0.001 if kind in {"Vickers", "Micro-Vickers"} else 0.0002
            if area < height * width * min_area_fraction:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if x <= 1 or y <= 1 or x + w >= width - 1 or y + h >= height - 1:
                # Keep large Brinell contours that touch very near the frame only
                # if most of the indentation remains visible.
                if kind != "Brinell" or area < height * width * 0.08:
                    continue
            if w < 10 or h < 10:
                continue
            contours.append(contour)
    return contours


def _choose_contour(gray: np.ndarray, kind: str) -> tuple[np.ndarray | None, dict[str, float]]:
    require_cv2()
    height, width = gray.shape
    center = np.array([width / 2, height / 2])
    best: tuple[float, np.ndarray, dict[str, float]] | None = None
    for contour in _candidate_contours(gray, kind):
        area = abs(cv2.contourArea(contour))
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        rect_center = np.array([x + w / 2, y + h / 2])
        centrality = 1.0 - min(1.0, np.linalg.norm(rect_center - center) / np.linalg.norm(center))
        extent = area / max(w * h, 1)
        aspect = max(w, h) / max(min(w, h), 1)
        circularity = 4.0 * np.pi * area / (perimeter * perimeter)

        if kind in {"Vickers", "Micro-Vickers"}:
            if aspect > 3.5:
                continue
            score = area * (0.6 + centrality) * (0.4 + extent) / max(1.0, abs(aspect - 1.0) + 0.4)
        else:
            if aspect > 2.2:
                continue
            score = area * (0.5 + centrality) * (0.5 + min(circularity, 1.0)) / max(1.0, abs(aspect - 1.0) + 0.2)
        metrics = {
            "contour_area_px2": float(area),
            "contour_perimeter_px": float(perimeter),
            "bbox_x": float(x),
            "bbox_y": float(y),
            "bbox_w": float(w),
            "bbox_h": float(h),
            "bbox_aspect": float(aspect),
            "contour_extent": float(extent),
            "circularity": float(circularity),
            "centrality": float(centrality),
        }
        if best is None or score > best[0]:
            best = (float(score), contour, metrics)
    if best is None:
        return None, {}
    return best[1], best[2]


def _edge_strength(gray: np.ndarray, contour: np.ndarray) -> float:
    require_cv2()
    proc = _preprocess(gray)
    gx = cv2.Sobel(proc, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(proc, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    pts = contour.reshape(-1, 2)
    values = mag[np.clip(pts[:, 1], 0, mag.shape[0] - 1), np.clip(pts[:, 0], 0, mag.shape[1] - 1)]
    return float(np.median(values)) if len(values) else np.nan


def _select_four_corners(contour: np.ndarray) -> tuple[np.ndarray | None, dict[str, float]]:
    require_cv2()
    hull = cv2.convexHull(contour).reshape(-1, 2).astype(float)
    if len(hull) < 4:
        return None, {"corner_count": float(len(hull))}
    center = hull.mean(axis=0)
    vectors = hull - center
    radii = np.linalg.norm(vectors, axis=1)
    angles = np.arctan2(vectors[:, 1], vectors[:, 0])
    order = np.argsort(-radii)
    selected: list[np.ndarray] = []
    selected_angles: list[float] = []
    min_sep = np.deg2rad(45)
    for idx in order:
        angle = float(angles[idx])
        if all(abs(np.angle(np.exp(1j * (angle - prev)))) >= min_sep for prev in selected_angles):
            selected.append(hull[idx])
            selected_angles.append(angle)
        if len(selected) == 4:
            break
    if len(selected) < 4:
        rect = cv2.minAreaRect(contour)
        selected = [p.astype(float) for p in cv2.boxPoints(rect)]
        selected_angles = [float(np.arctan2((p - center)[1], (p - center)[0])) for p in selected]
    corners = np.asarray(selected, dtype=float)
    angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
    corners = corners[np.argsort(angles)]
    sep = np.diff(np.r_[np.sort(angles), np.sort(angles)[0] + 2 * np.pi])
    metrics = {
        "corner_count": 4.0,
        "corner_radius_cv": float(np.std(np.linalg.norm(corners - center, axis=1)) / max(np.mean(np.linalg.norm(corners - center, axis=1)), 1e-9)),
        "min_corner_angle_deg": float(np.rad2deg(np.min(sep))),
        "max_corner_angle_deg": float(np.rad2deg(np.max(sep))),
    }
    return corners, metrics


def _status_from_reasons(reasons: list[str], rejection_reasons: list[str]) -> str:
    if rejection_reasons:
        return "rejected"
    if reasons:
        return "conditionally reliable"
    return "reliable"


def vickers_hardness_from_force_diagonal(force_n: float, mean_diagonal_um: float) -> float:
    """Calculate Vickers hardness from force in N and mean diagonal in um."""

    if force_n <= 0 or mean_diagonal_um <= 0:
        return np.nan
    d_mm = mean_diagonal_um / 1000.0
    return float(0.1891 * force_n / (d_mm * d_mm))


def brinell_hardness_from_force_diameter(force_n: float, ball_diameter_mm: float, mean_diameter_um: float) -> float:
    """Calculate Brinell hardness from force in N, ball diameter in mm, and indentation diameter in um."""

    if force_n <= 0 or ball_diameter_mm <= 0 or mean_diameter_um <= 0:
        return np.nan
    d_mm = mean_diameter_um / 1000.0
    if d_mm >= ball_diameter_mm:
        return np.nan
    denom = np.pi * ball_diameter_mm * (ball_diameter_mm - np.sqrt(ball_diameter_mm**2 - d_mm**2))
    return float(0.102 * 2.0 * force_n / denom)


def analyze_vickers_image(
    image_path: str | Path,
    sx_um_per_px: float,
    sy_um_per_px: float,
    force_n: float | None = None,
    config: ImageMeasurementConfig | None = None,
    overlay_path: str | Path | None = None,
) -> dict[str, Any]:
    """Measure Vickers/Micro-Vickers diagonals from one image."""

    require_cv2()
    config = config or ImageMeasurementConfig()
    image_path = Path(image_path)
    gray = load_gray_uint8(image_path)
    contour, metrics = _choose_contour(gray, "Vickers")
    if contour is None:
        return {"image_path": str(image_path), "image_status": "rejected", "classification_reason": "No suitable indentation contour detected"}
    corners, corner_metrics = _select_four_corners(contour)
    metrics.update(corner_metrics)
    edge_strength = _edge_strength(gray, contour)
    metrics["edge_strength"] = edge_strength
    if corners is None:
        return {"image_path": str(image_path), "image_status": "rejected", "classification_reason": "Four corner regions could not be detected", **metrics}

    d1 = calibrated_distance(corners[0], corners[2], sx_um_per_px, sy_um_per_px)
    d2 = calibrated_distance(corners[1], corners[3], sx_um_per_px, sy_um_per_px)
    mean_d = (d1 + d2) / 2.0
    diag_ratio = max(d1, d2) / max(min(d1, d2), 1e-12)
    metrics.update(
        {
            "python_d1_um": d1,
            "python_d2_um": d2,
            "python_mean_dimension_um": mean_d,
            "diagonal_ratio": diag_ratio,
            "corner_points": corners.tolist(),
        }
    )
    if force_n is not None and np.isfinite(force_n):
        metrics["python_hardness"] = vickers_hardness_from_force_diagonal(float(force_n), mean_d)

    conditional: list[str] = []
    rejection: list[str] = []
    if edge_strength < config.min_edge_strength:
        conditional.append("weak boundary contrast")
    if metrics["min_corner_angle_deg"] < config.min_corner_angle_deg:
        rejection.append("angular separation too small")
    if diag_ratio > config.reject_vickers_diagonal_ratio:
        rejection.append("opposite-corner consistency failed")
    elif diag_ratio > config.max_vickers_diagonal_ratio:
        conditional.append("large diagonal ratio")
    if metrics["corner_radius_cv"] > 0.35:
        conditional.append("unstable radial corner geometry")
    status = _status_from_reasons(conditional, rejection)
    reason = "; ".join(rejection + conditional) if (rejection or conditional) else "all configured image checks passed"

    if overlay_path is not None:
        save_vickers_overlay(gray, contour, corners, metrics, status, overlay_path)
    return {
        "image_path": str(image_path),
        "image_status": status,
        "classification_reason": reason,
        "analysis_type": "Vickers contour-corner",
        **metrics,
    }


def _diameter_by_angle(points: np.ndarray, angle_deg: float, sx: float, sy: float) -> float:
    theta = np.deg2rad(angle_deg)
    scaled = np.column_stack([points[:, 0] * sx, points[:, 1] * sy])
    direction = np.array([np.cos(theta), np.sin(theta)])
    proj = scaled @ direction
    return float(np.max(proj) - np.min(proj))


def analyze_brinell_image(
    image_path: str | Path,
    sx_um_per_px: float,
    sy_um_per_px: float,
    force_n: float | None = None,
    ball_diameter_mm: float | None = None,
    config: ImageMeasurementConfig | None = None,
    overlay_path: str | Path | None = None,
) -> dict[str, Any]:
    """Measure Brinell indentation diameters from one image."""

    require_cv2()
    config = config or ImageMeasurementConfig()
    image_path = Path(image_path)
    gray = load_gray_uint8(image_path)
    contour, metrics = _choose_contour(gray, "Brinell")
    if contour is None:
        return {"image_path": str(image_path), "image_status": "rejected", "classification_reason": "No complete Brinell boundary contour detected"}

    points = contour.reshape(-1, 2).astype(float)
    x, y, w, h = cv2.boundingRect(contour)
    d_horizontal = w * sx_um_per_px
    d_vertical = h * sy_um_per_px
    d_mean = (d_horizontal + d_vertical) / 2.0
    center, radius = cv2.minEnclosingCircle(contour)
    center_arr = np.asarray(center, dtype=float)
    scaled_points = np.column_stack([points[:, 0] * sx_um_per_px, points[:, 1] * sy_um_per_px])
    scaled_center = np.array([center_arr[0] * sx_um_per_px, center_arr[1] * sy_um_per_px])
    radii = np.linalg.norm(scaled_points - scaled_center, axis=1)
    radial_mean = float(np.mean(radii)) if len(radii) else np.nan
    radial_sd = float(np.std(radii, ddof=1)) if len(radii) > 1 else np.nan
    radial_cv = radial_sd / radial_mean if radial_mean else np.nan
    axis_ratio = np.nan
    ellipse_major_um = np.nan
    ellipse_minor_um = np.nan
    if len(contour) >= 5:
        (_, _), (axis1, axis2), _ = cv2.fitEllipse(contour)
        ellipse_major_um = max(axis1 * sx_um_per_px, axis2 * sy_um_per_px)
        ellipse_minor_um = min(axis1 * sx_um_per_px, axis2 * sy_um_per_px)
        axis_ratio = ellipse_major_um / max(ellipse_minor_um, 1e-12)

    angle4 = {f"diameter_{angle:g}deg_um": _diameter_by_angle(points, angle, sx_um_per_px, sy_um_per_px) for angle in [0, 45, 90, 135]}
    angle6 = {f"diameter6_{angle:g}deg_um": _diameter_by_angle(points, angle, sx_um_per_px, sy_um_per_px) for angle in [0, 30, 60, 90, 120, 150]}
    metrics.update(
        {
            "python_d1_um": d_horizontal,
            "python_d2_um": d_vertical,
            "python_mean_dimension_um": d_mean,
            "circle_radius_um": float(radius * (sx_um_per_px + sy_um_per_px) / 2.0),
            "radial_residual_sd_um": radial_sd,
            "radial_cv": radial_cv,
            "ellipse_major_um": ellipse_major_um,
            "ellipse_minor_um": ellipse_minor_um,
            "ellipse_axis_ratio": axis_ratio,
            "diameter_direction_range_4_um": float(max(angle4.values()) - min(angle4.values())),
            "diameter_direction_range_6_um": float(max(angle6.values()) - min(angle6.values())),
        }
    )
    metrics.update(angle4)
    metrics.update(angle6)
    if force_n is not None and ball_diameter_mm is not None and np.isfinite(force_n) and np.isfinite(ball_diameter_mm):
        metrics["python_hardness"] = brinell_hardness_from_force_diameter(float(force_n), float(ball_diameter_mm), d_mean)

    conditional: list[str] = []
    rejection: list[str] = []
    if metrics["circularity"] < config.min_brinnell_circularity:
        conditional.append("irregular Brinell boundary")
    if np.isfinite(axis_ratio) and axis_ratio > config.max_brinnell_axis_ratio:
        conditional.append("ellipse axis ratio high")
    if np.isfinite(radial_cv) and radial_cv > config.max_radial_cv:
        conditional.append("large radial residual variation")
    if x <= 1 or y <= 1 or x + w >= gray.shape[1] - 1 or y + h >= gray.shape[0] - 1:
        rejection.append("incomplete contour touches image boundary")
    status = _status_from_reasons(conditional, rejection)
    reason = "; ".join(rejection + conditional) if (rejection or conditional) else "all configured image checks passed"
    if overlay_path is not None:
        save_brinell_overlay(gray, contour, metrics, status, overlay_path)
    return {
        "image_path": str(image_path),
        "image_status": status,
        "classification_reason": reason,
        "analysis_type": "Brinell contour-diameter",
        **metrics,
    }


def save_vickers_overlay(
    gray: np.ndarray,
    contour: np.ndarray,
    corners: np.ndarray,
    metrics: dict[str, Any],
    status: str,
    output_path: str | Path,
) -> None:
    """Save Vickers diagnostic overlay."""

    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pts = contour.reshape(-1, 2)
    fig, ax = plt.subplots(figsize=(8, 7), dpi=140)
    ax.imshow(gray, cmap="gray")
    ax.plot(pts[:, 0], pts[:, 1], color="#2ca02c", linewidth=1.0, label="detected contour")
    closed = np.vstack([corners, corners[0]])
    ax.plot(closed[:, 0], closed[:, 1], color="#ff7f0e", linewidth=1.1, label="corner order")
    ax.scatter(corners[:, 0], corners[:, 1], s=32, color="#d62728", zorder=5)
    ax.plot([corners[0, 0], corners[2, 0]], [corners[0, 1], corners[2, 1]], color="#1f77b4", linewidth=1.2)
    ax.plot([corners[1, 0], corners[3, 0]], [corners[1, 1], corners[3, 1]], color="#9467bd", linewidth=1.2)
    ax.set_title(
        f"{status}: d1={metrics.get('python_d1_um', np.nan):.2f} um, "
        f"d2={metrics.get('python_d2_um', np.nan):.2f} um"
    )
    ax.set_axis_off()
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_brinell_overlay(
    gray: np.ndarray,
    contour: np.ndarray,
    metrics: dict[str, Any],
    status: str,
    output_path: str | Path,
) -> None:
    """Save Brinell diagnostic overlay."""

    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pts = contour.reshape(-1, 2)
    fig, ax = plt.subplots(figsize=(8, 7), dpi=140)
    ax.imshow(gray, cmap="gray")
    ax.plot(pts[:, 0], pts[:, 1], color="#2ca02c", linewidth=1.0, label="detected boundary")
    x = metrics.get("bbox_x", np.nan)
    y = metrics.get("bbox_y", np.nan)
    w = metrics.get("bbox_w", np.nan)
    h = metrics.get("bbox_h", np.nan)
    if np.isfinite(x + y + w + h):
        ax.plot([x, x + w], [y + h / 2, y + h / 2], color="#1f77b4", linewidth=1.2, label="horizontal diameter")
        ax.plot([x + w / 2, x + w / 2], [y, y + h], color="#9467bd", linewidth=1.2, label="vertical diameter")
    ax.set_title(
        f"{status}: dh={metrics.get('python_d1_um', np.nan):.2f} um, "
        f"dv={metrics.get('python_d2_um', np.nan):.2f} um"
    )
    ax.set_axis_off()
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def analyze_matched_images(
    matched_images: pd.DataFrame,
    measurements: pd.DataFrame,
    calibration: dict[str, dict[str, float | str]],
    diagnostic_dir: str | Path,
    config: ImageMeasurementConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze every exactly matched indentation image."""

    config = config or ImageMeasurementConfig()
    diagnostic_dir = Path(diagnostic_dir)
    rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    if matched_images.empty:
        return pd.DataFrame(), pd.DataFrame()

    merged = matched_images.merge(
        measurements,
        on=["record_id", "method", "series_id", "original_sheet", "excel_row"],
        how="left",
        suffixes=("", "_measurement"),
    )
    for _, row in merged.iterrows():
        base = {
            "record_id": row.get("record_id"),
            "series_id": row.get("series_id"),
            "method": row.get("method"),
            "picture_id": row.get("picture_id"),
            "excel_row": row.get("excel_row"),
            "magnification": row.get("magnification"),
            "manual_mean_dimension_um": row.get("manual_mean_dimension_um", np.nan),
            "automatic_mean_dimension_um": row.get("automatic_mean_dimension_um", np.nan),
            "manual_hardness": row.get("manual_hardness", np.nan),
            "automatic_hardness": row.get("automatic_hardness", np.nan),
        }
        if row.get("match_status") != "matched":
            result = {**base, "image_status": "rejected", "classification_reason": f"Image match status: {row.get('match_status')}"}
            rows.append(result)
            quality_rows.append(result)
            continue
        mag = row.get("magnification")
        cal = calibration.get(mag, {})
        if not cal:
            result = {
                **base,
                "image_path": str(row.get("image_path")),
                "image_status": "rejected",
                "classification_reason": f"insufficient calibration for magnification {mag}",
            }
            rows.append(result)
            quality_rows.append(result)
            continue

        overlay_path = diagnostic_dir / f"{row.get('picture_id')}_overlay.png"
        if row.get("method") in {"Vickers", "Micro-Vickers"}:
            result = analyze_vickers_image(
                row.get("image_path"),
                float(cal["sx_um_per_px"]),
                float(cal["sy_um_per_px"]),
                force_n=row.get("applied_force_n", np.nan),
                config=config,
                overlay_path=overlay_path,
            )
        elif row.get("method") == "Brinell":
            result = analyze_brinell_image(
                row.get("image_path"),
                float(cal["sx_um_per_px"]),
                float(cal["sy_um_per_px"]),
                force_n=row.get("applied_force_n", np.nan),
                ball_diameter_mm=row.get("ball_diameter_mm", np.nan),
                config=config,
                overlay_path=overlay_path,
            )
        else:
            result = {
                "image_path": str(row.get("image_path")),
                "image_status": "rejected",
                "classification_reason": "Knoop image analysis excluded because paired automatic Knoop data are unavailable",
            }
        result = {**base, **result}
        if np.isfinite(result.get("python_mean_dimension_um", np.nan)):
            result["python_minus_manual_dimension_um"] = result["python_mean_dimension_um"] - result.get("manual_mean_dimension_um", np.nan)
            result["python_minus_automatic_dimension_um"] = result["python_mean_dimension_um"] - result.get("automatic_mean_dimension_um", np.nan)
            pair_mean_pm = (result["python_mean_dimension_um"] + result.get("manual_mean_dimension_um", np.nan)) / 2
            pair_mean_pa = (result["python_mean_dimension_um"] + result.get("automatic_mean_dimension_um", np.nan)) / 2
            result["python_minus_manual_relative_percent"] = 100 * result["python_minus_manual_dimension_um"] / pair_mean_pm
            result["python_minus_automatic_relative_percent"] = 100 * result["python_minus_automatic_dimension_um"] / pair_mean_pa
            agreement_reasons: list[str] = []
            rel_values = [
                result.get("python_minus_manual_relative_percent", np.nan),
                result.get("python_minus_automatic_relative_percent", np.nan),
            ]
            max_abs_rel = np.nanmax(np.abs(rel_values)) if np.isfinite(rel_values).any() else np.nan
            if np.isfinite(max_abs_rel):
                if max_abs_rel > config.reject_relative_difference_percent:
                    result["image_status"] = "rejected"
                    agreement_reasons.append("excessive agreement difference")
                elif max_abs_rel > config.conditional_relative_difference_percent and result.get("image_status") == "reliable":
                    result["image_status"] = "conditionally reliable"
                    agreement_reasons.append("elevated agreement difference")
            if agreement_reasons:
                existing_reason = str(result.get("classification_reason", "")).strip()
                result["classification_reason"] = "; ".join(
                    [r for r in [existing_reason, *agreement_reasons] if r]
                )
        rows.append(result)

        quality_rows.append(
            {
                key: result.get(key, np.nan)
                for key in [
                    "record_id",
                    "series_id",
                    "method",
                    "picture_id",
                    "magnification",
                    "image_status",
                    "classification_reason",
                    "edge_strength",
                    "diagonal_ratio",
                    "corner_radius_cv",
                    "min_corner_angle_deg",
                    "circularity",
                    "ellipse_axis_ratio",
                    "radial_cv",
                    "diameter_direction_range_4_um",
                    "python_minus_manual_relative_percent",
                    "python_minus_automatic_relative_percent",
                ]
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(quality_rows)


def classify_suitability(
    image_quality: pd.DataFrame,
    en_results: pd.DataFrame | None = None,
    config: ImageMeasurementConfig | None = None,
) -> pd.DataFrame:
    """Transparent rule-based suitability classification."""

    config = config or ImageMeasurementConfig()
    en_lookup = {}
    if en_results is not None and not en_results.empty:
        en_lookup = dict(zip(en_results["series_id"], en_results["abs_en"]))
    records: list[dict[str, Any]] = []
    for _, row in image_quality.iterrows():
        reasons: list[str] = []
        status = row.get("image_status", "rejected")
        if status == "rejected":
            reasons.append(str(row.get("classification_reason", "algorithmic rejection")))
        elif status == "conditionally reliable":
            reasons.append(str(row.get("classification_reason", "conditional image-quality result")))
        rel_diff = row.get("python_minus_automatic_relative_percent", np.nan)
        if np.isfinite(rel_diff):
            if abs(rel_diff) > config.reject_relative_difference_percent:
                status = "rejected"
                reasons.append("excessive Python-automatic difference")
            elif abs(rel_diff) > config.conditional_relative_difference_percent and status == "reliable":
                status = "conditionally reliable"
                reasons.append("elevated Python-automatic difference")
        abs_en = en_lookup.get(row.get("series_id"), np.nan)
        if np.isfinite(abs_en) and abs_en > 1:
            if status == "reliable":
                status = "conditionally reliable"
            reasons.append("|E_n| > 1 for corresponding series")
        if status == "reliable":
            label = "suitable for automatic measurement"
            reasons.append("configured image and agreement checks passed")
        elif status == "conditionally reliable":
            label = "conditionally suitable/requires review"
        else:
            label = "unsuitable for unattended automatic measurement"
        records.append(
            {
                "record_id": row.get("record_id"),
                "series_id": row.get("series_id"),
                "method": row.get("method"),
                "picture_id": row.get("picture_id"),
                "magnification": row.get("magnification"),
                "suitability_class": label,
                "reason": "; ".join(dict.fromkeys([r for r in reasons if r])),
            }
        )
    return pd.DataFrame(records)
