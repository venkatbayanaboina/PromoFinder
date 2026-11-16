# Promo Finder — Kuku AI Generalist Assignment (Problem 1)

Reads timestamped microdrama screenplays and finds the best 20–60s promo
clips to post on Instagram/TikTok/YouTube: each promo **opens on a hook**
(something arresting in the first 3 seconds), **ends on a cliffhanger**
(cuts at an unresolved moment), and **makes sense on its own** to someone
who has never seen the show. Ranked shortlist goes to a human editor who
approves the top N — the tool saves hours, it doesn't remove the editor.

Show used for this run: *I Married a Broken Soldier. He was a Duke*
(episodes 1–50). The input pack is Kuku's own content — it is **not**
included in this repo.

## How it works (staged pipeline: code for exactness, AI for judgment)

| Stage | Tool | What it does |
|---|---|---|
| 1. Parse | code | screenplay → scenes + timestamped blocks with stable IDs (`ep1:b014`) |
| 2. Candidates | AI (cheap slot) | per episode: propose 20–60s clips **as block IDs, never timestamps** — invented cut points are impossible by design |
| 3. Validate | code | resolve IDs → timestamps; enforce 20–60s, ≤3 segments, cuts on block boundaries, hook within 3s (auto-trims leading blocks if the AI put the hook late) |
| 4. Score | AI (strong slot) | rubric: hook strength, cliffhanger strength, standalone clarity, emotional intensity (0–5), spoiler risk (0–5, penalized) + a blind "never saw the show" comprehension check on the top clips |
| 5. Rank | code | dedupe overlapping clips (IoU), variety caps (≤2/episode, ≥1 episode-1 clip, ≥1 cross-episode combo), weighted score |
| 6. Output | code | `outputs/`: JSON + CSV + markdown report + quality report; `prompts/` = unedited AI log |

## Run it

```bash
# 0. put episode .txt files under input/ (any folder depth)
python3 -I src/run.py prepare    # parse + build candidate prompts
# 1a. file backend (no key needed):
#     fill prompts/raw/cand-ep-NN.response.json, then:
python3 -I src/merge_responses.py
python3 -I src/run.py mid        # validate + build season combo prompt
#     fill prompts/raw/season-combos.response.json, then:
python3 -I src/merge_responses.py
# 1b. OR set backend="openai" in config.json and the calls go to the API directly
python3 -I src/run.py judge      # build judge prompts → fill responses as above
python3 -I src/run.py rank       # rank + reports (fills blind prompts, re-ranks)
```

With `backend: "openai"`, steps 1a–1b collapse: the pipeline calls the model
itself and writes the same prompt/response log.

## Swap the model with one edit

```jsonc
// config.json
"candidate_model": {
  "backend": "openai",                // was "file"
  "name": "gemini-2.0-flash",         // any model id
  "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
  "api_key_env": "GEMINI_API_KEY"     // env var holding the key
}
```

Works with OpenAI, Gemini's OpenAI-compatible endpoint, Groq, or any
OpenAI-compatible endpoint Kuku provides. `judge_model` is a separate slot,
so a cheap model can propose and a stronger model can judge.

## Repo layout

```
config.json      model slots + rules/thresholds (one-line swap)
src/             parse.py candidates.py validate.py score.py rank.py report.py llm.py merge_responses.py run.py
prompts/         unedited AI log: every prompt and every response (raw outputs)
outputs/         validated.jsonl, ranked_promos.json/.csv, promo_report.md, quality_report.md
doc/             solution.pdf (≤2 pages)
notebook/        Colab copy of the same pipeline
input/           (not committed — Kuku's content)
```

## Assumptions (full list in the doc)

- Hook window = 3s per the brief; clip length = sum of segment durations (join gaps excluded).
- Multi-segment promos ≤3 segments, each ≥3s; cross-episode combos allowed (the brief permits joining moments across episodes).
- Screenplay timestamps are ground-truth screen time (no video to verify against).
- Any block type can be the hook (a slap = ACTION, a sting = SOUND FX).
- Speaker-name drift across episodes (LADY JULIANA→JULIANA, THE FORMER GROOM→GERALD, …) is canonicalized via an alias table in `src/parse.py`.
- Deliverable = ranked shortlist (~10) for an editor.

## What we'd do with more time

- Auto-build the actual clip files with ffmpeg once timestamps are approved.
- A/B test hook styles against real view data to tune the rubric weights.
- Learn per-show thresholds instead of the fixed 20–60s/hook-3s defaults.
