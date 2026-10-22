import pandas as pd

from research_pipeline import build_panels


def test_research_panel_denominators():
    flights = pd.DataFrame([
        {"fl_date": pd.Timestamp("2019-01-01"), "year": 2019, "month": 1, "origin": "AAA",
         "cancelled_flag": 0, "arr_delay": 5, "diverted": 0},
        {"fl_date": pd.Timestamp("2019-01-01"), "year": 2019, "month": 1, "origin": "AAA",
         "cancelled_flag": 1, "arr_delay": None, "diverted": 0},
    ])
    day, _ = build_panels(flights)
    row = day.iloc[0]
    assert row["scheduled_flights"] == 2
    assert row["cancelled_flights"] == 1
    assert row["valid_arrival_flights"] == 1
    assert row["on_time_rate"] == 100
    assert row["missing_arrival_delay"] == 1
