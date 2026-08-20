"""Lightweight tests for core metrology formulas."""

from __future__ import annotations

import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agreement_analysis import deming_regression, normalized_error
from indentation_detection import calibrated_distance, vickers_hardness_from_force_diagonal
import pandas as pd


def test_calibrated_distance_anisotropic() -> None:
    assert math.isclose(calibrated_distance([0, 0], [3, 4], 2.0, 1.0), math.sqrt(52.0))


def test_vickers_hardness_formula() -> None:
    hv = vickers_hardness_from_force_diagonal(9.81, 100.0)
    assert math.isclose(hv, 185.531, rel_tol=5e-4)


def test_normalized_error_formula() -> None:
    df = pd.DataFrame(
        {
            "method": ["Vickers"],
            "series_id": ["s1"],
            "manual_series_mean_hardness": [100.0],
            "automatic_series_mean_hardness": [102.0],
            "manual_expanded_uncertainty": [3.0],
            "automatic_expanded_uncertainty": [4.0],
        }
    )
    out = normalized_error(df)
    assert math.isclose(float(out.loc[0, "en"]), 0.4)


def test_deming_identity() -> None:
    result = deming_regression([1, 2, 3, 4], [1, 2, 3, 4], lambda_ratio=1)
    assert math.isclose(result.intercept, 0.0, abs_tol=1e-12)
    assert math.isclose(result.slope, 1.0, abs_tol=1e-12)

