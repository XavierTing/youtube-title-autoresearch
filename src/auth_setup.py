"""One-time OAuth2 setup helper.

Run this locally to obtain a refresh token for YouTube API access.
The refresh token is then stored as a GitHub Actions secret.

Usage:
    1. Download OAuth credentials from Google Cloud Console as credentials.json
    2. Run: python -m src.auth_setup
    3. Complete the browser auth flow
    4. Copy the printed refresh_token into your GitHub repo secrets
"""

import json
import os
import tempfile

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _ensure_installed_format(creds_file: str) -> str:
    """Convert 'web' credentials to 'installed' format for InstalledAppFlow.

    Google Cloud Console can generate either 'web' or 'installed' (Desktop)
    credential types. InstalledAppFlow requires the 'installed' key.
    If the file has 'web', we rewrite it as 'installed' in a temp file.
    """
    with open(creds_file) as f:
        data = json.load(f)

    if "installed" in data:
        return creds_file

    if "web" in data:
        converted = {"installed": data["web"]}
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(converted, tmp)
        tmp.close()
        return tmp.name

    raise ValueError(f"Unrecognized credentials format in {creds_file}")


def main() -> None:
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

    if not os.path.exists(creds_file):
        print(f"ERROR: {creds_file} not found.")
        print("Download OAuth credentials from Google Cloud Console:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create OAuth 2.0 Client ID (Desktop app type)")
        print("  3. Download JSON and save as credentials.json")
        return

    actual_creds_file = _ensure_installed_format(creds_file)
    flow = InstalledAppFlow.from_client_secrets_file(actual_creds_file, SCOPES)
    credentials = flow.run_local_server(port=8080)

    print("\n=== OAuth Setup Complete ===\n")
    print("Add these as GitHub Actions secrets:\n")

    # Read client ID and secret from credentials file
    with open(creds_file) as f:
        creds_data = json.load(f)
        installed = creds_data.get("installed", creds_data.get("web", {}))

    print(f"  YOUTUBE_CLIENT_ID={installed['client_id']}")
    print(f"  YOUTUBE_CLIENT_SECRET={installed['client_secret']}")
    print(f"  YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    print()
    print("Also set:")
    print("  ANTHROPIC_API_KEY=<your Anthropic API key>")
    print("  VIDEO_ID=<YouTube video ID to optimize>")


if __name__ == "__main__":
    main()
