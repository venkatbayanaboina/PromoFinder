"""Run the complete PromoFinder ingestion, generation, validation and ranking flow."""
import argparse
import hashlib
import json
import logging
import sys
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .generation.llm_client import LLMClient, PendingResponse
from .generation.promo_generator import PromoGenerator
from .generation.retry_handler import RetryHandler
from .ingestion.episode_parser import parse_episode
from .ingestion.file_loader import discover_files
from .ingestion.text_extractor import extract_text
from .ranking.ranking_engine import RankingEngine
from .ranking.top_k_selector import select_top_k
from .reporting.report_generator import generate_report
from .reporting.statistics import build_statistics
from .storage.database import Database
from .storage.json_exporter import export_csv, write_json
from .storage.promo_repository import PromoRepository
from .settings import load_settings
from .utils.logger import get_logger
from .validation.semantic_validator import SemanticValidator
from .validation.validation_engine import ValidationEngine

logger = logging.getLogger("promofinder")


def _generation_profile_hash(settings):
    def model_part(value):
        return {"provider": value.provider, "model": value.model,
                "base_url": value.base_url, "temperature": value.temperature}

    prompt_names = ("generation_system.txt", "generation_examples.json",
                    "regeneration_system.txt", "semantic_validation.txt")
    prompt_hashes = {}
    for name in prompt_names:
        data = (settings.prompts_dir / name).read_bytes()
        prompt_hashes[name] = hashlib.sha256(data).hexdigest()
    profile = {
        "candidate_model": model_part(settings.candidate_model),
        "semantic_model": model_part(settings.ranking_model),
        "min_duration_seconds": settings.min_duration_seconds,
        "max_duration_seconds": settings.max_duration_seconds,
        "hook_window_seconds": settings.hook_window_seconds,
        "max_validation_retries": settings.max_validation_retries,
        "prompts": prompt_hashes,
    }
    return hashlib.sha256(json.dumps(profile, sort_keys=True).encode("utf-8")).hexdigest()


def _parse_inputs(input_dir):
    paths = discover_files(input_dir)
    episodes = []
    errors = []
    seen = set()
    for index, path in enumerate(paths, 1):
        try:
            episode = parse_episode(extract_text(path), str(path), index)
            if episode.episode_id in seen:
                raise ValueError("duplicate episode ID {}".format(episode.episode_id))
            if not episode.blocks:
                raise ValueError("no timestamped screenplay blocks were parsed")
            seen.add(episode.episode_id)
            episodes.append(episode)
        except Exception as exc:
            errors.append({"source_file": str(path), "error": str(exc)})
            logger.exception("Could not parse screenplay %s", path)
    return sorted(episodes, key=lambda item: item.episode_id), errors


def _export_run(settings, run_id, status, episodes, outcomes, rankings,
                ranking_errors, input_errors, attempt_count, top_k):
    output = settings.output_dir
    output.mkdir(parents=True, exist_ok=True)
    write_json(settings.processed_dir / "episodes.json",
               [episode.model_dump(mode="json") for episode in episodes])
    promo_by_id = {item["promo"].promo_id: item["promo"] for item in outcomes
                   if item.get("promo") is not None}
    valid_promos = [item["promo"] for item in outcomes
                    if item.get("status") == "valid" and item.get("promo") is not None]
    failed = [{"episode_id": item["episode"].episode_id,
               "source_file": item["episode"].source_file,
               "status": item.get("status"), "attempts": item.get("attempts", 0),
               "errors": item.get("errors", []),
               "no_candidate_reason": item.get("no_candidate_reason", "")}
              for item in outcomes if item.get("status") in ("failed", "no_candidate")]
    candidate_attempts = [{
        "episode_id": row["episode_id"], "attempt": row["attempt_no"] + 1,
        "is_valid": bool(row["is_valid"]),
        "validation": json.loads(row["validation_json"]),
        "raw_model_response": row["raw_candidate_response"],
    } for row in outcomes[0].get("attempt_rows", [])] if outcomes else []
    write_json(output / "candidates.json", {
        "run_id": run_id, "attempts": candidate_attempts,
        "note": "Every candidate-generation attempt is preserved, including invalid responses.",
    })
    write_json(output / "valid_promos.json", [item.model_dump(mode="json") for item in valid_promos])
    write_json(output / "failed_episodes.json", failed)
    write_json(output / "rankings.json", [item.model_dump(mode="json") for item in rankings])
    write_json(output / "top_promos.json", [item.model_dump(mode="json") for item in top_k])
    write_json(output / "ranking_errors.json", ranking_errors)
    export_csv(output / "rankings.csv", rankings, promo_by_id)
    summary = build_statistics(
        episodes, outcomes, rankings, attempt_count,
        input_errors=input_errors, ranking_errors=ranking_errors)
    summary["top_promo_ids"] = [item.promo_id for item in top_k]
    generate_report(settings.reports_dir, run_id, status, summary, rankings, top_k)
    return summary


