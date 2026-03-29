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
from phillies_stats.queries import (
    get_pitcher_options,
    get_pitcher_strikeout_leaders,
    get_pitcher_strikeouts_by_month,
    get_pitcher_strikeouts_by_opponent,
)


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Strikeout Leaders")
st.caption("Phillies pitchers ranked by strikeouts, with simple supporting breakdowns.")

leaders = get_pitcher_strikeout_leaders(conn, limit=20)
if leaders.empty:
    st.info("No Phillies pitcher strikeout data is available yet.")
else:
    st.markdown(render_centered_table(leaders.rename(columns={"player_name": "Pitcher"})), unsafe_allow_html=True)

pitchers = get_pitcher_options(conn)
if pitchers:
    selected_pitcher = st.selectbox("Pitcher", options=pitchers)

    st.subheader("Strikeouts By Month")
    by_month = get_pitcher_strikeouts_by_month(conn, selected_pitcher)
    if by_month.empty:
        st.info("No monthly strikeout breakdown is available for this pitcher yet.")
    else:
        month_chart = format_display_dataframe(
            by_month.rename(columns={"player_name": "Pitcher", "month_start": "Month", "strikeouts": "Strikeouts"})
        )
        month_chart["month_start"] = by_month["month_start"]
        chart = alt.Chart(month_chart).mark_bar().encode(
            x=alt.X("month_start:T", title="Month"),
            y=alt.Y("Strikeouts:Q", title="Strikeouts"),
            tooltip=["Pitcher", "Strikeouts", "Month"],
        )
        st.altair_chart(chart, use_container_width=True)
        st.markdown(render_centered_table(month_chart[["Month", "Pitcher", "Strikeouts"]]), unsafe_allow_html=True)

    st.subheader("Strikeouts By Opponent")
    by_opponent = get_pitcher_strikeouts_by_opponent(conn, selected_pitcher)
    if by_opponent.empty:
        st.info("No opponent strikeout breakdown is available for this pitcher yet.")
    else:
        st.markdown(render_centered_table(by_opponent), unsafe_allow_html=True)
