"""Run the PostgreSQL schema/load workflow through the psql client."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run_psql(sql_file: Path, database: str, data_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = ["psql", "--set", "ON_ERROR_STOP=1", "--dbname", database]
    if data_dir is not None:
        command.extend(["--set", f"data_dir={data_dir.resolve()}"])
    command.extend(["--file", str(sql_file)])
    return subprocess.run(command, text=True, capture_output=True, check=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="aviation_audit")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data_dir = args.data_dir or root / "Data"
    result = run_psql(root / "sql" / "schema.sql", args.database)
    print(result.stdout, end="")
    if result.returncode:
        raise SystemExit(result.returncode)
    if not args.schema_only:
        result = run_psql(root / "sql" / "load.sql", args.database, data_dir)
        print(result.stdout, end="")
        print(result.stderr, end="")
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
