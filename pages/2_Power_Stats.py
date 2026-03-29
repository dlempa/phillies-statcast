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
from phillies_stats.queries import (
    get_hardest_hit_balls,
    get_hardest_hit_home_runs,
    get_player_hr_distance_stats,
    get_shortest_home_runs,
)


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Power Stats")
st.caption("A quick look at the loudest contact from Phillies hitters this season.")

hard_hr, short_hr = st.columns(2)

with hard_hr:
    st.subheader("Hardest-hit HRs")
    hardest_home_runs = get_hardest_hit_home_runs(conn)
    if hardest_home_runs.empty:
        st.info("No home run data is available yet.")
    else:
        st.markdown(
            render_centered_table(
                hardest_home_runs.rename(
                    columns={
                        "player_name": "Player",
                        "game_date": "Date",
                        "opponent": "Opponent",
                        "venue_name": "Ballpark",
                        "distance_ft": "Distance (ft)",
                        "exit_velocity_mph": "Exit Velocity (mph)",
                        "launch_angle": "Launch Angle",
                    }
                )
            ),
            unsafe_allow_html=True,
        )

with short_hr:
    st.subheader("Shortest HRs / Wall-scrapers")
    shortest_home_runs = get_shortest_home_runs(conn)
    if shortest_home_runs.empty:
        st.info("No home run data is available yet.")
    else:
        st.markdown(
            render_centered_table(
                shortest_home_runs.rename(
                    columns={
                        "player_name": "Player",
                        "game_date": "Date",
                        "opponent": "Opponent",
                        "venue_name": "Ballpark",
                        "distance_ft": "Distance (ft)",
                        "exit_velocity_mph": "Exit Velocity (mph)",
                        "launch_angle": "Launch Angle",
                    }
                )
            ),
            unsafe_allow_html=True,
        )

st.subheader("Average and Max HR Distance by Player")
distance_stats = get_player_hr_distance_stats(conn)
if distance_stats.empty:
    st.info("Player distance summaries will appear after home run data is loaded.")
else:
    st.markdown(
        render_centered_table(
            distance_stats.rename(
                columns={
                    "player_name": "Player",
                    "home_run_count": "HRs",
                    "avg_hr_distance_ft": "Average HR Distance (ft)",
                    "max_hr_distance_ft": "Max HR Distance (ft)",
                }
            )
        ),
        unsafe_allow_html=True,
    )

st.subheader("Hardest-hit Balls Overall")
hardest_balls = get_hardest_hit_balls(conn)
if hardest_balls.empty:
    st.info("Hard-hit ball data will appear once events are ingested.")
else:
    st.markdown(
        render_centered_table(
            hardest_balls.rename(
                columns={
                    "player_name": "Player",
                    "game_date": "Date",
                    "opponent": "Opponent",
                    "venue_name": "Ballpark",
                    "outcome": "Outcome",
                    "exit_velocity_mph": "Exit Velocity (mph)",
                    "launch_angle": "Launch Angle",
                    "distance_ft": "Distance (ft)",
                }
            )
        ),
        unsafe_allow_html=True,
    )
