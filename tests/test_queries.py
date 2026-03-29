from __future__ import annotations

import unittest
from datetime import date

from support import TempDatabase, sample_event, sample_events_frame

from phillies_stats.ingest import upsert_statcast_data
from phillies_stats.queries import get_hardest_hit_balls, get_top_longest_home_runs


class QueryTests(unittest.TestCase):
    def test_longest_home_runs_leaderboard_updates_from_event_data(self):
        opening_events = sample_events_frame(
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
                event_id="game-2|ab-1|pitch-1",
                game_pk=2,
                game_date_value=date(2026, 3, 29),
                batter_name="Bryce Harper",
                batter_id=2,
                hit_distance_sc=415.0,
                launch_speed=108.4,
                launch_angle=30.0,
                opponent="WSH",
                away_team="WSH",
            ),
        )

        new_longer_home_run = sample_events_frame(
            sample_event(
                event_id="game-3|ab-1|pitch-1",
                game_pk=3,
                game_date_value=date(2026, 3, 30),
                batter_name="Nick Castellanos",
                batter_id=3,
                hit_distance_sc=451.0,
                launch_speed=111.0,
                launch_angle=26.0,
                opponent="LAD",
                away_team="LAD",
            )
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, opening_events, season=2026)
            initial = get_top_longest_home_runs(conn, limit=2)

            upsert_statcast_data(conn, new_longer_home_run, season=2026)
            updated = get_top_longest_home_runs(conn, limit=3)

        self.assertEqual(initial.iloc[0]["player_name"], "Kyle Schwarber")
        self.assertEqual(updated.iloc[0]["player_name"], "Nick Castellanos")
        self.assertEqual(updated.iloc[0]["distance_ft"], 451.0)
        self.assertEqual(updated.iloc[2]["player_name"], "Bryce Harper")

    def test_hardest_hit_balls_excludes_blank_names_and_limits_to_ten(self):
        rows = []
        for index in range(11):
            rows.append(
                sample_event(
                    event_id=f"game-{index}|ab-1|pitch-1",
                    game_pk=100 + index,
                    game_date_value=date(2026, 3, 26),
                    batter_name=f"player {index}",
                    batter_id=1000 + index,
                    hit_distance_sc=300.0 + index,
                    launch_speed=100.0 + index,
                    launch_angle=20.0,
                    events="single",
                    is_home_run=False,
                )
            )
        rows.append(
            sample_event(
                event_id="blank-name-row",
                game_pk=999,
                game_date_value=date(2026, 3, 26),
                batter_name="",
                batter_id=9999,
                hit_distance_sc=450.0,
                launch_speed=120.0,
                launch_angle=15.0,
                events="double",
                is_home_run=False,
            )
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, sample_events_frame(*rows), season=2026)
            hardest_balls = get_hardest_hit_balls(conn)

        self.assertEqual(len(hardest_balls), 10)
        self.assertTrue(hardest_balls["player_name"].notna().all())
        self.assertNotIn("", hardest_balls["player_name"].tolist())


if __name__ == "__main__":
    unittest.main()
