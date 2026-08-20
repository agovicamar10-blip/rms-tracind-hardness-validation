"""Statistical agreement analysis for indentation measurements."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable

import numpy as np
import pandas as pd


try:  # SciPy is part of the reproducible environment, but keep import graceful.
    from scipy import odr, stats
except Exception:  # pragma: no cover - exercised only in incomplete environments
    odr = None
    stats = None


@dataclass(frozen=True)
class DemingResult:
    """Deming regression coefficients and diagnostics."""

    intercept: float
    slope: float
    lambda_ratio: float
    n: int
    residual_sd: float


def _as_arrays(manual: Iterable[float], automatic: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(list(manual), dtype=float)
    y = np.asarray(list(automatic), dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def mean_ci_normal(values: Iterable[float], alpha: float = 0.05) -> tuple[float, float]:
    """Normal/t confidence interval for the mean."""

    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.nan, np.nan
    if arr.size == 1 or stats is None:
        return float(arr.mean()), float(arr.mean())
    sem = arr.std(ddof=1) / math.sqrt(arr.size)
    q = stats.t.ppf(1 - alpha / 2, arr.size - 1)
    return float(arr.mean() - q * sem), float(arr.mean() + q * sem)


def mad(values: Iterable[float]) -> float:
    """Median absolute deviation scaled to be comparable with standard deviation."""

    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.nan
    return float(1.4826 * np.median(np.abs(arr - np.median(arr))))


def bland_altman_core(manual: Iterable[float], automatic: Iterable[float], representation: str) -> pd.DataFrame:
    """Return pair means and differences for one Bland-Altman representation."""

    x, y = _as_arrays(manual, automatic)
    if representation == "absolute":
        pair_mean = (x + y) / 2.0
        diff = y - x
    elif representation == "relative_percent":
        pair_mean = (x + y) / 2.0
        diff = 100.0 * (y - x) / pair_mean
    elif representation == "log_ratio":
        mask = (x > 0) & (y > 0)
        x = x[mask]
        y = y[mask]
        pair_mean = (np.log(x) + np.log(y)) / 2.0
        diff = np.log(y) - np.log(x)
    else:
        raise ValueError(f"Unknown Bland-Altman representation: {representation}")
    return pd.DataFrame({"pair_mean": pair_mean, "difference": diff, "manual": x, "automatic": y})


def _ba_stats(diff: np.ndarray) -> dict[str, float]:
    n = int(diff.size)
    if n == 0:
        return {
            "n": 0,
            "bias": np.nan,
            "sd_diff": np.nan,
            "lower_loa": np.nan,
            "upper_loa": np.nan,
        }
    sd = float(np.std(diff, ddof=1)) if n > 1 else 0.0
    bias = float(np.mean(diff))
    return {
        "n": n,
        "bias": bias,
        "sd_diff": sd,
        "lower_loa": bias - 1.96 * sd,
        "upper_loa": bias + 1.96 * sd,
    }


def cluster_bootstrap_ci(
    df: pd.DataFrame,
    cluster_col: str,
    stat_func: Callable[[pd.DataFrame], dict[str, float]],
    n_boot: int = 2000,
    seed: int = 20260820,
    alpha: float = 0.05,
) -> dict[str, tuple[float, float]]:
    """Bootstrap confidence intervals by resampling whole clusters."""

    if df.empty or cluster_col not in df or n_boot <= 0:
        return {}
    clusters = np.asarray(sorted(df[cluster_col].dropna().unique()))
    if clusters.size < 2:
        return {}
    rng = np.random.default_rng(seed)
    boot_records: list[dict[str, float]] = []
    grouped = {cluster: group for cluster, group in df.groupby(cluster_col)}
    for _ in range(n_boot):
        selected = rng.choice(clusters, size=clusters.size, replace=True)
        sample = pd.concat([grouped[c] for c in selected], ignore_index=True)
        boot_records.append(stat_func(sample))
    boot = pd.DataFrame(boot_records)
    ci: dict[str, tuple[float, float]] = {}
    for col in boot.columns:
        series = boot[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(series) > 5:
            ci[col] = (
                float(series.quantile(alpha / 2)),
                float(series.quantile(1 - alpha / 2)),
            )
    return ci


def bland_altman_summary(
    df: pd.DataFrame,
    manual_col: str,
    automatic_col: str,
    group_cols: list[str],
    cluster_col: str = "series_id",
    n_boot: int = 2000,
    seed: int = 20260820,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate absolute, relative, and log-ratio Bland-Altman summaries."""

    summary_records: list[dict[str, float | str]] = []
    point_records: list[pd.DataFrame] = []
    reps = ["absolute", "relative_percent", "log_ratio"]

    if not group_cols:
        grouped = [("All", df)]
    else:
        grouped = list(df.groupby(group_cols, dropna=False))

    for group_key, group in grouped:
        group_values = group_key if isinstance(group_key, tuple) else (group_key,)
        group_dict = dict(zip(group_cols, group_values)) if group_cols else {}
        for rep in reps:
            ba_points = bland_altman_core(group[manual_col], group[automatic_col], rep)
            if ba_points.empty:
                continue
            ba_points = ba_points.assign(**group_dict, representation=rep, source_index=group.index[: len(ba_points)].to_numpy())
            metadata_cols = [
                cluster_col,
                "magnification",
                "hardness_scale",
                "hardness_level",
                "applied_force_n",
                "ball_diameter_mm",
                "serial_number",
            ]
            for metadata_col in metadata_cols:
                if metadata_col in group and metadata_col not in ba_points:
                    ba_points[metadata_col] = group[metadata_col].iloc[: len(ba_points)].to_numpy()
            point_records.append(ba_points)

            stats_row = _ba_stats(ba_points["difference"].to_numpy())
            ci = cluster_bootstrap_ci(
                ba_points,
                cluster_col=cluster_col,
                stat_func=lambda x: _ba_stats(x["difference"].to_numpy()),
                n_boot=n_boot,
                seed=seed,
            )
            record: dict[str, float | str] = {**group_dict, "representation": rep, **stats_row}
            for key, (lo, hi) in ci.items():
                record[f"{key}_ci_low"] = lo
                record[f"{key}_ci_high"] = hi

            if stats is not None and len(ba_points) >= 3:
                slope, intercept, r_value, p_value, _ = stats.linregress(
                    ba_points["pair_mean"], ba_points["difference"]
                )
                record["proportional_bias_slope"] = float(slope)
                record["proportional_bias_p"] = float(p_value)
                if len(ba_points) >= 4:
                    record["absdiff_pairmean_spearman"] = float(
                        stats.spearmanr(np.abs(ba_points["difference"]), ba_points["pair_mean"], nan_policy="omit").correlation
                    )
            summary_records.append(record)

    points = pd.concat(point_records, ignore_index=True) if point_records else pd.DataFrame()
    return pd.DataFrame(summary_records), points


