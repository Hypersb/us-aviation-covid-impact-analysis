# U.S. Aviation Disruption Intelligence Platform

## Project completion report

This report documents the work completed in the U.S. Aviation COVID-19 Impact Analysis project, the reproducible implementation that was added, the findings produced from the sampled data, and the limitations that must be disclosed.

## 1. Starting point

The repository already contained:

- 2019 and 2020 flight CSV files in `Data/`
- Several exploratory and business-analysis notebooks
- A basic Streamlit dashboard
- Initial monthly, airline, and airport summary CSV files
- A project plan describing the research objective

The existing work was preserved. The notebooks were not replaced with a new notebook workflow. Instead, a script-driven pipeline was added so the analysis can be regenerated consistently from the raw data.

## 2. Work completed

### 2.1 Reproducible data pipeline

Added:

- `analysis_pipeline.py`
- `requirements.txt`
- `sql/business_questions.sql`
- `processed_data/validation_report.json`

The pipeline:

1. Loads `Data/flights_2019.csv` and `Data/flights_2020.csv`.
2. Adds year, month, day-of-week, and route fields.
3. Normalizes cancellation flags and cancellation reasons.
4. Validates duplicates, required fields, cancellation values, cancellation codes, dates, airlines, airports, and routes.
5. Builds reusable summary tables.
6. Answers business questions A1–A7.
7. Calculates confidence intervals for cancellation rates.
8. Runs a two-proportion significance test.
9. Trains chronological cancellation models.
10. Writes all results to `processed_data/`.

Run it from the project root:

```powershell
python src/analysis_pipeline.py
```

### 2.2 SQL business analysis

Added PostgreSQL-style query examples in:

```text
sql/business_questions.sql
```

The SQL covers:

- A1: route cancellation-rate changes
- A2: route arrival-delay changes
- A3/A4: cancellation reasons by year and month
- A5: on-time and severe-delay rates

The Python pipeline materializes the complete set of A1–A7 outputs locally so the dashboard does not depend on a running PostgreSQL server.

### 2.3 Data engineering outputs

The pipeline produces:

- `monthly_summary.csv`
- `airline_summary.csv`
- `airport_summary.csv`
- `route_summary.csv`
- `performance_summary.csv`
- `a1_route_cancellation_changes.csv`
- `a2_route_arrival_delay_changes.csv`
- `a3_cancellation_reason_changes.csv`
- `a4_monthly_cancellation_reasons.csv`
- `a5_on_time_severe_delay.csv`
- `a6_airline_reliability_changes.csv`
- `a7_march_april_airports.csv`
- `a7_march_april_routes.csv`
- `cancellation_confidence_intervals.csv`
- `cancellation_significance_test.csv`
- `model_metrics.csv`
- `validation_report.json`

`a3_cancellation_reason_changes.csv` is the cancellation-reason summary equivalent requested in the project checklist. If a literal filename named `cancellation_reason_summary.csv` is required for a publication contract, it can be added as a copy or renamed output in a later packaging step.

### 2.4 Statistical analysis

Implemented:

- Wilson 95% confidence intervals for cancellation rates
- Two-proportion z-test comparing 2019 and 2020 cancellation proportions
- Difference in percentage points
- Practical interpretation of the difference
- Explicit limitation that the data is sampled

### 2.5 Machine learning

Implemented a chronological prediction workflow:

- Target: whether a scheduled flight is cancelled
- Training period: 2019
- Test period: 2020
- Features available before departure:
  - Year
  - Month
  - Day of week
  - Airline
  - Origin
  - Destination
  - Scheduled departure time
  - Scheduled arrival time
  - Distance
- Excluded leakage-prone post-departure fields such as actual departure time, arrival delay, and cancellation reason
- Compared:
  - Dummy baseline
  - Logistic regression
  - Random forest

### 2.6 Streamlit dashboard

Replaced the initial single-page dashboard with a structured application in:

```text
dashboard/app.py
```

The dashboard now contains:

- Overview
- Monthly activity and cancellation rates
- On-time and severe-delay trends
- Airline comparisons
- Airport comparisons
- Cancellation reasons
- Route findings
- March–April 2020 disruption analysis
- Confidence intervals
- Statistical test results
- Model performance
- Data-quality report

Run it with:

```powershell
streamlit run dashboard/app.py
```

The Streamlit health endpoint was tested successfully and returned `200 OK` with body `ok`.

## 3. Data validation findings

The pipeline processed:

