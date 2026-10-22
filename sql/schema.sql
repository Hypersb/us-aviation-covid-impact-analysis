CREATE TABLE IF NOT EXISTS aviation_flights (
    fl_date date NOT NULL,
    airline text NOT NULL,
    airline_dot text,
    airline_code text,
    dot_code text,
    fl_number integer,
    origin text NOT NULL,
    origin_city text,
    dest text NOT NULL,
    dest_city text,
    crs_dep_time integer,
    dep_time numeric,
    dep_delay numeric,
    taxi_out numeric,
    wheels_off numeric,
    wheels_on numeric,
    taxi_in numeric,
    crs_arr_time integer,
    arr_time numeric,
    arr_delay numeric,
    cancelled numeric NOT NULL,
    cancellation_code text,
    diverted numeric NOT NULL,
    crs_elapsed_time numeric,
    elapsed_time numeric,
    air_time numeric,
    distance numeric,
    delay_due_carrier numeric,
    delay_due_weather numeric,
    delay_due_nas numeric,
    delay_due_security numeric,
    delay_due_late_aircraft numeric
);

CREATE INDEX IF NOT EXISTS idx_aviation_flights_date
    ON aviation_flights (fl_date);
CREATE INDEX IF NOT EXISTS idx_aviation_flights_route_date
    ON aviation_flights (origin, dest, fl_date);
CREATE INDEX IF NOT EXISTS idx_aviation_flights_cancelled_date
    ON aviation_flights (cancelled, fl_date);
