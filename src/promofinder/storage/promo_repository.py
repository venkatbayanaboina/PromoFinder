"""Repository operations for execution, episode, promo, validation, and ranking records."""
import json
from datetime import datetime, timezone

from .database import Database
from ..validation.schemas import Episode, PromoCandidate, PromoRanking, ValidationResult


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class PromoRepository:
    def __init__(self, database):
        self.db = database if isinstance(database, Database) else Database(database)

    def begin_run(self, run_id, input_dir):
        self.db.execute(
            "INSERT INTO execution_runs(run_id, started_at, status, input_dir) VALUES(?,?,?,?)",
            (run_id, utc_now(), "running", str(input_dir)))

    def finish_run(self, run_id, status, summary):
        self.db.execute(
            "UPDATE execution_runs SET completed_at=?, status=?, summary_json=? WHERE run_id=?",
            (utc_now(), status, json.dumps(summary, ensure_ascii=False), run_id))

    def upsert_episode(self, episode: Episode, run_id=None, status="parsed", attempt_count=0,
                       errors=None, generation_config_sha256=""):
        self.db.execute(
            """INSERT INTO episodes(episode_id,source_file,source_sha256,generation_config_sha256,
               payload_json,last_status,last_run_id,attempt_count,errors_json,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(episode_id) DO UPDATE SET source_file=excluded.source_file,
               source_sha256=excluded.source_sha256,
               generation_config_sha256=excluded.generation_config_sha256,
               payload_json=excluded.payload_json,
               last_status=excluded.last_status,last_run_id=excluded.last_run_id,
               attempt_count=excluded.attempt_count,errors_json=excluded.errors_json,
               updated_at=excluded.updated_at""",
            (episode.episode_id, episode.source_file, episode.source_sha256,
             generation_config_sha256,
             episode.model_dump_json(), status, run_id, attempt_count,
             json.dumps(errors or [], ensure_ascii=False), utc_now()))

    def get_reusable_outcome(self, episode_id, source_sha256, generation_config_sha256=""):
        row = self.db.fetchone(
            """SELECT e.last_status,e.attempt_count,e.errors_json,c.promo_json
               FROM episodes e LEFT JOIN promo_candidates c ON c.episode_id=e.episode_id
               WHERE e.episode_id=? AND e.source_sha256=? AND e.generation_config_sha256=?
               AND e.last_status IN ('valid','no_candidate')
               ORDER BY c.created_at DESC LIMIT 1""",
            (episode_id, source_sha256, generation_config_sha256))
        if not row:
            return None
        return {
            "status": row["last_status"], "attempt_count": row["attempt_count"],
            "errors": json.loads(row["errors_json"] or "[]"),
            "promo": PromoCandidate.model_validate_json(row["promo_json"]) if row["promo_json"] else None,
        }

    def cache_signature_for_episode(self, episode_id):
        row = self.db.fetchone(
            "SELECT source_sha256,generation_config_sha256 FROM episodes WHERE episode_id=?",
            (episode_id,))
        return (row["source_sha256"], row["generation_config_sha256"]) if row else (None, None)

    def save_episode_outcome(self, episode, status, run_id, attempt_count, errors,
                             generation_config_sha256=""):
        self.upsert_episode(episode, run_id, status, attempt_count, errors,
                            generation_config_sha256)

    def save_candidate(self, promo: PromoCandidate, run_id):
        self.db.execute(
            """INSERT INTO promo_candidates(promo_id,episode_id,run_id,status,generation_attempt,
               promo_json,created_at) VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(promo_id) DO UPDATE SET episode_id=excluded.episode_id,
               run_id=excluded.run_id,status=excluded.status,
               generation_attempt=excluded.generation_attempt,promo_json=excluded.promo_json,
               created_at=excluded.created_at""",
            (promo.promo_id, promo.episode_id, run_id, promo.validation_status,
             promo.generation_attempt, promo.model_dump_json(), utc_now()))

    def record_attempt(self, run_id, episode_id, attempt_no, raw, validation: ValidationResult):
        attempt_id = self.db.execute(
            """INSERT OR REPLACE INTO validation_attempts(run_id,episode_id,attempt_no,
               raw_candidate_response,validation_json,is_valid,created_at) VALUES(?,?,?,?,?,?,?)""",
            (run_id, episode_id, attempt_no, raw,
             validation.model_dump_json(), int(validation.is_valid), utc_now()))
        for issue in validation.errors:
            self.db.execute(
                "INSERT INTO validation_errors(attempt_id,field,error) VALUES(?,?,?)",
                (attempt_id, issue.field, issue.error))

    def valid_candidates(self):
        rows = self.db.fetchall(
            "SELECT promo_json FROM promo_candidates WHERE status='valid' ORDER BY episode_id")
        return [PromoCandidate.model_validate_json(row["promo_json"]) for row in rows]

    def invalidate_candidates_for_episode(self, episode_id):
        self.db.execute(
            "UPDATE promo_candidates SET status='superseded' WHERE episode_id=? AND status='valid'",
            (episode_id,))

    def attempts_for_run(self, run_id):
        return self.db.fetchall(
            """SELECT attempt_id,episode_id,attempt_no,raw_candidate_response,
               validation_json,is_valid,created_at FROM validation_attempts
               WHERE run_id=? ORDER BY episode_id,attempt_no""", (run_id,))

    def episode_rows_for_run(self, run_id):
        return self.db.fetchall(
            "SELECT * FROM episodes WHERE last_run_id=? ORDER BY episode_id", (run_id,))

    def save_ranking(self, ranking: PromoRanking, run_id):
        self.db.execute(
            """INSERT INTO rankings(run_id,promo_id,total_score,rank,ranking_json,created_at)
               VALUES(?,?,?,?,?,?) ON CONFLICT(run_id,promo_id) DO UPDATE SET
               total_score=excluded.total_score,rank=excluded.rank,
               ranking_json=excluded.ranking_json,created_at=excluded.created_at""",
            (run_id, ranking.promo_id, ranking.total_score, ranking.rank,
             ranking.model_dump_json(), utc_now()))

    def rankings_for_run(self, run_id):
        rows = self.db.fetchall(
            "SELECT ranking_json FROM rankings WHERE run_id=? ORDER BY rank", (run_id,))
        return [PromoRanking.model_validate_json(row["ranking_json"]) for row in rows]

    def episodes_for_run(self, run_id):
        rows = self.db.fetchall(
            "SELECT * FROM episodes WHERE last_run_id=? ORDER BY episode_id", (run_id,))
        return rows

    def attempt_count_for_run(self, run_id):
        row = self.db.fetchone(
            "SELECT COUNT(*) AS n FROM validation_attempts WHERE run_id=?", (run_id,))
        return row["n"] if row else 0

    def run_record(self, run_id):
        return self.db.fetchone("SELECT * FROM execution_runs WHERE run_id=?", (run_id,))
