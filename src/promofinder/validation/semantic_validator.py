"""AI-based quality/source-match check after deterministic validation."""
from ..generation.prompt_builder import build_semantic_prompt
from ..utils.json_utils import extract_json
from .schemas import SemanticReview


class SemanticValidator:
    def __init__(self, llm_client, settings):
        self.llm_client = llm_client
        self.settings = settings

    def validate(self, candidate, episode, attempt):
        prompt = build_semantic_prompt(candidate, episode, self.settings.prompts_dir)
        raw = self.llm_client.complete(
            prompt=prompt, stage="semantic_validation", key=candidate.promo_id,
            attempt=attempt, model_settings=self.settings.ranking_model)
        review = SemanticReview.model_validate(extract_json(raw))
        threshold_ok = (review.hook_score >= 3 and review.cliffhanger_score >= 3
                        and review.standalone_score >= 3)
        return review, raw, review.is_valid and review.matches_source and threshold_ok
