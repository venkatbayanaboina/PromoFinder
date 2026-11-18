"""Deterministic sorting, rank assignment, and top-K selection."""
from ..validation.schemas import PromoRanking


def sort_and_assign_rank(rankings):
    ordered = sorted(rankings, key=lambda item: (-item.total_score, item.promo_id))
    return [item.model_copy(update={"rank": index}) for index, item in enumerate(ordered, 1)]


def select_top_k(rankings, k=10):
    if k < 0:
        raise ValueError("top K cannot be negative")
    return list(rankings[:k])
