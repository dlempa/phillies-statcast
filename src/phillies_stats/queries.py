from __future__ import annotations

import calendar
from datetime import date

import duckdb
import pandas as pd

from phillies_stats.display import format_player_name


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
