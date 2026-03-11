"""Tests for the enhanced v2 data analyzer service."""

import pytest
import pandas as pd

from app.services.analyzer_v2 import analyze, get_top_rows_csv, stats_to_json


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


class TestAnalyzeV2:
    def test_total_revenue(self):
        stats = analyze(_sample_df())
        expected = 180000 + 20250 + 88000 + 262500 + 24000 + 109250
        assert stats["total_revenue"] == expected

    def test_total_units(self):
        stats = analyze(_sample_df())
        assert stats["total_units_sold"] == 150 + 45 + 80 + 210 + 60 + 95

    def test_row_count(self):
        stats = analyze(_sample_df())
        assert stats["rows"] == 6

    def test_top_region(self):
        stats = analyze(_sample_df())
        assert stats["top_region"] == "North"

    def test_bottom_region(self):
        stats = analyze(_sample_df())
        assert stats["bottom_region"] is not None

    def test_top_category(self):
        stats = analyze(_sample_df())
        assert stats["top_category"] == "Electronics"

    def test_revenue_by_region_keys(self):
        stats = analyze(_sample_df())
        assert set(stats["revenue_by_region"].keys()) == {"North", "South", "East", "West"}

    def test_revenue_by_category_keys(self):
        stats = analyze(_sample_df())
        assert set(stats["revenue_by_category"].keys()) == {"Electronics", "Home Appliances"}

    def test_revenue_trend_has_three_months(self):
        stats = analyze(_sample_df())
        assert len(stats["revenue_trend"]) == 3

    def test_revenue_trend_structure(self):
        stats = analyze(_sample_df())
        trend = stats["revenue_trend"]
        for item in trend:
            assert "date" in item
            assert "value" in item
            assert isinstance(item["value"], float)

    def test_cancelled_orders_count(self):
        stats = analyze(_sample_df())
        assert stats["cancelled_orders_count"] == 1

    def test_cancellation_rate(self):
        stats = analyze(_sample_df())
        assert stats["cancellation_rate_pct"] == pytest.approx(16.67, abs=0.01)

    def test_mom_growth_length(self):
        stats = analyze(_sample_df())
        # 3 months → 2 MoM values
        assert len(stats["mom_growth_pct"]) == 2

    def test_avg_unit_price(self):
        stats = analyze(_sample_df())
        assert stats["avg_unit_price"] > 0

    def test_by_status(self):
        stats = analyze(_sample_df())
        assert stats["by_status"]["Shipped"] == 3
        assert stats["by_status"]["Delivered"] == 2
        assert stats["by_status"]["Cancelled"] == 1

    def test_by_region_breakdown(self):
        stats = analyze(_sample_df())
        assert "North" in stats["by_region"]
        assert stats["by_region"]["North"]["transactions"] == 3

    def test_by_category_breakdown(self):
        stats = analyze(_sample_df())
        assert "Electronics" in stats["by_category"]
        assert stats["by_category"]["Electronics"]["transactions"] == 4

    def test_outlier_detection(self):
        stats = analyze(_sample_df())
        assert "outliers" in stats
        assert "count" in stats["outliers"]
        assert isinstance(stats["outliers"]["count"], int)


class TestGetTopRowsCsv:
    def test_returns_csv_string(self):
        result = get_top_rows_csv(_sample_df(), n=3)
        assert isinstance(result, str)
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 rows

    def test_sorted_by_revenue_desc(self):
        result = get_top_rows_csv(_sample_df(), n=1)
        lines = result.strip().split("\n")
        # Top revenue is 262500 (North, Electronics)
        assert "262500" in lines[1]


class TestStatsToJson:
    def test_roundtrip_json(self):
        stats = analyze(_sample_df())
        json_str = stats_to_json(stats)
        import json
        parsed = json.loads(json_str)
        assert parsed["total_revenue"] == stats["total_revenue"]
        assert parsed["rows"] == 6
