"""Regenerate failed candidates with concrete validation feedback."""
from typing import List, Optional

from .promo_generator import CandidateResponseError
from ..validation.schemas import PromoCandidate, ValidationIssue, ValidationResult


class RetryOutcome:
    def __init__(self, status, promo=None, attempts=0, errors=None, no_candidate_reason=""):
        self.status = status
        self.promo = promo
        self.attempts = attempts
        self.errors = errors or []
        self.no_candidate_reason = no_candidate_reason


class RetryHandler:
    def __init__(self, generator, validation_engine, repository, max_retries=2,
                 generation_config_sha256=""):
        self.generator = generator
        self.validation_engine = validation_engine
        self.repository = repository
        self.max_retries = max_retries
        self.generation_config_sha256 = generation_config_sha256

    def generate_valid_promo(self, episode, run_id):
        errors: List[str] = []
        for attempt in range(self.max_retries + 1):
            raw = ""
            try:
                draft, raw = self.generator.generate(episode, attempt, errors)
                if draft.status == "no_valid_candidate":
                    self.repository.record_attempt(
                        run_id, episode.episode_id, attempt, raw,
                        ValidationResult(is_valid=False, errors=[ValidationIssue(
                            field="status", error=draft.reason or "model found no suitable promo")]))
                    self.repository.save_episode_outcome(
                        episode, "no_candidate", run_id=run_id, attempt_count=attempt + 1,
                        errors=[draft.reason or "No valid candidate identified."],
                        generation_config_sha256=self.generation_config_sha256)
                    return RetryOutcome("no_candidate", attempts=attempt + 1,
                                        no_candidate_reason=draft.reason)

                result = self.validation_engine.validate(
                    draft=draft, episode=episode, attempt=attempt, run_id=run_id)
                self.repository.record_attempt(run_id, episode.episode_id, attempt, raw, result)
                if result.is_valid and result.promo:
                    self.repository.save_candidate(result.promo, run_id)
                    self.repository.save_episode_outcome(
                        episode, "valid", run_id=run_id, attempt_count=attempt + 1, errors=[],
                        generation_config_sha256=self.generation_config_sha256)
                    return RetryOutcome("valid", result.promo, attempts=attempt + 1)
                errors = ["{}: {}".format(issue.field, issue.error) for issue in result.errors]
            except CandidateResponseError as exc:
                raw = exc.raw
                errors = ["candidate_response: {}".format(exc)]
                invalid = ValidationResult(is_valid=False, errors=[ValidationIssue(
                    field="candidate_response", error=str(exc))])
                self.repository.record_attempt(run_id, episode.episode_id, attempt, raw, invalid)

        self.repository.save_episode_outcome(
            episode, "failed", run_id=run_id, attempt_count=self.max_retries + 1,
            errors=errors or ["Retry limit reached without a valid promo."],
            generation_config_sha256=self.generation_config_sha256)
        return RetryOutcome("failed", attempts=self.max_retries + 1, errors=errors)
