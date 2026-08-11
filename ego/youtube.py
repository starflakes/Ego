"""YouTube OAuth, resumable upload, and quota-aware scheduling."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(CLIENT_SECRET_FILE).exists():
                raise SystemExit(
                    f"Missing {CLIENT_SECRET_FILE}. Follow the README's YouTube "
                    "setup steps and download your OAuth client JSON first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

    return creds


def authorize() -> None:
    _get_credentials()
    print("Authorized. token.json saved — you won't need to log in again.")


def _get_service():
    from googleapiclient.discovery import build

    creds = _get_credentials()
    return build("youtube", "v3", credentials=creds)


def upload_video(
    file_path: str,
    title: str,
    description: str,
    publish_at: dt.datetime | None = None,
    tags: list[str] | None = None,
    category_id: str = "22",  # People & Blogs; change if you want
) -> str:
    from googleapiclient.http import MediaFileUpload

    service = _get_service()

    status = {"selfDeclaredMadeForKids": False}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        status["privacyStatus"] = "public"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": status,
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/*")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status_resp, response = request.next_chunk()
    return response["id"]


def build_schedule(
    num_clips: int, per_day: int, times: list[str], start_date: dt.date
) -> list[dt.datetime]:
    """Spread num_clips uploads across days/times, oldest first."""
    schedule: list[dt.datetime] = []
    day_offset = 0
    while len(schedule) < num_clips:
        current_date = start_date + dt.timedelta(days=day_offset)
        for t in times:
            if len(schedule) >= num_clips:
                break
            hour, minute = map(int, t.split(":"))
            schedule.append(dt.datetime.combine(current_date, dt.time(hour, minute)))
            if len(schedule) % per_day == 0:
                continue
        day_offset += 1
    return schedule[:num_clips]


def upload_batch(
    clips_dir: Path,
    per_day: int = 5,
    times: list[str] | None = None,
    start_date: dt.date | None = None,
    shorts: bool = True,
) -> None:
    times = times or ["09:00", "17:00"]
    start_date = start_date or (dt.date.today() + dt.timedelta(days=1))

    meta_path = clips_dir / "metadata.json"
    if not meta_path.exists():
        raise SystemExit(f"No metadata.json found in {clips_dir} — run `ego clip` first.")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    schedule = build_schedule(len(meta), per_day, times, start_date)

    for item, publish_at in zip(meta, schedule):
        file_path = clips_dir / item["file"]
        if not file_path.exists():
            print(f"Skipping {item['file']} — file not found")
            continue
        title = item["title"]
        desc = item["description"]
        if shorts:
            title = f"{title} #Shorts"
            desc = f"{desc}\n\n#Shorts"
        video_id = upload_video(str(file_path), title, desc, publish_at=publish_at)
        print(f"Uploaded {item['file']} -> https://youtu.be/{video_id} (publishes {publish_at})")
