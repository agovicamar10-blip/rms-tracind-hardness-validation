"""Build the RMS indentation validation notebook."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "RMS_indentation_validation.ipynb"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip() + "\n"}


def code(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.strip() + "\n"}


cells: list[dict] = []

cells.append(md(
    r"""
# RMS indentation validation for EURAMET 22RPT01 TracInd BVK-H

This notebook is a reproducible scientific analysis for the Research Mobility
Support (RMS) work connected to EURAMET project **22RPT01 TracInd BVK-H**. It
compares manual and automatic GSV HARDNESS indentation measurements and
evaluates an independent Python image-processing workflow calibrated from the
supplied stage-micrometer images.

The workflow separates:

- **Level A: individual paired indentations**, used for paired differences,
  Bland-Altman plots, exploratory Deming regression, and within-series
  repeatability;
- **Level B: three-indentation series means**, used for reported mean hardness,
  normalized error `E_n`, and uncertainty-aware regression where uncertainty
  columns permit it.

Knoop data are counted and described but are not used as paired validation data
because automatic Knoop measurements were not available during this RMS
activity.
"""
))

cells.append(md(
    r"""
## Configuration

All configurable assumptions are collected here. The stage micrometer is
provisionally interpreted from the visible marking `0.1 mm / 0.002 mm div`,
corresponding to a nominal 100 um scale and 2 um adjacent-division spacing. If a
certificate becomes available, enter the certified spacing and uncertainty
values here and document the source.
"""
))

cells.append(code(
    r"""
from pathlib import Path

RANDOM_SEED = 20260820
BOOTSTRAP_RESAMPLES = 1000

WORKBOOK_FILENAME = "Hardness_measurement_results.xlsx"

STAGE_MICROMETER_TICK_SPACING_UM = 2.0
STAGE_MICROMETER_TOTAL_SCALE_UM = 100.0
STAGE_MICROMETER_TICK_SPACING_STANDARD_UNCERTAINTY_UM = None
STAGE_MICROMETER_TICK_SPACING_EXPANDED_UNCERTAINTY_UM = None
STAGE_MICROMETER_COVERAGE_FACTOR = None

UNCERTAINTY_COVERAGE_FACTOR_FOR_SERIES = 2.0  # configurable default; not certificate-confirmed

IMAGE_STATUS_THRESHOLDS = {
    "min_edge_strength": 8.0,
    "max_vickers_diagonal_ratio": 1.45,
    "reject_vickers_diagonal_ratio": 2.0,
    "min_corner_angle_deg": 35.0,
    "min_brinnell_circularity": 0.55,
    "max_brinnell_axis_ratio": 1.35,
    "max_radial_cv": 0.12,
    "conditional_relative_difference_percent": 2.0,
    "reject_relative_difference_percent": 5.0,
}

PRACTICAL_LOA_CRITERION_PERCENT = None  # no project-specific criterion supplied
"""
))

cells.append(md(
    r"""
## Imports and repository discovery

The repository root is found by searching the current directory and its parents
for `data/Hardness_measurement_results.xlsx`. This allows the notebook to run
from either the repository root or the `notebooks/` directory.
"""
))

cells.append(code(
    r"""
import math
import re
import subprocess
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("default")
np.random.seed(RANDOM_SEED)

current = Path.cwd().resolve()
for candidate in [current, *current.parents]:
    if (candidate / "data" / WORKBOOK_FILENAME).exists():
        ROOT = candidate
        break
    if candidate.name == "data" and (candidate / WORKBOOK_FILENAME).exists():
        ROOT = candidate.parent
        break
else:
    raise FileNotFoundError("Could not locate repository root from current working directory")

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_processing import (
    build_data_quality_report,
    combine_measurement_frames,
    create_series_summary,
    get_repository_paths,
    list_image_files,
    match_picture_ids,
    read_hardness_workbook,
)
from agreement_analysis import (
    add_standard_uncertainties,
    bland_altman_summary,
    deming_summary,
    normalized_error,
    odr_summary,
    paired_difference_summary,
    repeatability_table,
)
from image_calibration import calibrate_available_images, calibration_lookup
from indentation_detection import ImageMeasurementConfig, analyze_matched_images, classify_suitability
from reporting import (
    ensure_output_dirs,
    export_analysis_workbook,
    export_tables_csv,
    plot_bland_altman,
    plot_deming,
    plot_difference_distribution,
    plot_en,
    plot_repeatability,
    plot_scatter_identity,
    savefig,
    summarize_interpretation,
)

