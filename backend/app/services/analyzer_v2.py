"""Enhanced data analyzer — extracts structured analytics using vectorized pandas ops."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import numpy as np


def analyze(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute comprehensive sales statistics from a DataFrame.

    Returns a JSON-serialisable dictionary with the structured analytics schema:
    total_revenue, revenue_by_region, revenue_by_category, avg_unit_price,
    top_region, bottom_region, revenue_trend, cancelled_orders_count, rows.
    """
    stats: dict[str, Any] = {}
    stats["rows"] = int(len(df))
    stats["columns"] = list(df.columns)

    # ── Revenue metrics (vectorized) ──
    has_revenue = "Revenue" in df.columns
    if has_revenue:
        rev = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
        stats["total_revenue"] = float(rev.sum())
        stats["avg_revenue_per_transaction"] = float(rev.mean())
        stats["median_revenue"] = float(rev.median())
        stats["min_revenue"] = float(rev.min())
        stats["max_revenue"] = float(rev.max())
        stats["revenue_std_dev"] = float(rev.std()) if len(rev) > 1 else 0.0
    else:
        stats["total_revenue"] = 0.0

    # ── Units metrics (vectorized) ──
    has_units = "Units_Sold" in df.columns
    if has_units:
        units = pd.to_numeric(df["Units_Sold"], errors="coerce").fillna(0)
        stats["total_units_sold"] = int(units.sum())
        stats["avg_units_per_transaction"] = float(units.mean())
    else:
        stats["total_units_sold"] = 0

    # ── Unit price analysis (vectorized) ──
    if "Unit_Price" in df.columns:
        prices = pd.to_numeric(df["Unit_Price"], errors="coerce").fillna(0)
        stats["avg_unit_price"] = float(prices.mean())
        stats["price_range"] = {
            "min": float(prices.min()),
            "max": float(prices.max()),
        }
    else:
        stats["avg_unit_price"] = 0.0

    # ── Revenue by region (vectorized groupby) ──
    if "Region" in df.columns and has_revenue:
        rev_col = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
        region_rev = df.assign(_rev=rev_col).groupby("Region")["_rev"].sum().sort_values(ascending=False)
        stats["revenue_by_region"] = {str(k): float(v) for k, v in region_rev.items()}
        stats["top_region"] = str(region_rev.index[0]) if len(region_rev) > 0 else None
        stats["bottom_region"] = str(region_rev.index[-1]) if len(region_rev) > 0 else None
    else:
        stats["revenue_by_region"] = {}
        stats["top_region"] = None
        stats["bottom_region"] = None

    # ── Revenue by category (vectorized groupby) ──
    if "Product_Category" in df.columns and has_revenue:
        rev_col = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
        cat_rev = df.assign(_rev=rev_col).groupby("Product_Category")["_rev"].sum().sort_values(ascending=False)
        stats["revenue_by_category"] = {str(k): float(v) for k, v in cat_rev.items()}
        stats["top_category"] = str(cat_rev.index[0]) if len(cat_rev) > 0 else None
    else:
        stats["revenue_by_category"] = {}
        stats["top_category"] = None

    # ── Detailed regional breakdown (vectorized) ──
    if "Region" in df.columns:
        agg_dict: dict[str, tuple[str, str]] = {"transaction_count": ("Region", "count")}
        if has_revenue:
            agg_dict["total_revenue"] = ("Revenue", "sum")
        if has_units:
            agg_dict["total_units"] = ("Units_Sold", "sum")
        reg_agg = df.groupby("Region").agg(**agg_dict).sort_values(
            "total_revenue" if has_revenue else "transaction_count", ascending=False
        )
        stats["by_region"] = {
            str(reg): {
                "revenue": float(row.get("total_revenue", 0)),
                "units": int(row.get("total_units", 0)),
                "transactions": int(row["transaction_count"]),
            }
            for reg, row in reg_agg.iterrows()
        }
    else:
        stats["by_region"] = {}

    # ── Detailed category breakdown (vectorized) ──
    if "Product_Category" in df.columns:
        agg_dict2: dict[str, tuple[str, str]] = {"transaction_count": ("Product_Category", "count")}
        if has_revenue:
            agg_dict2["total_revenue"] = ("Revenue", "sum")
        if has_units:
            agg_dict2["total_units"] = ("Units_Sold", "sum")
        cat_agg = df.groupby("Product_Category").agg(**agg_dict2).sort_values(
            "total_revenue" if has_revenue else "transaction_count", ascending=False
        )
        stats["by_category"] = {
            str(cat): {
                "revenue": float(row.get("total_revenue", 0)),
                "units": int(row.get("total_units", 0)),
                "transactions": int(row["transaction_count"]),
            }
            for cat, row in cat_agg.iterrows()
        }
    else:
        stats["by_category"] = {}

    # ── Revenue trend (date→value list, vectorized) ──
    if "Date" in df.columns and has_revenue:
        df_dated = df.copy()
        df_dated["_date"] = pd.to_datetime(df_dated["Date"], errors="coerce")
        df_dated = df_dated.dropna(subset=["_date"])
        df_dated["_month"] = df_dated["_date"].dt.to_period("M").astype(str)
        monthly = df_dated.groupby("_month").agg(
            revenue=("Revenue", "sum"),
            units=("Units_Sold", "sum") if has_units else ("_month", "count"),
            transactions=("_month", "count"),
        ).sort_index()
        stats["revenue_trend"] = [
            {"date": str(m), "value": float(row["revenue"])}
            for m, row in monthly.iterrows()
        ]
        stats["monthly_trend"] = {
            str(m): {
                "revenue": float(row["revenue"]),
                "units": int(row.get("units", 0)),
                "transactions": int(row["transactions"]),
            }
            for m, row in monthly.iterrows()
        }
        # Month-over-month growth (vectorized)
        rev_arr = monthly["revenue"].values if len(monthly) > 1 else np.array([])
        if len(rev_arr) > 1:
            prev = rev_arr[:-1]
            curr = rev_arr[1:]
            safe_prev = np.where(prev == 0, 1.0, prev)
            mom = np.round((curr - prev) / safe_prev * 100, 2)
            stats["mom_growth_pct"] = mom.tolist()
        else:
            stats["mom_growth_pct"] = []
    else:
        stats["revenue_trend"] = []
        stats["monthly_trend"] = {}
        stats["mom_growth_pct"] = []

    # ── Status distribution (vectorized) ──
    if "Status" in df.columns:
        status_counts = df["Status"].value_counts()
        stats["by_status"] = {str(k): int(v) for k, v in status_counts.items()}
        total_status = int(status_counts.sum())
        cancelled_count = int(status_counts.get("Cancelled", 0))
        stats["cancelled_orders_count"] = cancelled_count
        if total_status > 0:
            stats["cancellation_rate_pct"] = round(cancelled_count / total_status * 100, 2)
        else:
            stats["cancellation_rate_pct"] = 0.0
    else:
        stats["by_status"] = {}
        stats["cancelled_orders_count"] = 0
        stats["cancellation_rate_pct"] = 0.0

    # ── Outlier detection (IQR, vectorized) ──
    if has_revenue:
        rev = pd.to_numeric(df["Revenue"], errors="coerce").dropna()
        q1 = float(rev.quantile(0.25))
        q3 = float(rev.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_mask = (rev < lower) | (rev > upper)
        outlier_vals = rev[outlier_mask]
        stats["outliers"] = {
            "count": int(outlier_mask.sum()),
            "iqr_lower_bound": round(lower, 2),
            "iqr_upper_bound": round(upper, 2),
            "outlier_values": [float(v) for v in outlier_vals.values[:10]],
        }
    else:
        stats["outliers"] = {"count": 0}

    return stats


def get_top_rows_csv(df: pd.DataFrame, n: int = 3) -> str:
    """Return the top N rows by Revenue as a CSV string."""
    if "Revenue" not in df.columns:
        return df.head(n).to_csv(index=False)
    sorted_df = df.nlargest(n, "Revenue")
    return sorted_df.to_csv(index=False)


def stats_to_json(stats: dict[str, Any]) -> str:
    """Serialize stats dict to pretty JSON for LLM prompt."""
    return json.dumps(stats, indent=2, default=str)
