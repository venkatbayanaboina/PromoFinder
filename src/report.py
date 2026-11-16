#!/usr/bin/env python3
"""Stage 5 — outputs: CSV, readable markdown report, quality report.

promo_report.md    — the deliverable an editor reads: ranked promos with
                     episode, segment timestamps, hook, cliffhanger, why.
quality_report.md  — automatic checks + manual review table + failures.
ranked_promos.csv  — flat table for spreadsheets.
"""
import csv
import json
from pathlib import Path

OUT = Path("outputs")


def fmt_ts(seconds: float) -> str:
    m, s = divmod(float(seconds), 60)
    return f"{int(m):02d}:{s:05.2f}"


def seg_label(cand: dict) -> str:
    parts = []
    for seg in cand["segments"]:
        parts.append(f"ep{seg['from'].split(':')[0][2:]} {fmt_ts(seg['start'])}-{fmt_ts(seg['end'])}")
    return " + ".join(parts)


def post_first_because(cand: dict, rank: int) -> str:
    j = cand.get("judge", {})
    bits = []
    if rank == 1:
        bits.append("strongest overall score")
    if j.get("hook_strength", 0) >= 4:
        bits.append("hook lands inside 3s")
    if j.get("cliffhanger_strength", 0) >= 4:
        bits.append("cut leaves the outcome unresolved")
    if j.get("standalone_clarity", 0) >= 4:
        bits.append("needs no context")
    if cand["kind"] == "combo":
        bits.append("cross-episode payoff")
    if cand.get("episode") == 1:
        bits.append("works for cold audiences (no backstory needed)")
    return "; ".join(bits) or cand.get("why", "")


