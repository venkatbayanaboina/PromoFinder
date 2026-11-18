"""SQLite schema and connection management."""
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS execution_runs (
  run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT,
  status TEXT NOT NULL, input_dir TEXT NOT NULL, summary_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS episodes (
  episode_id TEXT PRIMARY KEY, source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL,
  generation_config_sha256 TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL, last_status TEXT NOT NULL DEFAULT 'parsed',
  last_run_id TEXT, attempt_count INTEGER NOT NULL DEFAULT 0, errors_json TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS promo_candidates (
  promo_id TEXT PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
  run_id TEXT NOT NULL, status TEXT NOT NULL, generation_attempt INTEGER NOT NULL,
  promo_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS validation_attempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
  episode_id TEXT NOT NULL REFERENCES episodes(episode_id), attempt_no INTEGER NOT NULL,
  raw_candidate_response TEXT NOT NULL, validation_json TEXT NOT NULL,
  is_valid INTEGER NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(run_id, episode_id, attempt_no)
);
CREATE TABLE IF NOT EXISTS validation_errors (
  error_id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id INTEGER NOT NULL REFERENCES validation_attempts(attempt_id) ON DELETE CASCADE,
  field TEXT NOT NULL, error TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rankings (
  run_id TEXT NOT NULL, promo_id TEXT NOT NULL REFERENCES promo_candidates(promo_id),
  total_score REAL NOT NULL, rank INTEGER NOT NULL, ranking_json TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY(run_id, promo_id)
);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON promo_candidates(status);
CREATE INDEX IF NOT EXISTS idx_attempts_episode ON validation_attempts(episode_id, attempt_no);
CREATE INDEX IF NOT EXISTS idx_rankings_run ON rankings(run_id, rank);
"""


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(str(self.path), timeout=30,
                                     check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(episodes)")}
            if "generation_config_sha256" not in columns:
                connection.execute(
                    "ALTER TABLE episodes ADD COLUMN generation_config_sha256 TEXT NOT NULL DEFAULT ''")

    def execute(self, sql, params=()):
        with self.connect() as connection:
            cursor = connection.execute(sql, params)
            return cursor.lastrowid

    def fetchone(self, sql, params=()):
        with self.connect() as connection:
            return connection.execute(sql, params).fetchone()

    def fetchall(self, sql, params=()):
        with self.connect() as connection:
            return connection.execute(sql, params).fetchall()
