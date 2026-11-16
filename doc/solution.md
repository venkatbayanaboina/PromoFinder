# Promo Finder — Kuku AI Generalist Assignment (Problem 1)

**Problem chosen: 1 (Find the Promos) · Built in ~3 hours · Input: the 50-episode pack for "I Married a Broken Soldier. He was a Duke"**

## Why this problem
Promos are how microdramas acquire viewers, yet an editor watches every episode of every show by
hand, weekly. Problem 1 is the most on-brand of the three, the input is real, and output quality can
be checked against actual episodes. The deliverable is a ranked shortlist of 20–60s clips — the tool
shortlists, an editor approves the top N. It saves hours; it doesn't remove the editor.

## What I built (staged pipeline: code for exactness, AI for judgment)
1. **Parse (code).** Regex parser turns each screenplay into scenes and timestamped blocks with
   stable IDs (`ep12:b031`). Handles episode 6's silent switch to ALL-CAPS labels.
2. **Candidates (AI, cheap slot).** Per episode, the model proposes 3–5 promos **as block IDs, never
   timestamps** — invented cut points are impossible by design; code resolves every ID.
3. **Validate (code).** Hard rules: IDs exist, total 20–60s, cuts on block boundaries, hook starts
   within 3s of clip start (leading blocks auto-trimmed if the AI put the hook late), segments ≥3s,
   ≤3 segments. Every failure is logged with its reason.
4. **Score (AI, stronger slot).** Rubric 0–5: hook strength, cliffhanger strength, standalone
   clarity, emotional intensity; spoiler risk 0–5 penalized. Plus a **blind check**: a "never saw the
   show" pass over just the clip text — what did you understand, does it end unresolved, would you
   keep scrolling.
5. **Rank (code + AI).** Weighted total (hook .30, cliffhanger .25, standalone .20, intensity .15,
   spoiler −.10, blind +.02/pt); dedupe overlaps (within same kind — combos intentionally reuse
   their source segments); variety caps (≤2/episode, ≥1 episode-1 clip, ≥1 cross-episode combo);
   "post first because…" line for the top clips.
6. **Output.** JSON + CSV + markdown report + quality report; every prompt and response logged
   unedited in `prompts/` (that log is the raw-output evidence).

A season pass pairs already-validated candidates into cross-episode setup→payoff combos (the brief
allows joining moments across episodes).

**Model swap = one config edit** (`config.json`, `backend: "openai"` + base URL + model name + key
env var) — works with Gemini, Groq, OpenAI, or any endpoint Kuku provides. The submitted run used
the free route: prompts executed by GLM (via ZCode), with the full unedited log shipped as raw
outputs. Repo: code + README + Colab notebook; the input pack is never committed (confidentiality).

## Does it work? — measured on the real 50-episode run
**Automatic checks.** Parser: 50/50 episodes, 3,727 blocks, 0 unparsed lines. Candidates: 191
proposed (~3.8/episode), **187 passed hard validation (97.9%)**; **0 invalid block IDs, 0 invented
timestamps**, 0 unparseable responses; 10 clips auto-trimmed so the hook landed inside 3s; 4 failed
hard rules and were logged with reasons (3 too-short, 1 segment-too-short). Combos: 7 proposed, 6
passed — the 7th correctly refused because its source candidate had failed validation. All 193
surviving clips judged on the 5-part rubric; blind check on the top 15: **15/15 "keep scrolling",
avg comprehension 4.6/5.** Final board: 105 ranked promos.

**Manual review.** I hand-graded the top 15 against the brief's three criteria: **11 good, 4 ok, 0
bad.** For honesty I also graded a random sample of 5 low-ranked clips: 1 ok, 4 bad — matching their
low judge scores, i.e. the ranking is doing its job.

**Where it picks badly (honest failures).**
1. **Screen-time misjudgment caught by code:** cand-07-2 (ep7) was proposed as ~22s; resolving IDs
   showed 18.8s — rejected. This is exactly why the model returns IDs, not timestamps.
2. **Combos inherit source validity:** one combo was refused because its source clip had failed
   validation — a systems property, not luck, but worth knowing.
3. **Spoiler blindness at the candidate stage:** cand-39-3 shows the hero fully revealed as the
   hidden Duke (judge spoiler 3/5) and cand-19-1 names him outright — the season's central mystery.
   The rubric down-weights these, but a candidate-stage spoiler check would be cheaper.
4. **Breather episodes:** quiet episodes (6, 8, 17) yield clip-able but unpostable material — the
   tool fills the quota instead of saying "no promo found" below a score threshold.
5. **Fixed 3s hook window is brittle** for slow-build episodes: auto-trimming removed establishing
   context in 10 clips and hurt standalone clarity in a few (e.g. ep22's door-lock sequence).
6. **Judge variance is the weak link (measured):** a second independent judge run over the same 97
   clips agreed 99% (±1) on standalone clarity but only 51% on hook strength and 38% on spoiler
   risk — 1/10 top-ranked clips overlapped. Code owns everything objective; the shipped top 15 was
   human-graded (11 good / 4 ok / 0 bad); production would calibrate the rubric per show against
   real view-through data.

## Scale and cost
~2K tokens per episode in; candidates ≈3K in + 0.8K out per episode; judging ≈1.5K in per clip.
**A 50-episode show ≈ 230–250K tokens end-to-end → $0 on flash-class free tiers, ≈$0.04–0.08 paid;
~10–15 min wall-clock parallelized.** Scales linearly to 200-episode shows; the season pass reads
only loglines, so it stays cheap. Human stays in the loop: the tool shortlists, the editor approves
top N and final cut points — then ffmpeg renders the actual clips.

## Where I'd take it next
"No promo found" threshold per episode; per-show learned thresholds (hook window, ideal length);
auto-render approved clips; A/B the rubric weights against real view-through data.
