-- Non-destructive integration for tables already loaded by the user.
-- This script never imports, truncates, drops, or recreates flight tables.
\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS aviation_analytics;

CREATE OR REPLACE VIEW aviation_analytics.all_flights AS
SELECT 2019::smallint AS year, f.* FROM public.flights_2019_new AS f
UNION ALL
SELECT 2020::smallint AS year, f.* FROM public.flights_2020_new AS f;

CREATE OR REPLACE VIEW aviation_analytics.airport_day AS
SELECT fl_date, year, origin AS airport,
       COUNT(*)::bigint AS scheduled_flights,
       COUNT(*) FILTER (WHERE cancelled = 1)::bigint AS cancelled_flights,
       COUNT(*) FILTER (WHERE diverted = 1)::bigint AS diverted_flights,
       COUNT(arr_delay) FILTER (WHERE cancelled = 0)::bigint AS valid_arrival_flights,
       COUNT(*) FILTER (WHERE cancelled = 0 AND arr_delay IS NULL)::bigint AS missing_arrival_delay,
       AVG((arr_delay < 15)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS on_time_rate,
       AVG((arr_delay >= 60)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS severe_delay_rate,
       AVG(arr_delay) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) AS mean_arrival_delay,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY arr_delay)
         FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) AS median_arrival_delay
FROM aviation_analytics.all_flights
GROUP BY fl_date, year, origin;

CREATE OR REPLACE VIEW aviation_analytics.airport_month AS
SELECT year, EXTRACT(MONTH FROM fl_date)::smallint AS month, origin AS airport,
       COUNT(*)::bigint AS scheduled_flights,
       COUNT(*) FILTER (WHERE cancelled = 1)::bigint AS cancelled_flights,
       COUNT(*) FILTER (WHERE diverted = 1)::bigint AS diverted_flights,
       COUNT(arr_delay) FILTER (WHERE cancelled = 0)::bigint AS valid_arrival_flights,
       AVG((arr_delay < 15)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS on_time_rate,
       AVG((arr_delay >= 60)::int) FILTER (WHERE cancelled = 0 AND arr_delay IS NOT NULL) * 100 AS severe_delay_rate
FROM aviation_analytics.all_flights
GROUP BY year, EXTRACT(MONTH FROM fl_date), origin;

CREATE OR REPLACE VIEW aviation_analytics.cancellation_reason AS
SELECT year,
       CASE cancellation_code
         WHEN 'A' THEN 'Carrier'
         WHEN 'B' THEN 'Weather'
         WHEN 'C' THEN 'NAS'
         WHEN 'D' THEN 'Security'
         ELSE 'Unknown'
       END AS cancellation_reason,
       COUNT(*)::bigint AS cancelled_flights
FROM aviation_analytics.all_flights
WHERE cancelled = 1
GROUP BY year, cancellation_code;

CREATE INDEX IF NOT EXISTS flights_2019_new_date_route_idx
    ON public.flights_2019_new (fl_date, origin, dest);
CREATE INDEX IF NOT EXISTS flights_2020_new_date_route_idx
    ON public.flights_2020_new (fl_date, origin, dest);
CREATE INDEX IF NOT EXISTS flights_2019_new_cancelled_date_idx
    ON public.flights_2019_new (cancelled, fl_date);
CREATE INDEX IF NOT EXISTS flights_2020_new_cancelled_date_idx
    ON public.flights_2020_new (cancelled, fl_date);
