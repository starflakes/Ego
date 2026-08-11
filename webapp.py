"""Ego web app — upload a video, get clips, schedule to YouTube.
Single-user personal tool: no accounts, no multi-tenancy.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_from_directory, url_for

from . import clipper, highlight, transcribe, youtube_web

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
CLIPS_DIR = BASE_DIR / "data" / "clips"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("EGO_SECRET_KEY", "dev-key-change-me")


@app.route("/")
def index():
    return render_template("index.html", authorized=youtube_web.is_authorized())


@app.route("/clip", methods=["POST"])
def clip():
    video = request.files["video"]
    num_clips = int(request.form.get("num_clips", 10))
    vertical = request.form.get("vertical") == "on"
    captions = request.form.get("captions") == "on"

    video_path = UPLOAD_DIR / video.filename
    video.save(video_path)

    segments = transcribe.transcribe(str(video_path), model_size="small")
    clips = highlight.pick_clips(segments, num_clips=num_clips)

    out_dir = CLIPS_DIR / video_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(clips, start=1):
        out_path = out_dir / f"clip_{i:02d}.mp4"
        clipper.cut_clip(str(video_path), c, out_path, segments, vertical=vertical, captions=captions)
    clipper.write_metadata(clips, out_dir)

    return redirect(url_for("results", batch=video_path.stem))


@app.route("/results/<batch>")
def results(batch):
    out_dir = CLIPS_DIR / batch
    meta = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    return render_template(
        "results.html", batch=batch, clips=meta, authorized=youtube_web.is_authorized()
    )


@app.route("/clips/<batch>/<filename>")
def serve_clip(batch, filename):
    return send_from_directory(CLIPS_DIR / batch, filename)


@app.route("/auth/start")
def auth_start():
    redirect_uri = url_for("auth_callback", _external=True)
    return redirect(youtube_web.get_auth_url(redirect_uri))


@app.route("/auth/callback")
def auth_callback():
    redirect_uri = url_for("auth_callback", _external=True)
    youtube_web.finish_auth(request.url, redirect_uri)
    return redirect(url_for("index"))


@app.route("/schedule/<batch>", methods=["POST"])
def schedule(batch):
    out_dir = CLIPS_DIR / batch
    meta = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))

    per_day = int(request.form.get("per_day", 5))
    times = [t.strip() for t in request.form.get("times", "09:00,17:00").split(",")]
    start_date = dt.date.today() + dt.timedelta(days=1)
    shorts = request.form.get("shorts") == "on"

    times_schedule = youtube_web.build_schedule(len(meta), per_day, times, start_date)
    results_log = []
    for item, publish_at in zip(meta, times_schedule):
        file_path = out_dir / item["file"]
        title = item["title"] + (" #Shorts" if shorts else "")
        desc = item["description"] + ("\n\n#Shorts" if shorts else "")
        video_id = youtube_web.upload_video(str(file_path), title, desc, publish_at=publish_at)
        results_log.append({"file": item["file"], "url": f"https://youtu.be/{video_id}", "publish_at": str(publish_at)})

    return render_template("scheduled.html", results=results_log)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
