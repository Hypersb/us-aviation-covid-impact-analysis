import pandas as pd

from analysis_pipeline import build_summaries, business_questions, load_flights, validate


def sample_flights() -> pd.DataFrame:
    rows = []
    for year in (2019, 2020):
        for index in range(31):
            rows.append({
                "fl_date": pd.Timestamp(year, 1, 1) + pd.Timedelta(days=index),
                "airline": "Test Air",
                "fl_number": index,
                "origin": "AAA",
                "dest": "BBB",
                "crs_dep_time": 1000,
                "crs_arr_time": 1200,
                "dep_delay": 0,
                "arr_delay": index,
                "cancelled": 0,
                "cancellation_code": pd.NA,
                "distance": 100,
                "year": year,
                "month": 1,
                "day_of_week": 1,
                "cancelled_flag": 0,
                "cancellation_reason": "Not cancelled",
                "route": "AAA-BBB",
            })
    frame = pd.DataFrame(rows)
    frame.loc[0, "arr_delay"] = pd.NA
    return frame


def test_delay_denominator_uses_valid_arrivals():
    summaries = build_summaries(sample_flights())
    january = summaries["performance_summary"].iloc[0]
    assert january["valid_arrival_flights"] == 30
    assert january["on_time_flights"] == 14
    assert january["on_time_rate"] == 14 / 30 * 100


def test_route_delay_question_requires_valid_arrivals():
    flights = sample_flights()
    summaries = build_summaries(flights)
    result = business_questions(flights, summaries)["a2_route_arrival_delay_changes"]
    assert len(result) == 1
    assert result.iloc[0]["valid_arrival_flights_2019"] == 30


def test_validation_rejects_unknown_codes():
    flights = sample_flights()
    flights.loc[0, "cancellation_code"] = "X"
    report = validate(flights)
    assert report["invalid_cancellation_codes"] == ["X"]


def test_load_flights_maps_unknown_cancelled_reason():
    flights = load_flights()
    cancelled = flights[flights["cancelled_flag"].eq(1)]
    assert cancelled["cancellation_reason"].notna().all()
