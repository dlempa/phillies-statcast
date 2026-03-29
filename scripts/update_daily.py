from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from phillies_stats.config import get_config
from phillies_stats.database import get_connection, initialize_database
from phillies_stats.ingest import ingest_date_range
from phillies_stats.queries import get_latest_game_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily Phillies Statcast update.")
    parser.add_argument("--season", type=int, default=2026, help="Season year to update.")
    parser.add_argument("--lookback-days", type=int, default=3, help="Re-pull recent days to catch corrections safely.")
    parser.add_argument("--window-days", type=int, default=3, help="Number of days to request per Statcast pull.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config(args.season)
    conn = get_connection(config.db_path)
    initialize_database(conn)

    latest_game_date = get_latest_game_date(conn)
    today = date.today()

    if latest_game_date is None:
        start_date = config.season_start
    else:
        start_date = max(config.season_start, latest_game_date - timedelta(days=args.lookback_days))
    end_date = min(today, config.season_end)

    result = ingest_date_range(
        conn,
        season=config.season,
        start_date=start_date,
        end_date=end_date,
        team_code=config.team_code,
        window_days=args.window_days,
    )
    print(f"Daily update complete for {config.season}.")
    print(f"Window: {start_date} to {end_date}")
    print(f"Rows seen: {result['rows_seen']}")
    print(f"Rows inserted: {result['rows_inserted']}")
    print(f"Database: {config.db_path}")


if __name__ == "__main__":
    main()