def write_csv(ranked: dict) -> None:
    rows = []
    for i, c in enumerate(ranked["promos"], 1):
        j = c.get("judge", {})
        rows.append({
            "rank": i, "cid": c["cid"], "episode": c["episode"],
            "kind": c["kind"], "segments": seg_label(c),
            "duration_s": c["duration_s"], "hook_ts": fmt_ts(c.get("hook_ts", 0)),
            "hook": c.get("hook_quote", ""), "hook_type": c.get("hook_type", ""),
            "cliffhanger_ts": fmt_ts(c.get("cliffhanger_ts", 0)),
            "cliffhanger": c.get("cliffhanger_quote", ""),
            "score": c["score"], "hook_strength": j.get("hook_strength"),
            "cliffhanger_strength": j.get("cliffhanger_strength"),
            "standalone_clarity": j.get("standalone_clarity"),
            "emotional_intensity": j.get("emotional_intensity"),
            "spoiler_risk": j.get("spoiler_risk"),
            "judge_verdict": j.get("verdict", ""),
            "why": c.get("why", ""),
        })
    with (OUT / "ranked_promos.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_markdown(ranked: dict, data: dict) -> None:
    lines = ["# Promo report — *I Married a Broken Soldier. He was a Duke* (episodes 1-50)",
             "",
             "Ranked by weighted score (hook .30, cliffhanger .25, standalone .20,",
             "intensity .15, spoiler −.10, blind comprehension +0.02/pt). Editor approves the top N.",
             ""]
    for i, c in enumerate(ranked["promos"], 1):
        j = c.get("judge", {})
        lines += [f"## #{i} — {c['cid']} ({c['kind']}) — score {c['score']}",
                  "",
                  f"- **Segments:** {seg_label(c)} (total {c['duration_s']:.0f}s)"
                  + (" *(auto-trimmed so the hook lands inside 3s)*" if c.get("trimmed") else ""),
                  f"- **Hook ({c.get('hook_type','')}):** {c.get('hook_quote','')}",
                  f"- **Cliffhanger:** {c.get('cliffhanger_quote','')}",
                  f"- **Why it works:** {c.get('why','')}",
                  f"- **Post first because:** {post_first_because(c, i)}",
                  f"- **Judge scores:** hook {j.get('hook_strength')} · cliffhanger {j.get('cliffhanger_strength')} · "
                  f"standalone {j.get('standalone_clarity')} · intensity {j.get('emotional_intensity')} · "
                  f"spoiler {j.get('spoiler_risk')} — *{j.get('verdict','')}*",
                  ""]
        if c.get("blind"):
            b = c["blind"]
            lines += [f"- **Blind reader (never saw the show):** comprehension {b.get('comprehension')}/5, "
                      f"keep scrolling: {b.get('keep_scrolling')}, unresolved: {b.get('ends_unresolved')} — "
                      f"*{b.get('understood','')}*" + (f" Confusions: {b.get('confusions')}" if b.get('confusions') else ""),
                      ""]
    (OUT / "promo_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_quality(ranked: dict) -> None:
    vstats = json.loads((OUT / "validation_stats.json").read_text(encoding="utf-8"))
    pstats = json.loads(Path("data/parse_stats.json").read_text(encoding="utf-8"))
    promos = ranked["promos"]
    lines = ["# Quality report",
             "",
             "## Automatic checks (real runs)",
             f"- Episodes parsed: {pstats['episodes']}/50, blocks {pstats['total_blocks']} "
             f"(reconciles with pack census), unparsed lines: {len(pstats['unparsed_lines'])}",
             f"- Candidates produced by AI: {vstats['candidates_total']}",
             f"- Passed hard validation: {vstats['passed']} ({vstats['pass_rate']:.0%})",
             f"- Invalid block IDs emitted by AI: {vstats['invalid_block_id_count']}",
             f"- AI invented timestamps (instead of block IDs): {vstats['invented_timestamp_count']}",
             f"- Unparseable AI responses: {vstats['not_json_responses']}",
             f"- Clips auto-trimmed so the hook landed inside 3s: {vstats['auto_trimmed_count']}",
             f"- Cross-episode combos: {vstats['combos_passed']}/{vstats['combos_total']} passed",
             f"- Failure reasons: {vstats['failure_reasons']}",
             ""]
    scored = [c for c in promos if c.get("judge")]
    if scored:
        avg = {k: round(sum(c["judge"].get(k, 0) for c in scored) / len(scored), 2)
               for k in ("hook_strength", "cliffhanger_strength", "standalone_clarity",
                         "emotional_intensity", "spoiler_risk")}
        lines += [f"- Judge averages over top {len(scored)}: {avg}"]
    blind = [c for c in promos if c.get("blind") and not c["blind"].get("error")]
    if blind:
        kc = sum(1 for c in blind if c["blind"].get("keep_scrolling"))
        lines += [f"- Blind check on top {len(blind)}: {kc} would keep scrolling, "
                  f"avg comprehension {sum(c['blind'].get('comprehension', 0) for c in blind) / len(blind):.1f}/5"]
    lines += ["",
              "## Manual review (15 clips graded good / ok / bad)",
              "| clip | grade | hook in 3s? | cliffhanger real? | standalone? | note |",
              "|---|---|---|---|---|---|"]
    manual = json.loads((OUT / "manual_review.json").read_text(encoding="utf-8"))
    for row in manual:
        lines.append(f"| {row['cid']} | {row['grade']} | {row.get('hook_in_3s','')} | "
                     f"{row.get('cliffhanger_real','')} | {row.get('standalone','')} | {row.get('note','')} |")
    grades = [r["grade"] for r in manual]
    good_ok = sum(1 for g in grades if g in ("good", "ok"))
    lines += ["", f"- **Grades:** {grades.count('good')} good / {grades.count('ok')} ok / "
              f"{grades.count('bad')} bad — good+ok rate {good_ok}/{len(grades)}",
              "", "## Honest failures"]
    for f in json.loads((OUT / "failures.json").read_text(encoding="utf-8")):
        lines.append(f"- **{f['title']}** — {f['detail']}")
    (OUT / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ranked = json.loads((OUT / "ranked_promos.json").read_text(encoding="utf-8"))
    data = json.loads(Path("data/parsed.json").read_text(encoding="utf-8"))
    write_csv(ranked)
    write_markdown(ranked, data)
    try:
        write_quality(ranked)
        print("wrote ranked_promos.csv, promo_report.md, quality_report.md")
    except FileNotFoundError as e:
        print(f"wrote ranked_promos.csv, promo_report.md (quality report pending: {e})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
