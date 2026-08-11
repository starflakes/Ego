"""YouTube OAuth for the web app (authorization-code flow with a redirect URI,
as opposed to ego/youtube.py's installed-app flow used by the CLI)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .youtube import build_schedule, upload_video  # reused as-is

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = "client_secret.json"  # must be a "Web application" OAuth client, not Desktop
TOKEN_FILE = "token.json"

__all__ = ["is_authorized", "get_auth_url", "finish_auth", "build_schedule", "upload_video"]


def is_authorized() -> bool:
    return Path(TOKEN_FILE).exists()


def get_auth_url(redirect_uri: str) -> str:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _state = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url


def finish_auth(full_callback_url: str, redirect_uri: str) -> None:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(authorization_response=full_callback_url)
    Path(TOKEN_FILE).write_text(flow.credentials.to_json(), encoding="utf-8")
