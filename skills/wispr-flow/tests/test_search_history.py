"""Synthetic-only tests for Wispr Flow search; never reads a real database."""
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

script = Path(__file__).resolve().parents[1] / "scripts" / "search-history.py"
spec = importlib.util.spec_from_file_location("search_history", script)
search_history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search_history)


class SearchHistoryTest(unittest.TestCase):
    def setUp(self):
        self.previous_db_path = search_history.DB_PATH
        temp_root = Path(__file__).resolve().parents[4] / "verification" / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=temp_root)
        self.database = Path(self.temp_dir.name) / "synthetic.sqlite"
        search_history.DB_PATH = self.database
        conn = sqlite3.connect(self.database)
        try:
            conn.execute(
                "CREATE TABLE History "
                "(timestamp TEXT, app TEXT, formattedText TEXT, numWords INTEGER)"
            )
            conn.executemany(
                "INSERT INTO History VALUES (?, ?, ?, ?)",
                [
                    ("2026-10-01 12:00:00", "synthetic_app", "literal 100% complete", 3),
                    ("2026-10-01 12:01:00", "synthetic_app", "literal 100 percent", 3),
                    ("2026-10-01 12:02:00", "syntheticXapp", "underscore marker", 2),
                    ("2026-10-01 12:03:00", "synthetic_app", "path C:\\temp", 2),
                    ("2026-10-01 12:04:00", "synthetic_app", "O'Reilly notes", 2),
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        search_history.DB_PATH = self.previous_db_path
        self.temp_dir.cleanup()

    def texts(self, query, **kwargs):
        return [row[2] for row in search_history.search(query, **kwargs)]

    def test_percent_is_literal(self):
        self.assertEqual(self.texts("100%"), ["literal 100% complete"])

    def test_underscore_is_literal_in_app_filter(self):
        self.assertEqual(
            self.texts("marker", app="synthetic_app"),
            [],
        )
        self.assertEqual(
            self.texts("marker", app="syntheticXapp"),
            ["underscore marker"],
        )

    def test_backslash_and_quotes_are_literal(self):
        self.assertEqual(self.texts("C:\\temp"), ["path C:\\temp"])
        self.assertEqual(self.texts("O'Reilly"), ["O'Reilly notes"])


if __name__ == "__main__":
    unittest.main()
