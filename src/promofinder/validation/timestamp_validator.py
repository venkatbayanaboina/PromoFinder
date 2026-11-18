"""Resolve model-selected block IDs to source-backed timestamps."""
from ..utils.time_utils import format_timestamp
from .schemas import PromoCandidate, PromoSegment, ValidationIssue


def resolve_candidate(draft, episode, attempt, hook_window_seconds=3.0):
    errors = []
    if not draft.segments:
        return None, [ValidationIssue(field="segments", error="At least one segment is required")]
    blocks = {block.block_id: (index, block) for index, block in enumerate(episode.blocks)}
    resolved = []
    previous_end_index = -1

    for segment_index, draft_segment in enumerate(draft.segments):
        start_entry = blocks.get(draft_segment.start_block_id)
        end_entry = blocks.get(draft_segment.end_block_id)
        if start_entry is None or end_entry is None:
            errors.append(ValidationIssue(
                field="segments[{}]".format(segment_index),
                error="Start or end block ID is not present in this screenplay"))
            continue
        start_index, start_block = start_entry
        end_index, end_block = end_entry
        if start_block.episode_id != episode.episode_id or end_block.episode_id != episode.episode_id:
            errors.append(ValidationIssue(
                field="segments[{}].episode_id".format(segment_index),
                error="Every segment must belong to the supplied episode"))
        if end_index < start_index:
            errors.append(ValidationIssue(
                field="segments[{}]".format(segment_index), error="Segment end precedes its start"))
            continue
        if start_index <= previous_end_index:
            errors.append(ValidationIssue(
                field="segments[{}]".format(segment_index),
                error="Segments must be in episode order and cannot overlap or repeat blocks"))
        if end_block.end_seconds <= start_block.start_seconds:
            errors.append(ValidationIssue(
                field="segments[{}]".format(segment_index),
                error="Segment end timestamp must be after its start timestamp"))
        previous_end_index = max(previous_end_index, end_index)
        resolved.append((start_index, end_index, start_block, end_block,
                         draft_segment.reason))

    hook_entry = blocks.get(draft.hook_block_id)
    cliff_entry = blocks.get(draft.cliffhanger_block_id)
    if hook_entry is None:
        errors.append(ValidationIssue(field="hook_block_id", error="Hook block ID is not in the episode"))
    if cliff_entry is None:
        errors.append(ValidationIssue(
            field="cliffhanger_block_id", error="Cliffhanger block ID is not in the episode"))
    if len(resolved) != len(draft.segments):
        return None, errors

    if hook_entry is not None:
        hook_index, hook_block = hook_entry
        first_start = resolved[0][2]
        first_end_index = resolved[0][1]
        if not resolved[0][0] <= hook_index <= first_end_index:
            errors.append(ValidationIssue(
                field="hook_block_id", error="Hook must be inside the first selected segment"))
        elif hook_block.start_seconds - first_start.start_seconds > hook_window_seconds:
            errors.append(ValidationIssue(
                field="hook_block_id",
                error="Hook starts {:.2f}s after the promo start; maximum is {:.2f}s".format(
                    hook_block.start_seconds - first_start.start_seconds, hook_window_seconds)))
    if cliff_entry is not None:
        cliff_index, _ = cliff_entry
        last_start_index, last_end_index = resolved[-1][0], resolved[-1][1]
        if not last_start_index <= cliff_index <= last_end_index:
            errors.append(ValidationIssue(
                field="cliffhanger_block_id", error="Cliffhanger must be inside the last selected segment"))

    if errors:
        return None, errors

    segments = []
    for _, _, start_block, end_block, reason in resolved:
        segments.append(PromoSegment(
            episode_id=episode.episode_id, scene_id=start_block.scene_id,
            start_block_id=start_block.block_id, end_block_id=end_block.block_id,
            start_timestamp=format_timestamp(start_block.start_seconds),
            end_timestamp=format_timestamp(end_block.end_seconds),
            start_seconds=start_block.start_seconds, end_seconds=end_block.end_seconds,
            reason=reason))
    duration = sum(segment.end_seconds - segment.start_seconds for segment in segments)
    hook_text = hook_entry[1].text if hook_entry else ""
    cliff_text = cliff_entry[1].text if cliff_entry else ""
    promo = PromoCandidate(
        promo_id="PROMO_{}".format(episode.episode_id), episode_id=episode.episode_id,
        segments=segments, duration_seconds=round(duration, 2),
        hook_block_id=draft.hook_block_id, cliffhanger_block_id=draft.cliffhanger_block_id,
        hook=hook_text, cliffhanger=cliff_text, explanation=draft.explanation,
        validation_status="valid", generation_attempt=attempt)
    return promo, []
