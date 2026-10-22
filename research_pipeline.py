"""Research-ready airport panels, resilience metrics, and offline drift diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from analysis_pipeline import load_flights


def summarize(grouped: pd.core.groupby.DataFrameGroupBy) -> pd.DataFrame:
    result = grouped.agg(
        scheduled_flights=("cancelled_flag", "size"),
        cancelled_flights=("cancelled_flag", "sum"),
        diverted_flights=("diverted", "sum"),
        valid_arrival_flights=("valid_arrival", "sum"),
        on_time_flights=("on_time", "sum"),
        severe_delay_flights=("severe_delay", "sum"),
        missing_arrival_delay=("arr_delay", lambda values: values.isna().sum()),
        mean_arrival_delay=("arr_delay", "mean"),
        median_arrival_delay=("arr_delay", "median"),
    ).reset_index()
    result["cancellation_rate"] = result["cancelled_flights"] / result["scheduled_flights"] * 100
    result["diversion_rate"] = result["diverted_flights"] / result["scheduled_flights"] * 100
    result["on_time_rate"] = result["on_time_flights"] / result["valid_arrival_flights"] * 100
    result["severe_delay_rate"] = result["severe_delay_flights"] / result["valid_arrival_flights"] * 100
    result["missing_arrival_rate"] = result["missing_arrival_delay"] / result["scheduled_flights"] * 100
    return result


def build_panels(flights: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = flights.copy()
    frame["diverted"] = pd.to_numeric(frame["diverted"], errors="coerce").fillna(0)
    frame["on_time"] = frame["cancelled_flag"].eq(0) & frame["arr_delay"].notna() & frame["arr_delay"].lt(15)
    frame["severe_delay"] = frame["cancelled_flag"].eq(0) & frame["arr_delay"].notna() & frame["arr_delay"].ge(60)
    frame["valid_arrival"] = frame["cancelled_flag"].eq(0) & frame["arr_delay"].notna()
    airport_day = summarize(frame.groupby(["fl_date", "year", "month", "origin"], dropna=False))
    airport_day = airport_day.rename(columns={"origin": "airport"})
    airport_month = summarize(frame.groupby(["year", "month", "origin"], dropna=False))
    airport_month = airport_month.rename(columns={"origin": "airport"})
    return airport_day, airport_month


def wilson(count: pd.Series, total: pd.Series) -> tuple[pd.Series, pd.Series]:
    z = norm.ppf(0.975)
    p = count / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return (center - margin).clip(lower=0), (center + margin).clip(upper=1)


def resilience(airport_month: pd.DataFrame) -> pd.DataFrame:
    baseline = airport_month[airport_month["year"].eq(2019)].set_index(["airport", "month"])
    observed = airport_month[airport_month["year"].eq(2020)].set_index(["airport", "month"])
    joined = observed.join(
        baseline[["scheduled_flights", "cancellation_rate", "on_time_rate", "valid_arrival_flights"]],
        lsuffix="_2020", rsuffix="_2019", how="inner",
    ).reset_index()
    joined["activity_ratio_2020_to_2019"] = joined["scheduled_flights_2020"] / joined["scheduled_flights_2019"]
    joined["cancellation_rate_change_pp"] = joined["cancellation_rate_2020"] - joined["cancellation_rate_2019"]
    joined["on_time_rate_change_pp"] = joined["on_time_rate_2020"] - joined["on_time_rate_2019"]
    joined["valid_arrival_coverage_2020"] = joined["valid_arrival_flights_2020"] / joined["scheduled_flights_2020"]
    return joined


def drift_report(flights: pd.DataFrame) -> pd.DataFrame:
    frame = flights.copy()
    frame["month"] = frame["fl_date"].dt.month
    rows = []
    for month in range(1, 13):
        left = frame[(frame["year"] == 2019) & (frame["month"] == month)]
        right = frame[(frame["year"] == 2020) & (frame["month"] == month)]
        for metric, left_value, right_value in [
            ("scheduled_flights", len(left), len(right)),
            ("cancellation_prevalence", left["cancelled_flag"].mean(), right["cancelled_flag"].mean()),
            ("diversion_prevalence", left["diverted"].mean(), right["diverted"].mean()),
            ("missing_arrival_rate", left["arr_delay"].isna().mean(), right["arr_delay"].isna().mean()),
            ("unique_origins", left["origin"].nunique(), right["origin"].nunique()),
            ("unique_routes", (left["origin"].astype(str) + "-" + left["dest"].astype(str)).nunique(),
             (right["origin"].astype(str) + "-" + right["dest"].astype(str)).nunique()),
        ]:
            rows.append({"month": month, "metric": metric, "2019": left_value, "2020": right_value,
                         "change": right_value - left_value})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("processed_data"))
    args = parser.parse_args()
    flights = load_flights()
    airport_day, airport_month = build_panels(flights)
    airport_month["cancellation_ci_low"], airport_month["cancellation_ci_high"] = wilson(
        airport_month["cancelled_flights"], airport_month["scheduled_flights"]
    )
    airport_day.to_csv(args.output_dir / "airport_day_panel.csv", index=False)
    airport_month.to_csv(args.output_dir / "airport_month_panel.csv", index=False)
    resilience(airport_month).to_csv(args.output_dir / "airport_resilience_monthly.csv", index=False)
    drift_report(flights).to_csv(args.output_dir / "offline_drift_report.csv", index=False)
    print(f"Airport-day rows: {len(airport_day):,}; airport-month rows: {len(airport_month):,}")


if __name__ == "__main__":
    main()
