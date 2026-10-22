-- Capture each query with EXPLAIN (ANALYZE, BUFFERS) before and after
-- running sql/integrate_existing.sql. No result is valid until executed.
\set ON_ERROR_STOP on

EXPLAIN (ANALYZE, BUFFERS)
SELECT fl_date, origin, COUNT(*)
FROM public.flights_2020_new
WHERE fl_date >= DATE '2020-03-01' AND fl_date < DATE '2020-05-01'
GROUP BY fl_date, origin;

EXPLAIN (ANALYZE, BUFFERS)
SELECT origin, dest, COUNT(*)
FROM public.flights_2019_new
WHERE cancelled = 1
GROUP BY origin, dest;

EXPLAIN (ANALYZE, BUFFERS)
SELECT origin, AVG(arr_delay)
FROM public.flights_2020_new
WHERE cancelled = 0 AND arr_delay IS NOT NULL
GROUP BY origin;
