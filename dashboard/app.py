from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="US Aviation COVID-19 Impact",
    page_icon="✈️",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "processed_data"


@st.cache_data
def load_data():
    monthly = pd.read_csv(DATA_DIR / "monthly_summary.csv")
    airlines = pd.read_csv(DATA_DIR / "airline_summary.csv")
    airports = pd.read_csv(DATA_DIR / "airport_summary.csv")

    return monthly, airlines, airports


monthly_df, airline_df, airport_df = load_data()


# Dashboard heading
st.title("U.S. Aviation COVID-19 Impact Dashboard")

st.markdown(
    "An analysis of sampled U.S. flight cancellations, "
    "airline performance, and operational delays during 2019–2020."
)

st.divider()

selected_year = st.selectbox(
    "Select Year",
    options=[2019, 2020],
    index=1
)

filtered_df = monthly_df[
    monthly_df["year"] == selected_year
]


# KPI calculations
total_flights = filtered_df["total_flights"].sum()
cancelled_flights = filtered_df["cancelled_flights"].sum()

cancellation_rate = (
    cancelled_flights / total_flights * 100
    if total_flights > 0 else 0
)


col1, col2, col3 = st.columns(3)

col1.metric(
    "Sampled Flights",
    f"{total_flights:,}"
)

col2.metric(
    "Cancelled Flights",
    f"{cancelled_flights:,}"
)

col3.metric(
    "Cancellation Rate",
    f"{cancellation_rate:.2f}%"
)


st.subheader("Monthly Flight Cancellation Rates")

fig = px.line(
    monthly_df,
    x="month",
    y="cancellation_rate",
    color="year",
    markers=True,
    title="Monthly Cancellation Rates: 2019 vs 2020",
    labels={
        "month": "Month",
        "cancellation_rate": "Cancellation Rate (%)",
        "year": "Year"
    }
)

fig.update_layout(
    xaxis=dict(dtick=1),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader(f"Airline Cancellation Rates — {selected_year}")

filtered_airlines = airline_df[
    (airline_df["year"] == selected_year)
    & (airline_df["total_flights"] >= 100)
].sort_values(
    "cancellation_rate",
    ascending=False
).head(10)

airline_fig = px.bar(
    filtered_airlines,
    x="cancellation_rate",
    y="airline",
    orientation="h",
    title="Top 10 Airlines by Cancellation Rate",
    labels={
        "cancellation_rate": "Cancellation Rate (%)",
        "airline": "Airline"
    }
)

airline_fig.update_layout(
    yaxis={"categoryorder": "total ascending"}
)

st.plotly_chart(airline_fig, use_container_width=True)

st.subheader(f"Airport Cancellation Rates — {selected_year}")

filtered_airports = airport_df[
    (airport_df["year"] == selected_year)
    & (airport_df["total_flights"] >= 100)
].sort_values(
    "cancellation_rate",
    ascending=False
).head(10)

airport_fig = px.bar(
    filtered_airports,
    x="cancellation_rate",
    y="airport",
    orientation="h",
    title="Top 10 Departure Airports by Cancellation Rate",
    labels={
        "cancellation_rate": "Cancellation Rate (%)",
        "airport": "Departure Airport"
    }
)

airport_fig.update_layout(
    yaxis={"categoryorder": "total ascending"}
)

st.plotly_chart(airport_fig, use_container_width=True)


st.divider()

st.caption(
    "Data represents sampled U.S. flight records for 2019 and 2020. "
    "Differences in sample counts should not be interpreted as "
    "exact nationwide changes in flight volume."
)