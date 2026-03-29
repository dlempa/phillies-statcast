from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.display import format_metric_value, render_centered_table
from phillies_stats.queries import get_player_options, get_player_summary


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Player Summary")
st.caption("Pick a Phillies hitter to see a simple home run and power snapshot.")

players = get_player_options(conn)
if not players:
    st.info("No player summaries are available yet. Load some Statcast data first.")
else:
    selected_player = st.selectbox("Player", options=players)
    player_summary = get_player_summary(conn, selected_player)
    summary = player_summary["summary"]

    if not summary:
        st.info("No summary is available for this player yet.")
    else:
        hr_count, longest_hr, average_hr, hardest_hit_ball = summary
        card_1, card_2, card_3, card_4 = st.columns(4)
        card_1.metric("HR count", format_metric_value(hr_count))
        card_2.metric("Longest HR", f"{format_metric_value(longest_hr)} ft" if longest_hr is not None else "No data")
        card_3.metric(
            "Average HR distance", f"{format_metric_value(average_hr)} ft" if average_hr is not None else "No data"
        )
        card_4.metric(
            "Hardest-hit ball", f"{format_metric_value(hardest_hit_ball)} mph" if hardest_hit_ball is not None else "No data"
        )

        st.subheader("Monthly HR Breakdown")
        monthly = player_summary["monthly"]
        if monthly.empty:
            st.info("No monthly home run totals are available yet.")
        else:
            chart_data = monthly.rename(columns={"month_name": "Month", "home_run_count": "Home Runs"})[
                ["Month", "Home Runs"]
            ]
            st.bar_chart(chart_data.set_index("Month")["Home Runs"])
            st.markdown(render_centered_table(chart_data), unsafe_allow_html=True)

        st.subheader("All Home Runs")
        home_runs = player_summary["home_runs"]
        if home_runs.empty:
            st.info("No home runs are available for this player yet.")
        else:
            display_home_runs = home_runs.rename(
                columns={
                    "home_run_number": "HR #",
                    "game_date": "Date",
                    "opponent": "Opponent",
                    "venue_name": "Ballpark",
                    "distance_ft": "Distance (ft)",
                    "exit_velocity_mph": "Exit Velocity (mph)",
                    "launch_angle": "Launch Angle",
                }
            )
            st.markdown(render_centered_table(display_home_runs), unsafe_allow_html=True)