| Measure | Result |
|---|---:|
| Total records | 1,237,023 |
| 2019 records | 757,673 |
| 2020 records | 479,350 |
| Duplicate rows | 0 |
| Duplicate schedule keys | 0 |
| Invalid cancellation values | 0 |
| Invalid cancellation codes | 0 |
| Date parsing failures | 0 |
| Airlines in 2019 | 17 |
| Airlines in 2020 | 17 |
| Origin airports in 2019 | 360 |
| Origin airports in 2020 | 365 |
| Routes in 2019 | 6,365 |
| Routes in 2020 | 6,337 |

Missing values:

- Missing departure delays: 41,785
- Missing arrival delays: 45,104
- Missing cancellation codes: 1,194,672

The missing delay fields are expected for cancelled flights because a flight that never operated has no actual departure or arrival delay. Missing cancellation codes are expected for flights that were not cancelled.

## 4. Business findings

### A1 — Routes with the largest cancellation-rate increases

Routes were compared only when they had at least 30 sampled flights in both years. The largest increases were:

| Route | 2019 rate | 2020 rate | Change |
|---|---:|---:|---:|
| PIE–AVL | 0.00% | 31.82% | +31.82 pp |
| LAS–SCK | 0.00% | 29.27% | +29.27 pp |
| LAS–MFE | 0.00% | 28.95% | +28.95 pp |
| PGD–CVG | 0.00% | 27.66% | +27.66 pp |
| USA–FLL | 0.00% | 26.83% | +26.83 pp |
| SFB–TYS | 1.89% | 28.13% | +26.24 pp |
| CVG–SFB | 0.00% | 25.64% | +25.64 pp |
| AVL–SFB | 0.00% | 25.49% | +25.49 pp |
| EVV–ORD | 3.70% | 29.03% | +25.33 pp |
| PIE–USA | 0.00% | 23.33% | +23.33 pp |

These are sampled route-level changes. Small route counts can create unstable percentages, which is why the 30-flight minimum was applied.

### A2 — Routes with the largest increases in average arrival delay

The largest observed increases among routes with at least 30 flights in both years were:

| Route | 2019 average arrival delay | 2020 average arrival delay | Change |
|---|---:|---:|---:|
| HNL–ORD | -10.43 min | 49.44 min | +59.87 min |
| SFB–GRR | -0.25 min | 48.26 min | +48.51 min |
| EUG–PHX | -9.51 min | 34.46 min | +43.97 min |
| MFR–PHX | -3.85 min | 33.02 min | +36.87 min |
| ABE–SFB | 20.98 min | 50.15 min | +29.17 min |
| PBG–IAD | -6.12 min | 22.04 min | +28.16 min |
| BGM–DTW | 7.47 min | 34.31 min | +26.84 min |
| JAC–DFW | 5.38 min | 29.13 min | +23.75 min |
| ASE–LAX | 3.63 min | 25.28 min | +21.65 min |
| PIA–CLT | -0.80 min | 20.83 min | +21.62 min |

Average arrival delays are calculated from available delay observations. Cancelled flights do not have an actual arrival delay and therefore do not contribute to the average.

### A3 — How cancellation reasons changed

Cancellation reason shares changed substantially:

| Year | Reason | Cancelled flights | Share |
|---|---|---:|---:|
| 2019 | Weather | 7,309 | 53.77% |
| 2019 | Carrier | 3,836 | 28.22% |
| 2019 | NAS | 2,449 | 18.02% |
| 2020 | Security | 24,221 | 84.23% |
| 2020 | Weather | 2,142 | 7.45% |
| 2020 | Carrier | 1,924 | 6.69% |
| 2020 | NAS | 470 | 1.63% |

The most important observed shift is from weather-dominated cancellations in 2019 to security-coded cancellations in 2020. The dataset's source coding and the meaning of the security code should be documented before interpreting that category as a direct causal measure of COVID-19.

### A4 — Months when each cancellation reason was most common

Using the combined monthly cancellation-reason table:

| Reason | Peak month | Cancelled flights in peak month |
|---|---:|---:|
| Carrier | March | 1,554 |
| NAS | July | 435 |
| Security | April | 12,863 |
| Weather | January | 1,780 |

The sharpest disruption signal is the concentration of security-coded cancellations in March and April 2020, especially April.

### A5 — On-time performance and severe delays

On-time is defined as arrival delay below 15 minutes. Severe delay is defined as arrival delay of at least 60 minutes. These rates use operated flights with a valid arrival-delay observation; cancelled flights and operated flights without an arrival-delay observation are excluded from these delay denominators.

