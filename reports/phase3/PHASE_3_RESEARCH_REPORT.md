# Phase 3 research report

## Executive summary

**REPRODUCED:** The existing 2019–2020 records show a lower observed flight volume in 2020, a higher cancellation rate, and a higher on-time rate among operated flights with valid arrival delays. The generated tables and figures are the numerical source for this report.

The inference table reports absolute changes, confidence intervals, tests, and effect sizes. These intervals use independent-record approximations and do not fully account for clustering by airport, airline, route, or date.

## Data and methods

PostgreSQL was queried for annual and monthly aggregates before Python analysis. Local CSV records were used for composition, distribution, airport, airline, route, and sensitivity analyses. Definitions are in `../../docs/STATISTICAL_METRIC_DEFINITIONS.md`. Airport sensitivity thresholds are 100, 500, and 1,000 scheduled records in each year. Common-population analyses restrict to entities observed in both years.

## Results

See `tables/annual.csv`, `tables/monthly.csv`, `tables/inference_proportions.csv`, `tables/delay_distribution_summary.csv`, `tables/airline_comparison.csv`, `tables/airport_comparison.csv`, `tables/route_comparison.csv`, and `tables/composition_sensitivity.csv`. Figures are in `figures/`.

| Metric | 2019 | 2020 | Difference | 95% CI for difference | Absolute effect |
|---|---:|---:|---:|---:|---:|
| cancellation_rate | 1.7942% | 5.9992% | 4.2050 pp | [4.1314, 4.2786] pp | 4.2050 pp |
| on_time_rate | 80.9657% | 90.2026% | 9.2369 pp | [9.1123, 9.3615] pp | 9.2369 pp |
| severe_delay_rate | 6.6687% | 2.8220% | -3.8467 pp | [-3.9213, -3.7721] pp | 3.8467 pp |

The analysis contains 17 airlines in each year, 355 common origin airports, and 5,949 common routes. Airport sensitivity tables use thresholds of 100, 500, and 1,000 scheduled records in each year. The mean valid-arrival delay changed by -10.3194 minutes (bootstrap 95% interval: -10.4907 to -10.1504 minutes); the Mann–Whitney comparison is recorded in `delay_distribution_summary.csv`.

The 2020 security-code concentration is reported as recorded data. It is not recoded as a COVID category. March 2020 is treated as a descriptive timing comparison, not a causal intervention date.

## Limitations

The sampling mechanism and national completeness are **UNVERIFIED**. Only 2019–2020 are available; no recovery through 2023 is claimed. Independent-flight tests are sensitive to dependence and selection. Airport rankings are descriptive and threshold-sensitive; no arbitrary composite resilience score is used. No causal COVID-19 conclusion is supported.

## Reproduction

Configure the existing PostgreSQL libpq environment and run:

```powershell
python phase3_analysis.py
pytest -q
```
