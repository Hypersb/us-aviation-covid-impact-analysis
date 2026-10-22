# Research method: airport disruption and resilience

## Scope and estimands

The currently available files cover observed flight records in 2019 and 2020 only. They do not support a claim about complete national flight volume or full post-pandemic recovery. The research outputs therefore describe observed airport disruption and early response relative to a same-month 2019 baseline.

## Panels

- `airport_day_panel.csv`: airport-date observations with scheduled, cancelled, diverted, valid-arrival, missingness, on-time, severe-delay, mean, and median-delay fields.
- `airport_month_panel.csv`: the same measures aggregated by airport and calendar month.
- `airport_resilience_monthly.csv`: 2020-to-2019 same-month activity and reliability comparisons.

Cancelled flights remain in scheduled-flight and cancellation denominators. On-time and severe-delay rates use only operated records with non-null `arr_delay`. Diversion rates use all scheduled records.

## Resilience proxies

- **Disruption magnitude:** same-month 2020 minus 2019 cancellation rate in percentage points, and the activity ratio.
- **Activity ratio:** observed 2020 scheduled flights divided by observed 2019 scheduled flights for the same airport and month.
- **Coverage:** valid arrival observations divided by scheduled flights.
- **Uncertainty:** cancellation-rate Wilson intervals are descriptive binomial intervals; they do not account for sampling design or clustering.

Because the available data ends in 2020, no full recovery time, post-pandemic recovery stability, or cumulative multi-year recovery claim is made. A future 2018–2023 acquisition is required for those estimands.

## Offline drift diagnostics

`offline_drift_report.csv` compares monthly 2019 and 2020 target prevalence, diversion prevalence, missing-arrival rates, observed flight counts, airport counts, and route counts. It is an offline diagnostic, not a live monitoring system and not a retrained-model evaluation.
