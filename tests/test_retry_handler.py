from promofinder.generation.retry_handler import RetryHandler
from promofinder.validation.schemas import (PromoCandidate, PromoDraft, PromoSegment,
                                            CandidateSegmentDraft, ValidationIssue,
                                            ValidationResult)


class Generator:
    def __init__(self):
        self.calls = 0

    def generate(self, episode, attempt, errors):
        self.calls += 1
        draft = PromoDraft(
            status="candidate",
            segments=[CandidateSegmentDraft(start_block_id="a", end_block_id="b")],
            hook_block_id="a", cliffhanger_block_id="b", explanation="test")
        return draft, "response-{}".format(attempt)


class Validation:
    def __init__(self, succeeds_on=1):
        self.calls = 0
        self.succeeds_on = succeeds_on

    def validate(self, **kwargs):
        self.calls += 1
        if self.calls <= self.succeeds_on:
            return ValidationResult(is_valid=False, errors=[ValidationIssue(
                field="duration", error="Must be between 20 and 60 seconds")])
        promo = PromoCandidate(
            promo_id="PROMO_EP_001", episode_id="EP_001",
            segments=[PromoSegment(episode_id="EP_001", scene_id="SC_001",
                                  start_block_id="a", end_block_id="b",
                                  start_timestamp="00:00.00", end_timestamp="00:25.00",
                                  start_seconds=0, end_seconds=25)],
            duration_seconds=25, hook_block_id="a", cliffhanger_block_id="b",
            hook="A hook", cliffhanger="A turn", explanation="A reason",
            validation_status="valid", generation_attempt=kwargs["attempt"])
        return ValidationResult(is_valid=True, promo=promo)


class Repository:
    def __init__(self):
        self.attempts = []
        self.saved = []

    def record_attempt(self, *args):
        self.attempts.append(args)

    def save_candidate(self, promo, run_id):
        self.saved.append(promo)

    def save_episode_outcome(self, *args, **kwargs):
        pass


def test_first_attempt_fails_second_passes(sample_episode):
    generator, validation, repository = Generator(), Validation(succeeds_on=1), Repository()
    result = RetryHandler(generator, validation, repository, max_retries=2).generate_valid_promo(
        sample_episode, "run-1")
    assert result.status == "valid"
    assert result.attempts == 2
    assert generator.calls == 2
    assert len(repository.attempts) == 2
    assert len(repository.saved) == 1


def test_all_three_attempts_fail_and_episode_is_marked_failed(sample_episode):
    generator, validation, repository = Generator(), Validation(succeeds_on=3), Repository()
    result = RetryHandler(generator, validation, repository, max_retries=2).generate_valid_promo(
        sample_episode, "run-2")
    assert result.status == "failed"
    assert result.attempts == 3
    assert generator.calls == 3
    assert len(repository.attempts) == 3
