#!/usr/bin/env python3
"""End-to-end orchestrator.

  python3 -I src/run.py prepare    → parse + build candidate prompts
  (fill prompts/candidates_responses.jsonl — via API or the file backend)
  python3 -I src/run.py mid        → validate + season prompts
  (fill prompts/season_responses.jsonl)
  python3 -I src/run.py judge      → validate combos + build judge prompts
  (fill prompts/judges_responses.jsonl)
  python3 -I src/run.py rank       → scores merged, ranked, reports written
  (fill prompts/blind_responses.jsonl for the blind check, then rank again)

The `file` backend makes every AI hand-off explicit and leaves an unedited
prompt/response log in prompts/ — that log IS the raw outputs evidence.
"""
import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent


def run(step: str) -> int:
    script = {
        "parse": [sys.executable, "-I", str(SRC / "parse.py"), "--input",
                  "input/I Married a Broken Soldier. He was a Duke"],
        "candidates_prompts": [sys.executable, "-I", str(SRC / "candidates.py")],
        "validate": [sys.executable, "-I", str(SRC / "validate.py")],
        "season_prompts": [sys.executable, "-I", str(SRC / "candidates.py"), "--season"],
        "judge_prompts": [sys.executable, "-I", str(SRC / "score.py")],
        "blind_prompts": [sys.executable, "-I", str(SRC / "score.py"), "--blind"],
        "rank": [sys.executable, "-I", str(SRC / "rank.py")],
        "report": [sys.executable, "-I", str(SRC / "report.py")],
    }[step]
    return subprocess.run([str(x) for x in script], check=False).returncode


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in (
            "prepare", "mid", "judge", "rank", "full"):
        print(__doc__)
        return 2
    step = sys.argv[1]
    if step in ("prepare", "full"):
        if run("parse") != 0:
            return 1
        return run("candidates_prompts")
    if step == "mid":
        return run("validate") or run("season_prompts")
    if step == "judge":
        return run("judge_prompts")
    if step == "rank":
        return run("rank") or run("blind_prompts") or run("rank") or run("report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
