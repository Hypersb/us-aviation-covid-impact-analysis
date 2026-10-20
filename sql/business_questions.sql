-- PostgreSQL equivalents for the seven business questions.
-- The Python pipeline materializes the same analyses for the local dashboard.

-- A1: route cancellation-rate change, requiring at least 30 flights in each year
WITH route_rates AS (
    SELECT year, origin, dest, COUNT(*) AS total_flights,
           100.0 * SUM(cancelled) / COUNT(*) AS cancellation_rate
    FROM flights
    GROUP BY year, origin, dest
)
SELECT origin, dest,
       MAX(cancellation_rate) FILTER (WHERE year = 2019) AS rate_2019,
       MAX(cancellation_rate) FILTER (WHERE year = 2020) AS rate_2020,
       MAX(cancellation_rate) FILTER (WHERE year = 2020)
         - MAX(cancellation_rate) FILTER (WHERE year = 2019) AS change_percentage_points
FROM route_rates
GROUP BY origin, dest
HAVING MIN(total_flights) >= 30
ORDER BY change_percentage_points DESC;

-- A2: route arrival-delay change on operated flights
SELECT origin, dest,
       AVG(arr_delay) FILTER (WHERE year = 2019 AND cancelled = 0) AS avg_arrival_delay_2019,
       AVG(arr_delay) FILTER (WHERE year = 2020 AND cancelled = 0) AS avg_arrival_delay_2020
FROM flights
GROUP BY origin, dest
HAVING COUNT(*) FILTER (WHERE year = 2019) >= 30
   AND COUNT(*) FILTER (WHERE year = 2020) >= 30
ORDER BY avg_arrival_delay_2020 - avg_arrival_delay_2019 DESC;

-- A3/A4: cancellation reasons by year and month
SELECT year, month, cancellation_code, COUNT(*) AS cancelled_flights
FROM flights
WHERE cancelled = 1
GROUP BY year, month, cancellation_code
ORDER BY year, month, cancelled_flights DESC;

-- A5: on-time (<15 minutes) and severe-delay (>=60 minutes) rates
SELECT year,
       AVG((arr_delay < 15)::int) * 100 AS on_time_rate,
       AVG((arr_delay >= 60)::int) * 100 AS severe_delay_rate
FROM flights
WHERE cancelled = 0
GROUP BY year;
