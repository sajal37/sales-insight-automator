"""Data analyzer service — extracts key statistics from sales data using Pandas."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import numpy as np


def analyze(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute comprehensive sales statistics from a DataFrame.

    Returns a JSON-serialisable dictionary of KPIs ready for LLM consumption.
    """
    stats: dict[str, Any] = {}

    # ── Basic dimensions ──
    stats["total_rows"] = int(len(df))
    stats["columns"] = list(df.columns)

    # ── Revenue metrics ──
    if "Revenue" in df.columns:
        rev = pd.to_numeric(df["Revenue"], errors="coerce")
        stats["total_revenue"] = float(rev.sum())
        stats["avg_revenue_per_transaction"] = float(rev.mean())
        stats["median_revenue"] = float(rev.median())
        stats["min_revenue"] = float(rev.min())
        stats["max_revenue"] = float(rev.max())
        stats["revenue_std_dev"] = float(rev.std()) if len(rev) > 1 else 0.0
    else:
        stats["total_revenue"] = None

    # ── Units metrics ──
    if "Units_Sold" in df.columns:
        units = pd.to_numeric(df["Units_Sold"], errors="coerce")
        stats["total_units_sold"] = int(units.sum())
        stats["avg_units_per_transaction"] = float(units.mean())
    else:
        stats["total_units_sold"] = None

    # ── Product category breakdown ──
    if "Product_Category" in df.columns:
        cat_rev = (
            df.groupby("Product_Category")
            .agg(
                total_revenue=("Revenue", "sum") if "Revenue" in df.columns else ("Units_Sold", "count"),
                total_units=("Units_Sold", "sum") if "Units_Sold" in df.columns else ("Product_Category", "count"),
                transaction_count=("Product_Category", "count"),
            )
            .sort_values("total_revenue", ascending=False)
        )
        stats["by_category"] = {
            cat: {
                "revenue": float(row.get("total_revenue", 0)),
                "units": int(row.get("total_units", 0)),
                "transactions": int(row["transaction_count"]),
            }
            for cat, row in cat_rev.iterrows()
        }
        stats["top_category"] = cat_rev.index[0] if len(cat_rev) > 0 else None
    else:
        stats["by_category"] = {}

    # ── Regional breakdown ──
    if "Region" in df.columns:
        reg_rev = (
            df.groupby("Region")
            .agg(
                total_revenue=("Revenue", "sum") if "Revenue" in df.columns else ("Region", "count"),
                total_units=("Units_Sold", "sum") if "Units_Sold" in df.columns else ("Region", "count"),
                transaction_count=("Region", "count"),
            )
            .sort_values("total_revenue", ascending=False)
        )
        stats["by_region"] = {
            reg: {
                "revenue": float(row.get("total_revenue", 0)),
                "units": int(row.get("total_units", 0)),
                "transactions": int(row["transaction_count"]),
            }
            for reg, row in reg_rev.iterrows()
        }
        stats["top_region"] = reg_rev.index[0] if len(reg_rev) > 0 else None
    else:
        stats["by_region"] = {}

    # ── Monthly trend ──
    if "Date" in df.columns and "Revenue" in df.columns:
        df_dated = df.copy()
        df_dated["Date"] = pd.to_datetime(df_dated["Date"], errors="coerce")
        df_dated = df_dated.dropna(subset=["Date"])
        df_dated["Month"] = df_dated["Date"].dt.to_period("M").astype(str)
        monthly = (
            df_dated.groupby("Month")
            .agg(
                revenue=("Revenue", "sum"),
                units=("Units_Sold", "sum") if "Units_Sold" in df.columns else ("Month", "count"),
                transactions=("Month", "count"),
            )
            .sort_index()
        )
        stats["monthly_trend"] = {
            m: {
                "revenue": float(row["revenue"]),
                "units": int(row.get("units", 0)),
                "transactions": int(row["transactions"]),
            }
            for m, row in monthly.iterrows()
        }
        # Month-over-month growth
        rev_series = monthly["revenue"].values
        if len(rev_series) > 1:
            mom = []
            for i in range(1, len(rev_series)):
                prev = rev_series[i - 1]
                curr = rev_series[i]
                pct = ((curr - prev) / prev * 100) if prev != 0 else 0.0
                mom.append(round(pct, 2))
            stats["mom_growth_pct"] = mom
        else:
            stats["mom_growth_pct"] = []
    else:
        stats["monthly_trend"] = {}
        stats["mom_growth_pct"] = []

    # ── Status distribution ──
    if "Status" in df.columns:
        status_counts = df["Status"].value_counts().to_dict()
        stats["by_status"] = {k: int(v) for k, v in status_counts.items()}
        total = sum(stats["by_status"].values())
        stats["cancellation_rate_pct"] = round(
            stats["by_status"].get("Cancelled", 0) / total * 100, 2
        ) if total > 0 else 0.0
    else:
        stats["by_status"] = {}
        stats["cancellation_rate_pct"] = 0.0

    # ── Outlier detection (IQR method on Revenue) ──
    if "Revenue" in df.columns:
        rev = pd.to_numeric(df["Revenue"], errors="coerce").dropna()
        q1 = float(rev.quantile(0.25))
        q3 = float(rev.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = rev[(rev < lower) | (rev > upper)]
        stats["outliers"] = {
            "count": int(len(outliers)),
            "iqr_lower_bound": round(lower, 2),
            "iqr_upper_bound": round(upper, 2),
            "outlier_values": [float(v) for v in outliers.values[:10]],
        }
    else:
        stats["outliers"] = {"count": 0}

    # ── Unit price analysis ──
    if "Unit_Price" in df.columns:
        prices = pd.to_numeric(df["Unit_Price"], errors="coerce")
        stats["avg_unit_price"] = float(prices.mean())
        stats["price_range"] = {
            "min": float(prices.min()),
            "max": float(prices.max()),
        }
    else:
        stats["avg_unit_price"] = None

    return stats


def stats_to_json(stats: dict[str, Any]) -> str:
    """Serialize stats dict to pretty JSON for LLM prompt."""
    return json.dumps(stats, indent=2, default=str)
