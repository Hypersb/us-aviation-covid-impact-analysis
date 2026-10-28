# Technical Audit: U.S. Aviation COVID-19 Impact Analysis

**Audit date:** 2026-10-21  
**Scope:** Evidence-first review of the existing repository.  
**Change policy:** No production pipeline, raw dataset, dashboard, or notebook was modified during this audit.

## Evidence-status labels

- **VERIFIED** — directly observed in repository files, raw data, or an authoritative source.
- **REPRODUCED** — independently recalculated from the repository data or code.
- **INFERRED** — a reasoned interpretation that is consistent with the evidence but not directly proven.
- **UNVERIFIED** — not established by the repository evidence or this audit.

## 1. Executive assessment

1. **VERIFIED:** The repository contains two CSV extracts covering every calendar date in 2019 and 2020, with 1,237,023 records in total. The files contain the standard BTS-style on-time, cancellation, diversion, delay-cause, carrier, airport, route, and schedule fields. File provenance, extraction parameters, and sampling design are not recorded.
2. **VERIFIED:** The 2020 Security pattern is present in the raw file, not introduced by the Python label mapping. There are 24,221 code-D cancellations out of 28,757 cancellations (84.23%); code D is absent among 2019 cancellations and is concentrated in March and April 2020.
3. **VERIFIED:** BTS documentation identifies A as Air Carrier, B as Weather, C as National Aviation System, and D as Security. **UNVERIFIED:** the repository does not establish why code D became dominant in this extract or whether it represents a COVID-specific causal category.
4. **REPRODUCED:** The project’s cancellation rates, Wilson intervals, and two-proportion z-test result reproduce from the stored data. The z-test arithmetic is correct, but its iid and sampling assumptions are not defensible as a nationwide causal test without a documented sampling design.
5. **CONFIRMED DEFECT:** The on-time denominator in `analysis_pipeline.py` includes operated records with missing `arr_delay`. Missing arrival delays become `False` through `Series.lt(15)` but remain in `operated_flights`. This understates the reported on-time rate. The effect is small in this extract but the definition is incorrect.
6. **REPRODUCED:** The 2020 operated-flight on-time rate is higher than 2019 under both the existing and corrected denominators, and remains higher after common-route standardization. These are descriptive results, not causal evidence of improved system-wide reliability.
7. **VERIFIED:** The current model is a chronological 2019-to-2020 exploratory benchmark with leakage-prone post-departure fields excluded. It has no calibration analysis, rolling validation, or drift study. The current metrics do not support deployment.
8. **RECOMMENDATION:** First correct and test metric definitions and provenance documentation; then perform a source reconciliation for cancellation codes; only afterward expand the time range or build a research-grade resilience study.

## 2. Verified repository inventory

### Code and configuration

- [analysis_pipeline.py](../src/analysis_pipeline.py) is the executable source of truth.
- [dashboard/app.py](../dashboard/app.py) reads materialized CSV outputs and presents the analysis.
- [requirements.txt](../requirements.txt) lists pandas, NumPy, SciPy, scikit-learn, Streamlit, and Plotly.
- [business_questions.sql](../sql/business_questions.sql) contains PostgreSQL-style equivalents for A1–A5.
- The existing notebooks remain under [notebooks/](../notebooks/).
- [PROJECT_PLAN.txt](PROJECT_PLAN.txt) defines the original research questions and metric intentions.
- [PROJECT_COMPLETION_REPORT.md](PROJECT_COMPLETION_REPORT.md) records the prior implementation claims and limitations.

### Raw data and generated outputs

- `Data/flights_2019.csv`: 156,524,723 bytes; 757,673 rows.
- `Data/flights_2020.csv`: 97,377,677 bytes; 479,350 rows.
- Both raw files have 33 columns, including `fl_date`, carrier and airport identifiers, scheduled and actual times, `arr_delay`, `cancelled`, `cancellation_code`, `diverted`, distance, and delay-cause fields.
- The raw files contain 365 and 366 unique dates respectively, from January 1 through December 31 of each year.
- `processed_data/` contains summary, business-question, statistical, model, and validation outputs.
- [validation_report.json](../processed_data/validation_report.json) reports zero duplicate rows, zero duplicate schedule keys, zero invalid cancellation values, zero invalid cancellation codes, and zero date parse failures.

