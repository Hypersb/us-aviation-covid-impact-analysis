"""Validate and integrate the already-loaded PostgreSQL aviation tables.

Connection settings are read from libpq environment variables:
PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD or a supported
PGPASSFILE. Passwords are never printed or written by this module.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import psycopg


TABLES = ("flights_2019_new", "flights_2020_new")
REQUIRED_COLUMNS = {
    "fl_date", "airline", "origin", "dest", "crs_dep_time", "crs_arr_time",
    "dep_delay", "arr_delay", "cancelled", "cancellation_code", "distance",
}


def connection_kwargs() -> dict[str, str]:
    names = {
        "PGHOST": "host",
        "PGPORT": "port",
        "PGDATABASE": "dbname",
        "PGUSER": "user",
        "PGPASSWORD": "password",
        "PGPASSFILE": "passfile",
    }
    return {target: os.environ[source] for source, target in names.items()
            if os.environ.get(source)}


def validate() -> dict[str, Any]:
    kwargs = connection_kwargs()
    with psycopg.connect(**kwargs) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                ORDER BY table_name, ordinal_position
                """,
                (list(TABLES),),
            )
            schema_rows = cursor.fetchall()
            result: dict[str, Any] = {"connection": {"database": connection.info.dbname,
                                                     "user": connection.info.user,
                                                     "host": connection.info.host},
                                      "tables": {}}
            for table in TABLES:
                columns = [
                    {"name": row[1], "type": row[2]}
                    for row in schema_rows if row[0] == table
                ]
                cursor.execute(
                    f"""
                    SELECT COUNT(*)::bigint, MIN(fl_date), MAX(fl_date),
                           COUNT(*) FILTER (WHERE cancelled = 1)::bigint,
                           COUNT(*) FILTER (WHERE diverted = 1)::bigint
                    FROM public."{table}"
                    """
                )
                counts = cursor.fetchone()
                cursor.execute(
                    f"""
                    SELECT COALESCE(cancellation_code, '<NULL>') AS code,
                           COUNT(*)::bigint
                    FROM public."{table}"
                    WHERE cancelled = 1
                    GROUP BY 1
                    ORDER BY 1
                    """
                )
                codes = [{"code": row[0], "count": row[1]} for row in cursor.fetchall()]
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FILTER (WHERE arr_delay IS NULL)::bigint,
                           COUNT(*) FILTER (WHERE dep_delay IS NULL)::bigint,
                           COUNT(*) FILTER (WHERE origin IS NULL)::bigint,
                           COUNT(*) FILTER (WHERE dest IS NULL)::bigint
                    FROM public."{table}"
                    """
                )
                missing = cursor.fetchone()
                result["tables"][table] = {
                    "columns": columns,
                    "missing_required_columns": sorted(REQUIRED_COLUMNS - {item["name"] for item in columns}),
                    "row_count": counts[0],
                    "min_date": str(counts[1]),
                    "max_date": str(counts[2]),
                    "cancelled_count": counts[3],
                    "diverted_count": counts[4],
                    "cancellation_codes": codes,
                    "missingness": {
                        "arr_delay": missing[0],
                        "dep_delay": missing[1],
                        "origin": missing[2],
                        "dest": missing[3],
                    },
                }
            return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate()
    print(json.dumps(result, indent=2, default=str) if args.json else json.dumps(result, default=str))


if __name__ == "__main__":
    main()
