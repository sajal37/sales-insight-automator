"""Tests for the data analyzer service."""

import pytest
import pandas as pd

from app.services.analyzer import analyze, stats_to_json


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [
            "2026-01-05", "2026-01-12", "2026-01-20",
            "2026-02-15", "2026-02-28", "2026-03-10",
        ],
        "Product_Category": [
            "Electronics", "Home Appliances", "Electronics",
            "Electronics", "Home Appliances", "Electronics",
        ],
        "Region": ["North", "South", "East", "North", "North", "West"],
        "Units_Sold": [150, 45, 80, 210, 60, 95],
        "Unit_Price": [1200, 450, 1100, 1250, 400, 1150],
        "Revenue": [180000, 20250, 88000, 262500, 24000, 109250],
        "Status": ["Shipped", "Shipped", "Delivered", "Delivered", "Cancelled", "Shipped"],
    })


class TestAnalyze:
    def test_total_revenue(self):
        stats = analyze(_sample_df())
        expected_total = 180000 + 20250 + 88000 + 262500 + 24000 + 109250
        assert stats["total_revenue"] == expected_total

    def test_total_units(self):
        stats = analyze(_sample_df())
        assert stats["total_units_sold"] == 150 + 45 + 80 + 210 + 60 + 95

    def test_top_category_is_electronics(self):
        stats = analyze(_sample_df())
        assert stats["top_category"] == "Electronics"

    def test_top_region_is_north(self):
        stats = analyze(_sample_df())
        assert stats["top_region"] == "North"

    def test_monthly_trend_has_three_months(self):
        stats = analyze(_sample_df())
        assert len(stats["monthly_trend"]) == 3

    def test_mom_growth_length(self):
        stats = analyze(_sample_df())
        # 3 months → 2 mom values
        assert len(stats["mom_growth_pct"]) == 2

    def test_cancellation_rate(self):
        stats = analyze(_sample_df())
        # 1 cancelled out of 6 = 16.67%
        assert stats["cancellation_rate_pct"] == pytest.approx(16.67, abs=0.01)

    def test_by_status(self):
        stats = analyze(_sample_df())
        assert stats["by_status"]["Shipped"] == 3
        assert stats["by_status"]["Delivered"] == 2
        assert stats["by_status"]["Cancelled"] == 1

    def test_by_category_breakdown(self):
        stats = analyze(_sample_df())
        assert "Electronics" in stats["by_category"]
        assert "Home Appliances" in stats["by_category"]
        assert stats["by_category"]["Electronics"]["transactions"] == 4

    def test_by_region_breakdown(self):
        stats = analyze(_sample_df())
        assert "North" in stats["by_region"]
        assert stats["by_region"]["North"]["transactions"] == 3

    def test_outlier_detection(self):
        stats = analyze(_sample_df())
        assert "outliers" in stats
        assert "count" in stats["outliers"]

    def test_stats_to_json(self):
        stats = analyze(_sample_df())
        json_str = stats_to_json(stats)
        assert isinstance(json_str, str)
        assert "total_revenue" in json_str

    def test_empty_columns_graceful(self):
        """Analyzer should handle DataFrames missing expected columns."""
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        stats = analyze(df)
        assert stats["total_revenue"] is None
        assert stats["total_units_sold"] is None
