# Data provenance and acquisition record

## Current repository files

| File | Observed rows | Date coverage | SHA-256 recorded? | Acquisition evidence |
|---|---:|---|---|---|
| `Data/flights_2019.csv` | 757,673 | 2019-01-01 through 2019-12-31 | No | Local file only |
| `Data/flights_2020.csv` | 479,350 | 2020-01-01 through 2020-12-31 | No | Local file only |

**VERIFIED:** The files contain 33 columns matching the BTS Airline On-Time Performance style, including flight date, reporting carrier, scheduled and actual times, delays, cancellation status/code, diversion status, distance, and delay-cause fields.

**VERIFIED:** The repository has no original download URL, BTS query parameters, export timestamp, provider release identifier, checksum, or sampling description for these files. Their current provenance therefore cannot be independently established from repository evidence.

**VERIFIED:** The local transformation in [analysis_pipeline.py](../analysis_pipeline.py) adds year, month, day-of-week, cancellation flag/reason, and route. It does not alter the raw files.

## Official reference sources

The intended authoritative source is the Bureau of Transportation Statistics (BTS) TranStats Airline On-Time Performance dataset:

- [BTS download interface](https://www.transtats.bts.gov/DL_SelectFields.asp?Table_ID=236)
- [BTS On-Time Performance interface](https://www.transtats.bts.gov/ONTIME/)
- [BTS database information](https://www.transtats.bts.gov/DatabaseInfo.asp?DB_ID=120&DB_Name=Airline%20On-Time%20Performance%20Data%20(1987-present))
- [BTS cancellation/delay cause reference](https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp)
- [BTS technical directive on on-time reporting](https://www.bts.gov/topics/airlines-and-airports/number-23-technical-directive-time-reporting-effective-jan-1-2014)

**VERIFIED:** BTS defines cancellation codes A, B, C, and D as Air Carrier, Weather, National Aviation System, and Security respectively.

**UNVERIFIED:** The current files have not been matched row-for-row against an official BTS export. No new BTS partitions were downloaded during this phase.

## Security-code reconciliation status

**REPRODUCED:** The current raw files contain:

- 2019: 13,594 cancellations; code D count 0.
- 2020: 28,757 cancellations; code D count 24,221 (84.23%).
- 2020 code D is concentrated in March (9,921) and April (12,863).

**VERIFIED:** The Python mapping is a direct A/B/C/D label mapping. No code-D records were recoded or discarded.

**UNVERIFIED:** Whether the abrupt distribution change reflects actual reporting, an extraction/filtering change, a sampling change, or another provenance issue. The delay-cause fields are not an independent validation source for cancelled rows.

## Resumable acquisition design

[ingest_bts.py](../ingest_bts.py) implements a manifest-driven downloader for monthly 2018–2023 partitions. It:

- requires an exact source URL per year-month;
- supports optional expected SHA-256 checksums;
- downloads through a temporary `.part` file;
- verifies checksums when supplied;
- writes a state JSON file;
- skips an existing partition only when its recorded hash still matches;
- is idempotent and safe to resume;
- never overwrites raw repository files.

The [example manifest](../ingestion_manifest.example.json) intentionally contains a placeholder rather than an invented BTS URL.

**Actual acquisition result:** 0 of 72 requested 2018–2023 monthly partitions acquired in this phase. No download was claimed because exact export URLs and checksums were not available in the repository.

## Bronze/Silver/Gold record

[data_layers.py](../data_layers.py) implements:

- **Bronze:** immutable copies of source CSV partitions;
- **Silver:** typed dates/numeric cancellation values plus derived cancellation flag, month, day-of-week, and route;
- **Gold:** summary, business-question, and statistical tables generated with the existing pipeline functions.

These transforms preserve the original `Data/` files. A full Bronze/Silver/Gold run was not executed on the 250 MB source files in this phase; unit-level functionality and syntax were verified.

## Rules for future acquisitions

1. Preserve the exact downloaded file and source metadata.
2. Record URL, query fields, extraction date, response metadata, file size, and SHA-256.
3. Validate schema and code values before promotion from Bronze to Silver.
4. Validate date coverage, row counts, duplicate schedule keys, cancellation/diversion distributions, and null patterns.
5. Promote only reconciled partitions to Gold.
6. Never silently recode or remove cancellation-code D.
