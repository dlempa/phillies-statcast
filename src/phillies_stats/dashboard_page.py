from __future__ import annotations

import altair as alt
import streamlit as st

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.display import format_display_dataframe, format_metric_value, render_centered_table
from phillies_stats.queries import get_dashboard_metrics, get_hr_distance_over_time, get_last_updated, get_top_longest_home_runs


def _format_metric(result, unit: str, fallback: str = "No data yet") -> tuple[str, str]:
    if not result:
        return fallback, ""
    player_name, value = result
    if value is None:
        return fallback, ""
    return f"{format_metric_value(value)} {unit}", player_name


def render_hitter_dashboard() -> None:
    config = get_config()
    conn = get_connection(config.db_path)
    initialize_database(conn)

    st.title("Hitter Dashboard")
    st.caption(f"Phillies home runs and power stats for the {config.season} season.")

    metrics = get_dashboard_metrics(conn)
    last_updated = get_last_updated(conn)
    top_10 = get_top_longest_home_runs(conn, limit=10)
    distance_over_time = get_hr_distance_over_time(conn)

    card_1, card_2, card_3, card_4 = st.columns(4)
    value, player = _format_metric(metrics["longest_hr"], "ft")
    card_1.metric("Longest HR of season", value, player)
    value, player = _format_metric(metrics["most_hrs"], "HR")
    card_2.metric("Most HRs by a Phillies player", value, player)
    value, player = _format_metric(metrics["hardest_hr"], "mph")
    card_3.metric("Hardest-hit HR", value, player)
    value, player = _format_metric(metrics["hardest_ball"], "mph")
    card_4.metric("Hardest-hit ball overall", value, player)

    if last_updated:
        st.write(f"Last updated: {last_updated}")
    else:
        st.info("No Statcast data is loaded yet. Run the bootstrap script to backfill the season.")

    st.subheader("Current Top 10 Longest Phillies Home Runs")
    if top_10.empty:
        st.info("No home run data is available yet.")
    else:
        preview = top_10.rename(
            columns={
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
        st.markdown(render_centered_table(preview), unsafe_allow_html=True)

    st.subheader("Phillies Home Run Distance Scatter Plot")
    if distance_over_time.empty:
        st.info("The chart will appear after Phillies home run events are loaded.")
    else:
        chart_data = format_display_dataframe(
            distance_over_time.rename(
                columns={
                    "game_date": "Date",
                    "distance_ft": "Distance (ft)",
                    "player_name": "Player",
                    "opponent": "Opponent",
                    "venue_name": "Ballpark",
                }
            )
        )
        chart_data["Date"] = distance_over_time["game_date"]
        chart = (
            alt.Chart(chart_data)
            .mark_circle(size=90)
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Distance (ft):Q", title="Distance (ft)"),
                color=alt.Color("Player:N", title="Player"),
                tooltip=["Player", "Distance (ft)", "Opponent", "Ballpark", "Date"],
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)


def render_dashboard() -> None:
    render_hitter_dashboard()
