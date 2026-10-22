# Phase 2 engineering report

**Date:** 2026-10-21  
**Scope:** Remaining Prompt 2 engineering work after the accepted denominator correction.

## Executive result

The repository now contains source-configured monthly ingestion, Bronze/Silver/Gold transformation code, corrected route delay thresholds and cancellation-reason handling, PostgreSQL schema/load/query/benchmark assets, and automated tests. Raw datasets and existing dashboard structure were preserved. A `--skip-modeling` pipeline option was added so future engineering regenerations do not fit or rewrite ML outputs.

The current 2019–2020 source files were not independently proven to originate from a specific BTS export. No 2018–2023 partitions were downloaded. PostgreSQL client binaries and a listening server were detected, but noninteractive authentication failed because no password/credentials were available; therefore no database schema, load, or benchmark execution is claimed.

## Completed implementation

### Metric and grouping corrections

**VERIFIED:** [analysis_pipeline.py](../analysis_pipeline.py) now records `valid_arrival_flights` and computes delay rates only from operated flights with non-null `arr_delay`.

**VERIFIED:** Route arrival-delay comparisons require at least 30 valid arrival-delay observations in each year. Cancellation-rate comparisons continue to use the 30 total-flight threshold.

**VERIFIED:** Cancelled records with an unmapped code now receive an explicit `Unknown` cancellation reason. Known A/B/C/D codes retain their BTS labels; non-cancelled records retain `Not cancelled`.

### Resumable ingestion

**IMPLEMENTED:** [ingest_bts.py](../ingest_bts.py) provides manifest-driven, checksum-aware, temporary-file-based, idempotent monthly acquisition for the 72 year-month partitions from 2018 through 2023.

**ACTUAL RESULT:** 0 partitions acquired. The manifest example intentionally contains a placeholder because the repository has no exact BTS export URLs or checksums. This is a blocker, not a failed download represented as success.

### Bronze/Silver/Gold

**IMPLEMENTED:** [data_layers.py](../data_layers.py) defines Bronze copies, Silver typed/derived CSVs, and Gold analytical outputs. It does not modify `Data/`.

**ACTUAL RESULT:** Executed successfully against the current repository data in a temporary session directory: 2 Bronze partitions, 2 Silver partitions, and 15 Gold tables. The temporary outputs were removed after verification; the raw `Data/` files were unchanged.

### PostgreSQL

**IMPLEMENTED:** 

- [schema.sql](../sql/schema.sql)
- [load.sql](../sql/load.sql)
- [analytical_queries.sql](../sql/analytical_queries.sql)
- [benchmark.sql](../sql/benchmark.sql)
- [load_postgres.py](../load_postgres.py)

The SQL uses valid delay observations, explicit cancellation-reason grouping, and indexes suitable for before/after plan comparison.

**BLOCKER:** `pg_isready` reported a server accepting connections, but `psql -w` failed with `no password supplied`. No schema creation, load, query result, or benchmark timing is reported.

The three benchmark queries are ready to execute once credentials are supplied. Their before/after result must be captured using `EXPLAIN (ANALYZE, BUFFERS)` before and after the indexes in `schema.sql`.

### Automated tests

Added:

- [test_metrics.py](../tests/test_metrics.py)
- [test_ingestion.py](../tests/test_ingestion.py)
- [test_sql_consistency.py](../tests/test_sql_consistency.py)
- [conftest.py](../tests/conftest.py)

Coverage includes:

- valid-arrival denominator behavior;
- route delay threshold behavior;
- unknown cancellation-code validation;
- cancellation-reason completeness;
- ingestion idempotency;
- duplicate manifest rejection;
- SQL/Python definition consistency.

## Verification results

| Check | Result |
|---|---|
| Python compilation | Passed |
| Initial pytest run | Failed during collection because repository root was not on test import path |
| Corrected pytest run | Passed 6, failed 2 before final test-fixture/path fixes |
| Final pytest run | Passed: 8 tests |
| Pipeline regeneration | Passed with `--skip-modeling`; processed 1,237,023 flights and regenerated non-ML outputs |
| PostgreSQL server readiness | Server accepted TCP readiness check |
| PostgreSQL authentication | Blocked: no password/credentials |
| Dashboard health check | Passed: HTTP 200, body `ok` |

The table deliberately distinguishes observed intermediate results from final results. The final report should be updated after the final verification commands complete.

## Source and provenance blockers

See [DATA_PROVENANCE.md](DATA_PROVENANCE.md). The principal blocker is the missing acquisition manifest for the existing files. The BTS reference URLs are documented, but no row-level comparison was performed.

## Remaining limitations

- No official BTS row-level reconciliation.
- No 2018–2023 data acquired.
- No PostgreSQL load or benchmark results due to credentials.
- No ML retraining, calibration, or dashboard redesign, as required.
- No full Bronze/Silver/Gold run over the large files.
- The raw files still lack checksums and immutable source metadata.

## Recommended next actions

1. Provide or obtain exact BTS monthly export URLs and checksums.
2. Run the ingestion manifest for one month per year before scaling to all 72 partitions.
3. Supply PostgreSQL credentials and execute schema/load/benchmark capture.
4. Run the full Bronze/Silver/Gold workflow in a capacity-appropriate environment.
5. Provide PostgreSQL credentials, then execute the schema/load/benchmark workflow and append the captured plans and timings.
