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
from phillies_stats.display import format_player_name, render_highlight_table
from phillies_stats.queries import (
    get_fastest_pitches,
    get_last_updated,
    get_pitcher_home_run_allowed_leaders,
    get_pitcher_strikeout_leaders,
    get_pitcher_walks_leaders,
    get_pitcher_wins_leaders,
    get_pitching_dashboard_metrics,
    get_team_pitcher_velocity_trend,
)
from phillies_stats.ui import apply_app_theme, format_card, format_timestamp, render_page_header, render_section_heading, render_stat_cards, style_chart


def build_metric_card(label: str, result: tuple[object, object] | None, suffix: str, tone: str = "default") -> dict[str, str]:
    if not result:
        return {"label": label, "value": "No data", "helper": "", "tone": tone}
    player_name, value = result
    return {"label": label, "value": format_card(value, suffix), "helper": str(player_name), "tone": tone}


config = get_config()
conn = get_connection(config.db_path)
initialize_database(conn)
apply_app_theme()

metrics = get_pitching_dashboard_metrics(conn)
last_updated = get_last_updated(conn)
strikeout_leaders = get_pitcher_strikeout_leaders(conn, limit=6)
wins_leaders = get_pitcher_wins_leaders(conn, limit=6)
walks_leaders = get_pitcher_walks_leaders(conn, limit=6)
home_run_allowed = get_pitcher_home_run_allowed_leaders(conn, limit=6)
fastest_pitches = get_fastest_pitches(conn, limit=6)
velocity_trend = get_team_pitcher_velocity_trend(conn)

render_page_header(
    "Pitching Dashboard",
    "A premium season snapshot of Phillies pitching, built around strikeouts, velocity, wins, innings, and run-prevention pressure points.",
    eyebrow="Pitcher Stats",
    meta=f"Last updated {format_timestamp(last_updated)}" if last_updated else None,
)

render_stat_cards(
    [
        build_metric_card("Strikeout leader", metrics["strikeout_leader"], " K", tone="accent"),
        build_metric_card("Fastest pitch", metrics["fastest_pitch"], " mph"),
        build_metric_card("Wins leader", metrics["wins_leader"], " W"),
        build_metric_card("Innings pitched leader", metrics["innings_leader"], " IP"),
    ]
)

primary_col, side_col = st.columns([1.35, 1])

with primary_col:
    with st.container(border=True):
        render_section_heading("Primary Chart", "Maximum Phillies velocity by pitcher and game date across the season.")
        if velocity_trend.empty:
            st.info("Velocity trend data will appear once Phillies pitching events are loaded.")
        else:
            chart_data = velocity_trend.copy()
            chart_data["player_name"] = chart_data["player_name"].map(format_player_name)
            chart = style_chart(
                alt.Chart(chart_data)
                .mark_line(point=True, strokeWidth=2.4)
                .encode(
                    x=alt.X("game_date:T", title="Date"),
                    y=alt.Y("max_velocity_mph:Q", title="Max Velocity (mph)"),
                    color=alt.Color("player_name:N", title="Pitcher"),
                    tooltip=[
                        alt.Tooltip("player_name:N", title="Pitcher"),
                        alt.Tooltip("max_velocity_mph:Q", title="Max Velocity (mph)", format=".2f"),
                        alt.Tooltip("game_date:T", title="Date", format="%m-%d-%Y"),
                    ],
                )
                .interactive(),
                height=380,
            )
            st.altair_chart(chart, use_container_width=True)

with side_col:
    with st.container(border=True):
        render_section_heading("Leaderboard Preview", "Strikeouts and premium velocity side by side.")
        strikeout_tab, velocity_tab = st.tabs(["Strikeouts", "Fastest Pitches"])

        with strikeout_tab:
            if strikeout_leaders.empty:
                st.info("Pitcher strikeout data is not available yet.")
            else:
                st.markdown(
                    render_highlight_table(
                        strikeout_leaders.rename(
                            columns={
                                "player_name": "Pitcher",
                                "position": "Role",
                                "strikeouts": "Strikeouts",
                                "appearances": "Appearances",
                                "strikeouts_per_appearance": "K per Appearance",
                                "walks_issued": "Walks",
                                "home_runs_allowed": "HR Allowed",
                            }
                        ),
                        emphasis_columns=["Pitcher", "Strikeouts"],
                        secondary_columns=["Role", "Appearances", "K per Appearance", "Walks", "HR Allowed"],
                    ),
                    unsafe_allow_html=True,
                )

        with velocity_tab:
            if fastest_pitches.empty:
                st.info("Velocity data is not available yet.")
            else:
                st.markdown(
                    render_highlight_table(
                        fastest_pitches.rename(
                            columns={
                                "player_name": "Pitcher",
                                "game_date": "Date",
                                "opponent": "Opponent",
                                "pitch_name": "Pitch Type",
                                "release_speed": "Velocity (mph)",
                            }
                        ),
                        emphasis_columns=["Pitcher", "Velocity (mph)"],
                        secondary_columns=["Date", "Opponent", "Pitch Type"],
                    ),
                    unsafe_allow_html=True,
                )

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    with st.container(border=True):
        render_section_heading("Wins Leaders", "A clean season view of wins, innings, and run prevention.")
        if wins_leaders.empty:
            st.info("Pitcher season summary data is not available yet.")
        else:
            st.markdown(
                render_highlight_table(
                    wins_leaders.rename(
                        columns={
                            "player_name": "Pitcher",
                            "wins": "Wins",
                            "losses": "Losses",
                            "innings_pitched": "Innings Pitched",
                            "era": "ERA",
                            "whip": "WHIP",
                        }
                    ),
                    emphasis_columns=["Pitcher", "Wins", "Innings Pitched"],
                    secondary_columns=["ERA", "WHIP", "Losses", "Position"],
                ),
                unsafe_allow_html=True,
            )

with bottom_right:
    with st.container(border=True):
        render_section_heading("Secondary Panel", "Walk pressure and home run damage allowed, without crowding the main dashboard.")
        walks_tab, damage_tab = st.tabs(["Walks Issued", "Home Runs Allowed"])

        with walks_tab:
            if walks_leaders.empty:
                st.info("Walk data is not available yet.")
            else:
                st.markdown(
                    render_highlight_table(
                        walks_leaders.rename(
                            columns={
                                "player_name": "Pitcher",
                                "walks_issued": "Walks",
                                "strikeouts": "Strikeouts",
                                "appearances": "Appearances",
                            }
                        ),
                        emphasis_columns=["Pitcher", "Walks"],
                        secondary_columns=["Strikeouts", "Appearances", "Position"],
                    ),
                    unsafe_allow_html=True,
                )

        with damage_tab:
            if home_run_allowed.empty:
                st.info("Home run allowed data is not available yet.")
            else:
                st.markdown(
                    render_highlight_table(
                        home_run_allowed.rename(
                            columns={
                                "player_name": "Pitcher",
                                "home_runs_allowed": "HR Allowed",
                                "walks_issued": "Walks",
                                "strikeouts": "Strikeouts",
                            }
                        ),
                        emphasis_columns=["Pitcher", "HR Allowed"],
                        secondary_columns=["Walks", "Strikeouts", "Position"],
                    ),
                    unsafe_allow_html=True,
                )
