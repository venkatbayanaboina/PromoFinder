# Promo Finder — Kuku AI Generalist Assignment (Problem 1)

**Author:** Nani Bayanaboina · **Problem chosen:** 1 (Find the Promos) · **Time spent:** ~3 hours

## Why this problem
Kuku's fastest-growing content is AI-generated microdrama, and promo clips are how shows acquire
viewers — yet today an editor watches every episode of every show by hand, weekly. Problem 1 is the
most on-brand of the three, the input is real (50 screenplays of *I Married a Broken Soldier. He was
a Duke*), and output quality can be checked against actual episodes — which is what the brief weighs
most. The deliverable is a ranked shortlist of 20–60s clips; an editor still approves the top N. The
tool saves hours, it doesn't remove the editor.

## What I built (staged pipeline: code for exactness, AI for judgment)
1. **Parse (code).** Regex parser turns each screenplay into scenes and timestamped blocks with stable
   IDs (`ep12:b041`). Episode 6 uses ALL-CAPS labels — parsing is case-insensitive. Self-check
   reconciles every run against the pack census (3,727 blocks).
2. **Candidates (AI, cheap slot).** Per episode, the model proposes 3–5 promos **as block IDs, never
   timestamps** — so invented cut points are impossible by design; code resolves every ID.
3. **Validate (code).** Hard rules: IDs exist, total 20–60s, cuts on block boundaries, hook starts
   within 3s of clip start (leading blocks are auto-trimmed if the AI put the hook late), segments
   ≥3s, ≤3 segments. Every failure is logged with its reason.
4. **Score (AI, stronger slot).** Rubric 0–5: hook strength, cliffhanger strength, standalone clarity,
   emotional intensity; spoiler risk 0–5 penalized in ranking. Plus a **blind check**: a "never saw
   the show" pass over just the clip text — what did you understand, does it end unresolved, would you
   keep scrolling.
5. **Rank (code + AI).** Weighted total (hook .30, cliffhanger .25, standalone .20, intensity .15,
   spoiler −.10, blind +.02/pt); dedupe clips overlapping >0.5 IoU; variety caps (≤2 per episode, ≥1
   episode-1 clip, ≥1 cross-episode combo); each top promo gets a "post first because…" line.
6. **Output.** JSON + CSV + readable markdown report; every prompt and response logged unedited.

A cross-episode season pass pairs already-validated candidates into setup→payoff combos (the brief
allows joining moments across episodes), e.g. ep12's ultimatum cut to ep13's payoff.

**Model swap = one config edit.** `config.json` has two slots (`candidate_model`, `judge_model`);
setting `backend: "openai"` + base URL + model name + key env var points the same pipeline at Gemini,
Groq, OpenAI, or any endpoint Kuku plugs in. The submitted run used the free route: prompts were
executed by GLM (via ZCode) with the full unedited log in `prompts/`.

## Assumptions (where the brief was silent)
1. Hook window = first 3 seconds, per the brief; measured as hook-block start ≤ clip start + 3.0s.
2. Clip length = sum of segment durations (join gaps between segments don't count); 20–60s inclusive.
3. A promo = 1–3 segments, each ≥3s; cross-episode combos allowed and capped at ≤3 segments total.
4. Screenplay timestamps are ground-truth screen time (no video exists to check against).
5. Any block type can be the hook — a slap is an ACTION block, a sting is SOUND FX.
6. Speaker names drift across episodes (LADY JULIANA→JULIANA, THE FORMER GROOM→GERALD,
   LADY IN GOLD GOWN→CLARISSA); an alias table canonicalizes them. Genuinely ambiguous labels
   (BLOND NOBLEMAN) are kept raw rather than guessed.
7. "Cliffhanger" is judgment (AI-side); code enforces only length, boundaries, and the hook window.
8. The deliverable is a ranked shortlist (~10) for an editor, not auto-posting.

## Does it work? (quality checking)
**Automatic checks over the real 50-episode run** (full numbers in `outputs/quality_report.md`):
{{RESULTS_BLOCK}}

**Manual review.** I hand-graded 15 clips good / ok / bad against the three criteria:
{{MANUAL_BLOCK}}

**Where it picks badly (honest failures):**
{{FAILURES_BLOCK}}

## Scale and cost
~2K tokens per episode in; candidate ≈3K in + 0.8K out per episode; judging ≈1.5K in per clip.
**A 50-episode show ≈ 230–250K tokens end-to-end → $0 on flash-class free tiers, ≈$0.04–0.08 paid;
~10–15 min wall-clock parallelized.** A 200-episode show or 20 shows/week scales linearly; the
season pass (cross-episode combos) reads only loglines, so it stays cheap. Human stays in the loop:
the tool shortlists, the editor approves top N and the final cut points.

## Where I'd take it next
Auto-render the approved clips with ffmpeg; A/B the rubric weights against real view-through data;
learn per-show thresholds (hook window, ideal length) instead of fixed defaults.
