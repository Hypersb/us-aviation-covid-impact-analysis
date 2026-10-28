# PostgreSQL integration

## Existing database contract

The existing database already contains:

- `public.flights_2019_new`: 757,673 records.
- `public.flights_2020_new`: 479,350 records.
- Combined expected count: 1,237,023 records.

The integration scripts do not import CSVs and do not create duplicate flight tables.

## Secure connection

The Python validator [postgres_existing.py](../src/postgres_existing.py) uses libpq environment variables:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "<existing aviation database>"
$env:PGUSER = "<database user>"
# Set PGPASSWORD only in the current secure process, or configure PGpassFile.
python src/postgres_existing.py --json
```

Do not place passwords in source, `.env` files committed to Git, command history, or report output. On Windows, a supported `PGPASSFILE` is preferable to exposing a password in a command line.

During this execution, the PostgreSQL service accepted connections but this terminal had no password, `PGPASSFILE`, or other credential configuration. A noninteractive connection was therefore not attempted with a guessed credential and failed with `no password supplied`.

## Validation and integration scripts

- [validate_existing.sql](../sql/validate_existing.sql): schema, row count, dates, cancellation codes, and missingness.
- [integrate_existing.sql](../sql/integrate_existing.sql): creates only the `aviation_analytics` schema, views, and indexes over existing tables. It never imports, truncates, drops, or recreates flight tables.
- [benchmarks_existing.sql](../sql/benchmarks_existing.sql): three `EXPLAIN (ANALYZE, BUFFERS)` benchmark queries.

Run after secure authentication:

```powershell
psql --no-psqlrc --set ON_ERROR_STOP=1 --dbname $env:PGDATABASE --file sql/validate_existing.sql
psql --no-psqlrc --set ON_ERROR_STOP=1 --dbname $env:PGDATABASE --file sql/integrate_existing.sql
psql --no-psqlrc --set ON_ERROR_STOP=1 --dbname $env:PGDATABASE --file sql/benchmarks_existing.sql
```

The benchmark file should be run once before `integrate_existing.sql` and once afterward, saving the `EXPLAIN` output outside the repository or in an explicitly reviewed benchmark artifact. No benchmark result is claimed until both runs execute successfully.
