"""Reproducible data preparation, business analysis, statistics, and modeling.

Run from the repository root:
    python src/analysis_pipeline.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"
OUTPUT_DIR = ROOT / "processed_data"
REQUIRED_COLUMNS = {
    "fl_date", "airline", "origin", "dest", "crs_dep_time", "crs_arr_time",
    "dep_delay", "arr_delay", "cancelled", "cancellation_code", "distance",
}
REASON_LABELS = {"A": "Carrier", "B": "Weather", "C": "NAS", "D": "Security"}
UNKNOWN_REASON = "Unknown"


def load_flights() -> pd.DataFrame:
    frames = []
    for year in (2019, 2020):
        path = DATA_DIR / f"flights_{year}.csv"
        frame = pd.read_csv(path, low_memory=False)
        frame["year"] = year
        frames.append(frame)
    flights = pd.concat(frames, ignore_index=True)
    flights["fl_date"] = pd.to_datetime(flights["fl_date"], errors="coerce")
    flights["month"] = flights["fl_date"].dt.month.astype("Int64")
    flights["day_of_week"] = flights["fl_date"].dt.dayofweek.add(1).astype("Int64")
    flights["cancelled"] = pd.to_numeric(flights["cancelled"], errors="coerce")
    flights["cancelled_flag"] = flights["cancelled"].eq(1).astype(int)
    flights["cancellation_reason"] = flights["cancellation_code"].map(REASON_LABELS)
    cancelled = flights["cancelled_flag"].eq(1)
    flights.loc[cancelled, "cancellation_reason"] = (
        flights.loc[cancelled, "cancellation_reason"].fillna(UNKNOWN_REASON)
    )
    flights.loc[flights["cancelled_flag"].eq(0), "cancellation_reason"] = "Not cancelled"
    flights["route"] = flights["origin"].astype("string") + "-" + flights["dest"].astype("string")
    return flights


def validate(flights: pd.DataFrame) -> dict:
    duplicate_key = ["fl_date", "airline", "fl_number", "origin", "dest", "crs_dep_time"]
    invalid_codes = sorted(
        flights.loc[
            flights["cancellation_code"].notna()
            & ~flights["cancellation_code"].isin(REASON_LABELS),
            "cancellation_code",
        ].dropna().unique().tolist()
    )
    return {
        "row_count": int(len(flights)),
        "rows_by_year": {str(k): int(v) for k, v in flights.groupby("year").size().items()},
        "duplicate_rows": int(flights.duplicated().sum()),
        "duplicate_schedule_keys": int(flights.duplicated(duplicate_key).sum()),
        "missing_required_fields": {
            c: int(flights[c].isna().sum()) for c in sorted(REQUIRED_COLUMNS)
        },
        "invalid_cancelled_values": int((~flights["cancelled"].isin([0, 1])).sum()),
        "invalid_cancellation_codes": invalid_codes,
        "date_parse_failures": int(flights["fl_date"].isna().sum()),
        "years": sorted(flights["year"].dropna().unique().astype(int).tolist()),
        "airlines_by_year": {
            str(k): int(v) for k, v in flights.groupby("year")["airline"].nunique().items()
        },
        "origins_by_year": {
            str(k): int(v) for k, v in flights.groupby("year")["origin"].nunique().items()
        },
        "routes_by_year": {
            str(k): int(v) for k, v in flights.groupby("year")["route"].nunique().items()
        },
    }


def rate_table(grouped: pd.core.groupby.DataFrameGroupBy) -> pd.DataFrame:
    result = grouped.agg(
        total_flights=("cancelled_flag", "size"),
        cancelled_flights=("cancelled_flag", "sum"),
        valid_arrival_flights=("arr_delay", "count"),
        avg_departure_delay=("dep_delay", "mean"),
        avg_arrival_delay=("arr_delay", "mean"),
    ).reset_index()
    result["cancellation_rate"] = (
        result["cancelled_flights"] / result["total_flights"] * 100
    ).round(4)
    return result


def build_summaries(flights: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = rate_table(flights.groupby(["year", "month"], dropna=False))
    airlines = rate_table(flights.groupby(["year", "airline"], dropna=False))
    airports = rate_table(flights.groupby(["year", "origin"], dropna=False)).rename(
        columns={"origin": "airport"}
    )
    routes = rate_table(flights.groupby(["year", "origin", "dest"], dropna=False))

    operated = flights[flights["cancelled_flag"].eq(0)].copy()
    operated["valid_arrival"] = operated["arr_delay"].notna()
    measured = operated[operated["valid_arrival"]].copy()
    measured["on_time"] = measured["arr_delay"].lt(15)
    measured["severe_delay"] = measured["arr_delay"].ge(60)
    performance = (
        measured.groupby(["year", "month"])
        .agg(
            valid_arrival_flights=("on_time", "size"),
            on_time_flights=("on_time", "sum"),
            severe_delay_flights=("severe_delay", "sum"),
            avg_departure_delay=("dep_delay", "mean"),
            avg_arrival_delay=("arr_delay", "mean"),
        )
        .reset_index()
    )
    performance["on_time_rate"] = performance["on_time_flights"] / performance["valid_arrival_flights"] * 100
    performance["severe_delay_rate"] = (
        performance["severe_delay_flights"] / performance["valid_arrival_flights"] * 100
    )
    return {
        "monthly_summary": monthly,
        "airline_summary": airlines,
        "airport_summary": airports,
        "route_summary": routes,
        "performance_summary": performance,
    }


def business_questions(flights: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    routes = summaries["route_summary"]
    route_wide = routes.pivot_table(
        index=["origin", "dest"], columns="year",
        values=["total_flights", "valid_arrival_flights", "cancellation_rate", "avg_arrival_delay"],
    )
    route_wide.columns = [f"{a}_{b}" for a, b in route_wide.columns]
    route_wide = route_wide.reset_index()
    for metric in ("total_flights", "cancellation_rate", "avg_arrival_delay"):
        route_wide[f"{metric}_change"] = route_wide.get(f"{metric}_2020", np.nan) - route_wide.get(
            f"{metric}_2019", np.nan
        )
    comparable_routes = route_wide.dropna(subset=["total_flights_2019", "total_flights_2020"])
    a1 = comparable_routes[comparable_routes["total_flights_2019"].ge(30) & comparable_routes["total_flights_2020"].ge(30)].sort_values(
        "cancellation_rate_change", ascending=False
    ).head(100)
    a2 = comparable_routes[
        comparable_routes["valid_arrival_flights_2019"].ge(30)
        & comparable_routes["valid_arrival_flights_2020"].ge(30)
    ].sort_values(
        "avg_arrival_delay_change", ascending=False
    ).head(100)

    cancelled = flights[flights["cancelled_flag"].eq(1)]
    a3 = cancelled.groupby(["year", "cancellation_reason"]).size().rename("cancelled_flights").reset_index()
    totals = a3.groupby("year")["cancelled_flights"].transform("sum")
    a3["share_of_cancellations"] = a3["cancelled_flights"] / totals * 100
    a4 = cancelled.groupby(["month", "cancellation_reason"]).size().rename("cancelled_flights").reset_index()
    a4["month_reason_rank"] = a4.groupby("cancellation_reason")["cancelled_flights"].rank(
        method="min", ascending=False
    )
    a5 = summaries["performance_summary"].copy()

    airline = summaries["airline_summary"].pivot_table(
        index="airline", columns="year",
        values=["cancellation_rate", "avg_arrival_delay", "total_flights"],
    )
    airline.columns = [f"{a}_{b}" for a, b in airline.columns]
    airline = airline.reset_index()
    for metric in ("cancellation_rate", "avg_arrival_delay"):
        airline[f"{metric}_change"] = airline[f"{metric}_2020"] - airline[f"{metric}_2019"]
    a6 = airline.dropna(subset=["total_flights_2019", "total_flights_2020"])
    a6 = a6[a6["total_flights_2019"].ge(100) & a6["total_flights_2020"].ge(100)].sort_values(
        "cancellation_rate_change", ascending=False
    )

    march_april = flights[flights["month"].isin([3, 4])]
    a7_airports = rate_table(march_april.groupby(["year", "origin"])).rename(columns={"origin": "airport"})
    a7_routes = rate_table(march_april.groupby(["year", "origin", "dest"]))
    return {
        "a1_route_cancellation_changes": a1,
        "a2_route_arrival_delay_changes": a2,
        "a3_cancellation_reason_changes": a3,
        "a4_monthly_cancellation_reasons": a4,
        "a5_on_time_severe_delay": a5,
        "a6_airline_reliability_changes": a6,
        "a7_march_april_airports": a7_airports,
        "a7_march_april_routes": a7_routes,
    }


def statistics(flights: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for year, group in flights.groupby("year"):
        n = len(group)
        x = int(group["cancelled_flag"].sum())
        p = x / n
        z = norm.ppf(0.975)
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
        rows.append({"year": year, "flights": n, "cancelled": x, "cancellation_rate": p * 100,
                     "ci_low": max(0, center - margin) * 100, "ci_high": min(1, center + margin) * 100})
    ci = pd.DataFrame(rows)
    a, b = flights[flights["year"].eq(2019)], flights[flights["year"].eq(2020)]
    p1, p2 = a["cancelled_flag"].mean(), b["cancelled_flag"].mean()
    pooled = (a["cancelled_flag"].sum() + b["cancelled_flag"].sum()) / (len(a) + len(b))
    se = np.sqrt(pooled * (1 - pooled) * (1 / len(a) + 1 / len(b)))
    z_score = (p2 - p1) / se
    test = pd.DataFrame([{"test": "Two-proportion z-test", "rate_2019": p1 * 100, "rate_2020": p2 * 100,
                          "difference_percentage_points": (p2 - p1) * 100, "z_score": z_score,
                          "p_value_two_sided": 2 * norm.sf(abs(z_score)), "significant_at_05": 2 * norm.sf(abs(z_score)) < 0.05}])
    return ci, test


def modeling(flights: pd.DataFrame) -> pd.DataFrame:
    features = ["year", "month", "day_of_week", "airline", "origin", "dest", "crs_dep_time", "crs_arr_time", "distance"]
    data = flights.dropna(subset=["fl_date", "cancelled_flag"]).sort_values("fl_date")
    split_date = pd.Timestamp("2020-01-01")
    train, test = data[data["fl_date"] < split_date], data[data["fl_date"] >= split_date]
    if len(train) > 250_000:
        train = train.sample(250_000, random_state=42)
    X_train, y_train = train[features], train["cancelled_flag"]
    X_test, y_test = test[features], test["cancelled_flag"]
    numeric = ["month", "day_of_week", "crs_dep_time", "crs_arr_time", "distance"]
    categorical = ["year", "airline", "origin", "dest"]
    prep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    models = {
        "dummy_baseline": DummyClassifier(strategy="prior"),
        "logistic_regression": LogisticRegression(max_iter=300, class_weight="balanced", solver="saga"),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=14, min_samples_leaf=5, class_weight="balanced",
            n_jobs=-1, random_state=42,
        ),
    }
    rows = []
    for name, estimator in models.items():
        pipe = Pipeline([("preprocess", prep), ("model", estimator)])
        pipe.fit(X_train, y_train)
        probability = pipe.predict_proba(X_test)[:, 1]
        prediction = probability >= 0.5
        rows.append({"model": name, "train_rows": len(train), "test_rows": len(test),
                     "recall": recall_score(y_test, prediction, zero_division=0),
                     "precision": precision_score(y_test, prediction, zero_division=0),
                     "pr_auc": average_precision_score(y_test, probability),
                     "roc_auc": roc_auc_score(y_test, probability),
                     "brier_score": brier_score_loss(y_test, probability)})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-modeling",
        action="store_true",
        help="Regenerate analytical outputs without fitting or rewriting model_metrics.csv.",
    )
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(exist_ok=True)
    flights = load_flights()
    validation = validate(flights)
    (OUTPUT_DIR / "validation_report.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    summaries = build_summaries(flights)
    for name, frame in summaries.items():
        frame.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
    for name, frame in business_questions(flights, summaries).items():
        frame.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
    ci, test = statistics(flights)
    ci.to_csv(OUTPUT_DIR / "cancellation_confidence_intervals.csv", index=False)
    test.to_csv(OUTPUT_DIR / "cancellation_significance_test.csv", index=False)
    if not args.skip_modeling:
        modeling(flights).to_csv(OUTPUT_DIR / "model_metrics.csv", index=False)
    print(f"Processed {len(flights):,} flights; outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
