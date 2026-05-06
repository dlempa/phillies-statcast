from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4
import unittest

from support import PROJECT_ROOT, TempDatabase

from phillies_stats.queries import get_latest_team_state_summary
from phillies_stats.state_summary import (
    StateSummaryValidationError,
    load_team_state_summary_file,
    upsert_team_state_summary,
    write_team_state_summary_file,
)


class StateSummaryTests(unittest.TestCase):
    def test_upsert_stores_generated_summary_payload(self):
        payload = _summary_payload()

        with TempDatabase() as conn:
            row = upsert_team_state_summary(conn, payload, season=2026)
            stored = get_latest_team_state_summary(conn, season=2026)

        self.assertEqual(row["season"], 2026)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["headline"], "Phillies hit crisis mode after 10-game skid")
        self.assertEqual(stored["tone_label"], "Crisis Watch")
        self.assertEqual(json.loads(stored["key_stats_json"])[0], {"label": "Record", "value": "8-18"})
        self.assertEqual(json.loads(stored["sources_json"])[0]["label"], "Phillies Nation")

    def test_upsert_replaces_existing_summary_for_same_date(self):
        with TempDatabase() as conn:
            upsert_team_state_summary(conn, _summary_payload(headline="Old headline"), season=2026)
            upsert_team_state_summary(conn, _summary_payload(headline="New headline"), season=2026)
            stored = get_latest_team_state_summary(conn, season=2026)
            row_count = conn.execute("SELECT COUNT(*) FROM team_state_summaries").fetchone()[0]

        self.assertEqual(row_count, 1)
        assert stored is not None
        self.assertEqual(stored["headline"], "New headline")

    def test_latest_summary_returns_newest_as_of_date(self):
        with TempDatabase() as conn:
            upsert_team_state_summary(conn, _summary_payload(as_of_date="2026-04-24", headline="Yesterday"), season=2026)
            upsert_team_state_summary(conn, _summary_payload(as_of_date="2026-04-25", headline="Today"), season=2026)
            stored = get_latest_team_state_summary(conn, season=2026)

        assert stored is not None
        self.assertEqual(stored["headline"], "Today")

    def test_invalid_generated_payload_is_rejected(self):
        payload = _summary_payload()
        payload.pop("summary_text")

        with TempDatabase() as conn:
            with self.assertRaises(StateSummaryValidationError):
                upsert_team_state_summary(conn, payload, season=2026)

    def test_invalid_source_url_is_rejected(self):
        payload = _summary_payload()
        payload["sources"] = [{"label": "Bad source", "url": "not-a-url"}]

        with TempDatabase() as conn:
            with self.assertRaises(StateSummaryValidationError):
                upsert_team_state_summary(conn, payload, season=2026)

    def test_payload_season_mismatch_is_rejected(self):
        payload = _summary_payload()
        payload["season"] = 2025

        with TempDatabase() as conn:
            with self.assertRaises(StateSummaryValidationError):
                upsert_team_state_summary(conn, payload, season=2026)

    def test_write_state_summary_file_serializes_normalized_payload(self):
        summary_path = _temp_summary_dir(self) / "state_of_the_phillies_2026.json"
        row = write_team_state_summary_file(summary_path, _summary_payload(), season=2026)
        document = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(row["season"], 2026)
        self.assertEqual(document["season"], 2026)
        self.assertEqual(document["as_of_date"], "2026-04-25")
        self.assertEqual(document["headline"], "Phillies hit crisis mode after 10-game skid")
        self.assertEqual(document["key_stats"][0], {"label": "Record", "value": "8-18"})
        self.assertEqual(document["sources"][0]["label"], "Phillies Nation")
        self.assertEqual(document["generated_at"], "2026-04-25T11:30:00Z")

    def test_load_state_summary_file_returns_renderable_summary(self):
        summary_path = _temp_summary_dir(self) / "state_of_the_phillies_2026.json"
        write_team_state_summary_file(summary_path, _summary_payload(), season=2026)
        stored = load_team_state_summary_file(summary_path, season=2026)

        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["headline"], "Phillies hit crisis mode after 10-game skid")
        self.assertEqual(json.loads(stored["key_stats_json"])[0], {"label": "Record", "value": "8-18"})
        self.assertEqual(json.loads(stored["sources_json"])[0]["label"], "Phillies Nation")

    def test_load_state_summary_file_returns_none_for_missing_or_invalid_file(self):
        temp_dir = _temp_summary_dir(self)
        missing_path = temp_dir / "missing.json"
        invalid_path = temp_dir / "state_of_the_phillies_2026.json"
        invalid_path.write_text("{bad json", encoding="utf-8")

        self.assertIsNone(load_team_state_summary_file(missing_path, season=2026))
        self.assertIsNone(load_team_state_summary_file(invalid_path, season=2026))


def _summary_payload(
    *,
    as_of_date: str = "2026-04-25",
    headline: str = "Phillies hit crisis mode after 10-game skid",
) -> dict[str, object]:
    return {
        "as_of_date": as_of_date,
        "headline": headline,
        "summary_text": (
            "The Phillies are currently on a 10-game losing streak and have fallen to 8-18 on the season. "
            "The collapse has reached every part of the club, with the lineup going quiet and the pitching staff getting hit hard."
        ),
        "tone_label": "Crisis Watch",
        "key_stats": [
            {"label": "Record", "value": "8-18"},
            {"label": "Streak", "value": "10 losses"},
            {"label": "Run differential", "value": "-53"},
            {"label": "During streak", "value": "26 RF, 69 RA"},
        ],
        "sources": [
            {
                "label": "Phillies Nation",
                "url": "https://philliesnation.com/2026/04/philadelphia-phillies-poll-playoffs-8-18-10-game-losing-streak/",
            }
        ],
        "generated_at": "2026-04-25T11:30:00Z",
    }


def _temp_summary_dir(test_case: unittest.TestCase) -> Path:
    temp_dir = PROJECT_ROOT / "data" / "_test_temp" / f"state_summary_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    test_case.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
    return temp_dir


if __name__ == "__main__":
    unittest.main()
