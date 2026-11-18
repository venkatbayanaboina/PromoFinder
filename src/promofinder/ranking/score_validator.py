"""Validate per-dimension model scores and calculate deterministic totals."""
from typing import Dict

from ..validation.schemas import PromoRanking, RankingScores


def calculate_weighted_total(scores: RankingScores, weights: Dict[str, int]) -> float:
    values = {
        "hook_strength": scores.hook_strength,
        "cliffhanger_strength": scores.cliffhanger_strength,
        "standalone_clarity": scores.standalone_clarity,
        "emotional_impact": scores.emotional_impact,
        "duration_and_flow": scores.duration_and_flow,
    }
    if set(values) != set(weights) or sum(weights.values()) != 100:
        raise ValueError("Scoring weights must define all five criteria and total 100")
    return round(sum((values[key] / 5.0) * weight for key, weight in weights.items()), 2)


def validate_ranking(payload, promo_id, episode_id, weights, rank=1):
    scores = RankingScores.model_validate(payload)
    total = calculate_weighted_total(scores, weights)
    return PromoRanking(
        promo_id=promo_id, episode_id=episode_id, scores=scores,
        total_score=total, ranking_reason=scores.justification,
        weaknesses=scores.weaknesses, rank=rank)
