#!/usr/bin/env python3
"""Stage 3 — scoring (AI, stronger model slot) and stage 4 — ranking (code).

Judge prompt: rubric scores 0-5 on hook strength, cliffhanger strength,
standalone clarity, emotional intensity; spoiler risk 0-5 (higher = worse,
penalized in ranking). Also flags what confused a cold viewer.

Blind check: for the top clips only, a "never seen the show" reader gets
just the transcript and answers what they understood and whether they
would keep scrolling — the standalone-clarity reality check.
"""
import argparse
import json
from pathlib import Path

PROMPTS_DIR = Path("prompts")

JUDGE_PROMPT = """You are a strict promo judge for vertical microdrama (TikTok/ReelShort style). Below is a promo clip cut from the show "{show}".{combo_note}

Transcript (timestamps are screen positions; dialogue in quotes, CAMERA/ACTION/SOUND FX are non-spoken):
{transcript}

Rate this promo 0-5 on each criterion (0 = terrible, 5 = exceptional):
- hook_strength: does the FIRST 3 seconds stop a scrolling viewer? (a slap, a reveal, a shocking line in the open)
- cliffhanger_strength: does it cut at a moment you MUST see resolved? (5 = agonizing cut; 1 = fully resolved ending)
- standalone_clarity: can someone who has NEVER seen the show follow it? (who wants what, who blocks whom)
- emotional_intensity: conflict, stakes, visible emotion
- spoiler_risk: 0 = no spoilers, 5 = reveals a major twist outright (hidden identity, who the villain is, ending)

Also write:
- "verdict": one line, the single biggest weakness of this clip
- "confusions": list of things a cold viewer would not understand (empty if none)

Answer with ONLY a JSON object:
{{"hook_strength": n, "cliffhanger_strength": n, "standalone_clarity": n, "emotional_intensity": n, "spoiler_risk": n, "verdict": "...", "confusions": ["..."]}}"""

BLIND_PROMPT = """You have NEVER seen this show and know nothing about it. This clip would appear on your TikTok feed:

---
{transcript}
---

Answer with ONLY a JSON object:
{{"understood": "<2 sentences: what is happening, who wants what>", "ends_unresolved": true/false, "keep_scrolling": true/false, "confusions": ["<anything you could not follow>"], "comprehension": <0-5>}}"""


def transcript_of(cand: dict, idx: dict) -> str:
    lines = []
    for seg in cand["segments"]:
        ep_no = int(seg["from"].split(":")[0].replace("ep", ""))
        i, j = int(seg["from"].split(":b")[1]), int(seg["to"].split(":b")[1])
        blocks = idx[f"ep{ep_no}:b000"]["_ep_blocks"]
        if cand["kind"] == "combo" or len(cand["segments"]) > 1:
            lines.append(f"--- PART {len(lines) + 1} (episode {ep_no}) ---")
        for b in blocks[i:j + 1]:
            m, s = divmod(b["start"], 60)
            ts = f"{int(m):02d}:{s:04.1f}"
            if b["type"] == "DIALOGUE":
                lines.append(f"[{ts}] {b.get('speaker','')} ({b.get('speaker_raw','')}): {b.get('text','')}")
            else:
                lines.append(f"[{ts}] {b['type']}: {b.get('text','')}")
    return "\n".join(lines)


def build_judge_prompts(passed: list, idx: dict, cfg: dict) -> list:
    show = "I Married a Broken Soldier. He was a Duke"
    out = []
    for c in passed:
        combo_note = ("\nNOTE: this promo JOINS moments from different episodes "
                      "(a hard cut between parts is intentional)." if c["kind"] == "combo" else "")
        out.append({
            "key": f"judge-{c['cid']}", "cid": c["cid"],
            "prompt": JUDGE_PROMPT.format(show=show, combo_note=combo_note,
                                          transcript=transcript_of(c, idx))})
    return out


def build_blind_prompts(top: list, idx: dict) -> list:
    out = []
    for c in top:
        out.append({"key": f"blind-{c['cid']}", "cid": c["cid"],
                    "prompt": BLIND_PROMPT.format(transcript=transcript_of(c, idx))})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind", action="store_true", help="build blind-check prompts for top clips")
    ap.add_argument("--ranked", default="outputs/ranked_promos.json")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    data = json.loads(Path("data/parsed.json").read_text(encoding="utf-8"))
    idx = {}
    for ep in data["episodes"]:
        for b in ep["blocks"]:
            idx[b["id"]] = b
            b["_ep_blocks"] = ep["blocks"]

    cands = json.loads(Path("data/candidates.json").read_text(encoding="utf-8"))["candidates"]
    cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
    passed = [c for c in cands if c["pass"]]

    if args.blind:
        ranked = json.loads(Path(args.ranked).read_text(encoding="utf-8"))["promos"][:args.top]
        records = build_blind_prompts(ranked, idx)
        out = PROMPTS_DIR / "blind_prompts.jsonl"
    else:
        records = build_judge_prompts(passed, idx, cfg)
        out = PROMPTS_DIR / "judges_prompts.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} prompt(s) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