Overall comparison:

| Measure | 2019 | 2020 |
|---|---:|---:|
| On-time rate | approximately 81.0% | approximately 90.2% |
| Severe-delay rate | approximately 6.7% | approximately 2.8% |

The monthly pattern shows:

- 2020 on-time performance was higher than 2019 in every month in this sample.
- 2020 severe-delay rates were lower than 2019 in every month.
- This improvement among flights that operated occurred alongside a much higher cancellation rate.
- April 2020 had a 41.62% cancellation rate, while operated flights with valid arrival-delay observations had a 95.16% on-time rate and a 1.41% severe-delay rate.

This is an important selection effect: the flights that continued operating were not necessarily representative of all scheduled flights.

### A6 — Airlines with the greatest reliability changes

Airlines were compared only when they had at least 100 sampled flights in both years.

Largest increases in cancellation rate:

| Airline | 2019 rate | 2020 rate | Change |
|---|---:|---:|---:|
| Allegiant Air | 0.44% | 14.84% | +14.39 pp |
| United Air Lines Inc. | 0.84% | 7.16% | +6.32 pp |
| Southwest Airlines Co. | 2.44% | 8.21% | +5.77 pp |
| PSA Airlines Inc. | 2.35% | 7.30% | +4.94 pp |
| Hawaiian Airlines Inc. | 0.09% | 4.96% | +4.86 pp |
| Delta Air Lines Inc. | 0.18% | 4.99% | +4.81 pp |
| American Airlines Inc. | 2.10% | 6.07% | +3.96 pp |

All listed airlines had higher cancellation rates in 2020. At the same time, their average arrival delays generally decreased because the operating schedule and traffic mix changed substantially.

### A7 — Airports and routes most affected during March–April 2020

By number of cancelled flights at departure airports in March–April 2020:

| Airport | Sampled flights | Cancelled | Cancellation rate |
|---|---:|---:|---:|
| ATL | 4,798 | 1,095 | 22.82% |
| DFW | 4,269 | 1,047 | 24.53% |
| ORD | 4,206 | 1,016 | 24.16% |
| DEN | 3,651 | 951 | 26.05% |
| CLT | 3,445 | 938 | 27.23% |
| LAS | 2,322 | 803 | 34.58% |
| PHX | 2,673 | 693 | 25.93% |
| LAX | 2,636 | 586 | 22.23% |
| MCO | 2,004 | 517 | 25.80% |
| LGA | 1,791 | 515 | 28.75% |

By number of cancelled flights on routes in March–April 2020:

| Route | Sampled flights | Cancelled | Cancellation rate |
|---|---:|---:|---:|
| LGA–ORD | 146 | 54 | 36.99% |
| SFO–LAX | 207 | 47 | 22.71% |
| ORD–LGA | 135 | 44 | 32.59% |
| LAS–LAX | 161 | 44 | 27.33% |
| LAX–LAS | 168 | 40 | 23.81% |
| SAN–LAS | 87 | 40 | 45.98% |
| DAL–HOU | 107 | 40 | 37.38% |
| DEN–PHX | 136 | 39 | 28.68% |
| HOU–DAL | 107 | 39 | 36.45% |
| ORD–DCA | 96 | 38 | 39.58% |

The largest airports by cancellation count are not necessarily the airports with the highest cancellation rates. Airport size must be considered when interpreting these rankings.

## 5. Monthly activity findings

The overall cancellation rates were:

| Year | Cancellation rate |
|---|---:|
| 2019 | 1.79% |
| 2020 | 6.00% |

The major monthly pattern was:

- January 2020: 1.21%
- February 2020: 0.90%
- March 2020: 16.86%
- April 2020: 41.62%
- May 2020: 6.61%
- June 2020: 0.32%
- December 2020: 1.07%

The disruption was concentrated in March and April, followed by a rapid reduction in cancellations after April. The sample also shows substantially fewer scheduled/observed flights in later 2020 months than in 2019.

## 6. Statistical findings

### Confidence intervals

Wilson 95% confidence intervals:

| Year | Flights | Cancelled | Rate | 95% CI |
|---|---:|---:|---:|---:|
| 2019 | 757,673 | 13,594 | 1.794% | 1.765%–1.824% |
| 2020 | 479,350 | 28,757 | 5.999% | 5.932%–6.067% |

### Two-proportion test

