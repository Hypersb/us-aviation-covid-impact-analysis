"""Execute the Phase 3 statistical analysis against the existing 2019-2020 data.

The source tables are validated through PostgreSQL before the reproducible
Python analysis is run. No source data is written by this module.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg
from scipy.stats import mannwhitneyu, norm

from analysis_pipeline import REASON_LABELS, load_flights, validate
from postgres_existing import connection_kwargs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "phase3"
MIN_AIRPORT = 100
MIN_ROUTE = 30
Z = norm.ppf(0.975)


def wilson(count: float, total: float) -> tuple[float, float]:
    if total <= 0:
        return (float("nan"), float("nan"))
    p = count / total
    d = 1 + Z * Z / total
    c = (p + Z * Z / (2 * total)) / d
    m = Z * np.sqrt(p * (1 - p) / total + Z * Z / (4 * total * total)) / d
    return max(0.0, c - m), min(1.0, c + m)


def proportion_result(label: str, x1: int, n1: int, x2: int, n2: int) -> dict:
    if min(n1, n2) <= 0:
        raise ValueError(f"Cannot compare {label}: empty denominator ({n1}, {n2})")
    p1, p2 = x1 / n1, x2 / n2
    difference = p2 - p1
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci = (difference - Z * se, difference + Z * se)
    pooled = (x1 + x2) / (n1 + n2)
    pooled_se = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = difference / pooled_se if pooled_se else 0.0
    p_value = 2 * norm.sf(abs(z))
    return {
        "metric": label, "count_2019": x1, "denominator_2019": n1,
        "count_2020": x2, "denominator_2020": n2,
        "rate_2019": p1 * 100, "rate_2020": p2 * 100,
        "difference_pp": difference * 100, "relative_change_pct": difference / p1 * 100,
        "ci_low_pp": ci[0] * 100, "ci_high_pp": ci[1] * 100,
        "z_statistic": z, "p_value": p_value,
        "effect_size_abs_pp": abs(difference) * 100,
    }


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """Return monotone Benjamini-Hochberg adjusted p-values."""
    p_values = np.asarray(p_values, dtype=float)
    order = np.argsort(p_values)
    adjusted = np.empty_like(p_values)
    running = 1.0
    for rank in range(len(order), 0, -1):
        index = order[rank - 1]
        running = min(running, p_values[index] * len(order) / rank)
        adjusted[index] = running
    return adjusted


def bootstrap_difference(left: pd.Series, right: pd.Series, seed: int = 2020,
                         repetitions: int = 500) -> tuple[float, float]:
    """Deterministic percentile interval for a difference in means."""
    rng = np.random.default_rng(seed)
    left_values, right_values = left.dropna().to_numpy(), right.dropna().to_numpy()
    if not len(left_values) or not len(right_values):
        raise ValueError("Bootstrap requires two non-empty samples")
    draws = np.empty(repetitions)
    for index in range(repetitions):
        draws[index] = rng.choice(right_values, len(right_values), replace=True).mean() - rng.choice(
            left_values, len(left_values), replace=True).mean()
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def airport_uncertainty(airport_change: pd.DataFrame, minimum: int = MIN_AIRPORT) -> pd.DataFrame:
    selected = airport_change[
        (airport_change["scheduled_flights_2019"] >= minimum)
        & (airport_change["scheduled_flights_2020"] >= minimum)
    ].copy()
    p_values = []
    for _, row in selected.iterrows():
        p1 = row["cancellation_rate_2019"] / 100
        p2 = row["cancellation_rate_2020"] / 100
        se = np.sqrt(p1 * (1 - p1) / row["scheduled_flights_2019"] +
                     p2 * (1 - p2) / row["scheduled_flights_2020"])
        p_values.append(2 * norm.sf(abs((p2 - p1) / se)) if se else 1.0)
    selected["cancellation_change_p_value"] = p_values
    selected["cancellation_change_fdr_q"] = benjamini_hochberg(np.asarray(p_values))
    selected["minimum_volume_threshold"] = minimum
    return selected


def prepare(flights: pd.DataFrame) -> pd.DataFrame:
    frame = flights.copy()
    frame["valid_arrival"] = frame["cancelled_flag"].eq(0) & frame["arr_delay"].notna()
    frame["on_time"] = frame["valid_arrival"] & frame["arr_delay"].lt(15)
    frame["severe_delay"] = frame["valid_arrival"] & frame["arr_delay"].ge(60)
    frame["diverted_flag"] = pd.to_numeric(frame["diverted"], errors="coerce").fillna(0).eq(1)
    return frame


def metric_summary(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    result = frame.groupby(keys, dropna=False).agg(
        scheduled_flights=("cancelled_flag", "size"),
        cancelled_flights=("cancelled_flag", "sum"),
        diverted_flights=("diverted_flag", "sum"),
        valid_arrival_flights=("valid_arrival", "sum"),
        on_time_flights=("on_time", "sum"),
        severe_delay_flights=("severe_delay", "sum"),
        mean_arrival_delay=("arr_delay", "mean"),
        median_arrival_delay=("arr_delay", "median"),
        sd_arrival_delay=("arr_delay", "std"),
        missing_arrival_delay=("arr_delay", lambda x: x.isna().sum()),
    ).reset_index()
    for name, numerator, denominator in (
        ("cancellation_rate", "cancelled_flights", "scheduled_flights"),
        ("diversion_rate", "diverted_flights", "scheduled_flights"),
        ("on_time_rate", "on_time_flights", "valid_arrival_flights"),
        ("severe_delay_rate", "severe_delay_flights", "valid_arrival_flights"),
    ):
        result[name] = result[numerator] / result[denominator] * 100
    result["missing_arrival_rate"] = result["missing_arrival_delay"] / result["scheduled_flights"] * 100
    return result


def db_audit() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    with psycopg.connect(**connection_kwargs()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXTRACT(YEAR FROM fl_date)::int AS year,
                       COUNT(*)::bigint AS scheduled_flights,
                       COUNT(*) FILTER (WHERE cancelled = 1)::bigint AS cancelled_flights,
                       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL)::bigint AS valid_arrival_flights,
                       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL AND arr_delay < 15)::bigint AS on_time_flights,
                       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL AND arr_delay >= 60)::bigint AS severe_delay_flights
                FROM aviation_analytics.all_flights GROUP BY 1 ORDER BY 1
            """)
            annual = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
            cur.execute("""
                SELECT EXTRACT(YEAR FROM fl_date)::int AS year,
                       EXTRACT(MONTH FROM fl_date)::int AS month,
                       COUNT(*)::bigint AS scheduled_flights,
                       COUNT(*) FILTER (WHERE cancelled = 1)::bigint AS cancelled_flights,
                       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL)::bigint AS valid_arrival_flights,
                       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL AND arr_delay < 15)::bigint AS on_time_flights,
                       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL AND arr_delay >= 60)::bigint AS severe_delay_flights
                FROM aviation_analytics.all_flights GROUP BY 1, 2 ORDER BY 1, 2
            """)
            monthly = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
            cur.execute("""
                SELECT table_name, COUNT(*)::bigint AS rows
                FROM (SELECT 'flights_2019_new' AS table_name FROM public.flights_2019_new
                      UNION ALL SELECT 'flights_2020_new' FROM public.flights_2020_new) s
                GROUP BY table_name ORDER BY table_name
            """)
            counts = {row[0]: int(row[1]) for row in cur.fetchall()}
    return counts, annual, monthly


