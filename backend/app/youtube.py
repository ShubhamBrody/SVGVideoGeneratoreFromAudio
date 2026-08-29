"""YouTube upload via the Data API v3.

One-time setup:
  1. In Google Cloud Console, create a project and enable "YouTube Data API v3".
  2. Create an OAuth client credential of type "Desktop app" and download it as
     ``backend/client_secret.json``.
  3. Install deps:  pip install -r requirements-youtube.txt
  4. The first upload opens a browser for consent; the token is cached in
     ``backend/youtube_token.json`` and reused after that.

Uploads default to *unlisted* so nothing goes public by accident.
"""
from __future__ import annotations

from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "youtube_token.json"


class YouTubeNotConfigured(RuntimeError):
    pass


def _credentials():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except Exception as exc:
        raise YouTubeNotConfigured(
            "YouTube libraries not installed. Run: pip install -r requirements-youtube.txt"
        ) from exc

    token = Path(TOKEN_FILE)
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not Path(CLIENT_SECRET_FILE).exists():
            raise YouTubeNotConfigured(
                f"Missing {CLIENT_SECRET_FILE}. Create an OAuth Desktop client in Google "
                "Cloud Console (YouTube Data API v3) and download it here. See app/youtube.py."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload_video(
    path: str | Path,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy: str = "unlisted",
    category_id: str = "27",  # Education
) -> dict:
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except Exception as exc:
        raise YouTubeNotConfigured(
            "YouTube libraries not installed. Run: pip install -r requirements-youtube.txt"
        ) from exc

    youtube = build("youtube", "v3", credentials=_credentials())
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    upload = MediaFileUpload(str(path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=upload)

    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    return {"id": video_id, "url": f"https://youtu.be/{video_id}", "privacy": privacy}
