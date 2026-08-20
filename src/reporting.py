"""Reporting, plotting, and export helpers for the RMS notebook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def ensure_output_dirs(outputs: str | Path) -> dict[str, Path]:
    """Create and return standard output directories."""

    outputs = Path(outputs)
    dirs = {
        "outputs": outputs,
        "tables": outputs / "tables",
        "figures": outputs / "figures",
        "diagnostic_images": outputs / "diagnostic_images",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def safe_sheet_name(name: str) -> str:
    """Return an Excel-safe sheet name."""

    bad = set("[]:*?/\\")
    clean = "".join("_" if ch in bad else ch for ch in name)
    return clean[:31]


def _stringify_paths(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].map(lambda v: isinstance(v, Path)).any():
            out[col] = out[col].map(lambda v: str(v) if isinstance(v, Path) else v)
    return out


def export_tables_csv(tables: dict[str, pd.DataFrame], tables_dir: str | Path) -> list[Path]:
    """Export non-empty tables as CSV files."""

    tables_dir = Path(tables_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, table in tables.items():
        if table is None or table.empty:
            continue
        path = tables_dir / f"{safe_sheet_name(name)}.csv"
        _stringify_paths(table).to_csv(path, index=False)
        paths.append(path)
    return paths


def export_analysis_workbook(tables: dict[str, pd.DataFrame], output_path: str | Path) -> Path:
    """Export analysis tables to a separate workbook."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    readme = pd.DataFrame(
        [
            {
                "sheet": "README",
                "description": "Defines output tables, sign conventions and units.",
                "sign_convention": "Differences are automatic minus manual unless explicitly labelled otherwise.",
                "unit": "See table column name; indentation dimensions are in um.",
            },
            {
                "sheet": "Data_Quality",
                "description": "Counts, missing values, image matches and calibration assets found in the source data.",
                "sign_convention": "Not applicable.",
                "unit": "Counts or text.",
            },
            {
                "sheet": "Bland_Altman",
                "description": "Method-specific Bland-Altman bias, limits of agreement and bootstrap confidence intervals.",
                "sign_convention": "Automatic minus manual.",
                "unit": "um, percent, or log ratio depending on representation.",
            },
            {
                "sheet": "Deming",
                "description": "Error-in-variables regression results and lambda sensitivity.",
                "sign_convention": "x = manual, y = automatic.",
                "unit": "Same unit as fitted measurand.",
            },
            {
                "sheet": "En_Results",
                "description": "Normalized error from series mean hardness and expanded uncertainties.",
                "sign_convention": "Automatic minus manual in numerator.",
                "unit": "Dimensionless.",
            },
            {
                "sheet": "Image_Measurements",
                "description": "Independent Python image-processing measurements where image and calibration were available.",
                "sign_convention": "Python minus comparator where labelled.",
                "unit": "um and hardness units.",
            },
        ]
    )
    export_tables = {"README": readme, **tables}
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for name, table in export_tables.items():
            if table is None:
                table = pd.DataFrame()
            _stringify_paths(table).to_excel(writer, sheet_name=safe_sheet_name(name), index=False)
            ws = writer.book[safe_sheet_name(name)]
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.style = "Headline 4"
            for column_cells in ws.columns:
                values = [str(cell.value) if cell.value is not None else "" for cell in column_cells[:100]]
                width = min(max(len(v) for v in values) + 2, 48)
                ws.column_dimensions[column_cells[0].column_letter].width = width
    return output_path


def savefig(fig, path: str | Path) -> None:
    """Save a figure as high-resolution PNG and vector SVG."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")


def plot_scatter_identity(df: pd.DataFrame, manual_col: str, automatic_col: str, method: str, unit: str, output: str | Path):
    """Manual-vs-automatic scatterplot with identity line."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    data = df.dropna(subset=[manual_col, automatic_col])
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    sns.scatterplot(data=data, x=manual_col, y=automatic_col, hue="magnification", style="hardness_scale", ax=ax, s=48)
    if not data.empty:
        low = float(np.nanmin([data[manual_col].min(), data[automatic_col].min()]))
        high = float(np.nanmax([data[manual_col].max(), data[automatic_col].max()]))
        ax.plot([low, high], [low, high], color="0.25", linewidth=1, label="identity")
    ax.set_title(f"{method}: manual vs automatic (n={len(data)})")
    ax.set_xlabel(f"Manual ({unit})")
    ax.set_ylabel(f"Automatic IMS ({unit})")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    savefig(fig, output)
    return fig