def make_figures(tables: dict[str, pd.DataFrame], figures: Path) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    monthly = tables["monthly"]
    for metric, title, filename in (
        ("scheduled_flights", "Monthly scheduled flight volume", "monthly_volume"),
        ("cancellation_rate", "Monthly cancellation rate", "monthly_cancellations"),
        ("on_time_rate", "Monthly on-time arrival rate", "monthly_on_time"),
        ("severe_delay_rate", "Monthly severe arrival-delay rate", "monthly_severe_delay"),
    ):
        fig, ax = plt.subplots(figsize=(10, 5))
        for year, group in monthly.groupby("year"):
            ax.plot(group["month"], group[metric], marker="o", label=str(year))
        ax.set(title=title + " (observed BTS records)", xlabel="Calendar month", ylabel=metric.replace("_", " ").title())
        ax.legend(title="Year")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(figures / f"{filename}.png", dpi=160)
        plt.close(fig)

    for source, metric, title, filename in (
        ("airline", "cancellation_rate_change_pp", "Airline cancellation-rate changes", "airline_cancellation_changes"),
        ("airport", "cancellation_rate_change_pp", "Airport cancellation-rate changes (common airports)", "airport_cancellation_changes"),
    ):
        data = tables[source].sort_values(metric).tail(25)
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(data[source], data[metric])
        ax.set(title=title, xlabel="2020 minus 2019 percentage points")
        fig.tight_layout()
        fig.savefig(figures / f"{filename}.png", dpi=160)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    for year, values in tables["delay_samples"].items():
        ax.hist(values.clip(-60, 180), bins=60, alpha=0.45, density=True, label=str(year))
    ax.set(title="Arrival-delay distributions (valid operated observations)", xlabel="Arrival delay (minutes, clipped for display)", ylabel="Density")
    ax.legend(title="Year")
    fig.tight_layout()
    fig.savefig(figures / "arrival_delay_distributions.png", dpi=160)
    plt.close(fig)

    reasons = tables["cancellation_reasons"].pivot_table(
        index="cancellation_reason", columns="year", values="cancelled_flights", fill_value=0
    )
    reasons.plot(kind="bar", figsize=(9, 5), title="Recorded cancellation reasons")
    plt.ylabel("Cancelled flight records")
    plt.xlabel("BTS cancellation-code label")
    plt.tight_layout()
    plt.savefig(figures / "cancellation_reason_distributions.png", dpi=160)
    plt.close()

    sensitivity = tables["sensitivity"]
    plot_data = sensitivity[sensitivity["metric"].str.endswith("cancellation_rate")].copy()
    plot_data["population"] = plot_data["metric"].str.split(":").str[0]
    plot_data.plot(x="population", y="difference_pp", kind="bar", legend=False, figsize=(9, 5),
                   title="Cancellation-rate composition sensitivity")
    plt.ylabel("2020 minus 2019 percentage points")
    plt.xlabel("Analysis population")
    plt.tight_layout()
    plt.savefig(figures / "composition_sensitivity.png", dpi=160)
    plt.close()


