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
from phillies_stats.queries import get_game_log


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)

st.title("Game Log")
st.caption("One row per Phillies game, with quick power highlights from that game.")

game_log = get_game_log(conn)
if game_log.empty:
    st.info("The game log will appear after Statcast game data is loaded.")
else:
    st.markdown(
        render_centered_table(
            game_log.rename(
                columns={
                    "game_date": "Date",
                    "opponent": "Opponent",
                    "venue_name": "Ballpark",
                    "result_text": "Result",
                    "hr_count": "HRs",
                    "longest_hr_ft": "Longest HR (ft)",
                    "hardest_hit_ball_mph": "Hardest-hit Ball (mph)",
                }
            )
        ),
        unsafe_allow_html=True,
    )
