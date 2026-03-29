from __future__ import annotations

import streamlit as st

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.queries import get_last_updated
from phillies_stats.ui import apply_app_theme, format_timestamp, render_page_header, render_section_heading


def render_home(hitter_dashboard_page, pitching_dashboard_page) -> None:
    config = get_config()
    conn = get_connection(config.db_path)
    initialize_database(conn)
    apply_app_theme()

    last_updated = get_last_updated(conn)
    render_page_header(
        f"Phillies Statcast {config.season}",
        "A clean Phillies Statcast hub built around separate hitter and pitcher dashboards, with season-long leaderboards, profiles, and game-level context.",
        eyebrow="Overview",
        meta=f"Last updated {format_timestamp(last_updated)}" if last_updated else None,
    )

    if not last_updated:
        st.info("No Statcast data is loaded yet. Run the bootstrap script to backfill the season.")

    hitter_col, pitcher_col = st.columns(2)

    with hitter_col:
        with st.container(border=True):
            render_section_heading(
                "Hitter Dashboard",
                "Start with home runs, power leaders, and the key offensive Statcast moments from the season.",
            )
            if st.button("Open Hitter Dashboard", key="home_hitter_dashboard", use_container_width=True):
                st.switch_page(hitter_dashboard_page)

    with pitcher_col:
        with st.container(border=True):
            render_section_heading(
                "Pitching Dashboard",
                "Jump into strikeouts, velocity, wins, innings, and the season’s standout Phillies pitching performances.",
            )
            if st.button("Open Pitching Dashboard", key="home_pitching_dashboard", use_container_width=True):
                st.switch_page(pitching_dashboard_page)

    with st.container(border=True):
        render_section_heading(
            "How To Explore",
            "Use the sidebar to move between overview pages, hitter leaderboards, and pitcher profiles without losing the broader season context.",
        )
        st.write(
            "The Home page is intentionally lightweight so the real working dashboards live under their own hitter and pitcher sections."
        )
