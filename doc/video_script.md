# Video walkthrough script (~3 min)

[0:00–0:20] The problem
"Kuku's editors watch every episode of every microdrama by hand to pick promo clips — new shows
every week. This tool reads the screenplays and finds the promos: 20 to 60 seconds, opens on a hook
in the first 3 seconds, ends on a cliffhanger, makes sense with zero context. It shortlists; an
editor still approves."

[0:20–0:50] The input + parser
"Input: 50 real screenplays of 'I Married a Broken Soldier. He was a Duke' — every scene, dialogue
line and camera move timestamped. The parser turns them into blocks with stable IDs and
self-checks against the pack: 3,727 blocks, zero unparsed lines — including episode 6, which
silently switches to ALL-CAPS labels."

[0:50–1:30] The design trick
"Here's the key decision: the AI never writes timestamps. It proposes clips as block IDs; code
resolves the IDs to real timestamps. So it can't invent a cut point that doesn't exist. Validation
then enforces the hard rules — length, boundaries, hook within 3 seconds — and auto-trims when the
AI puts the hook late. On the real run: 191 candidates, 97.9% passed, zero invalid IDs — and this
one, where the AI misjudged 18.8 seconds as 22, got caught."

[1:30–2:10] Scoring + ranking
"Every surviving clip is judged on hook strength, cliffhanger, standalone clarity, emotional
intensity — spoiler risk penalized. Then a blind check: someone who's never seen the show reads
just the clip — 15 of 15 said they'd keep scrolling. I also ran a second independent judge to
measure variance: they agree on standalone clarity but only 51% on hook appeal — that's the honest
weak spot, which is why the top 15 get human grading. Final ranking dedupes overlaps, caps two
promos per episode, and forces variety — including cross-episode combos, like the ep12 ultimatum
cut to ep13's payoff."

[2:10–2:35] The output
"This is the report the editor gets: rank, exact timestamps, the hook line, the cliffhanger line,
why it works, and 'post first because…'. JSON and CSV for the pipeline, markdown for humans."

[2:35–3:00] Swapping models + cost
"The model is one config line — point it at Gemini, Groq, OpenAI, or Kuku's own endpoint. A whole
50-episode show costs about a quarter-million tokens — free on flash tiers, under 10 cents paid.
Show me another show's screenplays and it runs the same way."

## Recording notes
- Show `outputs/promo_report.md` and the validation stats JSON on screen.
- Show `config.json` and change the model line live.
- Show one failure example from `outputs/validated.jsonl`.
