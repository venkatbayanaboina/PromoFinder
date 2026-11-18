"""Build the per-promo ranking request without sending a full screenplay."""
import json
from pathlib import Path

from ..generation.prompt_builder import selected_transcript


def build_ranking_prompt(candidate, episode, prompts_dir, scoring_weights):
    instructions = (Path(prompts_dir) / "ranking_system.txt").read_text(encoding="utf-8")
    context = {
        "promo_id": candidate.promo_id,
        "episode_id": candidate.episode_id,
        "duration_seconds": candidate.duration_seconds,
        "segments": [segment.model_dump() for segment in candidate.segments],
        "hook": candidate.hook,
        "cliffhanger": candidate.cliffhanger,
        "explanation": candidate.explanation,
    }
    return ("{}\n\nSCORING WEIGHTS (Python calculates the total out of 100):\n{}\n\n"
            "VALIDATED PROMO\n{}\n\nSELECTED SCREENPLAY EXCERPTS\n{}").format(
        instructions, json.dumps(scoring_weights), json.dumps(context, ensure_ascii=False),
        selected_transcript(candidate, episode))
