#!/usr/bin/env python3
"""Stage 2 — validation (pure code, no AI).

Resolves AI-proposed block IDs to timestamps and enforces the hard rules:
  - every referenced block ID exists (the model answers in IDs, never
    timestamps, so invented cut points are impossible)
  - total length 20-60s, <=3 segments, each segment >=3s
  - the hook block starts within the first 3s of the clip — if the AI
    put the hook later, leading blocks are auto-trimmed, then length
    is re-checked.

Reads  prompts/candidates_responses.jsonl  (per-episode candidates)
       prompts/season_responses.jsonl      (cross-episode combos)
Writes data/candidates.json (normalized, pass/fail + reasons)
       outputs/validated.jsonl   (one line per candidate, unedited reasons)
       outputs/validation_stats.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm import extract_json  # noqa: E402

PROMPTS_DIR = Path("prompts")


def load_blocks(data: dict) -> dict:
    idx = {}
    for ep in data["episodes"]:
        for b in ep["blocks"]:
            idx[b["id"]] = b
    return idx


def resolve_segment(idx: dict, ep_no: int, frm: str, to: str) -> tuple:
    """Return (list_of_blocks, None) or (None, reason)."""
    for bid in (frm, to):
        if bid not in idx:
            return None, f"unknown_block_id:{bid}"
        if not bid.startswith(f"ep{ep_no}:"):
            return None, f"cross_episode_id:{bid}"
    blocks = idx[frm]["_ep_blocks"]
    i, j = int(frm.split(":b")[1]), int(to.split(":b")[1])
    if j < i:
        return None, f"out_of_order:{frm}>{to}"
    return blocks[i:j + 1], None


def normalize_candidate(raw: dict, idx: dict, ep_no: int, cid: str, kind: str) -> dict:
    """Resolve one candidate (single-episode or combo of candidate ids) into
    concrete segments, apply trim + hard rules."""
    reasons = []
    seg_specs = []
    if kind == "combo":
        for ref in raw.get("setup_ids", []) + raw.get("payoff_ids", []):
            seg_specs.append(("ref", ref))
    else:
        for seg in raw.get("segments", []):
            seg_specs.append(("range", (seg.get("from"), seg.get("to"))))

    segments = []
    for tag, spec in seg_specs:
        if tag == "ref":
            return None  # combo refs resolved separately in validate_combos
        blocks, err = resolve_segment(idx, ep_no, spec[0], spec[1])
        if err:
            reasons.append(err)
            continue
        segments.append(blocks)

    cand = {
        "cid": cid, "episode": ep_no, "kind": kind, "raw": raw,
        "segments": [], "duration_s": 0.0, "pass": False, "reasons": reasons,
        "trimmed": False,
    }
    if reasons:
        return cand

    # Auto-trim: hook must start within hook_window_s of clip start.
    hook_id = raw.get("hook_block_id")
    hook = idx.get(hook_id) if hook_id else None
    if hook is None:
        reasons.append(f"unknown_hook_id:{hook_id}")
    else:
        first_seg = segments[0]
        if hook["start"] < first_seg[0]["start"] - 0.01 or hook["start"] > first_seg[-1]["end"]:
            reasons.append("hook_outside_first_segment")
        else:
            hook_window = RULES["hook_window_s"]
            while first_seg and (hook["start"] - first_seg[0]["start"]) > hook_window:
                first_seg = first_seg[1:]
                cand["trimmed"] = True
            if not first_seg:
                reasons.append("hook_late_untrimmable")
            segments[0] = first_seg

    kept = []
    for seg in segments:
        if seg:
            kept.append(seg)
    segments = kept

    for seg in segments:
        dur = seg[-1]["end"] - seg[0]["start"]
        if dur < RULES["min_segment_s"]:
            reasons.append(f"segment_too_short:{seg[0]['id']}")
    total = sum(seg[-1]["end"] - seg[0]["start"] for seg in segments)
    if total < RULES["min_s"]:
        reasons.append(f"too_short:{total:.1f}s")
    if total > RULES["max_s"]:
        reasons.append(f"too_long:{total:.1f}s")
    if len(segments) > RULES["max_segments"]:
        reasons.append("too_many_segments")

    cand["segments"] = [
        {"from": seg[0]["id"], "to": seg[-1]["id"],
         "start": round(seg[0]["start"], 2), "end": round(seg[-1]["end"], 2),
         "duration_s": round(seg[-1]["end"] - seg[0]["start"], 2)}
        for seg in segments]
    cand["duration_s"] = round(total, 2)
    hook_b = idx.get(raw.get("hook_block_id"))
    cliff_b = idx.get(raw.get("cliffhanger_block_id"))
    cand["hook_quote"] = (hook_b or {}).get("text", "")
    cand["hook_ts"] = round((hook_b or {}).get("start", -1), 2)
    cand["cliffhanger_quote"] = (cliff_b or {}).get("text", "")
    cand["cliffhanger_ts"] = round((cliff_b or {}).get("start", -1), 2)
    cand["why"] = raw.get("why", "")
    cand["hook_type"] = raw.get("hook_type", "")
    cand["pass"] = not reasons
    cand["reasons"] = reasons
    return cand


def validate_combos(combos_raw: list, candidates_by_cid: dict, idx: dict) -> list:
    out = []
    for i, combo in enumerate(combos_raw, 1):
        refs = combo.get("setup_ids", []) + combo.get("payoff_ids", [])
        reasons = []
        if not 1 <= len(refs) <= 2:
            reasons.append(f"combo_ref_count:{len(refs)}")
        segs, ep_order = [], []
        for ref in refs:
            src = candidates_by_cid.get(ref)
            if src is None or not src["pass"]:
                reasons.append(f"bad_combo_ref:{ref}")
                continue
            ep_order.append(src["episode"])
            segs.extend(src["segments"])
        if ep_order != sorted(ep_order):
            reasons.append("combo_out_of_episode_order")
        cand = {
            "cid": f"combo-{i:02d}", "episode": f"{min(ep_order)}-{max(ep_order)}" if ep_order else "?",
            "kind": "combo", "raw": combo, "name": combo.get("name", ""),
            "why": combo.get("why", ""), "trimmed": False,
            "segments": segs, "duration_s": round(sum(s["duration_s"] for s in segs), 2),
            "pass": False, "reasons": reasons,
        }
        total = cand["duration_s"]
        if len(segs) > RULES["max_segments"]:
            reasons.append("too_many_segments")
        if total < RULES["min_s"]:
            reasons.append(f"too_short:{total:.1f}s")
        if total > RULES["max_s"]:
            reasons.append(f"too_long:{total:.1f}s")
        for s in segs:
            if s["duration_s"] < RULES["min_segment_s"]:
                reasons.append(f"segment_too_short:{s['from']}")
        # hook/cliffhanger inherit from first/last source candidate
        first_src = candidates_by_cid.get(refs[0]) if refs else None
        last_src = candidates_by_cid.get(refs[-1]) if refs else None
        if first_src:
            cand["hook_quote"] = first_src["hook_quote"]
            cand["hook_ts"] = first_src["hook_ts"]
            cand["hook_type"] = first_src.get("hook_type", "")
        if last_src:
            cand["cliffhanger_quote"] = last_src["cliffhanger_quote"]
            cand["cliffhanger_ts"] = last_src["cliffhanger_ts"]
        cand["pass"] = not reasons
        cand["reasons"] = reasons
        out.append(cand)
    return out


RULES = {}


def main() -> int:
    global RULES
    cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
    RULES = cfg["rules"]
    data = json.loads(Path("data/parsed.json").read_text(encoding="utf-8"))
    idx = load_blocks(data)
    for ep in data["episodes"]:
        for b in ep["blocks"]:
            b["_ep_blocks"] = ep["blocks"]

    # --- per-episode candidates from responses ---
    resp_path = PROMPTS_DIR / "candidates_responses.jsonl"
    singles = []
    invalid_id_count = 0
    invented_ts_count = 0
    n_not_json = 0
    for line in resp_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        ep_no = rec["episode"]
        try:
            raw_cands = extract_json(rec["response"])
            if isinstance(raw_cands, dict):  # tolerate a single object
                raw_cands = [raw_cands]
            assert isinstance(raw_cands, list)
        except Exception:
            n_not_json += 1
            singles.append({"cid": f"parse-fail-{rec['key']}", "episode": ep_no,
                            "kind": "single", "pass": False, "reasons": ["not_json"],
                            "segments": [], "raw": rec["response"][:200]})
            continue
        for k, raw in enumerate(raw_cands, 1):
            if isinstance(raw, dict) and ("start" in raw or "end" in raw):
                invented_ts_count += 1
            cand = normalize_candidate(raw, idx, ep_no, f"cand-{ep_no:02d}-{k}", "single")
            if cand is None:
                continue
            singles.append(cand)
            invalid_id_count += sum(1 for r in cand["reasons"] if "unknown" in r)

    # --- cross-episode combos ---
    combos = []
    season_resp = PROMPTS_DIR / "season_responses.jsonl"
    if season_resp.exists():
        by_cid = {c["cid"]: c for c in singles}
        for line in season_resp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            try:
                raw_combos = extract_json(rec["response"])
            except Exception:
                n_not_json += 1
                continue
            combos = validate_combos(raw_combos, by_cid, idx)

    all_cands = singles + combos
    Path("data/candidates.json").write_text(
        json.dumps({"candidates": all_cands}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    passed = [c for c in all_cands if c["pass"]]
    reason_hist = {}
    for c in all_cands:
        for r in c["reasons"]:
            key = r.split(":")[0]
            reason_hist[key] = reason_hist.get(key, 0) + 1
    with Path("outputs/validated.jsonl").open("w", encoding="utf-8") as f:
        for c in all_cands:
            f.write(json.dumps(
                {"cid": c["cid"], "episode": c["episode"], "kind": c["kind"],
                 "pass": c["pass"], "reasons": c["reasons"],
                 "duration_s": c.get("duration_s"), "segments": c.get("segments", [])},
                ensure_ascii=False) + "\n")

    stats = {
        "candidates_total": len(all_cands),
        "passed": len(passed),
        "pass_rate": round(len(passed) / max(len(all_cands), 1), 3),
        "invalid_block_id_count": invalid_id_count,
        "invented_timestamp_count": invented_ts_count,
        "not_json_responses": n_not_json,
        "auto_trimmed_count": sum(1 for c in singles if c.get("trimmed")),
        "combos_total": len(combos),
        "combos_passed": sum(1 for c in combos if c["pass"]),
        "failure_reasons": reason_hist,
    }
    Path("outputs/validation_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    gate = (stats["pass_rate"] >= 0.8 and stats["not_json_responses"] == 0)
    print("CP2 GATE:", "PASS" if gate else "FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
