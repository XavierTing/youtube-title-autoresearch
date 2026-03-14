# YouTube Title Autoresearch — Program

Autonomous YouTube title optimization system. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch), adapted for YouTube Shorts/video title A/B testing.

## Concept

Instead of iterating on ML training code and measuring validation loss, this system iterates on **YouTube video titles** and measures **impressions click-through rate (CTR)**.

## The Experiment Loop

```
HOURLY CRON (GitHub Actions):

1. Load results.tsv — check current experiment state
2. If an experiment is RUNNING:
   a. Has 72+ hours passed? → Evaluate it
      - Fetch CTR from YouTube Analytics API
      - If CTR improved over best → KEEP (advance)
      - If CTR same or worse → DISCARD (revert to best title)
   b. Less than 72h? → Exit (nothing to do yet)
3. After evaluation (or if no experiment running):
   a. Call Claude API to propose a new title based on history
   b. Update the video title on YouTube
   c. Log as "running" in results.tsv
   d. Commit and push results.tsv for persistence
```

## Why 72 Hours?

YouTube Analytics API has a 48-72 hour data delay. We wait 72 hours to ensure reliable CTR data for the evaluation window. The hourly cron ensures we act as soon as data is available.

## Metric: Impressions Click-Through Rate (CTR)

- **What:** The percentage of impressions that turned into views
- **Formula:** views / impressions (for the experiment's time window)
- **Higher is better** (opposite of autoresearch's val_bpb)
- **Source:** YouTube Analytics API `reports.query`

## What Can Change

- **Video title** — the only variable between experiments
- Title strategies: curiosity gaps, numbers, emotional hooks, power words, specificity, urgency, length, formatting, etc.

## What Cannot Change

- Video content (obviously)
- Video description and tags (held constant for fair comparison)
- Evaluation window (72 hours)
- Target video (set via VIDEO_ID env var)

## Experiment Tracking (results.tsv)

Tab-separated file with columns:

| Column      | Description                                  |
|-------------|----------------------------------------------|
| timestamp   | ISO 8601 when title was changed              |
| video_id    | YouTube video ID                             |
| title       | The title that was set                       |
| impressions | Impression count during evaluation window    |
| ctr         | Click-through rate (decimal, 0.0 if pending) |
| status      | running, keep, discard, or baseline          |
| description | Short note about the title strategy          |

## Setup

### 1. Google Cloud Project
- Create project at https://console.cloud.google.com
- Enable **YouTube Data API v3** and **YouTube Analytics API**
- Create OAuth 2.0 credentials (Desktop app type)
- Download credentials.json

### 2. Get Refresh Token
```bash
pip install -r requirements.txt
python -m src.auth_setup
```
Complete the browser OAuth flow. Copy the printed values.

### 3. GitHub Secrets
Add these to your repo's Settings → Secrets → Actions:
- `ANTHROPIC_API_KEY`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `VIDEO_ID` (the YouTube video to optimize)

### 4. Enable GitHub Actions
Push to GitHub. The workflow runs hourly automatically, or trigger manually from the Actions tab.

## Design Principles (from autoresearch)

- **Simplicity criterion:** All else equal, simpler titles are better
- **Never stop:** The system runs autonomously — no human intervention needed
- **Learn from history:** Claude reads all past experiments to inform new proposals
- **Fair comparison:** Fixed evaluation window ensures experiments are comparable
- **State persistence:** results.tsv is committed to git so CI runs can read previous state