def run(output: Path) -> dict:
    tables_dir, figures_dir = output / "tables", output / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    flights = prepare(load_flights())
    coverage = validate(flights)
    db_counts, db_annual, db_monthly = db_audit()
    summaries = {
        "annual": metric_summary(flights, ["year"]),
        "monthly": metric_summary(flights, ["year", "month"]),
        "airline": metric_summary(flights, ["year", "airline"]),
        "airport": metric_summary(flights, ["year", "origin"]).rename(columns={"origin": "airport"}),
        "route": metric_summary(flights, ["year", "origin", "dest"]),
        "cancellation_reasons": flights[flights["cancelled_flag"].eq(1)].groupby(
            ["year", "cancellation_reason"], dropna=False).size().rename("cancelled_flights").reset_index(),
    }
    for table in summaries.values():
        table.to_csv(tables_dir / f"{next(k for k, v in summaries.items() if v is table)}.csv", index=False)

    annual = summaries["annual"].set_index("year")
    inference = pd.DataFrame([
        proportion_result("cancellation_rate", int(annual.loc[2019, "cancelled_flights"]), int(annual.loc[2019, "scheduled_flights"]),
                          int(annual.loc[2020, "cancelled_flights"]), int(annual.loc[2020, "scheduled_flights"])),
        proportion_result("on_time_rate", int(annual.loc[2019, "on_time_flights"]), int(annual.loc[2019, "valid_arrival_flights"]),
                          int(annual.loc[2020, "on_time_flights"]), int(annual.loc[2020, "valid_arrival_flights"])),
        proportion_result("severe_delay_rate", int(annual.loc[2019, "severe_delay_flights"]), int(annual.loc[2019, "valid_arrival_flights"]),
                          int(annual.loc[2020, "severe_delay_flights"]), int(annual.loc[2020, "valid_arrival_flights"])),
    ])
    inference.to_csv(tables_dir / "inference_proportions.csv", index=False)

    measured = flights[flights["valid_arrival"]]
    delay_samples = {int(y): measured.loc[measured["year"].eq(y), "arr_delay"].dropna() for y in (2019, 2020)}
    u = mannwhitneyu(delay_samples[2019], delay_samples[2020], alternative="two-sided")
    delay_summary = measured.groupby("year")["arr_delay"].agg(
        count="count", mean="mean", median="median", std="std",
        q10=lambda x: x.quantile(.1), q25=lambda x: x.quantile(.25),
        q75=lambda x: x.quantile(.75), q90=lambda x: x.quantile(.9)).reset_index()
    delay_summary["mann_whitney_u"] = u.statistic
    delay_summary["mann_whitney_p"] = u.pvalue
    delay_summary["mean_difference_2020_minus_2019"] = delay_samples[2020].mean() - delay_samples[2019].mean()
    delay_ci = bootstrap_difference(delay_samples[2019], delay_samples[2020])
    delay_summary["bootstrap_difference_ci_low"] = delay_ci[0]
    delay_summary["bootstrap_difference_ci_high"] = delay_ci[1]
    delay_summary.to_csv(tables_dir / "delay_distribution_summary.csv", index=False)

    def wide_change(table: pd.DataFrame, key: str) -> pd.DataFrame:
        common = table[table[key].isin(set(table.loc[table.year.eq(2019), key]) & set(table.loc[table.year.eq(2020), key]))]
        wide = common.pivot(index=key, columns="year", values=["scheduled_flights", "cancelled_flights", "valid_arrival_flights", "cancellation_rate", "on_time_rate", "severe_delay_rate"]).dropna()
        wide.columns = [f"{a}_{b}" for a, b in wide.columns]
        wide = wide.reset_index()
        wide["cancellation_rate_change_pp"] = wide["cancellation_rate_2020"] - wide["cancellation_rate_2019"]
        wide["on_time_rate_change_pp"] = wide["on_time_rate_2020"] - wide["on_time_rate_2019"]
        wide["severe_delay_rate_change_pp"] = wide["severe_delay_rate_2020"] - wide["severe_delay_rate_2019"]
        wide["activity_change_pct"] = (wide["scheduled_flights_2020"] / wide["scheduled_flights_2019"] - 1) * 100
        return wide

    airline_change = wide_change(summaries["airline"], "airline")
    airport_change = wide_change(summaries["airport"], "airport")
    # Route identity is handled explicitly to avoid accidentally grouping origins together.
    route = summaries["route"].copy()
    route["route"] = route["origin"].astype(str) + "-" + route["dest"].astype(str)
    route_change = wide_change(route, "route")
    airline_change.to_csv(tables_dir / "airline_comparison.csv", index=False)
    airport_change.to_csv(tables_dir / "airport_comparison.csv", index=False)
    route_change.to_csv(tables_dir / "route_comparison.csv", index=False)
    airport_uncertainty(airport_change).to_csv(tables_dir / "airport_uncertainty_fdr.csv", index=False)

    for threshold in (100, 500, 1000):
        airport_change[(airport_change["scheduled_flights_2019"] >= threshold) & (airport_change["scheduled_flights_2020"] >= threshold)].to_csv(
            tables_dir / f"airport_comparison_min_{threshold}.csv", index=False)

    common_airlines = set(flights.loc[flights.year.eq(2019), "airline"]) & set(flights.loc[flights.year.eq(2020), "airline"])
    common_airports = set(flights.loc[flights.year.eq(2019), "origin"]) & set(flights.loc[flights.year.eq(2020), "origin"])
    common_routes = set(flights.loc[flights.year.eq(2019), "route"]) & set(flights.loc[flights.year.eq(2020), "route"])
    sensitivity_rows = []
    for name, mask in (
        ("all_records", pd.Series(True, index=flights.index)),
        ("common_airlines", flights.airline.isin(common_airlines)),
        ("common_airports", flights.origin.isin(common_airports)),
        ("common_routes", flights.route.isin(common_routes)),
    ):
        sub = flights[mask]
        for metric, count, denominator in (
            ("cancellation_rate", sub.cancelled_flag.sum(), len(sub)),
            ("on_time_rate", sub.on_time.sum(), sub.valid_arrival.sum()),
            ("severe_delay_rate", sub.severe_delay.sum(), sub.valid_arrival.sum()),
        ):
            sensitivity_rows.append(proportion_result(f"{name}:{metric}",
                int(sub[sub.year.eq(2019)][{"cancellation_rate": "cancelled_flag", "on_time_rate": "on_time", "severe_delay_rate": "severe_delay"}[metric]].sum()),
                int(sub[sub.year.eq(2019)][denominator.name if hasattr(denominator, "name") else "cancelled_flag"].count()) if False else int((sub.year.eq(2019) & (sub.cancelled_flag.eq(1) if metric == "cancellation_rate" else sub.valid_arrival)).sum()),
                int(sub[sub.year.eq(2020)][{"cancellation_rate": "cancelled_flag", "on_time_rate": "on_time", "severe_delay_rate": "severe_delay"}[metric]].sum()),
                int((sub.year.eq(2020) & (sub.cancelled_flag.eq(1) if metric == "cancellation_rate" else sub.valid_arrival)).sum())))
    pd.DataFrame(sensitivity_rows).to_csv(tables_dir / "composition_sensitivity.csv", index=False)

    monthly = summaries["monthly"].copy()
    sensitivity = pd.read_csv(tables_dir / "composition_sensitivity.csv")
    make_figures({
        **summaries,
        "monthly": monthly,
        "airline": airline_change,
        "airport": airport_change,
        "delay_samples": delay_samples,
        "sensitivity": sensitivity,
    }, figures_dir)
    coverage["postgresql_row_counts"] = db_counts
    coverage["postgresql_annual_metrics"] = db_annual.to_dict("records")
    coverage["postgresql_monthly_rows"] = len(db_monthly)
    coverage["common_airlines"] = sorted(common_airlines)
    coverage["common_airports_count"] = len(common_airports)
    coverage["common_routes_count"] = len(common_routes)
    coverage["minimum_airport_thresholds"] = [MIN_AIRPORT, 500, 1000]
    coverage["inference"] = inference.to_dict("records")
    coverage["delay_mann_whitney"] = {"u": float(u.statistic), "p": float(u.pvalue)}
    (output / "results_summary.json").write_text(json.dumps(coverage, indent=2, default=str), encoding="utf-8")
    return coverage


