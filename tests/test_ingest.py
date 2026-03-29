from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from support import TempDatabase, sample_event, sample_events_frame

from phillies_stats.ingest import (
    filter_to_team_games,
    normalize_pitcher_season_summary,
    upsert_pitcher_season_summary,
    upsert_statcast_data,
)


class IngestTests(unittest.TestCase):
    def test_filter_to_team_games_keeps_only_phillies_games(self):
        raw = pd.DataFrame(
            [
                {"game_pk": 1, "home_team": "PHI", "away_team": "ATL"},
                {"game_pk": 2, "home_team": "ATL", "away_team": "PHI"},
                {"game_pk": 3, "home_team": "NYY", "away_team": "BOS"},
            ]
        )

        filtered = filter_to_team_games(raw, team_code="PHI")

        self.assertEqual(filtered["game_pk"].tolist(), [1, 2])

    def test_upsert_statcast_data_is_idempotent(self):
        events = sample_events_frame(
            sample_event(
                event_id="game-1|ab-1|pitch-1",
                game_pk=1,
                game_date_value=date(2026, 3, 28),
                batter_name="Kyle Schwarber",
                batter_id=1,
                hit_distance_sc=430.0,
                launch_speed=110.2,
                launch_angle=28.0,
            ),
            sample_event(
                event_id="game-1|ab-2|pitch-2",
                game_pk=1,
                game_date_value=date(2026, 3, 28),
                batter_name="Bryce Harper",
                batter_id=2,
                hit_distance_sc=402.0,
                launch_speed=107.3,
                launch_angle=31.0,
            ),
        )

        with TempDatabase() as conn:
            first_insert = upsert_statcast_data(conn, events, season=2026)
            second_insert = upsert_statcast_data(conn, events, season=2026)
            event_count = conn.execute("SELECT COUNT(*) FROM statcast_events").fetchone()[0]

        self.assertEqual(first_insert, 2)
        self.assertEqual(second_insert, 0)
        self.assertEqual(event_count, 2)

    def test_pitcher_season_summary_normalizes_and_upserts(self):
        raw_summary = pd.DataFrame(
            [
                {
                    "Name": "zack wheeler",
                    "Team": "PHI",
                    "W": 3,
                    "L": 1,
                    "G": 4,
                    "GS": 4,
                    "SV": 0,
                    "IP": 25.1,
                    "SO": 31,
                    "BB": 5,
                    "HR": 2,
                    "ERA": 2.49,
                    "WHIP": 0.87,
                    "FBv": 97.4,
                    "WAR": 1.2,
                }
            ]
        )

        normalized = normalize_pitcher_season_summary(raw_summary, season=2026)

        with TempDatabase() as conn:
            upsert_count = upsert_pitcher_season_summary(conn, normalized)
            stored = conn.execute(
                "SELECT pitcher_name, wins, innings_pitched, era, avg_fastball_velocity FROM pitcher_season_summary"
            ).fetchone()

        self.assertEqual(upsert_count, 1)
        self.assertEqual(stored[0], "Zack Wheeler")
        self.assertEqual(stored[1], 3)
        self.assertEqual(stored[2], 25.1)
        self.assertEqual(stored[3], 2.49)
        self.assertEqual(stored[4], 97.4)


if __name__ == "__main__":
    unittest.main()
