"""Summarize execution outcomes using persisted, current-run data."""


def build_statistics(episodes, outcomes, rankings, candidate_attempt_count,
                     input_errors=None, ranking_errors=None):
    status_counts = {"valid": 0, "no_candidate": 0, "failed": 0, "pending": 0}
    for outcome in outcomes:
        status = outcome.get("status", "failed")
        status_counts[status] = status_counts.get(status, 0) + 1
    distinct_attempted_episodes = len({item["episode"].episode_id for item in outcomes
                                       if item.get("attempts", 0) > 0})
    return {
        "total_episodes_discovered": len(episodes) + len(input_errors or []),
        "total_episodes_parsed": len(episodes),
        "total_episodes_processed": len(outcomes),
        "valid_promos": status_counts["valid"],
        "no_candidate_episodes": status_counts["no_candidate"],
        "failed_after_retries": status_counts["failed"],
        "failed_episodes": status_counts["no_candidate"] + status_counts["failed"],
        "candidate_generation_attempts": candidate_attempt_count,
        "candidate_retries": max(0, candidate_attempt_count - distinct_attempted_episodes),
        "ranked_promos": len(rankings),
        "ranking_errors": len(ranking_errors or []),
        "input_errors": list(input_errors or []),
        "ranking_error_details": list(ranking_errors or []),
        "top_promo_ids": [item.promo_id for item in rankings[:10]],
    }