- Null hypothesis: the 2019 and 2020 cancellation proportions are equal.
- Difference: +4.205 percentage points.
- z-score: approximately 125.30.
- Two-sided p-value: effectively 0 at the displayed precision.
- Result: statistically significant at the 0.05 level.

The very small p-value is expected with more than one million observations. Statistical significance does not by itself establish causation, national representativeness, or business importance. The practical effect is more important here: the observed cancellation rate was roughly 3.3 times higher in 2020 than in 2019.

## 7. Machine-learning findings

The target was cancellation status. The split was chronological to avoid training on future observations.

| Model | Recall | Precision | PR-AUC | ROC-AUC | Brier score |
|---|---:|---:|---:|---:|---:|
| Dummy baseline | 0.000 | 0.000 | 0.0600 | 0.500 | 0.0582 |
| Logistic regression | 0.805 | 0.066 | 0.0774 | 0.579 | 0.4661 |
| Random forest | 0.577 | 0.086 | 0.0836 | 0.604 | 0.2169 |

Interpretation:

- The random forest was the strongest of the tested models by ROC-AUC and PR-AUC.
- Performance was still modest.
- Precision was low because cancellations are a minority class and the 2020 operating environment changed sharply.
- The model should not be marketed as a high-confidence operational prediction system.
- The model is suitable for an exploratory baseline and for demonstrating leakage-aware chronological evaluation.
- A production model would require richer pre-departure features, repeated time-based validation, calibration analysis, monitoring, and a clearer operational decision threshold.

## 8. Defensible conclusions

The following conclusions are supported by the sampled data:

1. Cancellation rates were materially higher in 2020 than in 2019.
2. The disruption was concentrated in March and April 2020.
3. Weather was the dominant cancellation reason in 2019, while security-coded cancellations dominated in 2020.
4. All sufficiently represented airlines in the comparison experienced higher cancellation rates in 2020.
5. Operated flights had better on-time and severe-delay metrics in 2020, but this occurred during a period of extensive cancellations and reduced activity.
6. Several routes and large airports experienced substantial cancellation-rate increases during the disruption period.
7. A simple chronological cancellation model showed only limited predictive discrimination.

## 9. Limitations

The following limitations must remain visible in the README, dashboard, or final presentation:

1. The datasets are described as samples, not verified complete national populations.
2. The analysis cannot claim exact nationwide flight-volume changes without a verified representative sampling design.
3. A statistically significant difference does not prove that COVID-19 alone caused the observed changes.
4. Airline, route, airport, and month comparisons can be affected by changing traffic mix and schedule reductions.
5. Cancellation-code meanings should be confirmed against the data provider's documentation, especially the large 2020 security-coded category.
6. Missing delay fields are structurally expected for cancelled flights.
7. Small route-level samples can produce unstable rates even after minimum-count filtering.
8. The model's poor-to-moderate performance means it does not yet justify a strong deployment use case.
9. The current implementation does not include calibration curves, bootstrap uncertainty for model metrics, feature-importance interpretation, or a public deployment.
10. The project was validated locally; it has not been publicly deployed or tested across multiple environments.

## 10. Reproduction instructions

From the project root:

```powershell
pip install -r requirements.txt
python src/analysis_pipeline.py
streamlit run dashboard/app.py
```

The PostgreSQL query examples are in:

```text
sql/business_questions.sql
```

The existing notebooks remain available for exploratory context:

```text
notebooks/analysis.ipynb
notebooks/business_problems.ipynb
notebooks/data_exploration.ipynb
notebooks/final_aviation_analysis.ipynb
```

## 11. Final project status

| Phase | Status | Notes |
|---|---|---|
| SQL business analysis | Implemented locally | A1–A7 outputs generated |
| SQL data engineering | Implemented locally | Validation and analytical summaries generated |
| Python/statistical analysis | Implemented locally | Monthly analysis, confidence intervals, significance test, and limitations included |
| Machine learning | Exploratory baseline complete | Chronological evaluation completed; not production-ready |
| Streamlit/publication | Local dashboard complete | Health check passed; public deployment remains |
| Public deployment | Not completed | Requires hosting, environment configuration, and public acceptance testing |

## 12. Files changed or added

- `analysis_pipeline.py`
- `dashboard/app.py`
- `PROJECT_PLAN.txt`
- `requirements.txt`
- `sql/business_questions.sql`
- `PROJECT_COMPLETION_REPORT.md`
- Regenerated and newly created files in `processed_data/`