def deming_regression(manual: Iterable[float], automatic: Iterable[float], lambda_ratio: float = 1.0) -> DemingResult:
    """Unweighted Deming regression for measurements with errors in both axes.

    ``lambda_ratio`` is the assumed error-variance ratio, conventionally
    var(error_x) / var(error_y).
    """

    x, y = _as_arrays(manual, automatic)
    n = int(x.size)
    if n < 2:
        return DemingResult(np.nan, np.nan, lambda_ratio, n, np.nan)
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    sxx = float(np.mean((x - x_mean) ** 2))
    syy = float(np.mean((y - y_mean) ** 2))
    sxy = float(np.mean((x - x_mean) * (y - y_mean)))
    if abs(sxy) < np.finfo(float).eps:
        return DemingResult(np.nan, np.nan, lambda_ratio, n, np.nan)
    term = syy - lambda_ratio * sxx
    slope = (term + math.sqrt(term * term + 4 * lambda_ratio * sxy * sxy)) / (2 * sxy)
    intercept = y_mean - slope * x_mean
    residual = y - (intercept + slope * x)
    residual_sd = float(np.std(residual, ddof=1)) if n > 2 else np.nan
    return DemingResult(float(intercept), float(slope), float(lambda_ratio), n, residual_sd)


def deming_summary(
    df: pd.DataFrame,
    manual_col: str,
    automatic_col: str,
    group_cols: list[str],
    lambdas: Iterable[float] = (0.5, 1.0, 2.0),
    cluster_col: str = "series_id",
    n_boot: int = 2000,
    seed: int = 20260820,
) -> pd.DataFrame:
    """Calculate Deming regression summaries and bootstrap intervals."""

    records: list[dict[str, float | str]] = []
    grouped = list(df.groupby(group_cols, dropna=False)) if group_cols else [("All", df)]
    for group_key, group in grouped:
        group_values = group_key if isinstance(group_key, tuple) else (group_key,)
        group_dict = dict(zip(group_cols, group_values)) if group_cols else {}
        data = group.dropna(subset=[manual_col, automatic_col]).copy()
        for lam in lambdas:
            result = deming_regression(data[manual_col], data[automatic_col], lambda_ratio=float(lam))
            record: dict[str, float | str] = {
                **group_dict,
                "model": "unweighted_deming",
                "lambda_ratio": float(lam),
                "n": result.n,
                "intercept": result.intercept,
                "slope": result.slope,
                "residual_sd": result.residual_sd,
            }
            if result.n >= 4:
                def stat_func(sample: pd.DataFrame) -> dict[str, float]:
                    r = deming_regression(sample[manual_col], sample[automatic_col], lambda_ratio=float(lam))
                    return {"intercept": r.intercept, "slope": r.slope}

                ci = cluster_bootstrap_ci(data, cluster_col, stat_func, n_boot=n_boot, seed=seed)
                for key, (lo, hi) in ci.items():
                    record[f"{key}_ci_low"] = lo
                    record[f"{key}_ci_high"] = hi
            records.append(record)
    return pd.DataFrame(records)


