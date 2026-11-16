#!/usr/bin/env python3
"""Stage 4 — ranking (code + AI one-liners).

Merges judge scores into passing candidates, computes the weighted total,
dedupes overlapping clips (IoU on per-episode time ranges), applies variety
caps (<=2 per episode, >=1 episode-1 clip, >=1 cross-episode combo, spread
of characters), and writes outputs/ranked_promos.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm import extract_json  # noqa: E402


def ep_time_ranges(cand: dict) -> dict:
    ranges = {}
    for seg in cand["segments"]:
        ep = seg["from"].split(":")[0].lstrip("ep")
        lo, hi = ranges.get(ep, (1e9, -1))
        ranges[ep] = (min(lo, seg["start"]), max(hi, seg["end"]))
    return ranges


def iou(a, b) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def overlaps(c1: dict, c2: dict) -> bool:
    """Two clips overlap if they share an episode and their ranges overlap >0.5 IoU."""
    r1, r2 = ep_time_ranges(c1), ep_time_ranges(c2)
    for ep in set(r1) & set(r2):
        if iou(r1[ep], r2[ep]) >= DEDUPE_IOU:
            return True
    return False


def weighted_score(cand: dict, weights: dict) -> float:
    s = cand.get("judge", {})
    total = 0.0
    for crit, w in weights.items():
        val = s.get(crit, 0)
        total += w * val
    return round(total, 3)


def dedupe(ranked: list) -> list:
    kept = []
    for c in ranked:  # already sorted by score desc
        if any(overlaps(c, k) for k in kept):
            c["deduped"] = True
            continue
        kept.append(c)
    return kept


def apply_variety(kept: list, rules: dict) -> list:
    """<= max_per_episode per episode; force-keep at least one ep1 clip and
    one cross-episode combo (if any exist) by promoting them ahead of the cut."""
    per_ep = {}
    out = []
    deferred = []
    for c in kept:
        eps = str(c["episode"])
        if c["kind"] == "combo":
            out.append(c)  # combos don't count toward single-episode caps
        elif per_ep.get(eps, 0) < rules["max_per_episode"]:
            per_ep[eps] = per_ep.get(eps, 0) + 1
            out.append(c)
        else:
            deferred.append(c)
    # ensure variety floors within the target window
    target = rules["target_top"]
    has_ep1 = any(str(c["episode"]) == "1" for c in out[:target])
    has_combo = any(c["kind"] == "combo" for c in out[:target])
    out_top, out_tail = out[:target], out[target:]
    if not has_ep1:
        ep1 = next((c for c in out_tail if str(c["episode"]) == "1"), None)
        if ep1:
            out_top.append(ep1)
            out_tail.remove(ep1)
    if not has_combo:
        combo = next((c for c in out_tail if c["kind"] == "combo"), None)
        if combo:
            out_top.append(combo)
            out_tail.remove(combo)
    return out_top[:target] + out_tail


def main() -> int:
    cands = json.loads(Path("data/candidates.json").read_text(encoding="utf-8"))["candidates"]
    cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
    rules, weights = cfg["rules"], cfg["weights"]
    global DEDUPE_IOU
    DEDUPE_IOU = rules["iou_dedupe"]

    judge_scores = {}
    for line in (Path("prompts/judges_responses.jsonl")).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        try:
            judge_scores[rec["cid"]] = extract_json(rec["response"])
        except Exception:
            judge_scores[rec["cid"]] = {"error": "unparseable", "raw": rec["response"][:200]}

    blind = {}
    blind_path = Path("prompts/blind_responses.jsonl")
    if blind_path.exists():
        for line in blind_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            try:
                blind[rec["cid"]] = extract_json(rec["response"])
            except Exception:
                blind[rec["cid"]] = {"error": "unparseable"}

    passed = [c for c in cands if c["pass"] and c["cid"] in judge_scores
              and "error" not in judge_scores[c["cid"]]]
    failed_scores = [c["cid"] for c in cands if c["pass"] and c["cid"] not in judge_scores]
    for c in passed:
        c["judge"] = judge_scores[c["cid"]]
        c["score"] = weighted_score(c, weights)
        c["blind"] = blind.get(c["cid"])
        if c["blind"] and "comprehension" in c["blind"]:
            c["score"] = round(c["score"] + 0.02 * c["blind"]["comprehension"], 3)

    passed.sort(key=lambda c: -c["score"])
    deduped = dedupe(passed)
    final = apply_variety(deduped, rules)
    final.sort(key=lambda c: -c["score"])

    ranked = {"promos": final, "deduped_out": [c["cid"] for c in deduped if c.get("deduped")],
              "no_judge_score": failed_scores}
    Path("outputs/ranked_promos.json").write_text(
        json.dumps(ranked, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ranked {len(final)} promos (top score {final[0]['score'] if final else '-'})"
          f" | no-judge-score: {len(failed_scores)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
