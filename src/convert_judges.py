#!/usr/bin/env python3
"""Convert judge batch files (one {"key","scores"} object per line) into the
prompts/judges_responses.jsonl contract rank.py expects."""
import json
from pathlib import Path

recs = []
for name in ("A", "B"):
    p = Path(f"prompts/raw/judges_batch_{name}.txt")
    if not p.exists():
        print(f"missing {p}")
        continue
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        recs.append({"key": rec["key"], "stage": "judges",
                     "response": json.dumps(rec["scores"], ensure_ascii=False)})

out = Path("prompts/judges_responses.jsonl")
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
               encoding="utf-8")
print(f"wrote {len(recs)} judge responses -> {out}")
