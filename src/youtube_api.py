"""YouTube Data API v3 and YouTube Analytics API wrapper."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_authenticated_services(
    client_id: str | None = None,
    client_secret: str | None = None,
    refresh_token: str | None = None,
) -> tuple:
    """Build authenticated YouTube Data API and YouTube Analytics API services.

    Uses OAuth2 refresh token flow (no interactive browser auth).
    Falls back to environment variables if args not provided.
    """
    client_id = client_id or os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = client_secret or os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = refresh_token or os.environ["YOUTUBE_REFRESH_TOKEN"]

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )

    youtube_data = build("youtube", "v3", credentials=credentials)
    youtube_analytics = build("youtubeAnalytics", "v2", credentials=credentials)

    return youtube_data, youtube_analytics


def get_video_info(youtube_data, video_id: str) -> dict:
    """Fetch current video snippet (title, description, categoryId, tags)."""
    response = (
        youtube_data.videos()
        .list(part="snippet,statistics", id=video_id)
        .execute()
    )
    if not response.get("items"):
        raise ValueError(f"Video not found: {video_id}")

    item = response["items"][0]
    snippet = item["snippet"]
    stats = item.get("statistics", {})

    return {
        "video_id": video_id,
        "title": snippet["title"],
        "description": snippet.get("description", ""),
        "category_id": snippet["categoryId"],
        "tags": snippet.get("tags", []),
        "channel_title": snippet.get("channelTitle", ""),
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
    }


def update_video_title(youtube_data, video_id: str, new_title: str) -> bool:
    """Update a video's title. Preserves all other snippet fields.

    YouTube's videos.update requires the full snippet with categoryId.
    """
    # First fetch current snippet to preserve fields
    response = (
        youtube_data.videos().list(part="snippet", id=video_id).execute()
    )
    if not response.get("items"):
        raise ValueError(f"Video not found: {video_id}")

    snippet = response["items"][0]["snippet"]
    snippet["title"] = new_title

    youtube_data.videos().update(
        part="snippet",
        body={"id": video_id, "snippet": snippet},
    ).execute()

    return True


def get_ctr_data(
    youtube_analytics,
    video_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Query YouTube Analytics for impressions and CTR in a date range.

    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format

    Returns:
        dict with keys: impressions, views, ctr
    """
    response = (
        youtube_analytics.reports()
        .query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="impressions,views",
            filters=f"video=={video_id}",
        )
        .execute()
    )

    rows = response.get("rows", [])
    if not rows:
        return {"impressions": 0, "views": 0, "ctr": 0.0}

    impressions = int(rows[0][0])
    views = int(rows[0][1])
    ctr = views / impressions if impressions > 0 else 0.0

    return {"impressions": impressions, "views": views, "ctr": ctr}


def get_date_range_for_experiment(
    start_timestamp: str, hours: int = 72
) -> tuple[str, str]:
    """Convert an experiment start timestamp to Analytics API date range."""
    start_dt = datetime.fromisoformat(start_timestamp)
    end_dt = start_dt + timedelta(hours=hours)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
