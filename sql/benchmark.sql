-- Run each section separately with EXPLAIN (ANALYZE, BUFFERS).
-- Capture the output before and after the indexes in schema.sql are created.
EXPLAIN (ANALYZE, BUFFERS)
SELECT origin, dest, COUNT(*)
FROM aviation_flights
WHERE fl_date >= DATE '2020-03-01' AND fl_date < DATE '2020-05-01'
GROUP BY origin, dest;

EXPLAIN (ANALYZE, BUFFERS)
SELECT fl_date, COUNT(*)
FROM aviation_flights
WHERE cancelled = 1
GROUP BY fl_date;

EXPLAIN (ANALYZE, BUFFERS)
SELECT origin, dest, AVG(arr_delay)
FROM aviation_flights
WHERE cancelled = 0 AND arr_delay IS NOT NULL
GROUP BY origin, dest;
