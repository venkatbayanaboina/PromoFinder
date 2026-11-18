# PromoFinder AI
**Kuku AI Generalist Assignment | Problem 1: Find the Promos**

## 1. Problem, user and success condition

Kuku editors currently need to watch each microdrama episode and manually find short moments that make a new viewer stop scrolling. PromoFinder is a source-grounded assistant for that step: it reads timestamped screenplay TXT files and proposes a ranked editorial shortlist. It does not edit video, add music or publish content.

Success for this prototype is an editor-reviewable recommendation: episode ID, ordered segment timestamps, opening hook, cliffhanger, reason and a transparent ranking score. A recommendation must be 20-60 seconds, start with a hook within the first 3 seconds, make sense to a new viewer and cut on an unresolved beat.

## 2. Scope and assumptions

- Input is the supplied English, timestamped screenplay pack. Scene, dialogue, action, camera and sound blocks are parsed into stable IDs; the original text and source hash are retained.
- Timecodes and screenplay-block boundaries are the available proxy for edit points. Duration is therefore estimated from script timecodes, not verified against rendered video or audio.
- The current prototype returns at most one promo candidate per episode. It may use multiple non-overlapping segments, but all segments must come from that same episode.
- A human editor remains the publishing decision-maker. The system is deliberately a recommender, not an autonomous clip publisher.

## 3. How the prototype works

1. **Parse and preserve provenance.** TXT files are discovered, parsed into timestamped blocks and saved in SQLite. Invalid or missing timecodes are reported instead of invented.
2. **Generate a candidate.** The candidate model receives the actual episode blocks and must return strict JSON containing only real block IDs, hook ID, cliffhanger ID and a reason. It can explicitly return no valid candidate.
3. **Validate with code first.** Pydantic validates JSON. Python verifies block ownership, chronological order, no repeated or overlapping blocks, positive timestamps, 20-60 second summed duration, hook position within the first 3 seconds, and cliffhanger placement in the final segment. Invalid output is regenerated with concrete error feedback, up to two corrections.
4. **Run a semantic judge.** A model sees only the chosen source excerpts plus candidate metadata. It must confirm source match and score hook, cliffhanger and standalone clarity. A candidate needs source match and at least 3/5 on all three to pass.
5. **Rank valid promos.** A ranking judge scores five criteria from 0-5. Python, not the model, calculates the weighted total out of 100 and sorts the shortlist. The Streamlit UI caps Top K at the number of selected files, so a two-file run cannot claim a Top 20 output.

## 4. Model, judge and swap strategy

The active route is `z-ai/glm-5.3-flash` through OpenRouter's OpenAI-compatible chat-completions API. It is used in three logical roles: candidate generator, semantic quality judge and ranking judge. Candidate and ranking routes are independently configured through `CANDIDATE_*` and `RANKING_*` variables in `api_config.py`; keys live only in `.env`. A Kuku-provided compatible API can therefore replace either route without changing parsing, validation, storage or the UI.

The ranking rubric is explicit: hook strength 30, cliffhanger strength 25, standalone clarity 20, emotional impact 15, and duration/flow 10. The model supplies the five 0-5 judgments and written weaknesses; Python verifies the response schema and recomputes the total. This separation avoids trusting an LLM to calculate or self-certify its own score.

<!-- PAGEBREAK -->

# PromoFinder AI
**Quality, evidence, scale and next steps**

## 5. Quality checks and evidence

Quality is checked at three layers: schema and timestamp rules prevent fabricated edits; the semantic judge rejects excerpts that do not match source or fail the core promo criteria; and the ranking judge produces a criterion-level explanation for an editor. SQLite stores runs, parsed episodes, candidate attempts, validation errors and rankings. JSON, CSV, Markdown and raw model-response logs make a run inspectable.

A successful live API sample run over five timestamped episodes produced five validated and ranked promos. The top scores were 95 (EP_001), 91 (EP_002), 91 (EP_003), 89 (EP_005) and 86 (EP_004). This is evidence that the full parse-generate-validate-rank path executes, not evidence of audience lift. For submission, I would run the full 50-episode pack with a stable API timeout and attach the unedited per-run JSON, CSV, raw responses and execution report.

Known failure modes are intentional review points: screenplay timecodes may not match the final video; a semantic judge can prefer a plausible but weaker moment; a single candidate can miss variety; and an API outage can stop a run before generation. The recent timeout diagnosis showed why runtime configuration matters: a one-second environment override caused repeated request failures, so production routes need monitored 120-180 second limits, retry telemetry and provider fallback.

## 6. Scale, cost and human workflow

The unit of work is an episode, so generation and semantic review can be queued or parallelized by episode while ranking remains deterministic. Source hashes plus a generation-profile hash allow reusable results when neither the script, prompt nor model configuration changed. SQLite is sufficient for a prototype; a production service would move run metadata and artifacts to managed storage, use a work queue, enforce budgets and record latency, retry and editor-acceptance metrics.

An editor sees ranked cards, source excerpts, segment maps, hook/cliffhanger text, score dimensions and weaknesses in Streamlit. They can select the final moment, adjust the cut in the NLE and feed accept/reject feedback back into calibration. The raw output is a recommendation package, not a final creative decision.

## 7. Future scope

- **Multiple promos per episode:** ask for a diverse set of candidates, validate each independently, reject near-duplicate block spans, use diversity-aware ranking and let editors choose several campaign variants per episode.
- **Cross-episode promos:** extend each segment with its own episode ID, create a global block timeline and validate global ordering, total duration, transition clarity and spoiler risk. The judge would receive only the selected multi-episode excerpts, with an editor confirmation step for every cross-cut.
- **Better signals:** add video/audio embeddings, face and action detection, subtitle readability, trend-specific hooks, and offline evaluation from editor choices and post-performance metrics.

## 8. AI-use disclosure and reproducibility

I used ChatGPT/Codex as a coding and documentation assistant, and an API-hosted GLM model as the generator and judges. AI helped scaffold prompts and UI, but deterministic source checks were kept in code. One correction was finding that the nominal 120-second API default was overridden to one second in runtime configuration; logs, rather than an AI guess, identified the real cause. Re-run with `uv sync --extra ui`, configure `.env`, then use `uv run streamlit run streamlit_app.py` or `uv run python -m promofinder.main`. Keep the supplied screenplays, API keys and raw outputs private.
