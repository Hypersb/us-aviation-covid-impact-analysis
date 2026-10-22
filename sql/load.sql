-- Run from psql after creating the schema.
-- Set :data_dir to the directory containing the immutable raw CSV files.
\set ON_ERROR_STOP on
\if :{?data_dir}
\else
\echo 'Set data_dir, for example: psql -v data_dir=''C:/repo/Data'' -f sql/load.sql'
\quit 2
\endif

\set file2019 :data_dir '/flights_2019.csv'
\set file2020 :data_dir '/flights_2020.csv'
TRUNCATE aviation_flights;
\copy aviation_flights FROM :'file2019' WITH (FORMAT csv, HEADER true, NULL '');
\copy aviation_flights FROM :'file2020' WITH (FORMAT csv, HEADER true, NULL '');
ANALYZE aviation_flights;