def plot_bland_altman(points: pd.DataFrame, summary: pd.DataFrame, method: str, representation: str, unit: str, output: str | Path):
    """Bland-Altman plot for one method and representation."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    data = points[(points["method"] == method) & (points["representation"] == representation)].copy()
    stats = summary[(summary["method"] == method) & (summary["representation"] == representation)]
    fig, ax = plt.subplots(figsize=(6.8, 5.2))
    if not data.empty:
        hue = "magnification" if "magnification" in data.columns else None
        sns.scatterplot(data=data, x="pair_mean", y="difference", hue=hue, ax=ax, s=42)
    if not stats.empty:
        row = stats.iloc[0]
        ax.axhline(row["bias"], color="#d62728", linewidth=1.2, label="bias")
        ax.axhline(row["lower_loa"], color="0.25", linestyle="--", linewidth=1, label="95% LOA")
        ax.axhline(row["upper_loa"], color="0.25", linestyle="--", linewidth=1)
    ylabel = {
        "absolute": f"Automatic - manual ({unit})",
        "relative_percent": "Symmetric difference (%)",
        "log_ratio": "log(automatic) - log(manual)",
    }[representation]
    xlabel = "Pair mean" if representation != "log_ratio" else "Log pair mean"
    ax.set_title(f"{method}: {representation.replace('_', ' ')} Bland-Altman")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    savefig(fig, output)
    return fig


def plot_deming(df: pd.DataFrame, deming: pd.DataFrame, method: str, manual_col: str, automatic_col: str, unit: str, output: str | Path):
    """Plot Deming regression for lambda=1 with identity line."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    data = df[df["method"] == method].dropna(subset=[manual_col, automatic_col])
    fit = deming[(deming["method"] == method) & (deming["lambda_ratio"] == 1.0)]
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    sns.scatterplot(data=data, x=manual_col, y=automatic_col, hue="magnification", style="hardness_scale", ax=ax, s=48)
    if not data.empty:
        low = float(np.nanmin([data[manual_col].min(), data[automatic_col].min()]))
        high = float(np.nanmax([data[manual_col].max(), data[automatic_col].max()]))
        ax.plot([low, high], [low, high], color="0.25", linewidth=1, label="identity")
        if not fit.empty and np.isfinite(fit.iloc[0]["slope"]):
            x = np.linspace(low, high, 100)
            y = fit.iloc[0]["intercept"] + fit.iloc[0]["slope"] * x
            ax.plot(x, y, color="#d62728", linewidth=1.4, label="Deming lambda=1")
    ax.set_title(f"{method}: Deming regression")
    ax.set_xlabel(f"Manual ({unit})")
    ax.set_ylabel(f"Automatic IMS ({unit})")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    savefig(fig, output)
    return fig


def plot_en(en_results: pd.DataFrame, output: str | Path, method: str | None = None):
    """Plot normalized error by series."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    data = en_results.copy()
    if method:
        data = data[data["method"] == method]
    data = data.reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    if not data.empty:
        sns.scatterplot(data=data, x=data.index, y="en", hue="method", style="magnification", ax=ax, s=48)
    ax.axhline(1, color="#d62728", linestyle="--", linewidth=1)
    ax.axhline(-1, color="#d62728", linestyle="--", linewidth=1)
    ax.axhline(0, color="0.35", linewidth=0.8)
    ax.set_title("Normalized error by series" if method is None else f"{method}: normalized error")
    ax.set_xlabel("Series index")
    ax.set_ylabel("E_n")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    savefig(fig, output)
    return fig


def plot_difference_distribution(df: pd.DataFrame, method: str, diff_col: str, output: str | Path):
    """Paired-difference distribution for one method."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    data = df[df["method"] == method].copy()
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    if not data.empty:
        sns.histplot(data[diff_col].dropna(), kde=True, ax=ax, color="#1f77b4")
        ax.axvline(data[diff_col].mean(), color="#d62728", linewidth=1.2, label="mean")
    ax.set_title(f"{method}: paired-difference distribution")
    ax.set_xlabel(diff_col.replace("_", " "))
    ax.set_ylabel("Count")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    savefig(fig, output)
    return fig


def plot_repeatability(repeatability: pd.DataFrame, output: str | Path):
    """Compare within-series repeatability standard deviations."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    data = repeatability.dropna(subset=["sd_dimension_um"]).copy()
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    if not data.empty:
        sns.boxplot(data=data, x="method", y="sd_dimension_um", hue="source", ax=ax)
        sns.stripplot(data=data, x="method", y="sd_dimension_um", hue="source", dodge=True, ax=ax, color="0.25", size=3, alpha=0.6)
    ax.set_title("Within-series repeatability")
    ax.set_xlabel("Method")
    ax.set_ylabel("Within-series SD (um)")
    ax.grid(True, axis="y", alpha=0.25)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles[:2], labels[:2], fontsize=8)
    savefig(fig, output)
    return fig


def summarize_interpretation(
    bland_altman: pd.DataFrame,
    en_results: pd.DataFrame,
    image_quality: pd.DataFrame,
) -> list[str]:
    """Generate cautious factual interpretation statements from computed values."""

    statements: list[str] = []
    for method in ["Vickers", "Micro-Vickers", "Brinell"]:
        ba = bland_altman[(bland_altman["method"] == method) & (bland_altman["representation"] == "absolute")]
        if not ba.empty:
            row = ba.iloc[0]
            direction = "larger" if row["bias"] > 0 else "smaller" if row["bias"] < 0 else "similar"
            statements.append(
                f"{method}: automatic dimensions were on average {direction} than manual dimensions "
                f"(bias {row['bias']:.3g} um, n={int(row['n'])})."
            )
        en = en_results[en_results["method"] == method]
        if not en.empty:
            ok = int((en["abs_en"] <= 1).sum())
            statements.append(
                f"{method}: {ok}/{len(en)} series ({100 * ok / len(en):.1f}%) had |E_n| <= 1 under the conventional independent-uncertainty denominator."
            )
        iq = image_quality[image_quality["method"] == method] if image_quality is not None and not image_quality.empty else pd.DataFrame()
        if not iq.empty:
            counts = iq["image_status"].value_counts().to_dict()
            statements.append(
                f"{method}: independent Python image analysis statuses were {counts}; these are algorithmic quality flags, not metrological acceptance decisions."
            )
    if not statements:
        statements.append("No computed paired results were available for automatic interpretation.")
    return statements
