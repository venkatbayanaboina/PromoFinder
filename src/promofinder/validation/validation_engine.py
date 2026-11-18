"""Combine hard timestamp/duration checks with semantic review."""
from ..generation.prompt_builder import selected_transcript
from .duration_validator import validate_duration
from .schemas import ValidationIssue, ValidationResult
from .timestamp_validator import resolve_candidate


class ValidationEngine:
    def __init__(self, settings, semantic_validator):
        self.settings = settings
        self.semantic_validator = semantic_validator

    def validate(self, draft, episode, attempt, run_id):
        promo, errors = resolve_candidate(
            draft, episode, attempt, self.settings.hook_window_seconds)
        if promo is None:
            return ValidationResult(is_valid=False, errors=errors)
        errors = validate_duration(
            promo.duration_seconds, self.settings.min_duration_seconds,
            self.settings.max_duration_seconds)
        if errors:
            return ValidationResult(is_valid=False, errors=errors, promo=promo)
        try:
            review, _, accepted = self.semantic_validator.validate(promo, episode, attempt)
        except ValueError as exc:
            return ValidationResult(is_valid=False, errors=[ValidationIssue(
                field="semantic_review", error="Invalid semantic response: {}".format(exc))], promo=promo)
        if not accepted:
            details = review.concerns or [review.explanation]
            errors = [ValidationIssue(field="semantic_review", error=detail) for detail in details]
            promo.validation_status = "failed"
            return ValidationResult(is_valid=False, errors=errors, promo=promo)
        return ValidationResult(is_valid=True, errors=[], promo=promo)
