"""Malaysia Road Accident Dashboard (synthetic data).

Run:
    pip install -r requirements.txt
    streamlit run app.py

Place Synthetic_Road_Accident_2016_2025.csv in the same folder as this file,
or upload any CSV with the same columns from the sidebar.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Road Accident Dashboard",
    page_icon="🚦",
    layout="wide",
)

DEFAULT_FILE = Path("C:\\Users\\USER\\Documents\\BSD SEM 5\\ML\\ASSIGNMENT\\Synthetic_Road_Accident_2016_2025.csv").parent / "Synthetic_Road_Accident_2016_2025.csv"

REQUIRED_COLUMNS = [
    "Year", "State", "Total_of_Accident", "Total_of_Accident_Death",
    "Total_of_Major_Accident", "Total_of_Minor_Accident",
    "Total_of_Damaged_Vehicle", "Total_of_Death", "Total_of_Major_Injured",
    "Total_of_Minor_Injured", "Latitude", "Longitude",
]

# Friendly label -> column name
METRICS = {
    "Total accidents": "Total_of_Accident",
    "Fatal accidents": "Total_of_Accident_Death",
    "Major accidents": "Total_of_Major_Accident",
    "Minor accidents": "Total_of_Minor_Accident",
    "Damage-only accidents": "Total_of_Damaged_Vehicle",
    "Deaths": "Total_of_Death",
    "Major injuries": "Total_of_Major_Injured",
    "Minor injuries": "Total_of_Minor_Injured",
    "Total injuries": "Total_Injured",
}


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def prepare(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"The file is missing these columns: {', '.join(missing)}")
        st.stop()
    df = df.copy()
    df["Year"] = df["Year"].astype(int)
    df["Total_Injured"] = df["Total_of_Major_Injured"] + df["Total_of_Minor_Injured"]
    return df


@st.cache_data
def load_default(path: str) -> pd.DataFrame:
    return prepare(pd.read_csv(path))


def fmt(n: float) -> str:
    return f"{n:,.0f}"


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
st.sidebar.title("🚦 Filters")

uploaded = st.sidebar.file_uploader("Use your own CSV (optional)", type="csv")
if uploaded is not None:
    data = prepare(pd.read_csv(uploaded))
elif DEFAULT_FILE.exists():
    data = load_default(str(DEFAULT_FILE))
else:
    st.error(
        f"Could not find {DEFAULT_FILE.name} next to app.py. "
        "Put the file there or upload a CSV in the sidebar."
    )
    st.stop()

year_min, year_max = int(data["Year"].min()), int(data["Year"].max())
if year_min == year_max:
    years = (year_min, year_max)
else:
    years = st.sidebar.slider("Year range", year_min, year_max, (year_min, year_max))

all_states = sorted(data["State"].unique())
states = st.sidebar.multiselect("States", all_states, default=all_states)

metric_label = st.sidebar.selectbox("Metric to explore", list(METRICS), index=0)
metric = METRICS[metric_label]

df = data[data["Year"].between(*years) & data["State"].isin(states)]

st.sidebar.caption("Synthetic data for demonstration only. Not real statistics.")

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.title("Malaysia Road Accident Dashboard")
st.caption(
    "Each row of the data is one state's annual total for one year. "
    "Figures are synthetic and for demonstration only."
)

if df.empty:
    st.warning("No data for the current filters. Select at least one state.")
    st.stop()

# --------------------------------------------------------------------------
# KPI cards
# --------------------------------------------------------------------------
total_acc = df["Total_of_Accident"].sum()
total_deaths = df["Total_of_Death"].sum()
total_inj = df["Total_Injured"].sum()
rate = total_deaths / total_acc * 1000 if total_acc else 0

latest_year = int(df["Year"].max())
prev_year = latest_year - 1
latest = df[df["Year"] == latest_year]
prev = df[df["Year"] == prev_year]


def delta(col: str):
    if prev.empty:
        return None
    p = prev[col].sum()
    if p == 0:
        return None
    return f"{(latest[col].sum() / p - 1) * 100:+.1f}% vs {prev_year}"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Total accidents", fmt(total_acc), delta("Total_of_Accident"), delta_color="inverse")
c2.metric("Deaths", fmt(total_deaths), delta("Total_of_Death"), delta_color="inverse")
c3.metric("Injuries", fmt(total_inj), delta("Total_Injured"), delta_color="inverse")
c4.metric("Deaths per 1,000 accidents", f"{rate:.1f}")
st.caption(
    f"Totals cover {years[0]}–{years[1]}. "
    f"Change arrows compare {latest_year} with {prev_year}."
)

tab_overview, tab_states, tab_trends, tab_data = st.tabs(
    ["Overview", "States", "Trends", "Data"]
)

# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
with tab_overview:
    left, right = st.columns(2)

    with left:
        yearly = df.groupby("Year", as_index=False)[metric].sum()
        fig = px.line(
            yearly, x="Year", y=metric, markers=True,
            title=f"{metric_label} per year (selected states)",
        )
        fig.update_layout(yaxis_title=metric_label, xaxis=dict(dtick=1))
        st.plotly_chart(fig, width="stretch")

    with right:
        severity = (
            df.groupby("Year")[[
                "Total_of_Accident_Death",
                "Total_of_Major_Accident",
                "Total_of_Minor_Accident",
            ]]
            .sum()
            .rename(columns={
                "Total_of_Accident_Death": "Fatal",
                "Total_of_Major_Accident": "Major",
                "Total_of_Minor_Accident": "Minor",
            })
            .reset_index()
            .melt(id_vars="Year", var_name="Severity", value_name="Accidents")
        )
        fig = px.bar(
            severity, x="Year", y="Accidents", color="Severity",
            title="Accident severity per year (excluding damage-only)",
        )
        fig.update_layout(xaxis=dict(dtick=1))
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Damage-only accidents are left out here because they are over 90% "
            "of all accidents and would hide the other categories."
        )

    st.subheader("Map")
    by_state = (
        df.groupby(["State", "Latitude", "Longitude"], as_index=False)[metric].sum()
    )
    fig = px.scatter_geo(
        by_state, lat="Latitude", lon="Longitude", size=metric, color=metric,
        hover_name="State", hover_data={metric: ":,.0f", "Latitude": False, "Longitude": False},
        color_continuous_scale="OrRd", size_max=45,
        title=f"{metric_label} by state, {years[0]}–{years[1]}",
    )
    fig.update_geos(
        fitbounds="locations", showcountries=True, showland=True,
        landcolor="#f2efe9", countrycolor="#999999", projection_type="mercator",
    )
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------------------
# States
# --------------------------------------------------------------------------
with tab_states:
    left, right = st.columns(2)

    with left:
        ranking = (
            df.groupby("State", as_index=False)[metric].sum()
            .sort_values(metric, ascending=True)
        )
        fig = px.bar(
            ranking, x=metric, y="State", orientation="h",
            title=f"{metric_label} by state, {years[0]}–{years[1]}",
        )
        fig.update_layout(xaxis_title=metric_label, height=520)
        st.plotly_chart(fig, width="stretch")

    with right:
        pivot = df.pivot_table(index="State", columns="Year", values=metric, aggfunc="sum")
        fig = px.imshow(
            pivot, aspect="auto", color_continuous_scale="YlOrRd",
            title=f"{metric_label}: state × year heatmap",
        )
        fig.update_layout(height=520, xaxis=dict(dtick=1))
        st.plotly_chart(fig, width="stretch")

    st.subheader("Fatality rate by state")
    rates = df.groupby("State", as_index=False)[["Total_of_Death", "Total_of_Accident"]].sum()
    rates["Deaths per 1,000 accidents"] = (
        rates["Total_of_Death"] / rates["Total_of_Accident"] * 1000
    )
    rates = rates.sort_values("Deaths per 1,000 accidents", ascending=False)
    fig = px.bar(
        rates, x="State", y="Deaths per 1,000 accidents",
        color="Deaths per 1,000 accidents", color_continuous_scale="Reds",
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Small states with few accidents (e.g. Perlis) can have a high rate "
        "because the total is small."
    )

# --------------------------------------------------------------------------
# Trends
# --------------------------------------------------------------------------
with tab_trends:
    compare = st.multiselect(
        "Compare states", sorted(df["State"].unique()),
        default=sorted(df["State"].unique())[:4],
    )
    if compare:
        sub = df[df["State"].isin(compare)]
        fig = px.line(
            sub, x="Year", y=metric, color="State", markers=True,
            title=f"{metric_label} by state over time",
        )
        fig.update_layout(yaxis_title=metric_label, xaxis=dict(dtick=1))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Pick at least one state to compare.")

    st.subheader("Relationship between measures")
    x_label = st.selectbox("X axis", list(METRICS), index=0, key="x")
    y_label = st.selectbox("Y axis", list(METRICS), index=5, key="y")
    fig = px.scatter(
        df, x=METRICS[x_label], y=METRICS[y_label], color="State",
        hover_data=["Year"], trendline=None,
        labels={METRICS[x_label]: x_label, METRICS[y_label]: y_label},
    )
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
with tab_data:
    st.dataframe(
        df.drop(columns=["Total_Injured"]).sort_values(["Year", "State"]),
        width="stretch", hide_index=True,
    )
    st.download_button(
        "Download filtered data (CSV)",
        df.drop(columns=["Total_Injured"]).to_csv(index=False).encode("utf-8"),
        file_name="filtered_road_accidents.csv",
        mime="text/csv",
    )
    with st.expander("Summary statistics"):
        st.dataframe(df[list(METRICS.values())].describe().round(1))
