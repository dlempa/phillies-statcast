from __future__ import annotations

from pathlib import Path

import duckdb


def get_connection(db_path: Path | str, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def initialize_database(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            player_id BIGINT PRIMARY KEY,
            player_name TEXT NOT NULL,
            player_type TEXT,
            bats TEXT,
            throws TEXT,
            last_seen_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS games (
            game_pk BIGINT PRIMARY KEY,
            game_date DATE NOT NULL,
            season INTEGER NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            venue_name TEXT,
            phillies_home BOOLEAN,
            opponent TEXT,
            home_score INTEGER,
            away_score INTEGER,
            result_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS statcast_events (
            event_id TEXT PRIMARY KEY,
            season INTEGER NOT NULL,
            game_pk BIGINT NOT NULL,
            game_date DATE NOT NULL,
            game_datetime TIMESTAMP,
            inning INTEGER,
            inning_topbot TEXT,
            at_bat_number INTEGER,
            pitch_number INTEGER,
            phillies_role TEXT,
            is_phillies_batter BOOLEAN,
            is_phillies_pitcher BOOLEAN,
            batting_team TEXT,
            fielding_team TEXT,
            home_team TEXT,
            away_team TEXT,
            opponent TEXT,
            venue_name TEXT,
            batter_id BIGINT,
            batter_name TEXT,
            pitcher_id BIGINT,
            pitcher_name TEXT,
            stand TEXT,
            p_throws TEXT,
            events TEXT,
            description TEXT,
            bb_type TEXT,
            pitch_type TEXT,
            pitch_name TEXT,
            release_speed DOUBLE,
            effective_speed DOUBLE,
            launch_speed DOUBLE,
            launch_angle DOUBLE,
            hit_distance_sc DOUBLE,
            zone INTEGER,
            balls INTEGER,
            strikes INTEGER,
            outs_when_up INTEGER,
            estimated_ba_using_speedangle DOUBLE,
            estimated_woba_using_speedangle DOUBLE,
            woba_value DOUBLE,
            delta_home_win_exp DOUBLE,
            post_away_score INTEGER,
            post_home_score INTEGER,
            is_home_run BOOLEAN,
            is_strikeout BOOLEAN,
            is_in_play BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ingestion_runs (
            run_id TEXT PRIMARY KEY,
            season INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            status TEXT NOT NULL,
            rows_seen INTEGER DEFAULT 0,
            rows_inserted INTEGER DEFAULT 0,
            notes TEXT
        );
        """
    )
    create_views(conn)


def create_views(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE OR REPLACE VIEW phillies_home_runs AS
        SELECT
            event_id,
            game_pk,
            game_date,
            opponent,
            venue_name,
            batter_id,
            batter_name,
            launch_speed,
            launch_angle,
            hit_distance_sc,
            CASE WHEN home_team = 'PHI' THEN 'Home' ELSE 'Away' END AS home_away
        FROM statcast_events
        WHERE is_home_run = TRUE
          AND is_phillies_batter = TRUE;

        CREATE OR REPLACE VIEW longest_home_runs AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY hit_distance_sc DESC NULLS LAST, launch_speed DESC NULLS LAST, game_date ASC, event_id ASC
            ) AS rank,
            batter_name AS player_name,
            game_date,
            opponent,
            venue_name,
            home_away,
            hit_distance_sc AS distance_ft,
            launch_speed AS exit_velocity_mph,
            launch_angle
        FROM phillies_home_runs
        WHERE hit_distance_sc IS NOT NULL;

        CREATE OR REPLACE VIEW hardest_hit_home_runs AS
        SELECT
            batter_name AS player_name,
            game_date,
            opponent,
            venue_name,
            hit_distance_sc AS distance_ft,
            launch_speed AS exit_velocity_mph,
            launch_angle
        FROM phillies_home_runs
        WHERE launch_speed IS NOT NULL
        ORDER BY launch_speed DESC, hit_distance_sc DESC NULLS LAST, game_date ASC;

        CREATE OR REPLACE VIEW hardest_hit_balls_overall AS
        SELECT
            batter_name AS player_name,
            game_date,
            opponent,
            venue_name,
            COALESCE(events, description) AS outcome,
            launch_speed AS exit_velocity_mph,
            launch_angle,
            hit_distance_sc AS distance_ft
        FROM statcast_events
        WHERE is_phillies_batter = TRUE
          AND batter_name IS NOT NULL
          AND TRIM(batter_name) <> ''
          AND launch_speed IS NOT NULL
        ORDER BY launch_speed DESC, game_date ASC, event_id ASC;

        CREATE OR REPLACE VIEW player_home_run_summary AS
        WITH player_hard_hit AS (
            SELECT
                batter_id,
                MAX(launch_speed) AS hardest_hit_ball_mph
            FROM statcast_events
            WHERE is_phillies_batter = TRUE
            GROUP BY batter_id
        )
        SELECT
            hr.batter_id,
            hr.batter_name AS player_name,
            COUNT(*) AS home_run_count,
            ROUND(AVG(hr.hit_distance_sc), 1) AS avg_hr_distance_ft,
            MAX(hr.hit_distance_sc) AS max_hr_distance_ft,
            p.hardest_hit_ball_mph
        FROM phillies_home_runs hr
        LEFT JOIN player_hard_hit p ON hr.batter_id = p.batter_id
        GROUP BY hr.batter_id, hr.batter_name, p.hardest_hit_ball_mph
        ORDER BY home_run_count DESC, max_hr_distance_ft DESC NULLS LAST, player_name ASC;

        CREATE OR REPLACE VIEW monthly_home_run_totals AS
        SELECT
            batter_name AS player_name,
            DATE_TRUNC('month', game_date) AS month_start,
            COUNT(*) AS home_run_count
        FROM phillies_home_runs
        GROUP BY batter_name, DATE_TRUNC('month', game_date)
        ORDER BY month_start ASC, home_run_count DESC, player_name ASC;

        CREATE OR REPLACE VIEW game_log_summaries AS
        SELECT
            g.game_pk,
            g.game_date,
            g.opponent,
            g.venue_name,
            g.result_text,
            COUNT(CASE WHEN e.is_home_run = TRUE AND e.is_phillies_batter = TRUE THEN 1 END) AS hr_count,
            MAX(CASE WHEN e.is_home_run = TRUE AND e.is_phillies_batter = TRUE THEN e.hit_distance_sc END) AS longest_hr_ft,
            MAX(CASE WHEN e.is_phillies_batter = TRUE THEN e.launch_speed END) AS hardest_hit_ball_mph
        FROM games g
        LEFT JOIN statcast_events e ON g.game_pk = e.game_pk
        GROUP BY g.game_pk, g.game_date, g.opponent, g.venue_name, g.result_text
        ORDER BY g.game_date DESC, g.game_pk DESC;

        CREATE OR REPLACE VIEW strikeout_leaders AS
        SELECT
            pitcher_id,
            pitcher_name AS player_name,
            COUNT(*) AS strikeouts
        FROM statcast_events
        WHERE is_phillies_pitcher = TRUE
          AND is_strikeout = TRUE
        GROUP BY pitcher_id, pitcher_name
        ORDER BY strikeouts DESC, player_name ASC;

        CREATE OR REPLACE VIEW fastest_pitches AS
        SELECT
            pitcher_id,
            pitcher_name AS player_name,
            game_date,
            opponent,
            venue_name,
            pitch_name,
            release_speed
        FROM statcast_events
        WHERE is_phillies_pitcher = TRUE
          AND release_speed IS NOT NULL
        ORDER BY release_speed DESC, game_date ASC, player_name ASC;
        """
    )
