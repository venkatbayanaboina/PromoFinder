"""Write stable JSON and CSV pipeline artifacts."""
import csv
import json
import os
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    os.replace(str(temporary), str(path))


def export_csv(path, rankings, promo_by_id):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["rank", "promo_id", "episode_id", "total_score", "hook_strength",
              "cliffhanger_strength", "standalone_clarity", "emotional_impact",
              "duration_and_flow", "duration_seconds", "segments", "ranking_reason"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in rankings:
            promo = promo_by_id[item.promo_id]
            writer.writerow({
                "rank": item.rank, "promo_id": item.promo_id, "episode_id": item.episode_id,
                "total_score": item.total_score,
                "hook_strength": item.scores.hook_strength,
                "cliffhanger_strength": item.scores.cliffhanger_strength,
                "standalone_clarity": item.scores.standalone_clarity,
                "emotional_impact": item.scores.emotional_impact,
                "duration_and_flow": item.scores.duration_and_flow,
                "duration_seconds": promo.duration_seconds,
                "segments": " | ".join("{}-{}".format(s.start_timestamp, s.end_timestamp)
                                         for s in promo.segments),
                "ranking_reason": item.ranking_reason,
            })
    os.replace(str(temporary), str(path))
