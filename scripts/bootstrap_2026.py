from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.ingest import ingest_date_range, refresh_pitcher_season_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Phillies Statcast data for a season.")
    parser.add_argument("--season", type=int, default=2026, help="Season year to backfill.")
    parser.add_argument("--start-date", type=str, default=None, help="Optional override, format YYYY-MM-DD.")
    parser.add_argument("--end-date", type=str, default=None, help="Optional override, format YYYY-MM-DD.")
    parser.add_argument("--window-days", type=int, default=7, help="Number of days to request per Statcast pull.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config(args.season)
    start_date = date.fromisoformat(args.start_date) if args.start_date else config.season_start
    end_date = date.fromisoformat(args.end_date) if args.end_date else config.season_end

    conn = get_connection(config.db_path)
    initialize_database(conn)

    result = ingest_date_range(
        conn,
        season=config.season,
        start_date=start_date,
        end_date=end_date,
        team_code=config.team_code,
        window_days=args.window_days,
    )
    pitcher_summary_rows = 0
    pitcher_summary_warning = None
    try:
        pitcher_summary_rows = refresh_pitcher_season_summary(conn, season=config.season, team_code=config.team_code)
    except Exception as exc:
        pitcher_summary_warning = str(exc)

    print(f"Backfill complete for {config.season}.")
    print(f"Rows seen: {result['rows_seen']}")
    print(f"Rows inserted: {result['rows_inserted']}")
    print(f"Pitcher summary rows refreshed: {pitcher_summary_rows}")
    if pitcher_summary_warning:
        print(f"Pitcher summary warning: {pitcher_summary_warning}")
    print(f"Database: {config.db_path}")


if __name__ == "__main__":
    main()
