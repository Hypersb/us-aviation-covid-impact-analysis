"""Bronze/Silver/Gold transformations for the aviation datasets."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

from analysis_pipeline import build_summaries, business_questions, load_flights, statistics

ROOT = Path(__file__).resolve().parents[1]


def write_bronze(source_dir: Path, bronze_dir: Path) -> list[Path]:
    bronze_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for source in sorted(source_dir.glob("flights_*.csv")):
        destination = bronze_dir / source.name
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        outputs.append(destination)
    return outputs


def transform_silver(bronze_dir: Path, silver_dir: Path) -> list[Path]:
    silver_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for source in sorted(bronze_dir.glob("flights_*.csv")):
        frame = pd.read_csv(source, low_memory=False)
        frame["fl_date"] = pd.to_datetime(frame["fl_date"], errors="coerce")
        frame["cancelled"] = pd.to_numeric(frame["cancelled"], errors="coerce")
        frame["cancelled_flag"] = frame["cancelled"].eq(1).astype("int8")
        frame["month"] = frame["fl_date"].dt.month.astype("Int64")
        frame["day_of_week"] = frame["fl_date"].dt.dayofweek.add(1).astype("Int64")
        frame["route"] = frame["origin"].astype("string") + "-" + frame["dest"].astype("string")
        destination = silver_dir / source.name
        frame.to_csv(destination, index=False)
        outputs.append(destination)
    return outputs


def transform_gold(repository_root: Path, gold_dir: Path) -> list[Path]:
    gold_dir.mkdir(parents=True, exist_ok=True)
    flights = load_flights()
    summaries = build_summaries(flights)
    outputs = []
    for name, frame in {**summaries, **business_questions(flights, summaries)}.items():
        destination = gold_dir / f"{name}.csv"
        frame.to_csv(destination, index=False)
        outputs.append(destination)
    ci, test = statistics(flights)
    for name, frame in {"cancellation_confidence_intervals": ci,
                        "cancellation_significance_test": test}.items():
        destination = gold_dir / f"{name}.csv"
        frame.to_csv(destination, index=False)
        outputs.append(destination)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT / "Data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data_layers")
    args = parser.parse_args()
    bronze = write_bronze(args.source_dir, args.output_dir / "bronze")
    silver = transform_silver(args.output_dir / "bronze", args.output_dir / "silver")
    gold = transform_gold(Path.cwd(), args.output_dir / "gold")
    print(f"Bronze partitions: {len(bronze)}; Silver partitions: {len(silver)}; Gold tables: {len(gold)}")


if __name__ == "__main__":
    main()