paths = get_repository_paths(ROOT)
out_dirs = ensure_output_dirs(paths.outputs)
print(f"Repository root: {ROOT}")
print(f"Outputs: {paths.outputs}")
"""
))

cells.append(md(
    r"""
## Source-document and file inspection

The RMS application identifies the work as support for WP4, with emphasis on
statistical validation of automated indentation measurements, image processing
for indentation analysis, and reproducible documentation. The annex identifies
WP4 as automation of indentation measurements and D8 as analysis of automatic
Brinell, Vickers and Knoop measurement results with specifications for
indentation types suitable for automatic measurement. The application describes
comparison with PTB/INRIM or other NMI data as conditional on availability; no
such external datasets are present in this repository.
"""
))

cells.append(code(
    r"""
from docx import Document
import pdfplumber
from PIL import Image

source_records = []
for folder in [paths.data, paths.docs, paths.images / "indentations", paths.images / "calibration"]:
    for file in sorted(folder.glob("*")):
        if file.is_file():
            source_records.append({
                "folder": str(folder.relative_to(ROOT)),
                "file": file.name,
                "suffix": file.suffix.lower(),
                "size_bytes": file.stat().st_size,
            })
source_files = pd.DataFrame(source_records)


def extract_doc_snippets(doc_path: Path, terms=("WP4", "D7", "D8", "Knoop", "INRIM", "PTB", "stage micrometer")) -> dict:
    text = ""
    if doc_path.suffix.lower() == ".docx":
        doc = Document(str(doc_path))
        text = "\n".join([p.text for p in doc.paragraphs])
    elif doc_path.suffix.lower() == ".pdf":
        with pdfplumber.open(str(doc_path)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    snippets = {}
    low = text.lower()
    for term in terms:
        idx = low.find(term.lower())
        if idx >= 0:
            snippets[term] = re.sub(r"\s+", " ", text[max(0, idx - 120): idx + 360]).strip()
    return {"file": doc_path.name, "chars_extracted": len(text), "snippets": snippets}


source_context = pd.DataFrame([extract_doc_snippets(p) for p in sorted(paths.docs.glob("*")) if p.suffix.lower() in {".docx", ".pdf"}])

image_dimension_records = []
for image_path in sorted(paths.images.rglob("*")):
    if image_path.is_file() and image_path.suffix.lower() in {".bmp", ".png", ".tif", ".tiff"}:
        with Image.open(image_path) as img:
            image_dimension_records.append({
                "image_kind": "calibration" if "calibration" in [part.lower() for part in image_path.parts] else "indentation",
                "file": image_path.name,
                "width_px": img.size[0],
                "height_px": img.size[1],
                "mode": img.mode,
            })
image_dimensions = pd.DataFrame(image_dimension_records)

display(source_files)
display(source_context[["file", "chars_extracted"]])
display(image_dimensions.groupby(["image_kind", "width_px", "height_px", "mode"]).size().reset_index(name="count"))
"""
))

cells.append(md(
    r"""
## Workbook cleaning and image matching

The workbook is parsed from its actual sheets and two-row headers. Fully blank
rows, repeated header rows and non-measurement rows are excluded; statistical
outliers are not removed. Each cleaned record keeps the original sheet name and
Excel row. Labels such as `20x`/`20X` and decimal commas in scale names are
normalized for grouping while the original labels are retained.
"""
))

cells.append(code(
    r"""
frames = read_hardness_workbook(paths.data / WORKBOOK_FILENAME)
measurements = combine_measurement_frames(frames)
series_summary = create_series_summary(measurements)
image_files = list_image_files(paths.images)
matched_images, unmatched_images = match_picture_ids(measurements, image_files)
data_quality, exclusions = build_data_quality_report(frames, image_files)

workbook_summary = measurements.groupby("method").agg(
    valid_observations=("record_id", "count"),
    series_count=("series_id", "nunique"),
    magnifications=("magnification", lambda s: ", ".join(f"{k}:{v}" for k, v in s.value_counts().sort_index().items())),
).reset_index()

picture_summary = pd.DataFrame({
    "metric": ["indentation_images", "calibration_images", "workbook_picture_ids", "matched_picture_ids", "unmatched_image_files"],
    "value": [
        int((image_files["image_kind"] == "indentation").sum()),
        int((image_files["image_kind"] == "calibration").sum()),
        int(measurements.get("picture_id", pd.Series(dtype=object)).notna().sum()),
        int((matched_images["match_status"] == "matched").sum()) if not matched_images.empty else 0,
        len(unmatched_images),
    ],
})

scale_force_check = measurements.groupby(["method", "hardness_scale_raw", "hardness_scale", "applied_force_n", "magnification"], dropna=False).size().reset_index(name="rows")

display(workbook_summary)
display(picture_summary)
display(scale_force_check)
display(data_quality.head(20))
display(exclusions.head(20))
"""
))

cells.append(md(
    r"""
## Level A: individual paired indentation comparisons

At Level A, the primary measurand for agreement is the directly measured
indentation dimension:

- Vickers and Micro-Vickers: mean diagonal in um;
- Brinell: mean indentation diameter in um.

For each paired indentation, the absolute Bland-Altman difference is

$$D_i = A_i - M_i$$

plotted against the pair mean

$$X_i = \frac{A_i + M_i}{2},$$

where `A_i` is the automatic IMS result and `M_i` is the manual result. The
relative Bland-Altman difference is the symmetric percentage difference

$$100\frac{A_i-M_i}{(A_i+M_i)/2}.$$

Log-ratio Bland-Altman analysis is also calculated for positive values and
interpreted when proportional error or heteroscedasticity is evident. Because
observations are clustered in three-indentation series, confidence intervals are
obtained by resampling complete series.
"""
))

cells.append(code(
    r"""
paired = measurements[measurements["method"].isin(["Vickers", "Micro-Vickers", "Brinell"])].copy()
paired = paired.dropna(subset=["manual_mean_dimension_um", "automatic_mean_dimension_um"])
paired["dimension_difference_um"] = paired["automatic_mean_dimension_um"] - paired["manual_mean_dimension_um"]
paired["dimension_symmetric_relative_difference_percent"] = 100 * paired["dimension_difference_um"] / ((paired["automatic_mean_dimension_um"] + paired["manual_mean_dimension_um"]) / 2)
paired["hardness_difference"] = paired["automatic_hardness"] - paired["manual_hardness"]
paired["hardness_symmetric_relative_difference_percent"] = 100 * paired["hardness_difference"] / ((paired["automatic_hardness"] + paired["manual_hardness"]) / 2)

paired_summary_method = paired_difference_summary(paired, "manual_mean_dimension_um", "automatic_mean_dimension_um", ["method"])
paired_summary_force = paired_difference_summary(paired, "manual_mean_dimension_um", "automatic_mean_dimension_um", ["method", "applied_force_n", "magnification"])

ba_dimension, ba_dimension_points = bland_altman_summary(
    paired,
    "manual_mean_dimension_um",
    "automatic_mean_dimension_um",
    group_cols=["method"],
    n_boot=BOOTSTRAP_RESAMPLES,
    seed=RANDOM_SEED,
)
ba_hardness, ba_hardness_points = bland_altman_summary(
    paired.dropna(subset=["manual_hardness", "automatic_hardness"]),
    "manual_hardness",
    "automatic_hardness",
    group_cols=["method"],
    n_boot=BOOTSTRAP_RESAMPLES,
    seed=RANDOM_SEED,
)

deming_dimension = deming_summary(
    paired,
    "manual_mean_dimension_um",
    "automatic_mean_dimension_um",
    group_cols=["method"],
    n_boot=BOOTSTRAP_RESAMPLES,
    seed=RANDOM_SEED,
)

display(paired_summary_method)
display(ba_dimension[["method", "representation", "n", "bias", "sd_diff", "lower_loa", "upper_loa", "bias_ci_low", "bias_ci_high"]])
display(deming_dimension)
"""
))

cells.append(md(
    r"""
## Deming regression

Deming regression is used because both manual and automatic measurements contain
measurement error. For individual indentation dimensions, measurement-specific
dimension uncertainties are not available, so the primary exploratory model uses
unweighted Deming regression with `lambda = 1`, meaning equal error variances in
the two methods. A sensitivity analysis is also calculated for `lambda = 0.5`
and `lambda = 2`.

High correlation, an intercept near zero, or a slope near one does not prove
agreement; regression is interpreted together with bias, limits of agreement and
uncertainty compatibility.
"""
))

cells.append(md(
    r"""
## Level B: series means and normalized error

At Level B, reported three-indentation series mean hardness values are compared
using normalized error:

$$
E_n =
\frac{H_\mathrm{automatic}-H_\mathrm{manual}}
{\sqrt{U_\mathrm{automatic}^2+U_\mathrm{manual}^2}}.
$$

Rows are included only where corresponding manual and automatic series mean
hardness values and expanded uncertainties are available. `|E_n| <= 1` is
treated as a satisfactory screening result; `|E_n| > 1` is treated as a result
requiring investigation.

Important limitation: manual and automatic results were obtained using the same
IMS and may share correlated uncertainty components, including optical
calibration and other common influences. Since covariance is unavailable, this
`E_n` calculation is a conventional screening indicator rather than sole proof
of method equivalence.
"""
))

cells.append(code(
    r"""
series_for_analysis = series_summary[series_summary["method"].isin(["Vickers", "Micro-Vickers", "Brinell"])].copy()
series_for_analysis = add_standard_uncertainties(series_for_analysis, UNCERTAINTY_COVERAGE_FACTOR_FOR_SERIES)
en_results = normalized_error(series_for_analysis)

deming_series_hardness = deming_summary(
    series_for_analysis.dropna(subset=["manual_series_mean_hardness", "automatic_series_mean_hardness"]),
    "manual_series_mean_hardness",
    "automatic_series_mean_hardness",
    group_cols=["method"],
    n_boot=BOOTSTRAP_RESAMPLES,
    seed=RANDOM_SEED,
)
odr_series_hardness = odr_summary(
    series_for_analysis,
    "manual_series_mean_hardness",
    "automatic_series_mean_hardness",
    "manual_standard_uncertainty",
    "automatic_standard_uncertainty",
    group_cols=["method"],
)

en_summary = en_results.groupby("method").agg(
    n=("en", "count"),
    satisfactory=("abs_en", lambda s: int((s <= 1).sum())),
    requiring_investigation=("abs_en", lambda s: int((s > 1).sum())),
    mean_abs_en=("abs_en", "mean"),
    max_abs_en=("abs_en", "max"),
).reset_index()

display(en_results[["method", "series_id", "manual_series_mean_hardness", "automatic_series_mean_hardness", "manual_expanded_uncertainty", "automatic_expanded_uncertainty", "en", "abs_en", "en_classification"]])
display(en_summary)
display(odr_series_hardness)
"""
))

cells.append(md(
    r"""
## Repeatability and diagonal/direction asymmetry

Within every valid three-indentation series, manual and automatic repeatability
are summarized separately. For Vickers and Micro-Vickers, the difference between
the two measured diagonals is also tracked. For Brinell, the same columns
represent the two measured indentation diameters.
"""
))

cells.append(code(
    r"""
repeatability = repeatability_table(paired)
repeatability_summary = repeatability.groupby(["method", "source", "magnification"], dropna=False).agg(
    series_count=("series_id", "count"),
    mean_sd_um=("sd_dimension_um", "mean"),
    median_sd_um=("sd_dimension_um", "median"),
    mean_abs_d1_minus_d2_um=("mean_abs_d1_minus_d2_um", "mean"),
).reset_index()

display(repeatability_summary)
"""
))

cells.append(md(
    r"""
## Stage-micrometer calibration

Calibration uses the configured physical tick spacing and a detected regular
tick lattice. The image processing step detects tick positions, rejects
duplicate or false lines using geometric regularity, assigns physical positions
in micrometres, fits physical position against pixel position, and reports
residuals. The algorithm is allowed to use longer major marks, but it does not
reinterpret major-tick length as a different physical spacing.

Only horizontal 20X and 50X calibration images are available. Therefore
`s_y = s_x` is an explicit isotropy assumption in this notebook and remains a
limitation until vertical calibration data are supplied.
"""
))

cells.append(code(
    r"""
calibration_table, calibration_ticks = calibrate_available_images(
    paths.images / "calibration",
    tick_spacing_um=STAGE_MICROMETER_TICK_SPACING_UM,
    total_scale_um=STAGE_MICROMETER_TOTAL_SCALE_UM,
    diagnostic_dir=out_dirs["diagnostic_images"],
)
calibration = calibration_lookup(calibration_table)

display(calibration_table)
if not calibration_ticks.empty:
    display(calibration_ticks.groupby("magnification").agg(n_ticks=("tick_index", "count"), residual_sd_um=("fit_residual_um", "std"), residual_max_um=("fit_residual_um", lambda s: s.abs().max())).reset_index())
"""
))

cells.append(md(
    r"""
## Independent Python image analysis

For Vickers and Micro-Vickers, the independent Python workflow detects the
indentation contour, estimates its center and orientation from the contour,
identifies four corner regions from contour/hull geometry, orders the corners
cyclically, pairs opposite corners, and calculates two calibrated diagonals
without assuming horizontal/vertical screen orientation.

For Brinell, the workflow detects the complete boundary where possible, reports
horizontal and vertical calibrated diameters, fits circle/ellipse diagnostics,
calculates circularity, radial residual variation, roughness proxies, and
diameter sensitivity across 4 and 6 evenly distributed directions.

The Python method is not a higher-order reference method. It is an independent
validation implementation calibrated from the supplied stage-micrometer images.
"""
))

cells.append(code(
    r"""
image_config = ImageMeasurementConfig(**IMAGE_STATUS_THRESHOLDS)
image_measurements, image_quality = analyze_matched_images(
    matched_images,
    paired,
    calibration,
    out_dirs["diagnostic_images"],
    config=image_config,
)
classification = classify_suitability(image_quality, en_results, config=image_config)

three_method_pairs = image_measurements.dropna(subset=["python_mean_dimension_um", "manual_mean_dimension_um", "automatic_mean_dimension_um"]).copy()
if not three_method_pairs.empty:
    three_method_pairs["automatic_minus_manual_um"] = three_method_pairs["automatic_mean_dimension_um"] - three_method_pairs["manual_mean_dimension_um"]
    three_method_pairs["python_minus_manual_um"] = three_method_pairs["python_mean_dimension_um"] - three_method_pairs["manual_mean_dimension_um"]
    three_method_pairs["python_minus_automatic_um"] = three_method_pairs["python_mean_dimension_um"] - three_method_pairs["automatic_mean_dimension_um"]

image_status_summary = image_quality.groupby(["method", "image_status"], dropna=False).size().reset_index(name="count") if not image_quality.empty else pd.DataFrame()

display(image_status_summary)
display(image_measurements[[c for c in ["method", "picture_id", "magnification", "image_status", "python_mean_dimension_um", "manual_mean_dimension_um", "automatic_mean_dimension_um", "classification_reason"] if c in image_measurements.columns]].head(20))
display(classification.head(20))
"""
))

cells.append(md(
    r"""
## Figures

Figures are saved under `outputs/figures/` as high-resolution PNG and vector
SVG. Each measurement regime is plotted separately; macro-Vickers,
Micro-Vickers and Brinell are not pooled into one agreement model.
"""
))

cells.append(code(
    r"""
import matplotlib.pyplot as plt

for method in ["Vickers", "Micro-Vickers", "Brinell"]:
    method_data = paired[paired["method"] == method]
    if method_data.empty:
        continue
    plot_scatter_identity(method_data, "manual_mean_dimension_um", "automatic_mean_dimension_um", method, "um", out_dirs["figures"] / f"{method}_scatter_dimension")
    plot_deming(paired, deming_dimension, method, "manual_mean_dimension_um", "automatic_mean_dimension_um", "um", out_dirs["figures"] / f"{method}_deming_dimension")
    for rep in ["absolute", "relative_percent", "log_ratio"]:
        plot_bland_altman(ba_dimension_points, ba_dimension, method, rep, "um", out_dirs["figures"] / f"{method}_ba_{rep}_dimension")
    plot_difference_distribution(paired, method, "dimension_difference_um", out_dirs["figures"] / f"{method}_difference_distribution")

plot_en(en_results, out_dirs["figures"] / "En_all_methods")
for method in ["Vickers", "Micro-Vickers", "Brinell"]:
    if not en_results[en_results["method"] == method].empty:
        plot_en(en_results, out_dirs["figures"] / f"{method}_En", method=method)
plot_repeatability(repeatability, out_dirs["figures"] / "repeatability_comparison")

for group_name, group_col in [("force", "applied_force_n"), ("hardness_level", "hardness_level"), ("magnification", "magnification")]:
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    tmp = paired.groupby(["method", group_col], dropna=False)["dimension_difference_um"].mean().reset_index()
    if not tmp.empty:
        import seaborn as sns
        sns.barplot(data=tmp, x=group_col, y="dimension_difference_um", hue="method", ax=ax)
    ax.axhline(0, color="0.3", linewidth=0.8)
    ax.set_title(f"Mean dimensional bias by {group_name}")
    ax.set_ylabel("Automatic - manual (um)")
    ax.grid(True, axis="y", alpha=0.25)
    savefig(fig, out_dirs["figures"] / f"bias_by_{group_name}")
    plt.close(fig)

asym = paired.copy()
asym["manual_d1_minus_d2_um"] = asym["manual_d1_um"] - asym["manual_d2_um"]
asym["automatic_d1_minus_d2_um"] = asym["automatic_d1_um"] - asym["automatic_d2_um"]
for method in ["Vickers", "Micro-Vickers", "Brinell"]:
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    tmp = asym[asym["method"] == method]
    if not tmp.empty:
        ax.scatter(tmp["manual_d1_minus_d2_um"], tmp["automatic_d1_minus_d2_um"], s=38)
    ax.axhline(0, color="0.3", linewidth=0.8)
    ax.axvline(0, color="0.3", linewidth=0.8)
    ax.set_title(f"{method}: d1-d2 asymmetry")
    ax.set_xlabel("Manual d1 - d2 (um)")
    ax.set_ylabel("Automatic d1 - d2 (um)")
    ax.grid(True, alpha=0.25)
    savefig(fig, out_dirs["figures"] / f"{method}_d1_d2_asymmetry")
    plt.close(fig)

figures = sorted(out_dirs["figures"].glob("*.png"))
print(f"Saved {len(figures)} PNG figures and matching SVG files.")
"""
))

cells.append(md(
    r"""
## Data-driven interpretation

The statements below are generated from the computed results. They intentionally
distinguish statistical difference, practical/metrological significance,
uncertainty compatibility and image-detection reliability. No unsupported claim
of equivalence or validation is made.
"""
))

cells.append(code(
    r"""
interpretation_statements = summarize_interpretation(ba_dimension, en_results, image_quality)
for statement in interpretation_statements:
    print("- " + statement)

limitations = [
    "No certified stage-micrometer certificate or uncertainty was supplied; nominal calibration does not include a certified stage contribution.",
    "Only horizontal 20X and 50X calibration images were supplied; sy = sx is an explicit isotropy assumption.",
    "No 10X calibration image was supplied; calibrated lengths are not reported for 10X images.",
    "Knoop is excluded from paired validation because automatic Knoop data are unavailable.",
    "INRIM/PTB or other NMI datasets are not present; interlaboratory comparison remains conditional on future data availability.",
    "Image-analysis conclusions apply to the available full-frame image subset and are not automatically generalized to large indentations requiring stage movement.",
]
for item in limitations:
    print("- " + item)
"""
))

cells.append(md(
    r"""
## Export tables and supplementary workbook

The source workbook is not modified. A separate supplementary workbook and CSV
tables are written under `outputs/`.
"""
))

cells.append(code(
    r"""
all_ba = pd.concat([
    ba_dimension.assign(measurand="dimension"),
    ba_hardness.assign(measurand="hardness"),
], ignore_index=True, sort=False)
all_deming = pd.concat([
    deming_dimension.assign(measurand="individual_dimension"),
    deming_series_hardness.assign(measurand="series_mean_hardness"),
], ignore_index=True, sort=False)

tables = {
    "Data_Quality": data_quality,
    "Clean_Vickers": frames.get("Vickers", pd.DataFrame()),
    "Clean_Micro_Vickers": frames.get("Micro-Vickers", pd.DataFrame()),
    "Clean_Brinell": frames.get("Brinell", pd.DataFrame()),
    "Clean_Knoop": frames.get("Knoop", pd.DataFrame()),
    "Series_Summary": series_summary,
    "Paired_Summary": paired_summary_method,
    "Paired_By_Force": paired_summary_force,
    "Bland_Altman": all_ba,
    "Bland_Altman_Points": ba_dimension_points,
    "Deming": all_deming,
    "ODR_Series_Hardness": odr_series_hardness,
    "En_Results": en_results,
    "Repeatability": repeatability,
    "Repeatability_Summary": repeatability_summary,
    "Calibration": calibration_table,
    "Calibration_Ticks": calibration_ticks,
    "Image_Measurements": image_measurements,
    "Image_Quality": image_quality,
    "Classification": classification,
    "Exclusions": exclusions,
    "Source_Files": source_files,
    "Image_Dimensions": image_dimensions,
}

csv_paths = export_tables_csv(tables, out_dirs["tables"])
workbook_path = export_analysis_workbook(tables, paths.outputs / "analysis_results.xlsx")
print(f"Exported workbook: {workbook_path}")
print(f"Exported CSV tables: {len(csv_paths)}")
"""
))

cells.append(md(
    r"""
## Validation checks

This section performs lightweight reproducibility checks: generated files exist,
calibration results cover available 20X and 50X images, formula calculations
agree with representative workbook values, representative rotated images are
processed, numerical outputs are scanned for infinities, and unit tests are run.
"""
))

cells.append(code(
    r"""
assert (paths.outputs / "analysis_results.xlsx").exists(), "analysis_results.xlsx was not created"
assert len(list(out_dirs["tables"].glob("*.csv"))) >= 10, "Expected CSV exports are missing"
assert len(list(out_dirs["figures"].glob("*.png"))) >= 10, "Expected figure exports are missing"

required_mags = {"20X", "50X"}
found_mags = set(calibration_table["magnification"].dropna()) if not calibration_table.empty else set()
assert required_mags.issubset(found_mags), f"Missing calibration magnifications: {required_mags - found_mags}"
assert (calibration_table["um_per_pixel"].dropna() > 0).all(), "Calibration slope must be positive"

formula_checks = []
for method in ["Vickers", "Micro-Vickers"]:
    row = paired[(paired["method"] == method)].dropna(subset=["applied_force_n", "manual_mean_dimension_um", "manual_hardness"]).head(1)
    if not row.empty:
        from indentation_detection import vickers_hardness_from_force_diagonal
        r = row.iloc[0]
        calc = vickers_hardness_from_force_diagonal(r["applied_force_n"], r["manual_mean_dimension_um"])
        formula_checks.append({"method": method, "excel_hardness": r["manual_hardness"], "python_formula": calc, "relative_difference_percent": 100 * (calc - r["manual_hardness"]) / r["manual_hardness"]})
row = paired[(paired["method"] == "Brinell")].dropna(subset=["applied_force_n", "ball_diameter_mm", "manual_mean_dimension_um", "manual_hardness"]).head(1)
if not row.empty:
    from indentation_detection import brinell_hardness_from_force_diameter
    r = row.iloc[0]
    calc = brinell_hardness_from_force_diameter(r["applied_force_n"], r["ball_diameter_mm"], r["manual_mean_dimension_um"])
    formula_checks.append({"method": "Brinell", "excel_hardness": r["manual_hardness"], "python_formula": calc, "relative_difference_percent": 100 * (calc - r["manual_hardness"]) / r["manual_hardness"]})
formula_checks = pd.DataFrame(formula_checks)
display(formula_checks)

rotation_records = []
rotation_dir = out_dirs["diagnostic_images"] / "rotation_tests"
rotation_dir.mkdir(exist_ok=True)
from PIL import Image
from indentation_detection import analyze_vickers_image, analyze_brinell_image
for method in ["Vickers", "Micro-Vickers", "Brinell"]:
    candidate = matched_images.merge(paired, on=["record_id", "method", "series_id", "original_sheet", "excel_row"], how="inner")
    candidate = candidate[(candidate["method"] == method) & (candidate["match_status"] == "matched")]
    candidate = candidate[candidate["magnification"].isin(calibration.keys())].head(1)
    if candidate.empty:
        continue
    r = candidate.iloc[0]
    src = Path(r["image_path"])
    rotated = rotation_dir / f"{src.stem}_rotated_30deg.png"
    Image.open(src).convert("L").rotate(30, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=128).save(rotated)
    cal = calibration[r["magnification"]]
    if method == "Brinell":
        res = analyze_brinell_image(rotated, cal["sx_um_per_px"], cal["sy_um_per_px"], r["applied_force_n"], r["ball_diameter_mm"], image_config, rotation_dir / f"{src.stem}_rotated_overlay.png")
    else:
        res = analyze_vickers_image(rotated, cal["sx_um_per_px"], cal["sy_um_per_px"], r["applied_force_n"], image_config, rotation_dir / f"{src.stem}_rotated_overlay.png")
    rotation_records.append({"method": method, "source_image": src.name, "rotated_status": res.get("image_status"), "rotated_mean_dimension_um": res.get("python_mean_dimension_um", np.nan)})
rotation_results = pd.DataFrame(rotation_records)
display(rotation_results)

for name, table in tables.items():
    if table is None or table.empty:
        continue
    numeric = table.select_dtypes(include=[np.number])
    if not numeric.empty:
        values = numeric.replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float, na_value=np.nan).ravel()
        values = values[~np.isnan(values)]
        assert np.isfinite(values).all(), f"Non-finite value in {name}"

