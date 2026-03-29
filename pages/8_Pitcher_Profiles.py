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
from phillies_stats.display import format_metric_value, render_centered_table
from phillies_stats.queries import get_pitcher_options, get_pitcher_profile


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Pitcher Profiles")
st.caption("Pick a Phillies pitcher to see season totals, velocity, pitch mix, and strikeout splits.")

pitchers = get_pitcher_options(conn)
if not pitchers:
    st.info("No Phillies pitcher profiles are available yet.")
else:
    selected_pitcher = st.selectbox("Pitcher", options=pitchers)
    profile = get_pitcher_profile(conn, selected_pitcher)
    summary = profile["summary"]

    if not summary:
        st.info("No profile data is available for this pitcher yet.")
    else:
        (
            wins,
            losses,
            innings_pitched,
            strikeouts,
            walks_issued,
            home_runs_allowed,
            era,
            whip,
            max_velocity,
            avg_fastball_velocity,
            whiffs,
            hardest_hit_allowed,
            appearances,
            games_started,
            saves,
            position,
        ) = summary

        row_1 = st.columns(5)
        row_1[0].metric("Wins", format_metric_value(wins))
        row_1[1].metric("Losses", format_metric_value(losses))
        row_1[2].metric("Innings Pitched", format_metric_value(innings_pitched))
        row_1[3].metric("Strikeouts", format_metric_value(strikeouts))
        row_1[4].metric("Walks", format_metric_value(walks_issued))

        row_2 = st.columns(5)
        row_2[0].metric("HR Allowed", format_metric_value(home_runs_allowed))
        row_2[1].metric("ERA", format_metric_value(era))
        row_2[2].metric("WHIP", format_metric_value(whip))
        row_2[3].metric("Games Started", format_metric_value(games_started))
        row_2[4].metric(
            "Avg Fastball Velo",
            f"{format_metric_value(avg_fastball_velocity)} mph" if avg_fastball_velocity is not None else "No data",
        )

        row_3 = st.columns(4)
        row_3[0].metric("Position", str(position) if position is not None else "No data")
        row_3[1].metric(
            "Max Velocity",
            f"{format_metric_value(max_velocity)} mph" if max_velocity is not None else "No data",
        )
        row_3[2].metric("Whiffs", format_metric_value(whiffs))
        row_3[3].metric("Saves", format_metric_value(saves))

        row_4 = st.columns(2)
        row_4[0].metric("Appearances", format_metric_value(appearances))
        row_4[1].metric(
            "Hardest-hit Allowed",
            f"{format_metric_value(hardest_hit_allowed)} mph" if hardest_hit_allowed is not None else "No data",
        )

        st.subheader("Pitch Usage Mix")
        pitch_usage = profile["pitch_usage"]
        if pitch_usage.empty:
            st.info("Pitch usage data is not available for this pitcher yet.")
        else:
            st.markdown(render_centered_table(pitch_usage), unsafe_allow_html=True)
            usage_chart = alt.Chart(pitch_usage).mark_bar().encode(
                x=alt.X("pitch_name:N", title="Pitch Type", sort="-y"),
                y=alt.Y("usage_pct:Q", title="Usage %"),
                tooltip=["pitch_name", "pitch_count", "usage_pct"],
            )
            st.altair_chart(usage_chart, use_container_width=True)

        st.subheader("Strikeouts By Month")
        strikeouts_by_month = profile["strikeouts_by_month"]
        if strikeouts_by_month.empty:
            st.info("No monthly strikeout data is available for this pitcher yet.")
        else:
            month_chart = alt.Chart(strikeouts_by_month).mark_bar().encode(
                x=alt.X("month_start:T", title="Month"),
                y=alt.Y("strikeouts:Q", title="Strikeouts"),
                tooltip=["month_start:T", "strikeouts"],
            )
            st.altair_chart(month_chart, use_container_width=True)

        st.subheader("Strikeouts By Opponent")
        strikeouts_by_opponent = profile["strikeouts_by_opponent"]
        if strikeouts_by_opponent.empty:
            st.info("No opponent strikeout data is available for this pitcher yet.")
        else:
            st.markdown(render_centered_table(strikeouts_by_opponent), unsafe_allow_html=True)

        st.subheader("Fastest Pitches")
        fastest_pitches = profile["fastest_pitches"]
        if fastest_pitches.empty:
            st.info("No pitch-level velocity data is available for this pitcher yet.")
        else:
            st.markdown(render_centered_table(fastest_pitches), unsafe_allow_html=True)
