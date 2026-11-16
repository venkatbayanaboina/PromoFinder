#!/usr/bin/env python3
"""Stage 1 — candidate finding (AI, cheap model slot).

Per episode: the model sees the ordered block list (with block IDs and
timestamps for pacing context) and proposes 20-60s promo candidates.
The model answers ONLY in block IDs — never timestamps — so code can
resolve every cut point and invented timestamps are impossible by design.

Season pass: after per-episode candidates exist, a second prompt sees all
candidates (ids + quotes) and proposes cross-episode combos by pairing
existing candidate ids.
"""
import argparse
import json
from pathlib import Path

PROMPTS_DIR = Path("prompts")

CANDIDATE_PROMPT = """You are a promo producer for a vertical microdrama series. Below is episode {ep} of "{show}" as a timestamped screenplay. Every line has a stable BLOCK ID.

Your job: find {n_min}-{n_max} promo candidates in this episode. A promo is a 20-60 second clip that:
1. OPENS ON A HOOK — something in the first 3 seconds that makes a scrolling viewer stop: a slap, a reveal, a shocking line, an entrance, an accusation. Any block type can be the hook (ACTION, SOUND FX or dialogue).
2. ENDS ON A CLIFFHANGER — cut at an unresolved moment so the viewer must know what happens next. NOT a resolved beat (no "resolving chord", no fade on a settled couple, no triumph).
3. MAKES SENSE ON ITS OWN to someone who has never seen the show.

Hard rules:
- A candidate is 1-2 contiguous segments of blocks. Total screen time 20-60 seconds (use the timestamps for pacing judgment only).
- Cuts fall on block boundaries: give `from` and `to` block IDs (inclusive) per segment.
- Prefer clips that END mid-tension. If the episode's final beat is a cliffhanger, ending the promo there is ideal.
- Vary the type of hook across your candidates (do not propose 3 dialogue-reveals).

EPISODE HEADER
Logline: {logline}
Continuity: {continuity}

BLOCKS (id | type | speaker | start-end | text)
{blocks}

Answer with ONLY a JSON array (no markdown), one object per candidate:
[{{"segments": [{{"from": "<block id>", "to": "<block id>"}}], "hook_block_id": "<id>", "hook_type": "<slap|reveal|shocking line|entrance|threat|other>", "cliffhanger_block_id": "<id>", "why": "<one line, why this works as a promo>"}}]"""

SEASON_PROMPT = """You are a promo producer for the vertical microdrama "{show}". Below are the loglines of all {n_eps} episodes and the promo candidates already found within single episodes.

Your job: propose up to 8 CROSS-EPISODE combo promos. A combo joins moments from two (max three) episodes into one 20-60 second promo: typically a SETUP (a threat, an ultimatum, a secret, a fall) followed by a PAYOFF (the reaction, the consequence, the reveal cut short). Combos work when the payoff is the answer the viewer is desperate to see — and still ends unresolved.

Rules:
- Use ONLY the candidate ids listed below (each candidate already has validated segments). A combo = 1-2 candidate ids, in episode order (setup episode number < payoff episode number).
- The combined screen time must stay 20-60 seconds. Prefer short, punchy candidates.
- Do NOT pick combos that spoil a major twist outright (e.g. revealing a hidden identity fully). Tease, don't resolve.

EPISODE LOGLINES
{loglines}

CANDIDATES (id | ep | duration_s | hook | cliffhanger)
{candidates}

Answer with ONLY a JSON array:
[{{"name": "<3-5 word name>", "setup_ids": ["<candidate id>"], "payoff_ids": ["<candidate id>"], "why": "<one line, why this combo works>"}}]"""


def fmt_ts(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:04.1f}"


def block_lines(ep: dict) -> str:
    lines = []
    for b in ep["blocks"]:
        kind = b["type"]
        who = b.get("speaker", "")
        if kind == "DIALOGUE" and b.get("speaker_raw", "").upper() != who:
            who = f"{who} (aka {b['speaker_raw']})"
        text = b.get("text", "")[:220]
        lines.append(f"{b['id']} | {kind} | {who} | {fmt_ts(b['start'])}-{fmt_ts(b['end'])} | {text}")
    return "\n".join(lines)


def build_candidate_prompts(data: dict, cfg: dict) -> list:
    show = "I Married a Broken Soldier. He was a Duke"
    out = []
    for ep in data["episodes"]:
        prompt = CANDIDATE_PROMPT.format(
            ep=ep["episode"], show=show, n_min=3, n_max=5,
            logline=ep["logline"], continuity=ep["continuity"][:300],
            blocks=block_lines(ep))
        out.append({"key": f"cand-ep-{ep['episode']:02d}", "episode": ep["episode"],
                    "stage": "candidates", "prompt": prompt})
    return out


def build_season_prompt(data: dict, candidates: list, cfg: dict) -> list:
    show = "I Married a Broken Soldier. He was a Duke"
    loglines = "\n".join(
        f"ep{e['episode']:02d}: {e['logline'][:220]}" for e in data["episodes"])
    cand_lines = "\n".join(
        f"{c['cid']} | ep{c['episode']} | {c['duration_s']:.0f}s | "
        f"{c['hook_quote'][:70]} -> {c['cliffhanger_quote'][:90]}"
        for c in candidates)
    prompt = SEASON_PROMPT.format(show=show, n_eps=len(data["episodes"]),
                                  loglines=loglines, candidates=cand_lines)
    return [{"key": "season-combos", "stage": "season", "prompt": prompt}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", action="store_true",
                    help="build the season combo prompt from existing candidates")
    ap.add_argument("--candidates", default="data/candidates.json")
    args = ap.parse_args()

    data = json.loads(Path("data/parsed.json").read_text(encoding="utf-8"))
    if args.season:
        candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))["candidates"]
        records = build_season_prompt(data, candidates, {})
        out = PROMPTS_DIR / "season_prompts.jsonl"
    else:
        records = build_candidate_prompts(data, {})
        out = PROMPTS_DIR / "candidates_prompts.jsonl"
    PROMPTS_DIR.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    total_chars = sum(len(r["prompt"]) for r in records)
    print(f"wrote {len(records)} prompt(s) to {out} (~{total_chars // 4} tokens total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
