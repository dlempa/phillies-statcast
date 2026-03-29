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
from phillies_stats.display import format_display_dataframe, format_metric_value, render_centered_table
from phillies_stats.queries import (
    get_fastest_pitches,
    get_pitcher_home_run_allowed_leaders,
    get_pitcher_strikeout_leaders,
    get_pitcher_walks_leaders,
    get_pitcher_wins_leaders,
    get_pitching_dashboard_metrics,
    get_team_pitcher_velocity_trend,
)


def format_metric(result, unit: str, fallback: str = "No data yet") -> tuple[str, str]:
    if not result:
        return fallback, ""
    player_name, value = result
    if value is None:
        return fallback, ""
    return f"{format_metric_value(value)} {unit}", str(player_name)


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Pitching Dashboard")
st.caption("A quick view of Phillies pitcher leaders, velocity, and run prevention stats.")

metrics = get_pitching_dashboard_metrics(conn)

card_1, card_2, card_3, card_4 = st.columns(4)
value, player = format_metric(metrics["strikeout_leader"], "K")
card_1.metric("Strikeout leader", value, player)
value, player = format_metric(metrics["fastest_pitch"], "mph")
card_2.metric("Fastest pitch of season", value, player)
value, player = format_metric(metrics["wins_leader"], "W")
card_3.metric("Wins leader", value, player)
value, player = format_metric(metrics["innings_leader"], "IP")
card_4.metric("Innings pitched leader", value, player)

leaders_col_1, leaders_col_2 = st.columns(2)

with leaders_col_1:
    st.subheader("Strikeout Leaders")
    strikeout_leaders = get_pitcher_strikeout_leaders(conn, limit=5)
    if strikeout_leaders.empty:
        st.info("Pitcher strikeout data is not available yet.")
    else:
        st.markdown(render_centered_table(strikeout_leaders.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

    st.subheader("Wins Leaders")
    wins_leaders = get_pitcher_wins_leaders(conn, limit=5)
    if wins_leaders.empty:
        st.info("Pitcher season summary data is not available yet.")
    else:
        st.markdown(render_centered_table(wins_leaders.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

with leaders_col_2:
    st.subheader("Fastest Pitches")
    fastest_pitches = get_fastest_pitches(conn, limit=5)
    if fastest_pitches.empty:
        st.info("Velocity data is not available yet.")
    else:
        st.markdown(render_centered_table(fastest_pitches.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

    st.subheader("Most Walks Issued")
    walks_leaders = get_pitcher_walks_leaders(conn, limit=5)
    if walks_leaders.empty:
        st.info("Walk data is not available yet.")
    else:
        st.markdown(render_centered_table(walks_leaders.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

st.subheader("Most Home Runs Allowed")
home_run_allowed = get_pitcher_home_run_allowed_leaders(conn, limit=5)
if home_run_allowed.empty:
    st.info("Home run allowed data is not available yet.")
else:
    st.markdown(render_centered_table(home_run_allowed.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

st.subheader("Velocity Trend")
velocity_trend = get_team_pitcher_velocity_trend(conn)
if velocity_trend.empty:
    st.info("Velocity trend data will appear once Phillies pitching events are loaded.")
else:
    chart_data = format_display_dataframe(velocity_trend.rename(columns={"player_name": "Pitcher", "max_velocity_mph": "Max Velocity (mph)"}))
    chart_data["game_date"] = velocity_trend["game_date"]
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("game_date:T", title="Date"),
            y=alt.Y("Max Velocity (mph):Q", title="Max Velocity (mph)"),
            color=alt.Color("Pitcher:N", title="Pitcher"),
            tooltip=["Pitcher", "Max Velocity (mph)", "game_date:T"],
        )
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)
