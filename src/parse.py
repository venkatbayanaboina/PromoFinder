#!/usr/bin/env python3
"""Parse Kuku microdrama screenplays into structured JSON.

Input:  a directory containing episode .txt files (flattened or nested).
Output: data/parsed.json  — episodes with scenes and timestamped blocks
        data/parse_stats.json — reconciliation counts for the self-check.

Format (verified against the pack):
  EPISODE NUMBER: Episode N
  EPISODE LOGLINE: ...
  CONTINUITY NOTES: ...
  --- SCRIPT START ---
  SCENE NN / Scene heading: ... / Scene start: MM:SS.ss / Scene end: MM:SS.ss
  Actions and dialogue:
  **CAMERA:** | **ACTION:** | **SOUND FX:** | **SPEAKER (Emotion):**
  Start: (MM:SS.ss) | End: (MM:SS.ss)
  <one content line; dialogue is quoted>
  --- SCRIPT END ---

Episode 6 uses ALL-CAPS field labels; every matcher is case-insensitive.
"""
import argparse
import json
import re
import sys
from pathlib import Path

TS = r"(\d+):(\d{1,2}(?:\.\d{1,2})?)"
TIMING_RE = re.compile(rf"Start:\s*\({TS}\)\s*\|\s*End:\s*\({TS}\)", re.I)
SCENE_RE = re.compile(r"^SCENE\s*:?\s*(\d+)\s*$", re.I)
SCENE_FIELD_RE = re.compile(r"^Scene (heading|start|end)\s*:\s*(.+)$", re.I)
HEADER_FIELDS = ("EPISODE NUMBER", "EPISODE LOGLINE", "CONTINUITY NOTES")
LABEL_RE = re.compile(r"^\*\*(.+?):\*\*\s*$")

# Speaker-name drift across episodes -> canonical character (verified by census).
ALIAS = {
    "LADY JULIANA": "JULIANA",
    "JULIANA": "JULIANA",
    "MYSTERIOUS BEARDED MAN": "ALEXANDER",
    "THE BEARDED STRANGER": "ALEXANDER",
    "ALEXANDER": "ALEXANDER",
    "LADY IN GOLD GOWN": "CLARISSA",
    "LADY CLARISSA": "CLARISSA",
    "CLARISSA": "CLARISSA",
    "LADY CATHERINE": "CATHERINE",
    "CATHERINE": "CATHERINE",
    "THE FORMER GROOM": "GERALD",
    "GERALD": "GERALD",
}
NON_DIALOGUE = {"CAMERA", "ACTION", "SOUND FX"}


def ts_to_seconds(minutes: str, seconds: str) -> float:
    return int(minutes) * 60 + float(seconds)


def canonical_speaker(raw: str) -> str:
    return ALIAS.get(raw.strip().upper(), raw.strip().upper())


