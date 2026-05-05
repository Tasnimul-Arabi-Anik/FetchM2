from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


RAW_STANDARDIZED_PAIRS = [
    ("Host", "Host_SD", "Host Distribution"),
    ("Geographic Location", "Country", "Country / Geography Distribution"),
    ("Collection Date", "Collection_Year", "Collection Year Distribution"),
    ("Isolation Source", "Isolation_Source_SD", "Isolation Source Distribution"),
    ("Sample Type", "Sample_Type_SD", "Sample Type Distribution"),
    ("Isolation Site", "Isolation_Site_SD", "Isolation Site Distribution"),
    ("Environment Medium", "Environment_Medium_SD", "Environment Medium Distribution"),
    ("Host Disease", "Host_Disease_SD", "Host Disease Distribution"),
    ("Host Health State", "Host_Health_State_SD", "Host Health State Distribution"),
]

BROAD_FIELDS = [
    "Continent",
    "Subcontinent",
    "Host_Rank",
    "Host_Superkingdom",
    "Host_Phylum",
    "Host_Class",
    "Host_Order",
    "Host_Family",
    "Host_Genus",
    "Host_Species",
    "Sample_Type_SD_Broad",
    "Isolation_Source_SD_Broad",
    "Environment_Medium_SD_Broad",
    "Environment_Broad_Scale_SD",
    "Environment_Local_Scale_SD",
]

CORE_STANDARDIZED_FIELDS = [
    "Host_Original",
    "Host_Cleaned",
    "Host_SD",
    "Host_TaxID",
    "Host_Rank",
    "Host_Superkingdom",
    "Host_Phylum",
    "Host_Class",
    "Host_Order",
    "Host_Family",
    "Host_Genus",
    "Host_Species",
    "Host_Common_Name",
    "Host_Match_Method",
    "Host_Confidence",
    "Host_Review_Status",
    "Country",
    "Continent",
    "Subcontinent",
    "Collection_Year",
    "Sample_Type_SD",
    "Sample_Type_SD_Broad",
    "Isolation_Source_SD",
    "Isolation_Source_SD_Broad",
    "Isolation_Site_SD",
    "Environment_Medium_SD",
    "Environment_Medium_SD_Broad",
    "Environment_Broad_Scale_SD",
    "Environment_Local_Scale_SD",
    "Host_Disease_SD",
    "Host_Health_State_SD",
]

NUMERIC_FIELDS = [
    "Assembly Stats Total Sequence Length",
    "Assembly Stats Total Number of Chromosomes",
    "Assembly Stats Number of Contigs",
    "Assembly Stats Contig N50",
    "Assembly Stats Scaffold N50",
    "Assembly Stats Number of Scaffolds",
    "Assembly Stats GC Percent",
    "Annotation Count Gene Total",
    "Annotation Count Gene Protein-coding",
    "Annotation Count Gene Pseudogene",
    "CheckM completeness",
    "CheckM contamination",
]


def present_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([], dtype="object")
    values = df[column].fillna("").astype(str).str.strip()
    return values[values != ""]


def safe_filename(label: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in label)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:120] or "plot"


def top_value_rows(df: pd.DataFrame, column: str, *, limit: int = 50) -> list[dict[str, Any]]:
    values = present_series(df, column)
    total_present = int(values.shape[0])
    rows = []
    for value, count in values.value_counts().head(limit).items():
        rows.append(
            {
                "field": column,
                "value": value,
                "count": int(count),
                "percent_of_present": round((int(count) / total_present) * 100, 2) if total_present else 0,
            }
        )
    return rows


def plot_top_values(df: pd.DataFrame, column: str, title: str, output_path: Path, *, limit: int = 20) -> bool:
    values = present_series(df, column)
    if values.empty:
        return False
    counts = values.value_counts().head(limit).sort_values(ascending=True)
    height = max(4.5, min(12.0, 0.38 * len(counts) + 1.6))
    plt.figure(figsize=(10, height))
    counts.plot(kind="barh", color="#2c7fb8")
    plt.title(title)
    plt.xlabel("Rows")
    plt.ylabel(column)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180)
    plt.close()
    return True


def plot_histogram(df: pd.DataFrame, column: str, output_path: Path) -> bool:
    if column not in df.columns:
        return False
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return False
    plt.figure(figsize=(9, 5.5))
    plt.hist(values, bins=min(40, max(10, int(values.shape[0] ** 0.5))), color="#3f8f6b", edgecolor="white")
    plt.title(f"{column} Distribution")
    plt.xlabel(column)
    plt.ylabel("Rows")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180)
    plt.close()
    return True


def plot_scatter_by_year(df: pd.DataFrame, y_column: str, output_path: Path) -> bool:
    if "Collection_Year" not in df.columns or y_column not in df.columns:
        return False
    plot_df = pd.DataFrame(
        {
            "Collection_Year": pd.to_numeric(df["Collection_Year"], errors="coerce"),
            y_column: pd.to_numeric(df[y_column], errors="coerce"),
        }
    ).dropna()
    if plot_df.empty:
        return False
    plt.figure(figsize=(9, 5.5))
    plt.scatter(plot_df["Collection_Year"], plot_df[y_column], s=18, alpha=0.65, color="#cc6c2f")
    plt.title(f"{y_column} vs Collection Year")
    plt.xlabel("Collection Year")
    plt.ylabel(y_column)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180)
    plt.close()
    return True


