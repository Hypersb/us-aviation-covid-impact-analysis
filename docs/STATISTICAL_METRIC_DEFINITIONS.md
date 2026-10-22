# Statistical metric definitions

All metrics are observational and use the repository's scheduled flight-record population.

| Metric | Numerator | Denominator | Missing-value rule | Unit |
|---|---|---|---|---|
| Flight volume | Records | None | Records with valid date | Records |
| Cancellation rate | `cancelled = 1` | Records with valid cancellation indicator | Invalid indicators excluded | Percent |
| On-time arrival rate | Operated records with `arr_delay < 15` | Operated records with non-null `arr_delay` | Cancelled and missing delays excluded | Percent |
| Severe-delay rate | Operated records with `arr_delay >= 60` | Same valid-arrival population | Cancelled and missing delays excluded | Percent |
| Diversion rate | `diverted = 1` | Scheduled records with valid diversion indicator | Missing indicators are not treated as positive | Percent |
| Mean/median delay | Valid `arr_delay` values | Valid operated arrivals | Missing values excluded | Minutes |

Year-over-year changes are reported as 2020 minus 2019 percentage points and, where the 2019 rate is nonzero, relative percent change. A percentage point is not a percent change.

Diverted flights remain in the scheduled population. If they have a valid arrival delay, they remain in the valid-arrival population; this is an observed-record estimand, not a claim about passenger experience.
