from promofinder.validation.schemas import PromoDraft, CandidateSegmentDraft
from promofinder.validation.timestamp_validator import resolve_candidate


def draft(sample_episode):
    return PromoDraft(
        status="candidate",
        segments=[CandidateSegmentDraft(
            start_block_id=sample_episode.blocks[0].block_id,
            end_block_id=sample_episode.blocks[1].block_id,
            reason="Escalating betrayal.")],
        hook_block_id=sample_episode.blocks[0].block_id,
        cliffhanger_block_id=sample_episode.blocks[1].block_id,
        explanation="A betrayal creates an unresolved question.")


def test_resolves_only_source_supported_timestamps(sample_episode):
    promo, issues = resolve_candidate(draft(sample_episode), sample_episode, 0)
    assert not issues
    assert promo.duration_seconds == 25
    assert promo.segments[0].start_timestamp == "00:00.00"
    assert promo.segments[0].end_timestamp == "00:25.00"


def test_missing_block_timestamp_reference_is_rejected(sample_episode):
    candidate = draft(sample_episode)
    candidate.segments[0].start_block_id = "not-a-real-block"
    promo, issues = resolve_candidate(candidate, sample_episode, 0)
    assert promo is None
    assert any("not present" in issue.error for issue in issues)