def field_coverage_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    total = int(df.shape[0])
    fields = []
    for raw, standardized, label in RAW_STANDARDIZED_PAIRS:
        fields.append((raw, f"{label} Raw"))
        fields.append((standardized, f"{label} Standardized"))
    fields.extend((field, field) for field in CORE_STANDARDIZED_FIELDS)
    fields.extend((field, field) for field in BROAD_FIELDS)
    fields.extend((field, field) for field in NUMERIC_FIELDS)
    seen = set()
    for field, label in fields:
        if field in seen:
            continue
        seen.add(field)
        present = int(present_series(df, field).shape[0])
        rows.append(
            {
                "field": field,
                "label": label,
                "present_rows": present,
                "total_rows": total,
                "present_percent": round((present / total) * 100, 2) if total else 0,
                "missing_rows": total - present,
            }
        )
    return rows


def numeric_summary_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for field in NUMERIC_FIELDS:
        if field not in df.columns:
            continue
        values = pd.to_numeric(df[field], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "field": field,
                "count": int(values.shape[0]),
                "mean": round(float(values.mean()), 4),
                "median": round(float(values.median()), 4),
                "min": round(float(values.min()), 4),
                "max": round(float(values.max()), 4),
                "std": round(float(values.std()), 4) if values.shape[0] > 1 else 0,
            }
        )
    return rows


def write_analysis_report(
    *,
    df: pd.DataFrame,
    output_dir: Path,
    coverage: list[dict[str, Any]],
    figures: list[str],
    top_values_path: Path,
    numeric_summary_path: Path,
) -> None:
    total = int(df.shape[0])
    coverage_lookup = {row["field"]: row for row in coverage}
    important_fields = [
        "Host_SD",
        "Host_TaxID",
        "Country",
        "Collection_Year",
        "Sample_Type_SD",
        "Isolation_Source_SD",
        "Isolation_Site_SD",
        "Environment_Medium_SD",
        "Host_Disease_SD",
        "Host_Health_State_SD",
    ]
    lines = [
        "# FetchM2 Metadata Analysis Report",
        "",
        f"Rows analyzed: {total}",
        "",
        "## Standardized Field Coverage",
        "",
    ]
    for field in important_fields:
        row = coverage_lookup.get(field)
        if row is None:
            continue
        lines.append(f"- `{field}`: {row['present_rows']} / {row['total_rows']} ({row['present_percent']}%)")
    lines.extend(
        [
            "",
            "## Output Tables",
            "",
            "- Field coverage: `tables/field_coverage_summary.csv`",
            f"- Top values: `{top_values_path.relative_to(output_dir)}`",
            f"- Numeric summary: `{numeric_summary_path.relative_to(output_dir)}`",
            "",
            "## Figures",
            "",
        ]
    )
    if figures:
        for figure in figures:
            lines.append(f"- `{figure}`")
    else:
        lines.append("- No figures were generated because no plottable values were present.")
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Raw distributions summarize original metadata fields when present.",
            "- Standardized distributions summarize FetchM2 curated fields.",
            "- Empty standardized fields usually mean the input lacked usable metadata or the value remained intentionally unresolved.",
            "- Use `audit/top_host_review_needed.csv` for remaining host curation candidates.",
        ]
    )
    (output_dir / "metadata_analysis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_metadata_analysis(df: pd.DataFrame, output_dir: Path, *, top_n: int = 30) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    coverage = field_coverage_rows(df)
    coverage_path = tables_dir / "field_coverage_summary.csv"
    pd.DataFrame(coverage).to_csv(coverage_path, index=False)

    top_rows = []
    figures: list[str] = []
    for raw, standardized, label in RAW_STANDARDIZED_PAIRS:
        for column, kind in [(standardized, "standardized"), (raw, "raw")]:
            if column not in df.columns:
                continue
            top_rows.extend(top_value_rows(df, column, limit=50))
            figure_path = figures_dir / f"{safe_filename(label)}_{kind}.png"
            if plot_top_values(df, column, f"{label} ({kind.title()})", figure_path, limit=top_n):
                figures.append(str(figure_path.relative_to(output_dir)))

    for column in BROAD_FIELDS:
        if column not in df.columns:
            continue
        top_rows.extend(top_value_rows(df, column, limit=50))
        figure_path = figures_dir / f"{safe_filename(column)}.png"
        if plot_top_values(df, column, f"{column} Distribution", figure_path, limit=top_n):
            figures.append(str(figure_path.relative_to(output_dir)))

    top_values_path = tables_dir / "top_values_by_field.csv"
    pd.DataFrame(top_rows).to_csv(top_values_path, index=False)

    numeric_summary = numeric_summary_rows(df)
    numeric_summary_path = tables_dir / "numeric_summary.csv"
    pd.DataFrame(numeric_summary).to_csv(numeric_summary_path, index=False)
    for column in NUMERIC_FIELDS:
        figure_path = figures_dir / f"{safe_filename(column)}_histogram.png"
        if plot_histogram(df, column, figure_path):
            figures.append(str(figure_path.relative_to(output_dir)))
    for column in [
        "Assembly Stats Total Sequence Length",
        "Assembly Stats Number of Contigs",
        "Annotation Count Gene Total",
        "Annotation Count Gene Protein-coding",
        "CheckM completeness",
    ]:
        figure_path = figures_dir / f"{safe_filename(column)}_vs_collection_year.png"
        if plot_scatter_by_year(df, column, figure_path):
            figures.append(str(figure_path.relative_to(output_dir)))

    write_analysis_report(
        df=df,
        output_dir=output_dir,
        coverage=coverage,
        figures=figures,
        top_values_path=top_values_path,
        numeric_summary_path=numeric_summary_path,
    )
    return {
        "analysis_dir": str(output_dir),
        "coverage_path": str(coverage_path),
        "top_values_path": str(top_values_path),
        "numeric_summary_path": str(numeric_summary_path),
        "figure_count": len(figures),
    }
