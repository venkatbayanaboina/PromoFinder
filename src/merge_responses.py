#!/usr/bin/env python3
"""Merge raw response files (prompts/raw/<key>.response.json) into the
JSONL contract the file backend expects. Each raw file's entire content is
the model's answer; merging just wraps it in {"key","stage","response"}."""
import json
from pathlib import Path

RAW = Path("prompts/raw")


def write_jsonl(out_name: str, recs: list) -> Path:
    out = Path("prompts") / out_name
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
                   encoding="utf-8")
    print(f"merged {len(recs)} responses -> {out}")
    return out


if __name__ == "__main__":
    # candidates: cand-ep-NN.response.json -> {"key": "cand-ep-NN", "episode": NN}
    recs = []
    for p in sorted(RAW.glob("cand-ep-*.response.json")):
        key = p.name.replace(".response.json", "")
        recs.append({"key": key, "stage": "candidates",
                     "episode": int(p.name.split("ep-")[1].split(".")[0]),
                     "response": p.read_text(encoding="utf-8")})
    write_jsonl("candidates_responses.jsonl", recs)

    season = RAW / "season-combos.response.json"
    if season.exists():
        write_jsonl("season_responses.jsonl",
                    [{"key": "season-combos", "stage": "season",
                      "response": season.read_text(encoding="utf-8")}])
    print(f"candidate responses: {len(recs)}/50")
