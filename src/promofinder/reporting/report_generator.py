"""Generate a concise human-readable execution report."""
from pathlib import Path

from ..storage.json_exporter import write_json


def generate_report(report_dir, run_id, status, summary, rankings, top_k):
    report_dir = Path(report_dir)
    write_json(report_dir / "execution_report.json", {
        "run_id": run_id, "status": status, "summary": summary,
        "rankings": [item.model_dump(mode="json") for item in rankings],
        "top_k": [item.model_dump(mode="json") for item in top_k],
    })
    lines = ["# PromoFinder execution report", "", "- Run: `{}`".format(run_id),
             "- Status: **{}**".format(status), "",
             "## Run counts", ""]
    for label, key in (("Episodes discovered", "total_episodes_discovered"),
                       ("Episodes parsed", "total_episodes_parsed"),
                       ("Episodes processed", "total_episodes_processed"),
                       ("Validated promos", "valid_promos"),
                       ("No suitable promo found", "no_candidate_episodes"),
                       ("Failed after retries", "failed_after_retries"),
                       ("Candidate attempts", "candidate_generation_attempts"),
                       ("Candidate retries", "candidate_retries"),
                       ("Promos ranked", "ranked_promos")):
        lines.append("- {}: {}".format(label, summary.get(key, 0)))
    lines.extend(["", "## Top recommendations", ""])
    if top_k:
        for item in top_k:
            lines.append("{}. **{}** ({}) — {:.2f}/100".format(
                item.rank, item.promo_id, item.episode_id, item.total_score))
    else:
        lines.append("No ranked promos are available in this run.")
    if summary.get("input_errors"):
        lines.extend(["", "## Input issues", ""])
        lines.extend("- {}".format(item) for item in summary["input_errors"])
    if summary.get("ranking_error_details"):
        lines.extend(["", "## Ranking issues", ""])
        lines.extend("- {}: {}".format(item["promo_id"], item["error"])
                     for item in summary["ranking_error_details"])
    (report_dir / "execution_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
