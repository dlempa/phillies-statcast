from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from phillies_stats.dashboard_page import render_hitter_dashboard
from phillies_stats.home_page import render_home


st.set_page_config(
    page_title="Phillies Statcast 2026",
    page_icon=":baseball:",
    layout="wide",
    initial_sidebar_state="expanded",
)

hitter_dashboard_page = st.Page(
    render_hitter_dashboard,
    title="Hitter Dashboard",
    icon=":material/dashboard:",
)
pitching_dashboard_page = st.Page(
    PROJECT_ROOT / "pages" / "5_Pitching_Dashboard.py",
    title="Pitching Dashboard",
    icon=":material/sports_baseball:",
)
home_page = st.Page(
    lambda: render_home(hitter_dashboard_page, pitching_dashboard_page),
    title="Home",
    icon=":material/home:",
    default=True,
)

navigation = st.navigation(
    {
        "Overview": [
            home_page,
            st.Page(
                PROJECT_ROOT / "pages" / "4_Game_Log.py",
                title="Game Log",
                icon=":material/calendar_month:",
            ),
        ],
        "Hitter Stats": [
            hitter_dashboard_page,
            st.Page(PROJECT_ROOT / "pages" / "1_Longest_Home_Runs.py", title="Longest Home Runs", icon=":material/emoji_events:"),
            st.Page(PROJECT_ROOT / "pages" / "2_Power_Stats.py", title="Power Stats", icon=":material/bolt:"),
            st.Page(PROJECT_ROOT / "pages" / "3_Player_Summary.py", title="Hitter Profiles", icon=":material/person:"),
        ],
        "Pitcher Stats": [
            pitching_dashboard_page,
            st.Page(PROJECT_ROOT / "pages" / "6_Strikeout_Leaders.py", title="Strikeout Leaders", icon=":material/leaderboard:"),
            st.Page(PROJECT_ROOT / "pages" / "7_Velocity_Leaders.py", title="Velocity Leaders", icon=":material/speed:"),
            st.Page(PROJECT_ROOT / "pages" / "8_Pitcher_Profiles.py", title="Pitcher Profiles", icon=":material/badge:"),
        ],
    },
    position="sidebar",
    expanded=True,
)

navigation.run()