**UNVERIFIED:** No README, metadata manifest, download query, provider release identifier, checksum, or sampling description was found that establishes whether the CSVs are complete BTS extracts, filtered extracts, or a sample.

## 3. Issue 1 — Cancellation-code anomaly

### 3.1 Transformation audit

**VERIFIED:** [analysis_pipeline.py:24-27](../src/analysis_pipeline.py#L24) defines:

```python
REASON_LABELS = {"A": "Carrier", "B": "Weather", "C": "NAS", "D": "Security"}
```

**VERIFIED:** [analysis_pipeline.py:39-40](../src/analysis_pipeline.py#L39) maps `cancellation_code` to those labels and assigns `"Not cancelled"` only when `cancelled_flag == 0`. There is no code that recodes D, imputes cancellation reasons, or discards D records.

**VERIFIED:** [analysis_pipeline.py:57-60](../src/analysis_pipeline.py#L57) validates unknown non-null cancellation codes, but it does not validate whether the cancellation reason agrees with an external BTS source or with other columns.

### 3.2 Raw counts reproduced

| Year | A Carrier | B Weather | C NAS | D Security | Total cancelled | D share |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | 3,836 | 7,309 | 2,449 | 0 | 13,594 | 0.00% |
| 2020 | 1,924 | 2,142 | 470 | 24,221 | 28,757 | 84.23% |

**REPRODUCED:** These counts come directly from `cancellation_code` among rows where `cancelled == 1`; they agree with [a3_cancellation_reason_changes.csv](../processed_data/a3_cancellation_reason_changes.csv).

**REPRODUCED:** Code D by month in 2020:

- January: 0
- February: 0
- March: 9,921 of 11,181 cancellations (88.73%)
- April: 12,863 of 13,350 cancellations (96.35%)
- May: 1,074 of 1,232 cancellations (87.18%)
- June: 24 of 73 cancellations (32.88%)
- July: 97 of 280 cancellations (34.64%)
- August: 87 of 392 cancellations (22.19%)
- September: 13 of 174 cancellations (7.47%)
- October: 85 of 187 cancellations (45.45%)
- November: 14 of 203 cancellations (6.90%)
- December: 43 of 404 cancellations (10.64%)

**REPRODUCED:** Code D occurs across 16 of 17 carriers in 2020. The largest counts are Southwest 6,948, American 3,152, Delta 2,420, United 2,133, and SkyWest 1,872. This is not a single-airline coding artifact in the observed file.

### 3.3 Official definition and provenance assessment

**VERIFIED:** The BTS technical-directive page identifies the standard cancellation categories as:

- A — Air Carrier
- B — Weather
- C — National Aviation System
- D — Security

Authoritative references:

- BTS, *Number 23 - Technical Directive: On-Time Reporting*: <https://www.bts.gov/topics/airlines-and-airports/number-23-technical-directive-time-reporting-effective-jan-1-2014>
- BTS TranStats cancellation/delay cause page: <https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp>
- 14 CFR Part 234 publication hosted by BTS ROSA-P: <https://rosap.ntl.bts.gov/view/dot/4740/dot_4740_DS1.pdf>

The BTS page was discoverable but returned HTTP 403 to the automated fetch in this environment; the definition was also returned in the authoritative-source search result. The direct page should be manually checked during source reconciliation.

**VERIFIED:** The raw values are valid BTS-style codes and the local mapping is semantically correct.

**UNVERIFIED:** Why D is absent in 2019 and dominates 2020. Plausible hypotheses include:

1. a genuine change in reporting during the pandemic;
2. an extraction or source-version change;
3. a filtered or sampled source whose composition changed sharply;
4. a provider-specific interpretation of D;
5. a data-ingestion/provenance problem.

These are hypotheses, not findings. The cancellation delay-cause columns are null for cancelled flights in both years, so they cannot independently validate the reason code.

**Not performed:** A row-level comparison with official BTS records for matching dates, carriers, and flights. It was not feasible without obtaining the matching BTS extract and without altering the repository.

## 4. Issue 2 — On-time performance and selection effects

### 4.1 Current implementation

**VERIFIED:** [analysis_pipeline.py:111-127](../src/analysis_pipeline.py#L111) filters to `cancelled_flag == 0`, defines `on_time = arr_delay < 15`, and aggregates `on_time_flights` and `operated_flights`.

**CONFIRMED DEFECT:** `operated_flights=("on_time", "size")` counts all operated rows, including rows where `arr_delay` is missing. Since `NaN < 15` is false, those rows reduce the numerator-to-denominator ratio. The code should define a valid-arrival mask and use only valid arrival observations for both the on-time and severe-delay denominators.

### 4.2 Reproduced denominators and corrected rates

| Year | Operated rows | Valid `arr_delay` | Existing rate | Correct valid-arrival rate |
|---|---:|---:|---:|---:|
| 2019 | 744,079 | 742,096 | 80.7499% | 80.9657% |
| 2020 | 450,593 | 449,823 | 90.0484% | 90.2026% |

**REPRODUCED:** The prior report’s approximately 80.3% and 91.7% overall figures do not match the current generated `performance_summary.csv` when weighted by operated rows. The actual current output is approximately 80.75% and 90.05%; the corrected valid-arrival rates are approximately 80.97% and 90.20%.

**REPRODUCED:** At the monthly level, 2020’s corrected on-time rate exceeds 2019’s in every month in this extract. April 2020 is 95.16% on valid arrivals versus 81.90% in April 2019.

### 4.3 Composition and standardization

**REPRODUCED:** There are 5,929 routes with valid operated-flight arrival observations in both years. Using pooled valid-arrival route weights:

- 2019 standardized on-time rate: 81.07%
- 2020 standardized on-time rate: 90.15%

Using equal weights across common routes:

- 2019: 80.83%
- 2020: 88.73%

**INFERRED:** The observed improvement is not explained solely by route composition. It remains descriptive and may reflect schedule cuts, congestion changes, airport mix, carrier mix, flight timing, and selective operation of flights less likely to be delayed.

**VERIFIED:** The repository does not currently provide fixed-weight airline, airport, month, or route standardization outputs. It provides unstandardized summaries only.

### 4.4 Airport-day feasibility

**INFERRED:** Airport-day comparisons are feasible from the available fields (`fl_date`, `origin`, operated status, and `arr_delay`) and should be used as a robustness design, subject to minimum-volume rules. A defensible implementation would compare common airport-days or airport fixed effects, report counts and missingness, and avoid treating sparse airport-days as equally reliable.

**UNVERIFIED:** Whether the extract has a stable sampling fraction by airport-day. This must be checked against official BTS counts before interpreting airport-day rates as population estimates.

## 5. Issue 3 — Statistical methodology

### 5.1 Wilson intervals

**VERIFIED:** [analysis_pipeline.py:185-196](../src/analysis_pipeline.py#L185) implements the standard Wilson interval with `z = norm.ppf(0.975)`.

**REPRODUCED:** The stored results are:

| Year | n | Cancelled | Rate | Wilson 95% interval |
|---|---:|---:|---:|---:|
| 2019 | 757,673 | 13,594 | 1.7942% | 1.765%–1.824% |
| 2020 | 479,350 | 28,757 | 5.9992% | 5.932%–6.067% |

The interval calculation is mathematically correct for a binomial proportion under its assumptions.

### 5.2 Two-proportion z-test

**VERIFIED:** [analysis_pipeline.py:197-204](../src/analysis_pipeline.py#L197) computes a pooled two-proportion z-test.

**REPRODUCED:** The result is:

- Difference: +4.20499 percentage points
- z-score: 125.30394
- two-sided p-value: underflows/displayed as 0.0
- stored significance flag: true

**CONFIRMED LIMITATION:** The p-value is not evidence that COVID caused the difference. The test assumes independent observations and a sampling framework suitable for the target population. Flights are clustered by date, carrier, airport, route, and schedule, and the extraction/sampling design is undocumented.

### 5.3 Recommended effect sizes and uncertainty

**RECOMMENDED:** Report the absolute difference (+4.205 percentage points), risk ratio (approximately 3.34), cancellation counts, and confidence intervals. For dependence-aware uncertainty, use cluster-robust or block bootstrap intervals at an explicitly chosen level (for example date or airport-day), with sensitivity analyses by carrier and route.

**INFERRED:** A Wilson interval is useful as a descriptive binomial interval but should not be presented as a population interval until the source sampling design is verified.

### 5.4 Interrupted time series and difference-in-differences

**INFERRED:** An interrupted time-series design is feasible if daily or weekly observations can be obtained consistently before and after a pre-specified intervention date, with seasonality, trend, exposure volume, and autocorrelation handled explicitly. The current two-year annual comparison is not an interrupted time series.

**UNVERIFIED / NOT CURRENTLY DEFENSIBLE:** A causal difference-in-differences design. The repository has no untreated comparison group, no documented parallel-trends assessment, and no external outcome series. A within-aviation comparison alone does not establish a valid untreated counterfactual.

## 6. Issue 4 — Machine learning

### 6.1 Split and leakage

**VERIFIED:** [analysis_pipeline.py:207-216](../src/analysis_pipeline.py#L207) sorts by date, trains on dates before 2020-01-01, and tests on dates from 2020-01-01 onward. It caps the 2019 training sample at 250,000 rows using a fixed random seed.

**VERIFIED:** The features are schedule/pre-departure fields: calendar fields, airline, origin, destination, scheduled times, and distance. Actual departure/arrival delays and cancellation reason are excluded.

**INFERRED:** Including `year` as a feature is not useful in this split because training year is constant at 2019 and 2020 is unseen at test time; one-hot encoding with `handle_unknown="ignore"` effectively removes its predictive value. It is not a target-leakage defect, but it should be documented or removed for clarity.

### 6.2 Imbalance, metrics, and calibration

**VERIFIED:** The pipeline compares a prior dummy baseline, balanced logistic regression, and balanced random forest. It reports recall, precision, PR-AUC, ROC-AUC, and Brier score in [model_metrics.csv](../processed_data/model_metrics.csv).

**REPRODUCED:** The random forest is the strongest current exploratory model by ROC-AUC (0.6036) and PR-AUC (0.0836), but precision is 0.0862 and the Brier score is 0.2169. The dummy baseline has PR-AUC 0.0600, approximately the test prevalence.

**CONFIRMED LIMITATION:** Class weighting changes the score distribution and can harm probability calibration. No reliability diagram, calibration intercept/slope, expected calibration error, threshold analysis, or post-hoc calibration is implemented. The Brier score is therefore reported without the calibration diagnostics needed to interpret it operationally.

**RECOMMENDATION:** Keep prediction exploratory. Do not expose it as an operational dashboard feature until rolling-origin validation, calibration, threshold/cost analysis, and drift monitoring show stable value.

### 6.3 Distribution shift and validation design

**VERIFIED:** The raw dataset’s observed flight volume falls sharply during March–April 2020, while cancellation prevalence rises sharply. This is a substantial temporal shift in the target environment.

**RECOMMENDED:** Use rolling-origin evaluation (for example train through successive historical windows and test on the next month), report uncertainty across time windows, and separately model/monitor:

- cancellation prevalence;
- airline, airport, route, scheduled-time, and distance distributions;
- missingness rates;
- calibration by month and carrier;
- performance at an operationally selected threshold.

No retraining was performed for this audit.

## 7. Issue 5 — Data expansion feasibility (2018–2023)

### 7.1 Authoritative sources

**VERIFIED:** BTS TranStats identifies the *Airline On-Time Performance Data (1987–present)* as the relevant detailed flight-level source. Official entry points include:

- Download interface: <https://www.transtats.bts.gov/DL_SelectFields.asp?Table_ID=236>
- On-time performance interface: <https://www.transtats.bts.gov/ONTIME/>
- Database information: <https://www.transtats.bts.gov/DatabaseInfo.asp?DB_ID=120&DB_Name=Airline%20On-Time%20Performance%20Data%20(1987-present)>
- BTS ASQP publication page: <https://www.bts.gov/browse-statistical-products-and-data/bts-publications/airline-service-quality-performance-234-time>

The download interface is the appropriate place to select fields and monthly/yearly periods. No expanded data was downloaded during this audit.

### 7.2 Schema and storage

**VERIFIED:** The current files share a 33-column schema with schedule, actual-operation, cancellation, diversion, distance, and delay-cause fields.

**UNVERIFIED:** Schema stability from 2018 through 2023. The expanded acquisition must compare headers, data types, codebooks, carrier identifiers, and null conventions for every period.

**REPRODUCED:** Current raw storage is approximately 253.9 MB for 2019–2020. A six-year estimate based on the current mean is approximately 761.7 MB before backups, indexes, compressed copies, and intermediate outputs.

**INFERRED:** This is only a planning estimate, not a verified 2018–2023 size forecast. The pandemic year is materially smaller than 2019, and BTS download packaging/compression will change the actual requirement.

### 7.3 Handling rules

**VERIFIED:** The current pipeline treats `cancelled == 1` as cancelled and retains cancelled rows in cancellation-rate denominators. It computes delay metrics from pandas means, which naturally exclude missing delay values, but its on-time/severe-delay denominators need correction as described above.

**RECOMMENDED:** Preserve cancelled and diverted flags as separate states. For delay outcomes, define an explicit estimand: operated flights with valid arrival delay; separately report cancellation and diversion rates. Do not convert missing delays to zero. Audit whether diverted flights have valid arrival delay and whether they should be excluded or analyzed separately.

### 7.4 Incremental acquisition plan

1. Download one month per year first, preserving the original BTS export and metadata.
2. Compare headers and code/value distributions against the current 2019–2020 files.
3. Validate row counts, date coverage, carrier/airport coverage, cancellation/diversion counts, and duplicate schedule keys.
4. Reconcile a small set of flights against BTS query results.
5. Add one year at a time with immutable raw partitions and checksums.
6. Run the pipeline only against a versioned staging area; do not overwrite the current data until reconciliation passes.

## 8. Issue 6 — Research differentiation

| Direction | Feasibility | Novelty | Statistical defensibility | Data requirements | Recruiter relevance | Complexity |
|---|---|---|---|---|---|---|
| Airport disruption and recovery resilience | High | Moderate | High if airport-day panels and pre/post periods are defined | BTS flight records plus airport-day panel | High | Moderate |
| Airline/airport network disruption and propagation | Moderate | High | Moderate; requires careful network exposure and dependence handling | BTS records plus route network and possibly schedule/connectivity data | High | High |
| Temporal model degradation and drift monitoring | High technically | Moderate | High for predictive evaluation, not causal explanation | Time-partitioned BTS records and monitoring metrics | High for ML/platform roles | Moderate |

**INFERRED RECOMMENDATION:** Choose **airport-level disruption and recovery resilience** as the primary research direction. It builds directly on the current data, supports transparent airport-day and event-study analyses, has a clear operational audience, and can be made statistically defensible without immediately requiring a large technology stack. Add temporal model drift as a secondary engineering track after the outcome definitions and data provenance are corrected.

**UNVERIFIED:** Claims of academic novelty for any direction. A literature review and comparison with existing COVID aviation studies are required before making a novelty claim.

## 9. Confirmed defects

1. **High — incorrect on-time/severe-delay denominators:** operated rows with missing `arr_delay` remain in `operated_flights`; see [analysis_pipeline.py:115-127](../src/analysis_pipeline.py#L115).
2. **High — undocumented data provenance:** no source URL, extraction parameters, release date, sampling rule, checksum, or reconciliation record is stored for the raw CSVs.
3. **Medium — unsupported causal interpretation risk:** the Security category is displayed as a reason label, but the project lacks source reconciliation and explicitly defined interpretation boundaries for the 2020 code-D shift.
4. **Medium — inference overstatement risk:** the z-test treats records as independent and reports a near-zero p-value without cluster- or design-aware uncertainty.
5. **Medium — model validation gap:** no rolling validation, calibration analysis, temporal drift analysis, or operational threshold evaluation.
6. **Low — report inconsistency:** the completion report’s approximately 91.7% 2020 on-time figure does not match the current generated output or the independently reproduced calculation.

## 10. Unverified assumptions

- The CSVs are representative of the intended U.S. flight population.
- The raw files were extracted from BTS without filtering or transformation.
- Code D has the same operational meaning in this extract as in the current BTS documentation.
- Carrier, airport, and route identifiers are stable and comparable across all proposed expansion years.
- Records are independent enough for the current binomial intervals and z-test.
- The operated-flight on-time comparison represents system-wide reliability rather than survivor-selected operations.
- A future 2018–2023 schema will remain compatible with the current pipeline.

## 11. Recommended corrections ranked by severity

### Priority 1 — before publishing additional findings

1. Correct the valid-arrival denominator for on-time and severe-delay metrics.
2. Add a provenance manifest without changing the raw files: source URLs, query parameters, extraction dates, file hashes, row counts, date coverage, and known transformations.
3. Reconcile a small, independently obtained BTS sample for 2019 and 2020, especially March–April 2020, including cancellation code D.
4. Update the completion report and dashboard labels to use the reproduced rates and clearly distinguish valid-arrival rates from operated-flight counts.

### Priority 2 — before scientific inference

5. Add fixed-weight route, airline, airport, and month standardizations plus airport-day sensitivity analyses.
6. Replace or supplement the iid z-test with design-aware or cluster/block-bootstrap uncertainty.
7. Pre-specify an interrupted-time-series design and do not call it causal unless trend, seasonality, autocorrelation, and intervention timing are justified.

### Priority 3 — before production ML or expansion

8. Add rolling-origin validation, calibration diagnostics, threshold analysis, and drift reporting.
9. Acquire the expanded years incrementally through a versioned staging process.
10. Add diverted-flight handling and schema-change tests before merging later years.

## 12. Proposed next implementation steps

1. Review this audit and decide whether the existing 2019–2020 files are authoritative enough to retain.
2. Implement the metric-definition correction in a separate reviewed change, with regression tests against the reproduced counts above.
3. Build the provenance manifest and source-reconciliation notebook/script.
4. Add standardized airport-day and common-route outputs.
5. Reassess the Security-code interpretation after reconciliation; do not silently recode or drop those observations.
6. Design the airport resilience study with pre-specified outcomes, comparison windows, minimum-volume rules, and uncertainty methods.
7. Only then begin staged 2018–2023 acquisition and optional ML drift monitoring.

## Final audit conclusion

**What is actually wrong:** the on-time and severe-delay denominator implementation is incorrect for missing arrival delays; provenance is undocumented; the current inferential uncertainty is too optimistic for clustered, design-unknown records; and the model lacks calibration and rolling temporal validation.

**What is suspicious but not proven wrong:** the abrupt shift to 84.23% Security-coded cancellations in 2020, especially the March–April concentration. The raw values are genuine and the A/B/C/D mapping is valid, but the cause of the shift and its interpretation are unverified.

**What should be fixed first:** correct the outcome denominators, document and reconcile raw-data provenance, and independently verify the cancellation-code distribution. Do not expand the dataset, redesign the dashboard, or promote the model until those evidence and metric issues are resolved.
