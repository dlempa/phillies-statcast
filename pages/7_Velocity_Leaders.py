from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.display import format_display_dataframe, render_centered_table
from phillies_stats.queries import get_fastest_pitches, get_pitcher_velocity_summary


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Velocity Leaders")
st.caption("The loudest Phillies velocity marks from the season so far.")

st.subheader("Top 10 Fastest Pitches")
fastest_pitches = get_fastest_pitches(conn, limit=10)
if fastest_pitches.empty:
    st.info("No Phillies pitch velocity data is available yet.")
else:
    st.markdown(render_centered_table(fastest_pitches.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

st.subheader("Max Velocity and Average Fastball Velocity By Pitcher")
velocity_summary = get_pitcher_velocity_summary(conn, limit=20)
if velocity_summary.empty:
    st.info("Pitcher velocity summaries are not available yet.")
else:
    display = velocity_summary.rename(
        columns={
            "player_name": "Pitcher",
            "max_velocity_mph": "Max Velocity (mph)",
            "avg_fastball_velocity_mph": "Average Fastball Velocity (mph)",
        }
    )
    st.markdown(render_centered_table(display), unsafe_allow_html=True)

    chart_data = format_display_dataframe(display.copy())
    velocity_chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Pitcher:N", sort="-y"),
        y=alt.Y("Max Velocity (mph):Q", title="Max Velocity (mph)"),
        tooltip=["Pitcher", "Max Velocity (mph)", "Average Fastball Velocity (mph)"],
    )
    st.altair_chart(velocity_chart, use_container_width=True)
