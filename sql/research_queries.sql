-- Airport-day reliability panel query.
SELECT fl_date, origin AS airport,
       COUNT(*) AS scheduled_flights,
       COUNT(*) FILTER (WHERE cancelled = 1) AS cancelled_flights,
       COUNT(*) FILTER (WHERE diverted = 1) AS diverted_flights,
       COUNT(arr_delay) FILTER (WHERE cancelled = 0) AS valid_arrival_flights,
       AVG((arr_delay < 15)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS on_time_rate,
       AVG((arr_delay >= 60)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS severe_delay_rate
FROM aviation_flights
GROUP BY fl_date, origin;

-- Same-month airport comparison for observed 2020 disruption.
WITH airport_month AS (
    SELECT EXTRACT(YEAR FROM fl_date)::int AS year,
           EXTRACT(MONTH FROM fl_date)::int AS month,
           origin AS airport,
           COUNT(*) AS scheduled_flights,
           100.0 * COUNT(*) FILTER (WHERE cancelled = 1) / COUNT(*) AS cancellation_rate
    FROM aviation_flights
    GROUP BY 1, 2, 3
)
SELECT current.airport, current.month,
       current.scheduled_flights / NULLIF(baseline.scheduled_flights, 0)::numeric AS activity_ratio,
       current.cancellation_rate - baseline.cancellation_rate AS cancellation_change_pp
FROM airport_month current
JOIN airport_month baseline
  ON baseline.airport = current.airport
 AND baseline.month = current.month
 AND baseline.year = 2019
WHERE current.year = 2020;