def run_pipeline(settings=None, input_dir=None, top_k=None, force_reprocess=False,
                 progress_callback=None):
    settings = settings or load_settings()
    if input_dir is not None:
        path = Path(input_dir)
        settings = replace(settings, input_dir=path if path.is_absolute() else settings.root / path)
    selected_top_k = settings.top_k if top_k is None else top_k
    if selected_top_k < 0:
        raise ValueError("top K cannot be negative")
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    logger = get_logger("promofinder", settings.output_dir)

    run_id = "run-{}-{}".format(
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), uuid.uuid4().hex[:8])
    repository = PromoRepository(Database(settings.database_path))
    repository.begin_run(run_id, settings.input_dir)
    episodes = []
    input_errors = []
    outcomes = []
    rankings = []
    ranking_errors = []
    attempt_count = 0
    status = "completed"

    def notify(stage, current, total, detail):
        if progress_callback:
            progress_callback({"stage": stage, "current": current,
                               "total": total, "detail": detail})

    try:
        notify("parse", 0, 1, "Reading timestamped screenplays")
        episodes, input_errors = _parse_inputs(settings.input_dir)
        notify("parse", 1, 1, "Loaded {} episode scripts".format(len(episodes)))
        generation_profile = _generation_profile_hash(settings)
        client = LLMClient(settings.output_dir, run_id=run_id,
                           prompts_dir=settings.prompts_dir,
                           force_refresh=force_reprocess)
        generator = PromoGenerator(client, settings)
        semantic_validator = SemanticValidator(client, settings)
        validation_engine = ValidationEngine(settings, semantic_validator)
        retry_handler = RetryHandler(
            generator, validation_engine, repository, settings.max_validation_retries,
            generation_config_sha256=generation_profile)

        for index, episode in enumerate(episodes, 1):
            notify("generation", index - 1, len(episodes),
                   "Selecting a promo for {}".format(episode.episode_id))
            old_hash, old_profile = repository.cache_signature_for_episode(episode.episode_id)
            if (force_reprocess or (old_hash and old_hash != episode.source_sha256)
                    or (old_hash and old_profile != generation_profile)):
                repository.invalidate_candidates_for_episode(episode.episode_id)
            reusable = None if force_reprocess else repository.get_reusable_outcome(
                episode.episode_id, episode.source_sha256, generation_profile)
            if reusable:
                repository.save_episode_outcome(
                    episode, reusable["status"], run_id, reusable["attempt_count"],
                    reusable["errors"], generation_profile)
                outcomes.append({"episode": episode, "status": reusable["status"],
                                 "promo": reusable["promo"], "attempts": 0,
                                 "errors": reusable["errors"], "reused": True})
                notify("generation", index, len(episodes),
                       "{} reused from the same model profile".format(episode.episode_id))
                continue

            repository.upsert_episode(episode, run_id=run_id, status="parsed",
                                      generation_config_sha256=generation_profile)
            result = retry_handler.generate_valid_promo(episode, run_id)
            attempt_count += result.attempts
            outcomes.append({"episode": episode, "status": result.status,
                             "promo": result.promo, "attempts": result.attempts,
                             "errors": result.errors,
                             "no_candidate_reason": result.no_candidate_reason})
            notify("generation", index, len(episodes),
                   "{}: {}".format(episode.episode_id, result.status))

        valid_candidates = [item["promo"] for item in outcomes
                            if item.get("status") == "valid" and item.get("promo")]
        notify("ranking", 0, len(valid_candidates),
               "Scoring {} validated promos".format(len(valid_candidates)))
        ranker = RankingEngine(client, repository, settings)
        rankings, ranking_errors = ranker.rank_all(
            valid_candidates, episodes, run_id,
            progress_callback=lambda current, total, detail: notify(
                "ranking", current, total, "Ranking {}".format(detail)))
    except PendingResponse as exc:
        status = "pending_responses"
        logger.info("Waiting for model response %s; edit data/prompts/pending_requests.jsonl and rerun",
                    exc.request_id)
    except Exception as exc:
        status = "failed"
        logger.exception("PromoFinder run failed")
        input_errors.append({"stage": "pipeline", "error": str(exc)})
    finally:
        notify("complete", 1, 1, "Run {}".format(status))
        attempt_rows = repository.attempts_for_run(run_id)
        for item in outcomes:
            item["attempt_rows"] = attempt_rows
        summary = _export_run(
            settings, run_id, status, episodes, outcomes, rankings,
            ranking_errors, input_errors, attempt_count, select_top_k(rankings, selected_top_k))
        repository.finish_run(run_id, status, summary)

    return {"run_id": run_id, "status": status, "summary": summary,
            "rankings": rankings}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find and rank promo moments in screenplays")
    parser.add_argument("--input-dir", help="Override the configured screenplay directory")
    parser.add_argument("--top-k", type=int, help="Override the configured shortlist size")
    args = parser.parse_args(argv)
    result = run_pipeline(input_dir=args.input_dir, top_k=args.top_k)
    print(json.dumps({"run_id": result["run_id"], "status": result["status"],
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
    if result["status"] == "failed":
        return 1
    if result["status"] == "pending_responses":
        print("Add the model response to data/prompts/pending_requests.jsonl, then rerun.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
