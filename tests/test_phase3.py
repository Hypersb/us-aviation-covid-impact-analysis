import numpy as np
import pandas as pd

from phase3_analysis import (
    benjamini_hochberg,
    bootstrap_difference,
    proportion_result,
    prepare,
)


def test_phase3_denominators_exclude_cancelled_and_missing_arrivals():
    flights = pd.DataFrame([
        {"cancelled_flag": 0, "arr_delay": 5, "diverted": 0},
        {"cancelled_flag": 0, "arr_delay": 60, "diverted": 0},
        {"cancelled_flag": 1, "arr_delay": np.nan, "diverted": 0},
        {"cancelled_flag": 0, "arr_delay": np.nan, "diverted": 1},
    ])
    result = prepare(flights)
    assert int(result["valid_arrival"].sum()) == 2
    assert int(result["on_time"].sum()) == 1
    assert int(result["severe_delay"].sum()) == 1
    assert int(result["diverted_flag"].sum()) == 1


def test_proportion_difference_reports_percentage_points_and_interval():
    result = proportion_result("test", 10, 100, 20, 100)
    assert result["difference_pp"] == 10
    assert result["ci_low_pp"] < 10 < result["ci_high_pp"]


def test_benjamini_hochberg_is_monotone_and_bounded():
    adjusted = benjamini_hochberg(np.array([0.01, 0.04, 0.2]))
    assert np.all(adjusted >= np.array([0.01, 0.04, 0.2]))
    assert np.all(adjusted <= 1)


def test_bootstrap_is_reproducible():
    left = pd.Series([1, 2, 3, 4])
    right = pd.Series([2, 3, 4, 5])
    assert bootstrap_difference(left, right, seed=42, repetitions=100) == bootstrap_difference(
        left, right, seed=42, repetitions=100
    )
