from __future__ import annotations

import streamlit as st

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.queries import get_last_updated
from phillies_stats.ui import (
    apply_app_theme,
    format_timestamp,
    render_page_header,
    render_section_heading,
)


def render_home(hitter_dashboard_page, pitching_dashboard_page) -> None:
    config = get_config()
    conn = get_connection(config.db_path)
    initialize_database(conn)
    apply_app_theme()

    last_updated = get_last_updated(conn)
    render_page_header(
        "Phillies Analytics, Built with AI",
        "A live Phillies dashboard built from public baseball data, free tools, and a lot of curiosity about what AI can help someone build.",
        eyebrow=f"Portfolio Product | {config.season} Season",
        meta=f"Last updated {format_timestamp(last_updated)}" if last_updated else None,
        show_mark=True,
    )

    if not last_updated:
        st.info("No Statcast data is loaded yet. Run the bootstrap script to backfill the season.")

    render_section_heading(
        "Explore the data",
        "Jump into the live dashboards first, or use the sidebar for leaderboards, profiles, and game-level views.",
    )
    hitter_col, pitcher_col = st.columns(2)

    with hitter_col:
        with st.container(border=True):
            render_section_heading(
                "Hitter Dashboard",
                "Home runs, power leaders, hitter profiles, and key offensive Statcast moments.",
            )
            if st.button("Open Hitter Dashboard", key="home_hitter_dashboard", use_container_width=True):
                st.switch_page(hitter_dashboard_page)

    with pitcher_col:
        with st.container(border=True):
            render_section_heading(
                "Pitching Dashboard",
                "Strikeouts, velocity, wins, innings, and standout Phillies pitching performances.",
            )
            if st.button("Open Pitching Dashboard", key="home_pitching_dashboard", use_container_width=True):
                st.switch_page(pitching_dashboard_page)

    st.caption(
        "More views in the sidebar: Game Log, Longest Home Runs, Power Stats, Hitter Profiles, Strikeout Leaders, Velocity Leaders, Pitcher Profiles."
    )

    about_col, pipeline_col = st.columns([1.1, 1])

    with about_col:
        with st.container(border=True):
            render_section_heading("What this is")
            st.write(
                "This project started as a way to combine a few things I am genuinely interested in: the Phillies, sports stats, building useful products, and AI."
            )
            st.write(
                "I wanted to see how far I could take an idea from scratch to a real, working application without traditional hand-coding. The result is a dashboard for exploring Phillies data in a way that feels more useful and interactive than statistics tables alone."
            )
            st.write(
                "As a Product Owner by trade, this side project became a hands-on way to learn more about software from the engineer's perspective while experimenting with AI as a build partner."
            )

    with pipeline_col:
        with st.container(border=True):
            render_section_heading("Data Pipeline")
            st.write(
                "The app pulls fresh Phillies data from public sources, stores and reshapes it in DuckDB, and serves it through Streamlit as an interactive dashboard."
            )
            st.write(
                "The dataset refreshes automatically every 24 hours through GitHub, so the app stays current without needing manual updates."
            )

    with st.container(border=True):
        render_section_heading("Tools used", "The stack stays intentionally lightweight and portfolio-friendly.")
        tool_left, tool_right = st.columns(2)
        with tool_left:
            st.caption("Data")
            st.write("MLB Stats API")
            st.caption("Database")
            st.write("DuckDB")
        with tool_right:
            st.caption("UI Hosting")
            st.write("Streamlit")
            st.caption("AI Code Editor")
            st.write("OpenAI Codex")
