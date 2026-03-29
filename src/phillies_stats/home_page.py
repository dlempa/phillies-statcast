from __future__ import annotations

import streamlit as st

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.queries import get_last_updated


def render_home(hitter_dashboard_page, pitching_dashboard_page) -> None:
    config = get_config()
    conn = get_connection(config.db_path)
    initialize_database(conn)

    st.title(f"Phillies Statcast {config.season}")
    st.caption("A season-long Phillies Statcast app organized around separate hitter and pitcher dashboards.")

    last_updated = get_last_updated(conn)
    if last_updated:
        st.write(f"Last updated: {last_updated}")
    else:
        st.info("No Statcast data is loaded yet. Run the bootstrap script to backfill the season.")

    hitter_col, pitcher_col = st.columns(2)

    with hitter_col:
        st.subheader("Hitter Stats")
        st.write("Start with the Hitter Dashboard for home runs, power leaders, and quick season context.")
        st.page_link(
            hitter_dashboard_page,
            label="Go to Hitter Dashboard",
            icon=":material/bolt:",
            use_container_width=True,
        )

    with pitcher_col:
        st.subheader("Pitcher Stats")
        st.write("Start with the Pitching Dashboard for strikeouts, velocity, wins, and bullpen or starter snapshots.")
        st.page_link(
            pitching_dashboard_page,
            label="Go to Pitching Dashboard",
            icon=":material/sports_baseball:",
            use_container_width=True,
        )

    st.markdown("---")
    st.write("Use the sidebar to jump into leaderboards, profiles, and the game log.")
