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
from phillies_stats.display import render_centered_table
from phillies_stats.queries import get_month_options, get_player_options, get_top_longest_home_runs


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Longest Home Runs")
st.caption("The Top 10 is generated live from stored Statcast events, so nightly updates can move the leaderboard automatically.")

players = get_player_options(conn)
months = get_month_options(conn)

filter_col_1, filter_col_2, filter_col_3 = st.columns(3)
player_filter = filter_col_1.selectbox("Player", options=["All players"] + players)
month_filter = filter_col_2.selectbox("Month", options=["All months"] + months)
home_away_filter = filter_col_3.selectbox("Home / Away", options=["All", "Home", "Away"])

results = get_top_longest_home_runs(
    conn,
    limit=10,
    player=None if player_filter == "All players" else player_filter,
    month=None if month_filter == "All months" else int(month_filter),
    home_away=None if home_away_filter == "All" else home_away_filter,
)

if results.empty:
    st.info("No home runs match the current filters yet.")
else:
    display = results.rename(
        columns={
            "rank": "Rank",
            "player_name": "Player",
            "game_date": "Date",
            "opponent": "Opponent",
            "venue_name": "Ballpark",
            "home_away": "Home/Away",
            "distance_ft": "Distance (ft)",
            "exit_velocity_mph": "Exit Velocity (mph)",
            "launch_angle": "Launch Angle",
        }
    )
    st.markdown(render_centered_table(display), unsafe_allow_html=True)
