# PromoFinder AI

PromoFinder reads the timestamped Kuku screenplay TXT files, proposes at most
one short promo per episode, checks the proposal against its source, and ranks
only the promos that pass validation. The project keeps generation and ranking
models in separate configuration slots so each can use a different model.

This prototype follows the supplied architecture: Python, Pydantic, SQLite,
JSON, configurable LLM calls, deterministic validation and ranking, a top 10
shortlist, and an execution report. For this version, a promo can combine
multiple segments from its own episode only.

## Install and run

Python 3.9 or newer is required for the pipeline. The Streamlit interface
requires Python 3.11 or newer.

```bash
uv sync --extra dev --extra reports
cp .env.example .env
```

To include the Streamlit studio, use Python 3.11 or newer and install its
optional dependency too:

```bash
uv sync --extra dev --extra reports --extra ui
uv run streamlit run streamlit_app.py
```

Place TXT screenplays under `data/input/` (subfolders are supported), then run:

```bash
uv run python -m promofinder.main
```

Or install with pip and run from the project root:

```bash
pip install -e '.[dev,reports]'
python -m promofinder.main
```

The included screenplays are already in `data/input/`. That directory is
excluded from Git because it contains source material.

## Configure model APIs

The Streamlit interface has no model selectors. Inference uses API routes loaded by
[`src/promofinder/api_config.py`](src/promofinder/api_config.py). Set each route's provider,
model ID, endpoint, and tuning values through the corresponding environment
variables in `.env`; keep API keys there as well.

Both routes default to OpenRouter's OpenAI-compatible API using
`z-ai/glm-5.3-flash`. Set `LLM_KEY` in `.env`; the candidate and
ranking routes share it unless you set a route-specific key. The run button
stays disabled until both routes have a model ID, base URL, and API key. The
optional `file` provider is only for deliberate manual prompt/response hand-off.
Set `PROMOFINDER_TOP_K` in `.env` to choose the default shortlist size. Refresh
the Streamlit page after changing it to load the new default.

In the Streamlit interface, **Force fresh generation** bypasses saved episode
results and requests a fresh API response. It is available for API mode.

The API key is read from `.env` and is never written into logs. Configure the
candidate and ranking routes separately; either slot can point to a different
OpenAI-compatible endpoint, including a Kuku API endpoint if it accepts the
chat-completions request format. An endpoint with a different protocol needs a transport adapter in
`src/promofinder/generation/llm_client.py`.

```dotenv
LLM_KEY=your-key

CANDIDATE_PROVIDER=openai_compatible
CANDIDATE_MODEL=z-ai/glm-5.3-flash
CANDIDATE_BASE_URL=https://openrouter.ai/api/v1

RANKING_PROVIDER=openai_compatible
RANKING_MODEL=z-ai/glm-5.3-flash
RANKING_BASE_URL=https://openrouter.ai/api/v1
```

## What the pipeline checks

The parser uses the actual TXT format: episode headers, scene headings and
time ranges, plus timestamped action, camera, sound and dialogue blocks. The
model chooses block IDs rather than inventing cut timestamps. Python resolves
those IDs into timestamps and checks the episode, order, duplicate/overlapping
segments, hook position and 20–60 second duration. The duration is an estimate
from screenplay timecodes and selected block boundaries; no video is available
to verify the final edit. A separate semantic model checks source match, hook,
cliffhanger and standalone clarity. Invalid candidates get one initial attempt
and up to two correction attempts.

The ranking model scores each validated promo from 0–5 on five criteria.
Python applies the 30/25/20/15/10 weights, calculates the score out of 100,
sorts the candidates, and selects the configured top K. Ranking sees only the
selected transcript excerpts and promo metadata, not all episode scripts.

## Outputs

- `data/processed/promofinder.sqlite3`: runs, parsed episodes, candidates,
  validation attempts/errors and rankings.
- `data/outputs/candidates.json`: all candidate generation attempts and their
  validation results for the latest run.
- `data/outputs/valid_promos.json`, `failed_episodes.json`, `rankings.json`,
  `rankings.csv`, `top_promos.json`, and `raw_llm_responses.jsonl`.
- `reports/execution_report.json` and `execution_report.md`.
- `data/prompts/pending_requests.jsonl` for the manual provider hand-off.

Generated data, API logs, pending requests, local secrets, and Kuku source
screenplays are excluded from Git. The original scripts and prior outputs are
preserved under `legacy/previous_pipeline/`; they are not imported by the new
pipeline.

## Tests and notebook

Run the unit and mocked end-to-end tests:

```bash
uv run pytest
```

The notebook at `notebooks/demo.ipynb` demonstrates screenplay upload, model
configuration, and execution in Google Colab. Model credentials
are requested interactively and are not stored in the notebook.

The Streamlit studio lets you choose multiple screenplays from the input
library or drag and drop TXT files, then sends only the selected files into
the pipeline. Its Output tab lists the top K promos in rank order; selecting a
promo shows its source segments, ranking metrics, and scoring explanation.
The studio also provides manual response hand-off for model requests that
use the optional `file` provider.

## Application Screenshots

![Screenshot 1](screenshots/Screenshot%202026-11-18%20at%2016.40.36.png)

![Screenshot 2](screenshots/Screenshot%202026-11-18%20at%2016.40.48.png)

![Screenshot 3](screenshots/Screenshot%202026-11-18%20at%2016.41.08.png)

![Screenshot 4](screenshots/Screenshot%202026-11-18%20at%2016.41.27.png)

![Screenshot 5](screenshots/Screenshot%202026-11-18%20at%2016.42.08.png)

![Screenshot 6](screenshots/Screenshot%202026-11-18%20at%2016.42.21.png)