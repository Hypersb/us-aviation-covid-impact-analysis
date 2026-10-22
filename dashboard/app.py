from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="U.S. Aviation Disruption Intelligence", page_icon="✈️", layout="wide")
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "processed_data"


@st.cache_data
def load_outputs() -> dict[str, pd.DataFrame | dict]:
    names = [
        "monthly_summary", "airline_summary", "airport_summary", "route_summary",
        "performance_summary", "a1_route_cancellation_changes", "a2_route_arrival_delay_changes",
        "a3_cancellation_reason_changes", "a4_monthly_cancellation_reasons",
        "a5_on_time_severe_delay", "a6_airline_reliability_changes",
        "a7_march_april_airports", "a7_march_april_routes",
        "cancellation_confidence_intervals", "cancellation_significance_test", "model_metrics",
        "airport_resilience_monthly", "offline_drift_report",
    ]
    outputs = {name: pd.read_csv(DATA_DIR / f"{name}.csv") for name in names}
    outputs["validation"] = json.loads((DATA_DIR / "validation_report.json").read_text(encoding="utf-8"))
    return outputs


try:
    data = load_outputs()
except FileNotFoundError:
    st.error("Dashboard outputs are missing. Run `python analysis_pipeline.py` from the project root.")
    st.stop()

monthly = data["monthly_summary"]
st.title("U.S. Aviation Disruption Intelligence")
st.caption("Sampled U.S. flight records: 2019 baseline compared with 2020 disruption period.")

year = st.selectbox("Focus year", [2019, 2020], index=1)
yearly = monthly[monthly["year"].eq(year)]
total = int(yearly["total_flights"].sum())
cancelled = int(yearly["cancelled_flights"].sum())
rate = cancelled / total * 100 if total else 0
operated = data["performance_summary"]
overall_on_time = operated[operated["year"].eq(year)]["on_time_flights"].sum() / operated[operated["year"].eq(year)]["valid_arrival_flights"].sum() * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Sampled flights", f"{total:,}")
col2.metric("Cancelled flights", f"{cancelled:,}")
col3.metric("Cancellation rate", f"{rate:.2f}%")
col4.metric("On-time rate", f"{overall_on_time:.2f}%")

tab_overview, tab_entities, tab_business, tab_research, tab_stats, tab_quality = st.tabs(
    ["Overview", "Airlines and airports", "Business questions", "Airport resilience", "Statistics and model", "Data quality"]
)

with tab_overview:
    st.subheader("Monthly activity and cancellation rate")
    fig = px.line(monthly, x="month", y="cancellation_rate", color="year", markers=True,
                  labels={"cancellation_rate": "Cancellation rate (%)", "month": "Month"})
    st.plotly_chart(fig, use_container_width=True)
    performance = data["performance_summary"]
    fig2 = px.line(performance, x="month", y=["on_time_rate", "severe_delay_rate"], color="year",
                   labels={"value": "Rate (%)", "variable": "Measure"})
    st.plotly_chart(fig2, use_container_width=True)

with tab_entities:
    airline = data["airline_summary"]
    airline = airline[(airline["year"].eq(year)) & airline["total_flights"].ge(100)].nlargest(15, "cancellation_rate")
    st.subheader(f"Airlines with highest cancellation rates ({year})")
    st.plotly_chart(px.bar(airline, x="cancellation_rate", y="airline", orientation="h",
                           labels={"cancellation_rate": "Cancellation rate (%)"}), use_container_width=True)
    airport = data["airport_summary"]
    airport = airport[(airport["year"].eq(year)) & airport["total_flights"].ge(100)].nlargest(15, "cancellation_rate")
    st.subheader(f"Departure airports with highest cancellation rates ({year})")
    st.plotly_chart(px.bar(airport, x="cancellation_rate", y="airport", orientation="h",
                           labels={"cancellation_rate": "Cancellation rate (%)"}), use_container_width=True)

with tab_business:
    st.subheader("Cancellation reasons")
    st.dataframe(data["a3_cancellation_reason_changes"], use_container_width=True, hide_index=True)
    st.subheader("Routes with largest cancellation-rate increases")
    st.dataframe(data["a1_route_cancellation_changes"].head(20), use_container_width=True, hide_index=True)
    st.subheader("Routes with largest arrival-delay increases")
    st.dataframe(data["a2_route_arrival_delay_changes"].head(20), use_container_width=True, hide_index=True)
    st.subheader("March-April 2020 disruption: airports")
    st.dataframe(data["a7_march_april_airports"].query("year == 2020").nlargest(20, "cancelled_flights"),
                 use_container_width=True, hide_index=True)

with tab_research:
    st.subheader("Observed airport disruption and resilience")
    st.caption("Same-month 2020 versus 2019 observed records. This is not a full post-pandemic recovery estimate.")
    resilience = data["airport_resilience_monthly"]
    st.dataframe(
        resilience[resilience["month"].isin([3, 4])].sort_values(
            "cancellation_rate_change_pp", ascending=False
        ).head(25),
        use_container_width=True,
        hide_index=True,
    )
    st.subheader("Offline distribution-shift diagnostics")
    st.dataframe(data["offline_drift_report"], use_container_width=True, hide_index=True)

with tab_stats:
    st.subheader("Inference")
    st.dataframe(data["cancellation_confidence_intervals"], use_container_width=True, hide_index=True)
    st.dataframe(data["cancellation_significance_test"], use_container_width=True, hide_index=True)
    st.caption("Intervals describe this sampled dataset. Delay rates use operated flights with a valid arrival-delay observation. The z-test treats records as independent observations; sampling design limits nationwide inference.")
    st.subheader("Chronological cancellation prediction")
    st.dataframe(data["model_metrics"], use_container_width=True, hide_index=True)
    st.caption("Models train on 2019 and test on 2020. PR-AUC and calibration-sensitive Brier score are more informative than accuracy for this imbalanced target.")

with tab_quality:
    report = data["validation"]
    st.json(report)
    st.info("Missing delay fields are expected for cancelled flights. No duplicate rows, duplicate schedule keys, invalid cancellation values, or invalid cancellation codes were found.")

st.divider()
st.caption("This dashboard reports sampled records, not nationwide flight totals. Run analysis_pipeline.py to regenerate every table.")
