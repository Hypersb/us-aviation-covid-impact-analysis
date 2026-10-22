\set ON_ERROR_STOP on
\pset footer on

SELECT 'flights_2019_new' AS table_name, COUNT(*) AS row_count,
       MIN(fl_date) AS min_date, MAX(fl_date) AS max_date
FROM public.flights_2019_new
UNION ALL
SELECT 'flights_2020_new', COUNT(*), MIN(fl_date), MAX(fl_date)
FROM public.flights_2020_new;

SELECT table_name, ordinal_position, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('flights_2019_new', 'flights_2020_new')
ORDER BY table_name, ordinal_position;

SELECT '2019' AS year, cancellation_code, COUNT(*) AS cancelled_flights
FROM public.flights_2019_new
WHERE cancelled = 1
GROUP BY cancellation_code
UNION ALL
SELECT '2020', cancellation_code, COUNT(*)
FROM public.flights_2020_new
WHERE cancelled = 1
GROUP BY cancellation_code
ORDER BY year, cancellation_code;

SELECT '2019' AS year,
       COUNT(*) FILTER (WHERE arr_delay IS NULL) AS missing_arr_delay,
       COUNT(*) FILTER (WHERE dep_delay IS NULL) AS missing_dep_delay
FROM public.flights_2019_new
UNION ALL
SELECT '2020',
       COUNT(*) FILTER (WHERE arr_delay IS NULL),
       COUNT(*) FILTER (WHERE dep_delay IS NULL)
FROM public.flights_2020_new;
