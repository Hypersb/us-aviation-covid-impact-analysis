# PostgreSQL integration report

**Date:** 2026-10-21

## Scope and safety

This integration targets the two existing user-loaded tables only:

- `public.flights_2019_new`
- `public.flights_2020_new`

No CSV import was run. No existing table was overwritten, dropped, truncated, or duplicated. The integration created only the `aviation_analytics` schema, analytical views, and reviewed indexes.

## Connection

The PostgreSQL 18 service was reachable at `127.0.0.1:5432`. Authentication succeeded using the standard Windows password file at `%APPDATA%\postgresql\pgpass.conf`; its contents were not read or displayed.

Database: `aviation_covid_analysis`  
User: `postgres`

## Source-table validation

| Table | Rows | Minimum date | Maximum date | Cancelled | Diverted |
|---|---:|---|---|---:|---:|
| `public.flights_2019_new` | 757,673 | 2019-01-01 | 2019-12-31 | 13,594 | 1,983 |
| `public.flights_2020_new` | 479,350 | 2020-01-01 | 2020-12-31 | 28,757 | 770 |
| Combined analytical view | 1,237,023 | — | — | — | — |

Both source tables have the same 32-column schema. All required project fields are present. `origin` and `dest` have zero missing values in both tables.

Missingness queried from PostgreSQL:

- 2019: `arr_delay` 15,577; `dep_delay` 13,142.
- 2020: `arr_delay` 29,527; `dep_delay` 28,643.

Cancellation-code counts:

- 2019: A 3,836; B 7,309; C 2,449; D 0.
- 2020: A 1,924; B 2,142; C 470; D 24,221.

These values match the local raw-file validation and the Python outputs.

## SQL/Python reconciliation

The SQL aggregates matched the generated Python outputs exactly:

| Year | Total | Cancelled | Valid arrivals | On-time rate | Severe-delay rate |
|---|---:|---:|---:|---:|---:|
| 2019 | 757,673 | 13,594 | 742,096 | 80.965670% | 6.668679% |
| 2020 | 479,350 | 28,757 | 449,823 | 90.202591% | 2.821999% |

## Analytical views

Created successfully:

- `aviation_analytics.all_flights`
- `aviation_analytics.airport_day` — 143,882 rows
- `aviation_analytics.airport_month` — 8,310 rows
- `aviation_analytics.cancellation_reason` — 7 rows

The views use the same denominator definitions as Python: cancellation/diversion metrics use scheduled observations; on-time and severe-delay metrics use operated flights with non-null arrival delay.

## Index review and application

Before integration, the two source tables had no indexes listed in `pg_indexes`.

After the baseline benchmark, these four indexes were created:

- `flights_2019_new_date_route_idx`
- `flights_2020_new_date_route_idx`
- `flights_2019_new_cancelled_date_idx`
- `flights_2020_new_cancelled_date_idx`

The executable integration SQL contains no import, `TRUNCATE`, `DROP TABLE`, or source-table write operation.

## Benchmark measurements

Each query was measured before and after integration with `EXPLAIN (ANALYZE, BUFFERS)`. The benchmark script was corrected so the same table and predicates are used in both runs.

| Query | Baseline | After indexes | Change |
|---|---:|---:|---|
| March–April 2020 date/origin aggregation | 202.925 ms | 37.918 ms | 81.3% lower |
| 2019 cancelled route aggregation | 136.882 ms | 73.845 ms | 46.0% lower |
| 2020 operated valid-arrival airport average | 179.868 ms | 179.013 ms | 0.5% lower; effectively unchanged |

The first query used an index-only scan after integration. The second used the cancellation index. The third remained a parallel sequential scan, so no meaningful improvement is claimed for that workload. These are local single-run observations, not general performance guarantees.

## Mutation and duplication checks

- Existing source-table counts remained 757,673 and 479,350.
- Combined view count was 1,237,023.
- Duplicate schedule-key excess was 0 for both source tables.
- No source rows were inserted, updated, deleted, or overwritten.
- No duplicate flight table was created.

## Verification commands and results

- `python src/postgres_existing.py --json`: passed.
- `sql/validate_existing.sql`: passed.
- `sql/integrate_existing.sql`: passed.
- Comparable baseline benchmarks: passed.
- Comparable post-index benchmarks: passed.
- Analytical view counts: passed.
- Python tests: **11 passed**.
- Python compilation: passed.
- `git diff --check`: passed.

## Remaining limitations

- Database contains only the existing 2019–2020 tables; no 2018–2023 data was acquired.
- Benchmark timings are local single-run observations.
- No causal interpretation is implied by the views.
- No database-level constraints were added to the user-loaded source tables.
- Views are regular views rather than materialized aggregates.