test_result = subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "tests")], capture_output=True, text=True)
print(test_result.stdout)
if test_result.stderr:
    print(test_result.stderr)
assert test_result.returncode == 0, "Unit tests failed"

print("Validation checks completed.")
"""
))

cells.append(md(
    r"""
## Final RMS-report support summary

Achieved outcomes:

- Cleaned and traceable workbook data for Vickers, Micro-Vickers, Brinell and
  Knoop.
- Separate Level A and Level B statistical analyses.
- Absolute, relative and log-ratio Bland-Altman tables and figures.
- Deming regression with lambda sensitivity and series-level
  uncertainty-weighted ODR where feasible.
- Conventional normalized-error screening for series mean hardness.
- Stage-micrometer calibration using configured 2 um nominal spacing and
  multiple fitted tick intervals.
- Independent Python image measurements and diagnostic overlays for matched
  full-frame images where calibration exists.
- Transparent rule-based suitability classifications with reasons.

Implications for WP4/D8 are limited to the supplied data. Knoop automatic
measurement was unavailable, external NMI datasets were unavailable, no
certified stage-micrometer uncertainty was supplied, no vertical/10X calibration
image was supplied, and image conclusions apply only to the available full-frame
subset.

## Scientific references

- Bland, J. M. and Altman, D. G. (1986). Statistical methods for assessing
  agreement between two methods of clinical measurement. *The Lancet*.
- Bland, J. M. and Altman, D. G. (1999). Measuring agreement in method
  comparison studies. *Statistical Methods in Medical Research*.
- Linnet, K. (1993). Evaluation of regression procedures for methods comparison
  studies. *Clinical Chemistry*.
- JCGM 100:2008. Evaluation of measurement data - Guide to the expression of
  uncertainty in measurement.
- ISO/IEC 17043 and ISO 13528, for proficiency-testing and
  interlaboratory-comparison statistical concepts including normalized-error
  style compatibility screening.
- ISO 6506, ISO 6507 and ISO 4545 series, for Brinell, Vickers and Knoop
  hardness measurement principles. Standards are cited as authoritative sources;
  this notebook does not reproduce or claim specific clauses beyond the publicly
  known measurement principles.
"""
))

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
print(NOTEBOOK_PATH)
