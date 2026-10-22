# Cancellation prediction model card

## Intended use

The existing models are exploratory benchmarks for chronological cancellation prediction. They are not approved for operational cancellation decisions, passenger communications, staffing, or safety-critical use.

## Prediction timing and features

The target is scheduled-flight cancellation. Features are limited to calendar, carrier, origin, destination, scheduled departure/arrival times, and distance. Actual departure/arrival delays and cancellation reasons are excluded.

## Evaluation

The current pipeline trains on 2019 and tests on 2020, with a capped 250,000-row training sample. The stored metrics include a prior dummy baseline, balanced logistic regression, and balanced random forest. This is a single historical shift evaluation, not rolling validation.

## Limitations

- The source files have unresolved provenance and sampling limitations.
- 2020 is an extreme distribution shift, not a representative future operating period.
- No calibration, repeated temporal validation, threshold-cost analysis, or live monitoring is implemented.
- Low precision and modest discrimination limit operational usefulness.
- The offline drift report is descriptive and does not imply model performance drift without repeated model scoring.

## Governance

Do not interpret an ROC-AUC above 0.5 as proof of operational value. Any future deployment would require approved data governance, calibration, decision thresholds, monitoring, retraining policy, and human oversight.
