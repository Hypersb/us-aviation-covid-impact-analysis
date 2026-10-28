# U.S. Airport Recovery & Resilience Intelligence

## Completion report

**Execution date:** 2026-10-21  
**Evidence policy:** Only executed results are reported as results. Missing BTS partitions, PostgreSQL outputs, and post-2020 recovery estimates are explicitly marked unavailable.

## Delivered

### Existing-work reconciliation

- Reverified the existing 2019–2020 pipeline, outputs, tests, and dashboard.
- Preserved raw CSVs, notebooks, and existing dashboard functionality.
- Confirmed that the repository contains 1,237,023 observed flight records.
- Confirmed the original files cover all calendar dates in 2019 and 2020.

### Data engineering

- [ingest_bts.py](../src/ingest_bts.py): resumable, checksum-aware, idempotent monthly acquisition.
- [data_layers.py](../src/data_layers.py): Bronze/Silver/Gold transformations.
- [research_pipeline.py](../src/research_pipeline.py): airport-day/month panels, resilience comparisons, and offline drift diagnostics.
- [DATA_PROVENANCE.md](DATA_PROVENANCE.md): source evidence, provenance gaps, and acquisition status.
- [RESEARCH_METHOD.md](RESEARCH_METHOD.md): estimands, denominators, and research limitations.

### Research outputs actually generated

Running `python src/research_pipeline.py` generated:

- `processed_data/airport_day_panel.csv`: 143,882 rows.
- `processed_data/airport_month_panel.csv`: 8,310 rows.
- `processed_data/airport_resilience_monthly.csv`.
- `processed_data/offline_drift_report.csv`.

The panels separate scheduled observations, cancellations, diversions, valid arrival-delay observations, missing arrival delays, on-time flights, and severe delays. On-time and severe-delay denominators use operated flights with non-null arrival delay.

The resilience output compares 2020 with the same calendar month in 2019. It is an observed disruption/early-response comparison, not a full post-pandemic recovery analysis.

### PostgreSQL assets

Created executable:

- [schema.sql](../sql/schema.sql)
- [load.sql](../sql/load.sql)
- [analytical_queries.sql](../sql/analytical_queries.sql)
- [research_queries.sql](../sql/research_queries.sql)
- [benchmark.sql](../sql/benchmark.sql)
- [load_postgres.py](../src/load_postgres.py)
- [postgres_existing.py](../src/postgres_existing.py)
- [integrate_existing.sql](../sql/integrate_existing.sql)
- [validate_existing.sql](../sql/validate_existing.sql)
- [benchmarks_existing.sql](../sql/benchmarks_existing.sql)

The integration now targets the user-loaded `public.flights_2019_new` and `public.flights_2020_new` tables without importing or recreating flight tables. The local server passed `pg_isready`, but authentication failed because no password or supported local credential was available. No PostgreSQL schema inspection, query result, or benchmark is claimed. Details are in [POSTGRES_INTEGRATION_REPORT.md](POSTGRES_INTEGRATION_REPORT.md).

### Machine-learning governance

- No models were retrained for this completion.
- Added [MODEL_CARD.md](MODEL_CARD.md).
- Added the offline distribution-shift report.
- Kept the existing model metrics unchanged.
- The drift report is not a live monitoring system and does not claim model-performance drift without repeated scoring.

### Dashboard

The existing Streamlit dashboard was extended with an Airport resilience tab showing:

- Same-month airport disruption comparisons.
- Activity ratios.
- Cancellation-rate changes.
- Offline distribution-shift diagnostics.

Health verification returned:

```text
HTTP 200 ok
```

## Verification

| Verification | Actual result |
|---|---|
| `pytest -q` | 9 passed |
| Python compilation | Passed |
| `git diff --check` | Passed |
| Research pipeline | Passed; 143,882 airport-day and 8,310 airport-month rows |
| Bronze/Silver/Gold workflow | Passed previously; 2 Bronze, 2 Silver, 15 Gold outputs |
| Dashboard health | Passed; HTTP 200 `ok` |
| PostgreSQL readiness | Passed |
| PostgreSQL authentication | Blocked; no credentials |
| BTS 2018–2023 acquisition | 0 partitions acquired |
| ML retraining | Intentionally not performed |

## Important limitations

1. Existing 2019–2020 CSV provenance remains unresolved; the repository lacks original BTS export metadata, checksums, and sampling documentation.
2. The Security cancellation-code anomaly is confirmed in the raw files but not independently reconciled to official BTS flight-level records.
3. No full 2018–2023 data was downloaded or fabricated.
4. Full post-pandemic recovery cannot be estimated from 2019–2020 data alone.
5. Statistical intervals in the generated panels are descriptive Wilson intervals and do not account for clustered sampling.
6. The existing ML evaluation remains a single chronological 2019-to-2020 benchmark without rolling validation or calibration study.
7. PostgreSQL performance claims cannot be made until authenticated execution captures before/after plans and timings.

## Reproducibility commands

```powershell
pytest -q
python src/analysis_pipeline.py --skip-modeling
python src/research_pipeline.py
python src/data_layers.py --output-dir data_layers
streamlit run dashboard/app.py
```

To acquire BTS data, first populate [ingestion_manifest.example.json](../ingestion_manifest.example.json) with exact official export URLs and expected checksums. The downloader will then acquire only explicitly configured partitions and report each status.
