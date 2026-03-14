"""Claude API integration for generating optimized YouTube titles."""

from __future__ import annotations

import os

import anthropic


def propose_new_title(
    experiment_history: str,
    current_best_title: str | None,
    current_best_ctr: float,
    video_metadata: dict,
) -> tuple[str, str]:
    """Use Claude to propose a new YouTube title based on experiment history.

    Returns:
        (new_title, strategy_description)
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system_prompt = """\
You are a YouTube title optimization expert. Your job is to propose a new title \
for a YouTube video that will maximize the impressions click-through rate (CTR).

You will be given:
- The video's current metadata (description, channel, stats)
- A history of all past title experiments and their CTR results
- The current best-performing title and its CTR

Your goal: propose a title that will BEAT the current best CTR.

Rules:
- Title must be 100 characters or fewer (YouTube limit)
- Title must be relevant to the video content (use the description as context)
- Be creative — try different strategies: curiosity gaps, numbers, emotional hooks, \
power words, controversy, specificity, urgency, etc.
- Learn from the experiment history: what strategies worked? What failed?
- Do NOT repeat a title that was already tested
- Each experiment should test a meaningfully different approach

Respond in EXACTLY this format (no extra text):
TITLE: <your proposed title>
STRATEGY: <one sentence explaining your approach>\
"""

    best_info = (
        f"Current best title: \"{current_best_title}\" (CTR: {current_best_ctr * 100:.2f}%)"
        if current_best_title
        else "No baseline yet — this is the first experiment."
    )

    user_prompt = f"""\
## Video Metadata
- Channel: {video_metadata.get('channel_title', 'Unknown')}
- Description: {video_metadata.get('description', 'No description')[:500]}
- Views: {video_metadata.get('view_count', 'Unknown')}
- Likes: {video_metadata.get('like_count', 'Unknown')}

## {best_info}

## Experiment History
{experiment_history}

Propose a new title that will beat the current best CTR.\
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()
    return _parse_response(text)


def _parse_response(text: str) -> tuple[str, str]:
    """Parse Claude's response into (title, strategy)."""
    title = ""
    strategy = ""

    for line in text.split("\n"):
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line[len("TITLE:"):].strip().strip('"')
        elif line.upper().startswith("STRATEGY:"):
            strategy = line[len("STRATEGY:"):].strip()

    if not title:
        raise ValueError(f"Failed to parse title from Claude response:\n{text}")
    if not strategy:
        strategy = "No strategy provided"

    # Enforce YouTube's 100-char limit
    if len(title) > 100:
        title = title[:97] + "..."

    return title, strategy