def parse_episode(text: str, episode_no: int, source: str) -> dict:
    lines = text.splitlines()
    header = {}
    scenes, blocks = [], []
    cur_scene, cur_block = None, None
    unparsed = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            if cur_block is not None and cur_block.get("text"):
                blocks.append(cur_block)
                cur_block = None
            continue

        for field in HEADER_FIELDS:
            if stripped.upper().startswith(field + ":"):
                header[field] = stripped[len(field) + 1:].strip()
                break
        else:  # not a header line
            m = LABEL_RE.match(stripped)
            if m:
                if cur_block is not None:
                    blocks.append(cur_block)
                label = m.group(1).strip()
                # **SPEAKER (V.O.) (Emotion):** vs **CAMERA:**
                top = label.split("(")[0].strip().upper()
                if top in NON_DIALOGUE:
                    cur_block = {"type": top}
                else:
                    cur_block = {
                        "type": "DIALOGUE",
                        "speaker_raw": label,
                        "speaker": canonical_speaker(top),
                    }
                cur_block["_lineno"] = lineno
                continue
            m = TIMING_RE.search(stripped)
            if m and cur_block is not None and "start" not in cur_block:
                cur_block["start"] = ts_to_seconds(m.group(1), m.group(2))
                cur_block["end"] = ts_to_seconds(m.group(3), m.group(4))
                continue
            m = SCENE_RE.match(stripped)
            if m:
                if cur_block is not None:
                    blocks.append(cur_block)
                    cur_block = None
                cur_scene = {"scene_no": int(m.group(1))}
                scenes.append(cur_scene)
                continue
            m = SCENE_FIELD_RE.match(stripped)
            if m and cur_scene is not None:
                key, val = m.group(1).lower(), m.group(2).strip()
                if key == "start" or key == "end":
                    tm = re.match(TS, val)
                    cur_scene["scene_" + key] = ts_to_seconds(tm.group(1), tm.group(2))
                else:
                    cur_scene["heading"] = val
                continue
            if cur_block is not None and "text" not in cur_block:
                cur_block["text"] = stripped
                continue
            if stripped.startswith("--- SCRIPT") or re.match(
                    r"^Actions and dialogue\s*:\s*$", stripped, re.I):
                continue
            unparsed.append({"line": lineno, "text": stripped[:120]})

    if cur_block is not None:
        blocks.append(cur_block)

    # Assign scenes + stable IDs to blocks.
    scene_spans = [(s.get("scene_start", -1), s.get("scene_end", 1e9), s["scene_no"])
                   for s in scenes]
    for i, b in enumerate(blocks):
        b["id"] = f"ep{episode_no}:b{i:03d}"
        sid = None
        for lo, hi, no in scene_spans:
            if b.get("start") is not None and lo - 0.01 <= b["start"] <= hi + 0.01:
                sid = no
                break
        b["scene"] = sid
        for k in ("_lineno",):
            b.pop(k, None)

    duration = max((s.get("scene_end", 0) for s in scenes), default=0)
    return {
        "episode": episode_no,
        "source": source,
        "header": header,
        "logline": header.get("EPISODE LOGLINE", ""),
        "continuity": header.get("CONTINUITY NOTES", ""),
        "duration_s": round(duration, 2),
        "scenes": scenes,
        "blocks": blocks,
        "unparsed": unparsed,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="dir with episode txt files")
    ap.add_argument("--outdir", default="data")
    args = ap.parse_args()

    root = Path(args.input)
    files = sorted(root.rglob("episode-*.txt"))
    if not files:
        files = sorted(root.rglob("*.txt"))
    episodes, all_unparsed = [], []
    type_counts = {}
    for f in files:
        text = f.read_text(encoding="utf-8")
        num_m = re.search(r"episode-(\d+)-", f.name)
        ep_no = int(num_m.group(1)) if num_m else len(episodes) + 1
        ep = parse_episode(text, ep_no, f.name)
        episodes.append(ep)
        all_unparsed.extend({"episode": ep_no, **u} for u in ep["unparsed"])
        for b in ep["blocks"]:
            type_counts[b["type"]] = type_counts.get(b["type"], 0) + 1
    episodes.sort(key=lambda e: e["episode"])

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "parsed.json").write_text(
        json.dumps({"episodes": episodes}, ensure_ascii=False, indent=1), encoding="utf-8")

    speakers = {}
    for ep in episodes:
        for b in ep["blocks"]:
            if b["type"] == "DIALOGUE":
                key = b["speaker"]
                speakers[key] = speakers.get(key, 0) + 1

    stats = {
        "episodes": len(episodes),
        "total_blocks": sum(type_counts.values()),
        "blocks_by_type": type_counts,
        "dialogue_speakers": dict(sorted(speakers.items(), key=lambda kv: -kv[1])),
        "unparsed_lines": all_unparsed,
        "durations": {str(e["episode"]): e["duration_s"] for e in episodes},
    }
    (outdir / "parse_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    # Self-check gate (CP0)
    print(f"episodes: {len(episodes)}")
    print(f"blocks:   {stats['total_blocks']} {type_counts}")
    print(f"unparsed: {len(all_unparsed)}")
    dur = stats["durations"]
    print(f"durations: min {min(dur.values()):.2f}s max {max(dur.values()):.2f}s")
    expected = {"CAMERA": 1754, "ACTION": 372, "SOUND FX": 114, "DIALOGUE": 1487}
    ok = len(episodes) == 50 and stats["total_blocks"] == 3727 and not all_unparsed
    for k, v in expected.items():
        if type_counts.get(k) != v:
            print(f"MISMATCH {k}: got {type_counts.get(k)}, expected {v}")
            ok = False
    print("CP0 GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
