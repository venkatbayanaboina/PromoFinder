import pytest

from promofinder.ranking.score_validator import calculate_weighted_total, validate_ranking
from promofinder.ranking.top_k_selector import select_top_k, sort_and_assign_rank
from promofinder.validation.schemas import RankingScores

WEIGHTS = {
    "hook_strength": 30, "cliffhanger_strength": 25,
    "standalone_clarity": 20, "emotional_impact": 15, "duration_and_flow": 10,
}


def test_weighted_scores_are_calculated_and_sorted_in_python():
    scores = RankingScores(hook_strength=5, cliffhanger_strength=4,
                           standalone_clarity=3, emotional_impact=2,
                           duration_and_flow=1, justification="Good opening.")
    assert calculate_weighted_total(scores, WEIGHTS) == 70
    high = validate_ranking({**scores.model_dump(), "hook_strength": 5}, "P1", "E1", WEIGHTS)
    low = validate_ranking({**scores.model_dump(), "hook_strength": 1}, "P2", "E2", WEIGHTS)
    ordered = sort_and_assign_rank([low, high])
    assert [item.rank for item in ordered] == [1, 2]
    assert select_top_k(ordered, 1) == ordered[:1]


def test_scores_outside_range_and_bad_weights_are_rejected():
    with pytest.raises(ValueError):
        RankingScores(hook_strength=6, cliffhanger_strength=4, standalone_clarity=3,
                      emotional_impact=2, duration_and_flow=1, justification="x")
    with pytest.raises(ValueError, match="all five"):
        calculate_weighted_total(RankingScores(
            hook_strength=1, cliffhanger_strength=1, standalone_clarity=1,
            emotional_impact=1, duration_and_flow=1, justification="x"), {"wrong": 100})
