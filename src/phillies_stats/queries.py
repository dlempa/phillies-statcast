from __future__ import annotations

import calendar
from datetime import date

import duckdb
import pandas as pd

from phillies_stats.config import get_config
from phillies_stats.display import format_player_name, normalize_player_key


def get_last_updated(conn: duckdb.DuckDBPyConnection):
    run_row = conn.execute(
        """
        SELECT MAX(completed_at)
        FROM ingestion_runs
        WHERE status = 'completed'
        """
    ).fetchone()
    if run_row and run_row[0]:
        return run_row[0]
    event_row = conn.execute("SELECT MAX(created_at) FROM statcast_events").fetchone()
    return event_row[0] if event_row else None


def get_dashboard_metrics(conn: duckdb.DuckDBPyConnection) -> dict[str, object]:
    longest_hr = conn.execute(
        """
        SELECT player_name, distance_ft
        FROM longest_home_runs
        ORDER BY rank
        LIMIT 1
        """
    ).fetchone()
    most_hrs = conn.execute(
        """
        SELECT player_name, home_run_count
        FROM player_home_run_summary
        ORDER BY home_run_count DESC, max_hr_distance_ft DESC NULLS LAST, player_name ASC
        LIMIT 1
        """
    ).fetchone()
    hardest_hr = conn.execute(
        """
        SELECT player_name, exit_velocity_mph
        FROM hardest_hit_home_runs
        LIMIT 1
        """
    ).fetchone()
    hardest_ball = conn.execute(
        """
        SELECT player_name, exit_velocity_mph
        FROM hardest_hit_balls_overall
        LIMIT 1
        """
    ).fetchone()
    return {
        "longest_hr": _format_metric_tuple(longest_hr),
        "most_hrs": _format_metric_tuple(most_hrs),
        "hardest_hr": _format_metric_tuple(hardest_hr),
        "hardest_ball": _format_metric_tuple(hardest_ball),
    }


def _format_metric_tuple(result: tuple[object, object] | None) -> tuple[object, object] | None:
    if not result:
        return result
    player_name, value = result
    return (format_player_name(player_name), value)


def get_pitching_dashboard_metrics(conn: duckdb.DuckDBPyConnection) -> dict[str, object]:
    overview = _build_pitcher_overview(conn)
    strikeout_leader = conn.execute(
        """
        SELECT player_name, strikeouts
        FROM pitcher_event_summary
        ORDER BY strikeouts DESC, player_name ASC
        LIMIT 1
        """
    ).fetchone()
    fastest_pitch = conn.execute(
        """
        SELECT player_name, release_speed
        FROM fastest_pitches
        LIMIT 1
        """
    ).fetchone()
    wins_leader = None
    innings_leader = None
    if not overview.empty:
        wins_df = overview.loc[overview["wins"].notna(), ["player_name", "wins"]].sort_values(
            ["wins", "player_name"], ascending=[False, True]
        )
        innings_df = overview.loc[overview["innings_pitched"].notna(), ["player_name", "innings_pitched"]].sort_values(
            ["innings_pitched", "player_name"], ascending=[False, True]
        )
        wins_leader = tuple(wins_df.iloc[0]) if not wins_df.empty else None
        innings_leader = tuple(innings_df.iloc[0]) if not innings_df.empty else None
    return {
        "strikeout_leader": _format_metric_tuple(strikeout_leader),
        "fastest_pitch": _format_metric_tuple(fastest_pitch),
        "wins_leader": _format_metric_tuple(wins_leader),
        "innings_leader": _format_metric_tuple(innings_leader),
    }


def get_top_longest_home_runs(
    conn: duckdb.DuckDBPyConnection,
    *,
    limit: int = 10,
    player: str | None = None,
    month: int | None = None,
    home_away: str | None = None,
) -> pd.DataFrame:
    sql = """
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY distance_ft DESC NULLS LAST, exit_velocity_mph DESC NULLS LAST, game_date ASC, player_name ASC
            ) AS rank,
            player_name,
            game_date,
            opponent,
            venue_name,
            home_away,
            distance_ft,
            exit_velocity_mph,
            launch_angle
        FROM longest_home_runs
        WHERE 1=1
    """
    params: list[object] = []
    if player:
        sql += " AND LOWER(player_name) = LOWER(?)"
        params.append(player)
    if month:
        sql += " AND EXTRACT(MONTH FROM game_date) = ?"
        params.append(month)
    if home_away:
        sql += " AND home_away = ?"
        params.append(home_away)
    sql += " ORDER BY distance_ft DESC NULLS LAST, exit_velocity_mph DESC NULLS LAST, game_date ASC, player_name ASC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).df()