def odr_summary(
    df: pd.DataFrame,
    manual_col: str,
    automatic_col: str,
    manual_u_col: str,
    automatic_u_col: str,
    group_cols: list[str],
) -> pd.DataFrame:
    """Uncertainty-weighted orthogonal-distance regression for series means."""

    records: list[dict[str, float | str]] = []
    if odr is None:
        return pd.DataFrame(
            [{"model": "weighted_odr", "status": "not_run", "reason": "scipy.odr is unavailable"}]
        )
    grouped = list(df.groupby(group_cols, dropna=False)) if group_cols else [("All", df)]
    for group_key, group in grouped:
        group_values = group_key if isinstance(group_key, tuple) else (group_key,)
        group_dict = dict(zip(group_cols, group_values)) if group_cols else {}
        data = group.dropna(subset=[manual_col, automatic_col, manual_u_col, automatic_u_col])
        if len(data) < 3:
            records.append({**group_dict, "model": "weighted_odr", "status": "not_run", "reason": "n < 3", "n": len(data)})
            continue
        x = data[manual_col].to_numpy(float)
        y = data[automatic_col].to_numpy(float)
        sx = data[manual_u_col].to_numpy(float)
        sy = data[automatic_u_col].to_numpy(float)
        if np.any(sx <= 0) or np.any(sy <= 0):
            records.append({**group_dict, "model": "weighted_odr", "status": "not_run", "reason": "nonpositive uncertainty", "n": len(data)})
            continue
        model = odr.Model(lambda beta, xx: beta[0] + beta[1] * xx)
        data_obj = odr.RealData(x, y, sx=sx, sy=sy)
        fit = odr.ODR(data_obj, model, beta0=[0.0, 1.0]).run()
        records.append(
            {
                **group_dict,
                "model": "weighted_odr",
                "status": "run",
                "n": len(data),
                "intercept": float(fit.beta[0]),
                "slope": float(fit.beta[1]),
                "intercept_sd": float(fit.sd_beta[0]),
                "slope_sd": float(fit.sd_beta[1]),
                "residual_variance": float(fit.res_var),
            }
        )
    return pd.DataFrame(records)


def normalized_error(series_summary: pd.DataFrame) -> pd.DataFrame:
    """Calculate signed and absolute normalized error from series mean hardness."""

    required = [
        "manual_series_mean_hardness",
        "automatic_series_mean_hardness",
        "manual_expanded_uncertainty",
        "automatic_expanded_uncertainty",
    ]
    data = series_summary.dropna(subset=required).copy()
    numerator = data["automatic_series_mean_hardness"] - data["manual_series_mean_hardness"]
    denominator = np.sqrt(data["automatic_expanded_uncertainty"] ** 2 + data["manual_expanded_uncertainty"] ** 2)
    data["en_numerator"] = numerator
    data["en_denominator"] = denominator
    data["en"] = numerator / denominator
    data["abs_en"] = data["en"].abs()
    data["en_classification"] = np.where(
        data["abs_en"] <= 1.0,
        "satisfactory screening result",
        "result requiring investigation",
    )
    return data


