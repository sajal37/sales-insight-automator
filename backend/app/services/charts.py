"""Chart generation service — produces high-resolution PNG charts from analytics."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _ensure_chart_dir(job_id: str) -> str:
    """Create a safe temp directory for chart output."""
    base = settings.chart_dir
    if not base:
        base = os.path.join(tempfile.gettempdir(), "sia_charts")
    chart_path = os.path.join(base, job_id)
    os.makedirs(chart_path, exist_ok=True)
    return chart_path


def generate_charts(stats: dict[str, Any], job_id: str) -> list[str]:
    """
    Generate three PNG charts and return their file paths:
    1. Revenue by Region (horizontal bar)
    2. Revenue by Category (bar)
    3. Sales Trend over Time (line)
    """
    chart_dir = _ensure_chart_dir(job_id)
    paths: list[str] = []

    # ── Chart 1: Revenue by Region ──
    region_data = stats.get("revenue_by_region", {})
    if region_data:
        path = _chart_revenue_by_region(region_data, chart_dir)
        paths.append(path)

    # ── Chart 2: Revenue by Category ──
    category_data = stats.get("revenue_by_category", {})
    if category_data:
        path = _chart_revenue_by_category(category_data, chart_dir)
        paths.append(path)

    # ── Chart 3: Revenue Trend ──
    trend_data = stats.get("revenue_trend", [])
    if trend_data:
        path = _chart_revenue_trend(trend_data, chart_dir)
        paths.append(path)

    logger.info("Generated %d charts for job %s", len(paths), job_id)
    return paths


def _chart_revenue_by_region(data: dict[str, float], chart_dir: str) -> str:
    regions = list(data.keys())
    values = list(data.values())

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    colors = plt.cm.viridis([i / max(len(regions) - 1, 1) for i in range(len(regions))])
    bars = ax.barh(regions, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Revenue ($)", fontsize=11)
    ax.set_title("Revenue by Region", fontsize=14, fontweight="bold", pad=12)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    path = os.path.join(chart_dir, "revenue_by_region.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _chart_revenue_by_category(data: dict[str, float], chart_dir: str) -> str:
    categories = list(data.keys())
    values = list(data.values())

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    colors = plt.cm.Set2([i / max(len(categories) - 1, 1) for i in range(len(categories))])
    ax.bar(categories, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_ylabel("Revenue ($)", fontsize=11)
    ax.set_title("Revenue by Product Category", fontsize=14, fontweight="bold", pad=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()

    path = os.path.join(chart_dir, "revenue_by_category.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _chart_revenue_trend(data: list[dict[str, Any]], chart_dir: str) -> str:
    dates = [d["date"] for d in data]
    values = [d["value"] for d in data]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    ax.plot(dates, values, marker="o", linewidth=2, markersize=6, color="#6366f1")
    ax.fill_between(dates, values, alpha=0.15, color="#6366f1")
    ax.set_xlabel("Month", fontsize=11)
    ax.set_ylabel("Revenue ($)", fontsize=11)
    ax.set_title("Sales Revenue Trend", fontsize=14, fontweight="bold", pad=12)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    path = os.path.join(chart_dir, "revenue_trend.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path