def get_hr_distance_over_time(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT game_date, player_name, distance_ft, opponent, venue_name
        FROM longest_home_runs
        ORDER BY game_date ASC, distance_ft DESC
        """
    ).df()


def get_hardest_hit_home_runs(conn: duckdb.DuckDBPyConnection, limit: int = 15) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT *
        FROM hardest_hit_home_runs
        LIMIT ?
        """,
        [limit],
    ).df()


def get_shortest_home_runs(conn: duckdb.DuckDBPyConnection, limit: int = 15) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            player_name,
            game_date,
            opponent,
            venue_name,
            distance_ft,
            exit_velocity_mph,
            launch_angle
        FROM longest_home_runs
        ORDER BY distance_ft ASC, game_date ASC, player_name ASC
        LIMIT ?
        """,
        [limit],
    ).df()


def get_player_hr_distance_stats(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            player_name,
            home_run_count,
            avg_hr_distance_ft,
            max_hr_distance_ft
        FROM player_home_run_summary
        ORDER BY home_run_count DESC, max_hr_distance_ft DESC NULLS LAST, player_name ASC
        """
    ).df()


def get_hardest_hit_balls(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT *
        FROM hardest_hit_balls_overall
        LIMIT ?
        """,
        [limit],
    ).df()


def get_player_options(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT batter_name AS player_name
        FROM statcast_events
        WHERE is_phillies_batter = TRUE
          AND batter_name IS NOT NULL
        ORDER BY player_name ASC
        """
    ).fetchall()
    return sorted({format_player_name(row[0]) for row in rows if row[0]})


def get_player_summary(conn: duckdb.DuckDBPyConnection, player_name: str) -> dict[str, object]:
    hr_summary = conn.execute(
        """
        SELECT
            home_run_count,
            max_hr_distance_ft,
            avg_hr_distance_ft,
            hardest_hit_ball_mph
        FROM player_home_run_summary
        WHERE LOWER(player_name) = LOWER(?)
        """,
        [player_name],
    ).fetchone()
    monthly = conn.execute(
        """
        SELECT month_start, home_run_count
        FROM monthly_home_run_totals
        WHERE LOWER(player_name) = LOWER(?)
        ORDER BY month_start ASC
        """,
        [player_name],
    ).df()
    if not monthly.empty:
        monthly["month_name"] = monthly["month_start"].map(lambda value: calendar.month_name[value.month])

    home_runs = conn.execute(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY game_date ASC, event_id ASC) AS home_run_number,
            game_date,
            opponent,
            venue_name,
            hit_distance_sc AS distance_ft,
            launch_speed AS exit_velocity_mph,
            launch_angle
        FROM phillies_home_runs
        WHERE LOWER(batter_name) = LOWER(?)
        ORDER BY game_date ASC, event_id ASC
        """,
        [player_name],
    ).df()

    return {"summary": hr_summary, "monthly": monthly, "home_runs": home_runs}


def get_game_log(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            game_date,
            opponent,
            venue_name,
            result_text,
            hr_count,
            longest_hr_ft,
            hardest_hit_ball_mph
        FROM game_log_summaries
        ORDER BY game_date DESC
        """
    ).df()


def get_month_options(conn: duckdb.DuckDBPyConnection) -> list[int]:
    rows = conn.execute(
        """
        SELECT DISTINCT EXTRACT(MONTH FROM game_date)::INTEGER AS month_number
        FROM phillies_home_runs
        ORDER BY month_number ASC
        """
    ).fetchall()
    return [row[0] for row in rows]


def get_latest_game_date(conn: duckdb.DuckDBPyConnection) -> date | None:
    row = conn.execute("SELECT MAX(game_date) FROM statcast_events").fetchone()
    return row[0] if row else None


