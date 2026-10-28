"""Generate publication-ready figures from the materialized analytical outputs.

The plotting layer is deliberately downstream of the analysis pipeline: it does
not recompute metrics or touch the raw flight files. This makes the visual
artifact set deterministic and safe to regenerate in CI or on a fresh clone.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "processed_data"
OUTPUT = ROOT / "reports" / "figures"

NAVY = "#102A43"
BLUE = "#1976A8"
TEAL = "#00A6A6"
ORANGE = "#F28E2B"
RED = "#D1495B"
SLATE = "#627D98"
LIGHT = "#F4F7FA"
GRID = "#D9E2EC"
YEAR_COLORS = {2019: BLUE, 2020: ORANGE}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelcolor": NAVY,
    "axes.edgecolor": GRID,
    "axes.labelsize": 10,
    "xtick.color": SLATE,
    "ytick.color": SLATE,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(INPUT / f"{name}.csv")


def finish(ax: plt.Axes, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, loc="left", color=NAVY, pad=18)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=SLATE, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUTPUT / name, dpi=240, bbox_inches="tight")
    plt.close(fig)


def executive_overview() -> None:
    monthly = load("monthly_summary")
    performance = load("performance_summary")
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.2))
    for year, group in monthly.groupby("year"):
        axes[0, 0].plot(group["month"], group["total_flights"], marker="o",
                        color=YEAR_COLORS[year], linewidth=2.4, label=str(year))
        axes[0, 1].plot(group["month"], group["cancellation_rate"], marker="o",
                        color=YEAR_COLORS[year], linewidth=2.4, label=str(year))
    for year, group in performance.groupby("year"):
        axes[1, 0].plot(group["month"], group["on_time_rate"], marker="o",
                        color=YEAR_COLORS[year], linewidth=2.4, label=str(year))
        axes[1, 1].plot(group["month"], group["severe_delay_rate"], marker="o",
                        color=YEAR_COLORS[year], linewidth=2.4, label=str(year))
    titles = [
        ("Scheduled flight volume", "Monthly records in the analytical sample", "Flights"),
        ("Cancellation rate", "The 2020 disruption signal is visible immediately", "Rate (%)"),
        ("On-time performance", "Operated flights with valid arrival observations", "Rate (%)"),
        ("Severe arrival delays", "Operated flights arriving 60+ minutes late", "Rate (%)"),
    ]
    for ax, (title, subtitle, ylabel) in zip(axes.flat, titles):
        finish(ax, title, subtitle)
        ax.set_xlabel("Month")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(1, 13))
        ax.legend(frameon=False, ncol=2, loc="upper right")
    axes[0, 0].yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:.0f}k"))
    axes[0, 1].yaxis.set_major_formatter(PercentFormatter(100))
    axes[1, 0].yaxis.set_major_formatter(PercentFormatter(100))
    axes[1, 1].yaxis.set_major_formatter(PercentFormatter(100))
    save(fig, "01_executive_overview.png")


def airline_reliability() -> None:
    data = load("a6_airline_reliability_changes").nlargest(12, "cancellation_rate_change")
    data = data.sort_values("cancellation_rate_change")
    labels = data["airline"].str.replace(" Inc.", "", regex=False).str.replace(" Co.", "", regex=False)
    fig, ax = plt.subplots(figsize=(11, 7))
    for y, (_, row) in enumerate(data.iterrows()):
        ax.plot([row["cancellation_rate_2019"], row["cancellation_rate_2020"]], [y, y],
                color=GRID, linewidth=3, zorder=1)
        ax.scatter(row["cancellation_rate_2019"], y, color=BLUE, s=55, zorder=2, label="2019" if y == 0 else None)
        ax.scatter(row["cancellation_rate_2020"], y, color=ORANGE, s=55, zorder=2, label="2020" if y == 0 else None)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Cancellation rate (%)")
    ax.legend(frameon=False, ncol=2, loc="lower right")
    finish(ax, "Airline reliability shifted unevenly", "Top 12 increases; endpoints are rates, not rank scores")
    save(fig, "02_airline_reliability_shift.png")


def airport_change() -> None:
    data = load("airport_summary")
    wide = data.pivot(index="airport", columns="year", values=["cancellation_rate", "total_flights"]).dropna()
    wide = wide[wide[("total_flights", 2019)].ge(100) & wide[("total_flights", 2020)].ge(100)].copy()
    wide["change"] = wide[("cancellation_rate", 2020)] - wide[("cancellation_rate", 2019)]
    data = wide.nlargest(15, "change").sort_values("change")
    fig, ax = plt.subplots(figsize=(10.5, 7))
    colors = [RED if x >= 0 else TEAL for x in data["change"]]
    ax.barh(data.index, data["change"], color=colors)
    ax.axvline(0, color=NAVY, linewidth=0.8)
    ax.set_xlabel("Change in cancellation rate (percentage points)")
    finish(ax, "Airport disruption was spatially heterogeneous",
           "Top increases among airports with at least 100 scheduled flights in each year")
    save(fig, "03_airport_cancellation_change.png")


def cancellation_reasons() -> None:
    data = load("a3_cancellation_reason_changes")
    pivot = data.pivot(index="year", columns="cancellation_reason", values="share_of_cancellations").fillna(0)
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    pivot.plot.bar(stacked=True, ax=ax, color=[ORANGE, BLUE, TEAL], width=0.62)
    ax.set_xlabel("")
    ax.set_ylabel("Share of cancellations")
    ax.yaxis.set_major_formatter(PercentFormatter(100))
    ax.legend(title="", frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    finish(ax, "Cancellation composition changed during the disruption",
           "Reason mix is calculated among cancelled records within each year")
    save(fig, "04_cancellation_reason_mix.png")


def route_changes() -> None:
    data = load("a1_route_cancellation_changes").head(12).sort_values("cancellation_rate_change")
    labels = data["origin"] + " → " + data["dest"]
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.barh(labels, data["cancellation_rate_change"], color=RED)
    ax.set_xlabel("Cancellation-rate increase (percentage points)")
    finish(ax, "Route-level disruption exposed concentrated shocks", "Largest increases; minimum 30 flights in both comparison years")
    save(fig, "05_route_cancellation_shocks.png")

    delays = load("a2_route_arrival_delay_changes").head(12).sort_values("avg_arrival_delay_change")
    labels = delays["origin"] + " → " + delays["dest"]
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.barh(labels, delays["avg_arrival_delay_change"], color=TEAL)
    ax.set_xlabel("Change in mean arrival delay (minutes)")
    finish(ax, "Some routes moved from early to materially delayed", "Largest increases among routes with comparable operating volume")
    save(fig, "06_route_arrival_delay_shocks.png")


def resilience_map() -> None:
    data = load("airport_resilience_monthly")
    data = data[(data["month"].isin([3, 4])) & data["scheduled_flights_2020"].ge(100)].copy()
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    sizes = np.sqrt(data["scheduled_flights_2020"]) * 5
    scatter = ax.scatter(data["activity_ratio_2020_to_2019"], data["cancellation_rate_change_pp"],
                         s=sizes, c=data["on_time_rate_change_pp"], cmap="RdYlGn", alpha=0.72,
                         edgecolor="white", linewidth=0.5)
    ax.axvline(1, color=SLATE, linestyle="--", linewidth=1)
    ax.axhline(0, color=SLATE, linestyle="--", linewidth=1)
    ax.set_xlabel("2020 activity / 2019 activity")
    ax.set_ylabel("Cancellation-rate change (percentage points)")
    ax.annotate("volume preserved", (1.03, ax.get_ylim()[0]), color=SLATE, fontsize=9)
    ax.annotate("higher cancellations", (ax.get_xlim()[0], ax.get_ylim()[1] * 0.9), color=SLATE, fontsize=9)
    fig.colorbar(scatter, ax=ax, label="On-time-rate change (pp)")
    finish(ax, "Airport resilience has multiple dimensions", "March–April 2020; bubble size reflects 2020 scheduled volume")
    save(fig, "07_airport_resilience_map.png")


def model_benchmark() -> None:
    data = load("model_metrics")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
    metrics = [("pr_auc", "PR-AUC", False), ("roc_auc", "ROC-AUC", False), ("brier_score", "Brier score", True)]
    for ax, (column, label, lower_is_better) in zip(axes, metrics):
        ordered = data.sort_values(column, ascending=lower_is_better)
        ax.barh(ordered["model"].str.replace("_", " ").str.title(), ordered[column],
                color=[SLATE if x == "dummy_baseline" else (ORANGE if x == "random_forest" else BLUE)
                       for x in ordered["model"]])
        ax.set_xlabel(label)
        finish(ax, label, "2020 chronological holdout")
    save(fig, "08_model_benchmark.png")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    executive_overview()
    airline_reliability()
    airport_change()
    cancellation_reasons()
    route_changes()
    resilience_map()
    model_benchmark()
    print(f"Generated figures in {OUTPUT}")


if __name__ == "__main__":
    main()
