from __future__ import annotations

import unittest
from datetime import date

from support import TempDatabase, sample_event, sample_events_frame

from phillies_stats.ingest import upsert_statcast_data
from phillies_stats.ingest import upsert_pitcher_season_summary
from phillies_stats.queries import (
    get_dashboard_metrics,
    get_hardest_hit_balls,
    get_pitcher_home_run_allowed_leaders,
    get_pitcher_profile,
    get_pitcher_strikeout_leaders,
    get_pitcher_walks_leaders,
    get_pitcher_wins_leaders,
    get_player_hr_distance_stats,
    get_top_longest_home_runs,
)


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

    def test_hitter_home_run_summary_rolls_up_same_player_id_with_name_variants(self):
        home_runs = sample_events_frame(
            sample_event(
                event_id="schwarber-1",
                game_pk=301,
                game_date_value=date(2026, 4, 1),
                batter_name="Kyle Schwarber",
                batter_id=656941,
                hit_distance_sc=460.0,
                launch_speed=110.7,
            ),
            sample_event(
                event_id="schwarber-2",
                game_pk=302,
                game_date_value=date(2026, 4, 2),
                batter_name="kyle schwarber",
                batter_id=656941,
                hit_distance_sc=383.0,
                launch_speed=103.2,
            ),
            sample_event(
                event_id="schwarber-3",
                game_pk=303,
                game_date_value=date(2026, 4, 3),
                batter_name="Kyle Schwarber",
                batter_id=656941,
                hit_distance_sc=397.0,
                launch_speed=107.0,
            ),
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, home_runs, season=2026)
            metrics = get_dashboard_metrics(conn)
            player_power = get_player_hr_distance_stats(conn)

        self.assertEqual(metrics["most_hrs"], ("Kyle Schwarber", 3))
        schwarber_rows = player_power[player_power["player_name"].str.lower().eq("kyle schwarber")]
        self.assertEqual(len(schwarber_rows), 1)
        self.assertEqual(schwarber_rows.iloc[0]["home_run_count"], 3)

    def test_pitcher_strikeout_leaders_uses_pitching_events(self):
        pitching_events = sample_events_frame(
            sample_event(
                event_id="pitching-game-1",
                game_pk=501,
                game_date_value=date(2026, 4, 1),
                batter_name="Opponent One",
                batter_id=501,
                pitcher_name="Wheeler, Zack",
                pitcher_id=45,
                events="strikeout",
                is_home_run=False,
                is_strikeout=True,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="ATL",
                fielding_team="PHI",
                home_team="PHI",
                away_team="ATL",
                inning_topbot="Top",
            ),
            sample_event(
                event_id="pitching-game-2",
                game_pk=502,
                game_date_value=date(2026, 4, 2),
                batter_name="Opponent Two",
                batter_id=502,
                pitcher_name="Wheeler, Zack",
                pitcher_id=45,
                events="strikeout",
                is_home_run=False,
                is_strikeout=True,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="NYM",
                fielding_team="PHI",
                home_team="NYM",
                away_team="PHI",
                inning_topbot="Bot",
                opponent="NYM",
            ),
        )
        pitcher_summary = sample_events_frame(
            {
                "season": 2026,
                "pitcher_name": "Zack Wheeler",
                "team": "PHI",
                "wins": 2,
                "losses": 0,
                "games": 2,
                "games_started": 2,
                "saves": 0,
                "innings_pitched": 12.0,
                "strikeouts": 14,
                "walks": 2,
                "home_runs_allowed": 1,
                "era": 1.50,
                "whip": 0.92,
                "avg_fastball_velocity": 97.5,
                "war": 0.8,
            }
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, pitching_events, season=2026)
            upsert_pitcher_season_summary(conn, pitcher_summary)
            leaders = get_pitcher_strikeout_leaders(conn, limit=5)

        self.assertEqual(leaders.iloc[0]["player_name"], "Zack Wheeler")
        self.assertEqual(leaders.iloc[0]["strikeouts"], 14)
        self.assertEqual(leaders.iloc[0]["appearances"], 2)

    def test_pitcher_leaderboards_roll_up_same_pitcher_id_with_name_variants(self):
        pitching_events = sample_events_frame(
            sample_event(
                event_id="nola-1",
                game_pk=801,
                game_date_value=date(2026, 4, 1),
                batter_name="Opponent One",
                batter_id=801,
                pitcher_name="Aaron Nola",
                pitcher_id=605400,
                events="strikeout",
                is_home_run=False,
                is_strikeout=True,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="ATL",
                fielding_team="PHI",
                home_team="PHI",
                away_team="ATL",
                inning_topbot="Top",
            ),
            sample_event(
                event_id="nola-2",
                game_pk=802,
                game_date_value=date(2026, 4, 2),
                batter_name="Opponent Two",
                batter_id=802,
                pitcher_name="Nola, Aaron",
                pitcher_id=605400,
                events="walk",
                is_home_run=False,
                is_strikeout=False,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="NYM",
                fielding_team="PHI",
                home_team="NYM",
                away_team="PHI",
                inning_topbot="Bot",
                opponent="NYM",
            ),
            sample_event(
                event_id="nola-3",
                game_pk=803,
                game_date_value=date(2026, 4, 3),
                batter_name="Opponent Three",
                batter_id=803,
                pitcher_name="Aaron Nola",
                pitcher_id=605400,
                events="home_run",
                is_home_run=True,
                is_strikeout=False,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="MIA",
                fielding_team="PHI",
                home_team="PHI",
                away_team="MIA",
                inning_topbot="Top",
                opponent="MIA",
            ),
        )
        pitcher_summary = sample_events_frame(
            {
                "season": 2026,
                "pitcher_name": "Aaron Nola",
                "team": "PHI",
                "wins": 1,
                "losses": 0,
                "games": 3,
                "games_started": 3,
                "saves": 0,
                "innings_pitched": 17.1,
                "strikeouts": 1,
                "walks": 1,
                "home_runs_allowed": 1,
                "era": 3.12,
                "whip": 1.04,
                "avg_fastball_velocity": 93.5,
                "war": 0.3,
            }
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, pitching_events, season=2026)
            upsert_pitcher_season_summary(conn, pitcher_summary)
            strikeout_leaders = get_pitcher_strikeout_leaders(conn, limit=5)
            wins_leaders = get_pitcher_wins_leaders(conn, limit=5)
            walks_leaders = get_pitcher_walks_leaders(conn, limit=5)
            home_run_allowed = get_pitcher_home_run_allowed_leaders(conn, limit=5)

        for leaders in [strikeout_leaders, wins_leaders, walks_leaders, home_run_allowed]:
            self.assertEqual(leaders["player_name"].tolist().count("Aaron Nola"), 1)

        self.assertEqual(strikeout_leaders.iloc[0]["appearances"], 3)
        self.assertEqual(walks_leaders.iloc[0]["walks_issued"], 1)
        self.assertEqual(home_run_allowed.iloc[0]["home_runs_allowed"], 1)

    def test_pitcher_profile_merges_summary_stats_with_last_first_event_name(self):
        pitching_events = sample_events_frame(
            sample_event(
                event_id="duran-1",
                game_pk=601,
                game_date_value=date(2026, 4, 5),
                batter_name="Opponent Three",
                batter_id=601,
                pitcher_name="Duran, Jhoan",
                pitcher_id=77,
                events="strikeout",
                is_home_run=False,
                is_strikeout=True,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="ATL",
                fielding_team="PHI",
                home_team="PHI",
                away_team="ATL",
                inning_topbot="Top",
                release_speed=101.2,
            )
        )
        pitcher_summary = sample_events_frame(
            {
                "season": 2026,
                "pitcher_name": "Jhoan Duran",
                "team": "PHI",
                "wins": 1,
                "losses": 0,
                "games": 3,
                "games_started": 0,
                "saves": 2,
                "innings_pitched": 3.1,
                "strikeouts": 5,
                "walks": 1,
                "home_runs_allowed": 0,
                "era": 0.00,
                "whip": 0.90,
                "avg_fastball_velocity": 100.4,
                "war": 0.4,
            }
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, pitching_events, season=2026)
            upsert_pitcher_season_summary(conn, pitcher_summary)
            profile = get_pitcher_profile(conn, "Jhoan Duran")

        summary = profile["summary"]
        self.assertEqual(summary[0], 1)
        self.assertEqual(summary[1], 0)
        self.assertEqual(summary[2], 3.1)
        self.assertEqual(summary[6], 0.0)
        self.assertEqual(summary[7], 0.9)
        self.assertEqual(summary[14], 2)
        self.assertEqual(summary[15], "Closer")

    def test_pitcher_strikeout_leaders_handles_missing_season_summary(self):
        pitching_events = sample_events_frame(
            sample_event(
                event_id="pitching-no-summary-1",
                game_pk=701,
                game_date_value=date(2026, 4, 6),
                batter_name="Opponent Four",
                batter_id=701,
                pitcher_name="Sanchez, Cristopher",
                pitcher_id=61,
                events="strikeout",
                is_home_run=False,
                is_strikeout=True,
                phillies_role="pitching",
                is_phillies_batter=False,
                is_phillies_pitcher=True,
                batting_team="MIA",
                fielding_team="PHI",
                home_team="PHI",
                away_team="MIA",
                inning_topbot="Top",
            )
        )

        with TempDatabase() as conn:
            upsert_statcast_data(conn, pitching_events, season=2026)
            leaders = get_pitcher_strikeout_leaders(conn, limit=5)

        self.assertEqual(leaders.iloc[0]["player_name"], "Cristopher Sanchez")
        self.assertEqual(leaders.iloc[0]["strikeouts"], 1)
        self.assertEqual(leaders.iloc[0]["position"], "Reliever")


if __name__ == "__main__":
    unittest.main()
