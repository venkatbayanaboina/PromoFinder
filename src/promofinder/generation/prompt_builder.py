"""Build prompts from checked-in prompt instructions and parsed screenplay data."""
import json
from pathlib import Path

from ..utils.time_utils import format_timestamp


def _prompt_text(prompts_dir, filename):
    return (Path(prompts_dir) / filename).read_text(encoding="utf-8").strip()


def format_episode_blocks(episode):
    lines = []
    for block in episode.blocks:
        speaker = " [{}]".format(block.speaker) if block.speaker else ""
        lines.append("{} | {}{} | {}-{} | {}".format(
            block.block_id, block.block_type, speaker,
            format_timestamp(block.start_seconds), format_timestamp(block.end_seconds),
            block.text.replace("\n", " ")))
    return "\n".join(lines)


def build_generation_prompt(episode, prompts_dir, previous_errors=None):
    system = _prompt_text(prompts_dir, "generation_system.txt")
    examples = json.loads(_prompt_text(prompts_dir, "generation_examples.json"))
    blocks = format_episode_blocks(episode)
    correction = ""
    if previous_errors:
        correction = "\n\nPREVIOUS VALIDATION ERRORS TO FIX:\n- " + "\n- ".join(previous_errors)
        system = _prompt_text(prompts_dir, "regeneration_system.txt") + "\n\n" + system
    return ("SYSTEM INSTRUCTIONS\n{}\n\nSTRUCTURE EXAMPLES (placeholders only; use IDs from this episode)\n{}\n\n"
            "EPISODE {}\nLOGLINE: {}\nCONTINUITY: {}\n\n"
            "SOURCE BLOCKS (actual screenplay content)\n{}{}\n\n"
            "Required candidate JSON fields: status, segments (start_block_id, end_block_id, reason), "
            "hook_block_id, cliffhanger_block_id, explanation. For no candidate use status and reason.").format(
        system, json.dumps(examples, ensure_ascii=False), episode.episode_id,
        episode.logline, episode.continuity_notes, blocks, correction)


def selected_transcript(candidate, episode):
    by_id = {block.block_id: block for block in episode.blocks}
    lines = []
    for part, segment in enumerate(candidate.segments, 1):
        start = by_id[segment.start_block_id]
        end = by_id[segment.end_block_id]
        start_index = episode.blocks.index(start)
        end_index = episode.blocks.index(end)
        lines.append("--- SEGMENT {} ---".format(part))
        for block in episode.blocks[start_index:end_index + 1]:
            who = "{}: ".format(block.speaker) if block.speaker else ""
            lines.append("[{}] {}{}".format(format_timestamp(block.start_seconds), who, block.text))
    return "\n".join(lines)


def build_semantic_prompt(candidate, episode, prompts_dir):
    rules = _prompt_text(prompts_dir, "semantic_validation.txt")
    return "{}\n\nPROMO METADATA\n{}\n\nSCREENPLAY EXCERPTS\n{}".format(
        rules, candidate.model_dump_json(indent=2), selected_transcript(candidate, episode))


def build_regeneration_prompt(episode, prompts_dir, previous_errors):
    return build_generation_prompt(episode, prompts_dir, previous_errors)
