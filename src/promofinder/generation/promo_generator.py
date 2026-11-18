"""Generate one structured promo proposal for an episode."""
from ..utils.json_utils import extract_json
from ..validation.schemas import PromoDraft
from .prompt_builder import build_generation_prompt


class CandidateResponseError(ValueError):
    def __init__(self, message, raw=""):
        self.raw = raw
        super().__init__(message)


class PromoGenerator:
    def __init__(self, llm_client, settings):
        self.llm_client = llm_client
        self.settings = settings

    def generate(self, episode, attempt, previous_errors=None):
        prompt = build_generation_prompt(
            episode, self.settings.prompts_dir, previous_errors or [])
        raw = self.llm_client.complete(
            prompt=prompt, stage="generation", key=episode.episode_id,
            attempt=attempt, model_settings=self.settings.candidate_model)
        try:
            payload = extract_json(raw)
            draft = PromoDraft.model_validate(payload)
        except Exception as exc:
            raise CandidateResponseError(
                "candidate response schema/JSON error: {}".format(exc), raw=raw) from exc
        return draft, raw