def paired_difference_summary(
    df: pd.DataFrame,
    manual_col: str,
    automatic_col: str,
    group_cols: list[str],
) -> pd.DataFrame:
    """Additional paired-difference statistics for relevant groups."""

    records: list[dict[str, float | str]] = []
    grouped = list(df.groupby(group_cols, dropna=False)) if group_cols else [("All", df)]
    for group_key, group in grouped:
        group_values = group_key if isinstance(group_key, tuple) else (group_key,)
        group_dict = dict(zip(group_cols, group_values)) if group_cols else {}
        data = group.dropna(subset=[manual_col, automatic_col]).copy()
        x = data[manual_col].to_numpy(float)
        y = data[automatic_col].to_numpy(float)
        diff = y - x
        n = len(diff)
        if n == 0:
            continue
        ci_low, ci_high = mean_ci_normal(diff)
        record: dict[str, float | str] = {
            **group_dict,
            "n": n,
            "mean_difference": float(np.mean(diff)),
            "median_difference": float(np.median(diff)),
            "sd_difference": float(np.std(diff, ddof=1)) if n > 1 else np.nan,
            "mad_difference": mad(diff),
            "iqr_difference": float(np.percentile(diff, 75) - np.percentile(diff, 25)) if n > 1 else 0.0,
            "rmse": float(np.sqrt(np.mean(diff**2))),
            "mae": float(np.mean(np.abs(diff))),
            "symmetric_mean_relative_difference_percent": float(np.mean(100 * diff / ((x + y) / 2))),
            "bias_ci_low": ci_low,
            "bias_ci_high": ci_high,
            "cohens_dz": float(np.mean(diff) / np.std(diff, ddof=1)) if n > 1 and np.std(diff, ddof=1) > 0 else np.nan,
        }
        if stats is not None and n >= 2:
            record["paired_t_p"] = float(stats.ttest_rel(y, x, nan_policy="omit").pvalue)
            try:
                record["wilcoxon_p"] = float(stats.wilcoxon(y, x, zero_method="wilcox").pvalue)
            except ValueError:
                record["wilcoxon_p"] = np.nan
        records.append(record)
    return pd.DataFrame(records)


def repeatability_table(df: pd.DataFrame) -> pd.DataFrame:
    """Within-series repeatability metrics for manual and automatic readings."""

    records: list[dict[str, float | str]] = []
    methods = [m for m in ["manual", "automatic"] if f"{m}_mean_dimension_um" in df.columns]
    for series_id, group in df.groupby("series_id", dropna=False):
        first = group.iloc[0]
        for source in methods:
            dim_col = f"{source}_mean_dimension_um"
            d1_col = f"{source}_d1_um"
            d2_col = f"{source}_d2_um"
            values = group[dim_col].dropna().to_numpy(float)
            if len(values) == 0:
                continue
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else np.nan
            record: dict[str, float | str] = {
                "series_id": series_id,
                "method": first["method"],
                "source": source,
                "serial_number": first["serial_number"],
                "hardness_scale": first["hardness_scale"],
                "hardness_level": first["hardness_level"],
                "applied_force_n": first.get("applied_force_n", np.nan),
                "ball_diameter_mm": first.get("ball_diameter_mm", np.nan),
                "magnification": first["magnification"],
                "n": len(values),
                "mean_dimension_um": mean,
                "sd_dimension_um": std,
                "cv_percent": 100 * std / mean if mean and np.isfinite(std) else np.nan,
                "range_dimension_um": float(np.max(values) - np.min(values)),
            }
            if d1_col in group and d2_col in group:
                asym = (group[d1_col] - group[d2_col]).dropna()
                record["mean_d1_minus_d2_um"] = float(asym.mean()) if len(asym) else np.nan
                record["mean_abs_d1_minus_d2_um"] = float(asym.abs().mean()) if len(asym) else np.nan
            records.append(record)
    return pd.DataFrame(records)


def add_standard_uncertainties(series_summary: pd.DataFrame, coverage_factor: float | None = 2.0) -> pd.DataFrame:
    """Add standard-uncertainty columns from expanded uncertainties."""

    out = series_summary.copy()
    if coverage_factor is None or coverage_factor <= 0:
        out["manual_standard_uncertainty"] = np.nan
        out["automatic_standard_uncertainty"] = np.nan
        return out
    out["manual_standard_uncertainty"] = out["manual_expanded_uncertainty"] / coverage_factor
    out["automatic_standard_uncertainty"] = out["automatic_expanded_uncertainty"] / coverage_factor
    return out
