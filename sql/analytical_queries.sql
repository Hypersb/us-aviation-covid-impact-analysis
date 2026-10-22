-- Gold analytical queries. All delay denominators require valid arr_delay.
WITH route_stats AS (
    SELECT EXTRACT(YEAR FROM fl_date)::int AS year, origin, dest,
           COUNT(*) AS total_flights,
           COUNT(*) FILTER (WHERE cancelled = 1) AS cancelled_flights,
           COUNT(arr_delay) FILTER (WHERE cancelled = 0) AS valid_arrival_flights,
           AVG(arr_delay) FILTER (WHERE cancelled = 0) AS avg_arrival_delay,
           100.0 * COUNT(*) FILTER (WHERE cancelled = 1) / COUNT(*) AS cancellation_rate
    FROM aviation_flights
    GROUP BY 1, origin, dest
)
SELECT origin, dest,
       MAX(cancellation_rate) FILTER (WHERE year = 2019) AS rate_2019,
       MAX(cancellation_rate) FILTER (WHERE year = 2020) AS rate_2020,
       MAX(cancellation_rate) FILTER (WHERE year = 2020)
         - MAX(cancellation_rate) FILTER (WHERE year = 2019) AS change_percentage_points
FROM route_stats
GROUP BY origin, dest
HAVING MIN(total_flights) >= 30
ORDER BY change_percentage_points DESC;

SELECT EXTRACT(YEAR FROM fl_date)::int AS year,
       AVG((arr_delay < 15)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS on_time_rate,
       AVG((arr_delay >= 60)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS severe_delay_rate
FROM aviation_flights
GROUP BY 1
ORDER BY 1;

SELECT EXTRACT(YEAR FROM fl_date)::int AS year,
       COALESCE(CASE cancellation_code
           WHEN 'A' THEN 'Carrier'
           WHEN 'B' THEN 'Weather'
           WHEN 'C' THEN 'NAS'
           WHEN 'D' THEN 'Security'
           ELSE 'Unknown'
       END, 'Unknown') AS cancellation_reason,
       COUNT(*) AS cancelled_flights
FROM aviation_flights
WHERE cancelled = 1
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