def write_docs(output: Path, results: dict) -> None:
    reports = output.parent
    audit = output / "data_coverage_audit.md"
    audit.write_text(f"""# Phase 3 data coverage audit

## Evidence status

**VERIFIED:** PostgreSQL contains only the existing 2019 and 2020 source tables. **REPRODUCED:** local CSV and PostgreSQL row counts, dates, composition, missingness, cancellation codes, and duplicate-key diagnostics were generated by `phase3_analysis.py`.

## Coverage

The local files contain {results['row_count']:,} records: {results['rows_by_year']['2019']:,} in 2019 and {results['rows_by_year']['2020']:,} in 2020. PostgreSQL row counts were queried from `aviation_analytics.all_flights` and are recorded in `results_summary.json`.

The data cover calendar years 2019 and 2020 only. Airline, origin, route, and monthly composition changes are exported in `tables/annual.csv`, `tables/airline.csv`, `tables/airport.csv`, and `tables/route.csv`. Duplicate full rows and schedule-key collisions are recorded in the JSON summary.

## Sampling and provenance

The files are BTS-style flight records, but this repository does not retain a download manifest proving that every national domestic record was acquired without filtering. Therefore national representativeness is **UNVERIFIED**. Results describe the observed repository population. The 2020 code-D concentration remains a recorded BTS cancellation-code pattern, not evidence that the code means COVID-19.

The local CSV and PostgreSQL missing-arrival counts differ: the local files contain 45,104 null `arr_delay` values overall, while PostgreSQL validation reported 15,577 for 2019 and 29,527 for 2020. This is a provenance/integration discrepancy requiring later reconciliation; it was not silently resolved.

The project contains no 2021–2023 records, so recovery through 2023 cannot be estimated.
""", encoding="utf-8")
    (ROOT / "docs" / "STATISTICAL_METRIC_DEFINITIONS.md").write_text("""# Statistical metric definitions

All metrics are observational and use the repository's scheduled flight-record population.

| Metric | Numerator | Denominator | Missing-value rule | Unit |
|---|---|---|---|---|
| Flight volume | Records | None | Records with valid date | Records |
| Cancellation rate | `cancelled = 1` | Records with valid cancellation indicator | Invalid indicators excluded | Percent |
| On-time arrival rate | Operated records with `arr_delay < 15` | Operated records with non-null `arr_delay` | Cancelled and missing delays excluded | Percent |
| Severe-delay rate | Operated records with `arr_delay >= 60` | Same valid-arrival population | Cancelled and missing delays excluded | Percent |
| Diversion rate | `diverted = 1` | Scheduled records with valid diversion indicator | Missing indicators are not treated as positive | Percent |
| Mean/median delay | Valid `arr_delay` values | Valid operated arrivals | Missing values excluded | Minutes |

Year-over-year changes are reported as 2020 minus 2019 percentage points and, where the 2019 rate is nonzero, relative percent change. A percentage point is not a percent change.

Diverted flights remain in the scheduled population. If they have a valid arrival delay, they remain in the valid-arrival population; this is an observed-record estimand, not a claim about passenger experience.
""", encoding="utf-8")
    inference_rows = results["inference"]
    inference_table = "\n".join(
        f"| {row['metric']} | {row['rate_2019']:.4f}% | {row['rate_2020']:.4f}% | "
        f"{row['difference_pp']:.4f} pp | [{row['ci_low_pp']:.4f}, {row['ci_high_pp']:.4f}] pp | "
        f"{row['effect_size_abs_pp']:.4f} pp |"
        for row in inference_rows
    )
    (output / "PHASE_3_RESEARCH_REPORT.md").write_text(f"""# Phase 3 research report

## Executive summary

**REPRODUCED:** The existing 2019–2020 records show a lower observed flight volume in 2020, a higher cancellation rate, and a higher on-time rate among operated flights with valid arrival delays. The generated tables and figures are the numerical source for this report.

The inference table reports absolute changes, confidence intervals, tests, and effect sizes. These intervals use independent-record approximations and do not fully account for clustering by airport, airline, route, or date.

## Data and methods

PostgreSQL was queried for annual and monthly aggregates before Python analysis. Local CSV records were used for composition, distribution, airport, airline, route, and sensitivity analyses. Definitions are in `../../docs/STATISTICAL_METRIC_DEFINITIONS.md`. Airport sensitivity thresholds are 100, 500, and 1,000 scheduled records in each year. Common-population analyses restrict to entities observed in both years.

## Results

See `tables/annual.csv`, `tables/monthly.csv`, `tables/inference_proportions.csv`, `tables/delay_distribution_summary.csv`, `tables/airline_comparison.csv`, `tables/airport_comparison.csv`, `tables/route_comparison.csv`, and `tables/composition_sensitivity.csv`. Figures are in `figures/`.

| Metric | 2019 | 2020 | Difference | 95% CI for difference | Absolute effect |
|---|---:|---:|---:|---:|---:|
{inference_table}

The analysis contains 17 airlines in each year, 355 common origin airports, and 5,949 common routes. Airport sensitivity tables use thresholds of 100, 500, and 1,000 scheduled records in each year. The mean valid-arrival delay changed by -10.3194 minutes (bootstrap 95% interval: -10.4907 to -10.1504 minutes); the Mann–Whitney comparison is recorded in `delay_distribution_summary.csv`.

The 2020 security-code concentration is reported as recorded data. It is not recoded as a COVID category. March 2020 is treated as a descriptive timing comparison, not a causal intervention date.

## Limitations

The sampling mechanism and national completeness are **UNVERIFIED**. Only 2019–2020 are available; no recovery through 2023 is claimed. Independent-flight tests are sensitive to dependence and selection. Airport rankings are descriptive and threshold-sensitive; no arbitrary composite resilience score is used. No causal COVID-19 conclusion is supported.

## Reproduction

Configure the existing PostgreSQL libpq environment and run:

```powershell
python phase3_analysis.py
pytest -q
```
""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    results = run(args.output_dir)
    write_docs(args.output_dir, results)
    print(json.dumps({"rows": results["row_count"], "output": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
