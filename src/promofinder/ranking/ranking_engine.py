"""Ask a ranking model to score each valid promo, then calculate totals in Python."""
import logging

from ..utils.json_utils import extract_json
from ..generation.llm_client import PendingResponse
from ..validation.schemas import PromoRanking
from .ranking_prompt import build_ranking_prompt
from .score_validator import validate_ranking
from .top_k_selector import sort_and_assign_rank

logger = logging.getLogger(__name__)


class RankingEngine:
    def __init__(self, llm_client, repository, settings):
        self.llm_client = llm_client
        self.repository = repository
        self.settings = settings

    def rank_all(self, candidates, episodes, run_id, progress_callback=None):
        episode_by_id = {episode.episode_id: episode for episode in episodes}
        rankings = []
        errors = []
        for index, candidate in enumerate(candidates, 1):
            episode = episode_by_id.get(candidate.episode_id)
            if episode is None:
                errors.append({"promo_id": candidate.promo_id,
                               "error": "source episode is missing"})
                continue
            prompt = build_ranking_prompt(
                candidate, episode, self.settings.prompts_dir,
                self.settings.scoring_weights)
            try:
                raw = self.llm_client.complete(
                    prompt=prompt, stage="ranking", key=candidate.promo_id,
                    attempt=0, model_settings=self.settings.ranking_model)
                ranking = validate_ranking(
                    extract_json(raw), candidate.promo_id, candidate.episode_id,
                    self.settings.scoring_weights)
                rankings.append(ranking)
            except PendingResponse:
                raise
            except Exception as exc:
                logger.exception("Could not rank %s", candidate.promo_id)
                errors.append({"promo_id": candidate.promo_id, "error": str(exc)})
            if progress_callback:
                progress_callback(index, len(candidates), candidate.promo_id)

        ordered = sort_and_assign_rank(rankings)
        for item in ordered:
            self.repository.save_ranking(item, run_id)
        return ordered, errors