def _ensure_pitcher_summary_loaded(conn: duckdb.DuckDBPyConnection) -> None:
    row = conn.execute("SELECT COUNT(*) FROM pitcher_season_summary").fetchone()
    if row and row[0] > 0:
        return
    try:
        from phillies_stats.ingest import refresh_pitcher_season_summary

        config = get_config()
        refresh_pitcher_season_summary(conn, season=config.season, team_code=config.team_code)
    except Exception:
        return


def _build_pitcher_overview(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    _ensure_pitcher_summary_loaded(conn)

    event_summary = conn.execute(
        """
        SELECT
            pitcher_id,
            player_name,
            appearances,
            strikeouts,
            walks_issued,
            home_runs_allowed,
            whiffs,
            hardest_hit_allowed_mph,
            max_velocity_mph,
            avg_fastball_velocity_mph
        FROM pitcher_event_summary
        """
    ).df()
    season_summary = conn.execute(
        """
        SELECT
            pitcher_name AS player_name,
            wins,
            losses,
            games,
            games_started,
            saves,
            innings_pitched,
            strikeouts,
            walks,
            home_runs_allowed,
            era,
            whip,
            avg_fastball_velocity
        FROM pitcher_season_summary
        """
    ).df()

    event_columns = [
        "pitcher_id",
        "player_name",
        "appearances",
        "strikeouts",
        "walks_issued",
        "home_runs_allowed",
        "whiffs",
        "hardest_hit_allowed_mph",
        "max_velocity_mph",
        "avg_fastball_velocity_mph",
    ]
    season_columns = [
        "player_name",
        "wins",
        "losses",
        "games",
        "games_started",
        "saves",
        "innings_pitched",
        "strikeouts",
        "walks",
        "home_runs_allowed",
        "era",
        "whip",
        "avg_fastball_velocity",
    ]

    if not event_summary.empty:
        event_summary["player_name"] = event_summary["player_name"].map(format_player_name)
        event_summary["player_key"] = event_summary["player_name"].map(normalize_player_key)
    else:
        event_summary = pd.DataFrame(columns=event_columns + ["player_key"])

    if not season_summary.empty:
        season_summary["player_name"] = season_summary["player_name"].map(format_player_name)
        season_summary["player_key"] = season_summary["player_name"].map(normalize_player_key)
    else:
        season_summary = pd.DataFrame(columns=season_columns + ["player_key"])

    overview = event_summary.merge(
        season_summary,
        on="player_key",
        how="outer",
        suffixes=("_event", "_season"),
    )
    if overview.empty:
        return overview

    for column in [
        "player_name_event",
        "player_name_season",
        "strikeouts_event",
        "strikeouts_season",
        "walks_issued",
        "walks",
        "home_runs_allowed_event",
        "home_runs_allowed_season",
        "avg_fastball_velocity_mph",
        "avg_fastball_velocity",
        "wins",
        "losses",
        "games",
        "games_started",
        "saves",
        "innings_pitched",
        "era",
        "whip",
        "appearances",
        "whiffs",
        "hardest_hit_allowed_mph",
        "max_velocity_mph",
        "pitcher_id",
    ]:
        if column not in overview.columns:
            overview[column] = pd.NA

    overview["player_name"] = overview["player_name_season"].fillna(overview["player_name_event"])
    overview["strikeouts"] = overview["strikeouts_season"].fillna(overview["strikeouts_event"])
    overview["walks_issued"] = overview["walks"].fillna(overview["walks_issued"])
    overview["home_runs_allowed"] = overview["home_runs_allowed_season"].fillna(overview["home_runs_allowed_event"])
    overview["avg_fastball_velocity_mph"] = overview["avg_fastball_velocity"].fillna(
        overview["avg_fastball_velocity_mph"]
    )
    overview["position"] = overview.apply(_derive_pitcher_position, axis=1)
    return overview


def _derive_pitcher_position(row: pd.Series) -> str:
    saves = row.get("saves")
    games_started = row.get("games_started")
    games = row.get("games")
    if pd.notna(saves) and saves > 0:
        return "Closer"
    if pd.notna(games_started) and games_started > 0:
        if pd.notna(games) and games > 0 and games_started >= games / 2:
            return "Starter"
        return "Starter"
    return "Reliever"


def _filter_pitcher_frame(frame: pd.DataFrame, player_name: str, column: str = "player_name") -> pd.DataFrame:
    if frame.empty:
        return frame
    target_key = normalize_player_key(player_name)
    working = frame.copy()
    working["_player_key"] = working[column].map(normalize_player_key)
    filtered = working.loc[working["_player_key"].eq(target_key)].drop(columns=["_player_key"])
    return filtered


def get_pitcher_options(conn: duckdb.DuckDBPyConnection) -> list[str]:
    overview = _build_pitcher_overview(conn)
    if overview.empty:
        return []
    return sorted({name for name in overview["player_name"].dropna().tolist() if name})


def get_pitcher_strikeout_leaders(conn: duckdb.DuckDBPyConnection, limit: int = 15) -> pd.DataFrame:
    overview = _build_pitcher_overview(conn)
    if overview.empty:
        return overview
    leaders = overview[
        ["player_name", "position", "strikeouts", "appearances", "walks_issued", "home_runs_allowed"]
    ].copy()
    leaders = leaders.loc[leaders["strikeouts"].notna()]
    leaders["strikeouts_per_appearance"] = (leaders["strikeouts"] / leaders["appearances"]).round(2)
    leaders = leaders.sort_values(["strikeouts", "player_name"], ascending=[False, True]).head(limit)
    return leaders[
        ["player_name", "position", "strikeouts", "appearances", "strikeouts_per_appearance", "walks_issued", "home_runs_allowed"]
    ]


def get_pitcher_strikeouts_by_month(conn: duckdb.DuckDBPyConnection, player_name: str | None = None) -> pd.DataFrame:
    sql = """
        SELECT month_start, player_name, strikeouts
        FROM pitcher_strikeouts_by_month
        WHERE strikeouts > 0
    """
    params: list[object] = []
    sql += " ORDER BY month_start ASC, strikeouts DESC, player_name ASC"
    frame = conn.execute(sql, params).df()
    if frame.empty:
        return frame
    frame["player_name"] = frame["player_name"].map(format_player_name)
    if player_name:
        frame = _filter_pitcher_frame(frame, player_name)
    return frame


def get_pitcher_strikeouts_by_opponent(conn: duckdb.DuckDBPyConnection, player_name: str) -> pd.DataFrame:
    frame = conn.execute(
        """
        SELECT player_name, opponent, strikeouts
        FROM pitcher_strikeouts_by_opponent
        ORDER BY strikeouts DESC, opponent ASC
        """,
    ).df()
    if frame.empty:
        return frame
    frame["player_name"] = frame["player_name"].map(format_player_name)
    filtered = _filter_pitcher_frame(frame, player_name)
    return filtered[["opponent", "strikeouts"]]


def get_fastest_pitches(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> pd.DataFrame:
    frame = conn.execute(
        """
        SELECT
            player_name,
            game_date,
            opponent,
            pitch_name,
            release_speed
        FROM fastest_pitches
        LIMIT ?
        """,
        [limit],
    ).df()
    if frame.empty:
        return frame
    frame["player_name"] = frame["player_name"].map(format_player_name)
    return frame


def get_pitcher_velocity_summary(conn: duckdb.DuckDBPyConnection, limit: int = 15) -> pd.DataFrame:
    overview = _build_pitcher_overview(conn)
    if overview.empty:
        return overview
    summary = overview[["player_name", "position", "max_velocity_mph", "avg_fastball_velocity_mph"]].copy()
    summary = summary.loc[summary["max_velocity_mph"].notna() | summary["avg_fastball_velocity_mph"].notna()]
    summary = summary.sort_values(
        ["max_velocity_mph", "avg_fastball_velocity_mph", "player_name"],
        ascending=[False, False, True],
    ).head(limit)
    return summary


def get_pitcher_wins_leaders(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> pd.DataFrame:
    overview = _build_pitcher_overview(conn)
    if overview.empty:
        return overview
    leaders = overview[["player_name", "position", "wins", "losses", "innings_pitched", "era", "whip"]].copy()
    leaders = leaders.loc[leaders["wins"].notna()]
    return leaders.sort_values(["wins", "innings_pitched", "player_name"], ascending=[False, False, True]).head(limit)


def get_pitcher_walks_leaders(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> pd.DataFrame:
    overview = _build_pitcher_overview(conn)
    if overview.empty:
        return overview
    leaders = overview[["player_name", "position", "walks_issued", "strikeouts", "appearances"]].copy()
    leaders = leaders.loc[leaders["walks_issued"].notna()]
    return leaders.sort_values(["walks_issued", "strikeouts", "player_name"], ascending=[False, False, True]).head(limit)


def get_pitcher_home_run_allowed_leaders(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> pd.DataFrame:
    overview = _build_pitcher_overview(conn)
    if overview.empty:
        return overview
    leaders = overview[["player_name", "position", "home_runs_allowed", "walks_issued", "strikeouts"]].copy()
    leaders = leaders.loc[leaders["home_runs_allowed"].notna()]
    return leaders.sort_values(["home_runs_allowed", "player_name"], ascending=[False, True]).head(limit)


def get_team_pitcher_velocity_trend(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    frame = conn.execute(
        """
        SELECT
            e.game_date,
            COALESCE(p.player_name, e.pitcher_name) AS player_name,
            MAX(e.release_speed) AS max_velocity_mph
        FROM statcast_events e
        LEFT JOIN players p ON e.pitcher_id = p.player_id
        WHERE e.is_phillies_pitcher = TRUE
          AND e.release_speed IS NOT NULL
          AND e.pitcher_name IS NOT NULL
        GROUP BY e.game_date, COALESCE(p.player_name, e.pitcher_name)
        ORDER BY game_date ASC, max_velocity_mph DESC
        """
    ).df()
    if frame.empty:
        return frame
    frame["player_name"] = frame["player_name"].map(format_player_name)
    return frame


def get_pitcher_profile(conn: duckdb.DuckDBPyConnection, player_name: str) -> dict[str, object]:
    overview = _build_pitcher_overview(conn)
    summary_row = _filter_pitcher_frame(overview, player_name)
    summary = None
    if not summary_row.empty:
        row = summary_row.iloc[0]
        summary = (
            row.get("wins"),
            row.get("losses"),
            row.get("innings_pitched"),
            row.get("strikeouts"),
            row.get("walks_issued"),
            row.get("home_runs_allowed"),
            row.get("era"),
            row.get("whip"),
            row.get("max_velocity_mph"),
            row.get("avg_fastball_velocity_mph"),
            row.get("whiffs"),
            row.get("hardest_hit_allowed_mph"),
            row.get("appearances"),
            row.get("games_started"),
            row.get("saves"),
            row.get("position"),
        )

    pitch_usage = conn.execute(
        """
        SELECT player_name, pitch_name, pitch_count, usage_pct
        FROM pitcher_pitch_usage
        ORDER BY pitch_count DESC, pitch_name ASC
        """
    ).df()
    if not pitch_usage.empty:
        pitch_usage["player_name"] = pitch_usage["player_name"].map(format_player_name)
        pitch_usage = _filter_pitcher_frame(pitch_usage, player_name)[["pitch_name", "pitch_count", "usage_pct"]]

    strikeouts_by_month = get_pitcher_strikeouts_by_month(conn, player_name)
    strikeouts_by_opponent = get_pitcher_strikeouts_by_opponent(conn, player_name)
    fastest_pitches = conn.execute(
        """
        SELECT player_name, game_date, opponent, pitch_name, release_speed
        FROM fastest_pitches
        LIMIT 200
        """,
    ).df()
    if not fastest_pitches.empty:
        fastest_pitches["player_name"] = fastest_pitches["player_name"].map(format_player_name)
        fastest_pitches = _filter_pitcher_frame(fastest_pitches, player_name)[
            ["game_date", "opponent", "pitch_name", "release_speed"]
        ].head(10)

    return {
        "summary": summary,
        "pitch_usage": pitch_usage,
        "strikeouts_by_month": strikeouts_by_month,
        "strikeouts_by_opponent": strikeouts_by_opponent,
        "fastest_pitches": fastest_pitches,
    }
