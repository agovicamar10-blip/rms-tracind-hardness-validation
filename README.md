# RMS indentation validation

This repository contains a reproducible Python/Jupyter workflow for the Research
Mobility Support work connected to EURAMET project 22RPT01 TracInd BVK-H. The
analysis compares manual and automatic GSV HARDNESS indentation measurements,
performs agreement and uncertainty-screening analyses, and runs an independent
calibrated image-processing workflow on the supplied indentation images.

## Repository structure

```text
data/
  Hardness_measurement_results.xlsx
docs/
  APPLICATION.docx
  RMS Sampling.docx
  Research Mobility Support (RMS) Applicants Guide.pdf
  22RPT01 Tracind BVK-H Annex 1 v1.0.pdf
images/
  indentations/
  calibration/
notebooks/
  RMS_indentation_validation.ipynb
src/
  data_processing.py
  agreement_analysis.py
  image_calibration.py
  indentation_detection.py
  reporting.py
outputs/
  analysis_results.xlsx
  tables/
  figures/
  diagnostic_images/
tests/
  test_core_formulas.py
```

The raw workbook and source images are read-only inputs. The notebook writes
new result files under `outputs/` and does not modify
`data/Hardness_measurement_results.xlsx`.

## Installation

Using pip:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Using conda or mamba:

```bash
conda env create -f environment.yml
conda activate rms-indentation-validation
```

## Running the notebook

Open and run:

```text
notebooks/RMS_indentation_validation.ipynb
```

The notebook includes a repository-root finder, so it can be launched from the
repository root or from the `notebooks/` directory. Viewing the `.ipynb` file on
GitHub does not execute it. To reproduce the analysis, clone or download the
repository and run the notebook locally, or configure a Binder/Colab workflow
that includes the data files.

The normal local workflow uses relative repository paths and does not download
source data from hardcoded internet URLs.

## Input-data requirements

The workbook is expected at `data/Hardness_measurement_results.xlsx`. It may
contain merged two-row headers and the sheet name `Mirco-Vickers`; the workflow
handles that spelling without changing the source workbook. Knoop measurements
are counted and described, but Knoop is excluded from paired manual-versus-
automatic validation because automatic Knoop measurements are unavailable.

Indentation images are matched to workbook records by exact case-insensitive
filename stem in the `Picture ID` column. Supported image extensions are
`.bmp`, `.BMP`, `.png`, `.tif`, and `.tiff`. Partial filename similarity is not
used for matching.

## Stage-micrometer configuration

The supplied calibration images are interpreted provisionally as a stage
micrometer marked `0.1 mm / 0.002 mm div`, meaning:

- nominal total scale length: 100 um;
- nominal adjacent-division spacing: 2 um;
- approximately 50 intervals across the nominal scale.

These values are placed in the notebook configuration cell:

```python
STAGE_MICROMETER_TICK_SPACING_UM = 2.0
STAGE_MICROMETER_TOTAL_SCALE_UM = 100.0
STAGE_MICROMETER_TICK_SPACING_STANDARD_UNCERTAINTY_UM = None
STAGE_MICROMETER_TICK_SPACING_EXPANDED_UNCERTAINTY_UM = None
STAGE_MICROMETER_COVERAGE_FACTOR = None
```

If a calibration certificate becomes available, enter the certified spacing and
uncertainty values in that configuration cell and document the source. Without a
certificate, the independent Python image-measurement uncertainty does not
include a certified stage-micrometer contribution.

Only 20X and 50X stage-micrometer images are currently present. Images acquired
at 10X can be classified qualitatively, but calibrated lengths in micrometres
should not be reported unless a compatible 10X calibration image is added.

## Outputs

The notebook creates:

- `outputs/analysis_results.xlsx` with README, cleaned data, agreement,
  regression, normalized-error, repeatability, calibration, image-measurement,
  image-quality, classification, and exclusion sheets;
- CSV copies of important result tables in `outputs/tables/`;
- publication-oriented figures in `outputs/figures/`;
- calibration and indentation diagnostic overlays in
  `outputs/diagnostic_images/`.

## Known limitations

- No certified stage-micrometer certificate or uncertainty file is supplied.
- No vertical calibration image is supplied; the workflow documents the explicit
  isotropy assumption when using the horizontal calibration for both axes.
- No 10X calibration image is supplied.
- External INRIM/PTB/NMI datasets are not present, so interlaboratory comparison
  is not performed.
- No project-specific acceptance criterion for practical equivalence or limit of
  agreement width is supplied. The notebook reports statistical and metrological
  screening results cautiously.
- Large BMP source images should be kept unchanged. If this repository is pushed
  to GitHub and file size becomes problematic, use Git LFS for the raw BMPs
  rather than converting or compressing the scientific source images.

