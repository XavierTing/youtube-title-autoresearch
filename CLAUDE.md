# YouTube Title Autoresearch

## Project Overview

Autonomous YouTube title A/B testing system inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch). Changes a video's title, waits for YouTube Analytics data (72h), evaluates impressions CTR, keeps or reverts, then proposes the next experiment via Claude API. Runs on autopilot via GitHub Actions (hourly cron).

## Core Loop

1. **Check** — Is there a running experiment? Has 72h passed?
2. **Evaluate** — Fetch CTR from YouTube Analytics. Keep if improved, discard (revert) if not.
3. **Propose** — Claude generates a new title based on full experiment history.
4. **Update** — Set the new title via YouTube Data API, log to results.tsv, commit & push.

## Tech Stack

- **Language:** Python 3.11+
- **AI:** Anthropic SDK (`anthropic`) — Claude Sonnet for title generation
- **YouTube:** `google-api-python-client` — Data API v3 (read/write) + Analytics API (CTR)
- **Auth:** OAuth 2.0 with refresh token (no interactive browser auth in CI)
- **CI:** GitHub Actions (hourly cron)

## Project Structure

```
├── CLAUDE.md
├── program.md              # Detailed system design doc
├── requirements.txt
├── results.tsv             # Experiment log (committed for CI persistence)
├── .github/workflows/
│   └── autotitle.yml       # Hourly GitHub Actions cron
├── src/
│   ├── __init__.py
│   ├── main.py             # Orchestrator — the experiment state machine
│   ├── youtube_api.py      # YouTube Data + Analytics API wrapper
│   ├── analyzer.py         # Results parsing, keep/discard logic
│   ├── generator.py        # Claude API title generation
│   └── auth_setup.py       # One-time OAuth bootstrap (run locally)
└── autoresearch/           # Reference: karpathy's original repo (gitignored)
```

## Environment Variables (GitHub Actions Secrets)

- `ANTHROPIC_API_KEY` — Claude API key
- `YOUTUBE_CLIENT_ID` — Google OAuth client ID
- `YOUTUBE_CLIENT_SECRET` — Google OAuth client secret
- `YOUTUBE_REFRESH_TOKEN` — OAuth refresh token (from auth_setup.py)
- `VIDEO_ID` — YouTube video ID to optimize

## Commands

- `python -m src.auth_setup` — One-time OAuth setup (run locally with credentials.json)
- `python -m src.main` — Run one iteration of the experiment loop
- `pip install -r requirements.txt` — Install dependencies

## Conventions

- Type hints on all function signatures
- One responsibility per module
- All API keys from environment, never hardcoded
- results.tsv is committed to git (CI state persistence)
- Metric: impressions CTR (higher is better)
- Evaluation window: 72 hours (YouTube Analytics data delay)
