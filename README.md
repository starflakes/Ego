# Ego

Turn one long video into a batch of short clips, then auto-schedule them to
your own YouTube channel. Runs entirely on your machine — no subscription,
no third-party service sitting in the middle.

What it does:
1. Transcribes your video (local, via faster-whisper)
2. Scores the transcript to find the strongest short-form moments
3. Cuts clips around those moments with ffmpeg, optionally reframed to 9:16
   with burned-in captions
4. Uploads the clips to YouTube, spaced out over multiple days so you don't
   blow through your daily API quota (~6 uploads/day by default)

What it doesn't do (yet): TikTok/Instagram posting. Those need per-platform
developer approval (weeks-long review) before they'll let an app post
publicly, so they're left as a clean extension point — see `ego/tiktok.py`
and `ego/instagram.py` stubs — rather than something that pretends to work
today.

---

## 1. Install

Requires Python 3.10+ and ffmpeg installed and on your PATH.

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows: download from ffmpeg.org and add to PATH
```

Then install the Python dependencies:

```bash
pip install -r requirements.txt
```

The first time you transcribe a video, faster-whisper will download a model
(a few hundred MB to ~1.5GB depending on size you pick) — that needs internet
once, then it's cached locally.

## 2. Set up YouTube access (one-time, ~10 minutes)

1. Go to https://console.cloud.google.com/ and create a new project.
2. Enable the **YouTube Data API v3** for that project
   (APIs & Services → Library → search "YouTube Data API v3" → Enable).
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
   - Application type: **Desktop app**
   - Name it whatever you want (e.g. "Ego")
4. Download the resulting JSON and save it as `client_secret.json` in this
   project folder.
5. On the **OAuth consent screen** tab, add your own Google account as a
   **test user** (this keeps the app in "Testing" mode, which is fine —
   you don't need to publish or verify it for personal use).

Run once to authorize:

```bash
python -m ego auth
```

This opens a browser, you log in and approve, and it saves `token.json`
locally so you don't have to log in again.

## 3. Cut clips from a video

```bash
python -m ego clip my_podcast.mp4 --num-clips 15 --vertical --out-dir clips/
```

Options:
- `--num-clips` — how many clips to generate (default 10)
- `--min-len` / `--max-len` — clip length bounds in seconds (default 20-90)
- `--vertical` — reframe to 9:16 for Shorts (omit for original aspect ratio)
- `--captions` / `--no-captions` — burn in captions (default on)
- `--out-dir` — where clips + a `metadata.json` (titles/descriptions) get written

## 4. Upload and schedule to YouTube

```bash
python -m ego upload clips/ --per-day 5 --times "09:00,17:00" --shorts
```

This sets each clip's `publishAt` to a future time and uploads as
**private** — YouTube itself flips it to public automatically at that
timestamp. Nothing needs to keep running on your machine after upload;
YouTube handles the timing server-side.

- `--per-day` — max uploads/day (stay at or under ~6 to respect free quota)
- `--times` — comma-separated times of day to publish at
- `--shorts` — adds #Shorts to the title/description so YouTube treats it
  as a Short (needs vertical, ≤3min clips)
- `--start-date` — defaults to tomorrow

## 5. Running it as a website instead (phone-only setup)

The CLI above needs a computer. If you only have a phone, deploy the same
tool as a small website instead — everything's already built for it
(`ego/webapp.py`, `Dockerfile`). This whole process is doable from your
phone's browser, no terminal needed.

**Pick a host.** Free tiers usually don't have enough RAM for the
transcription step, so use a cheap paid one:
- **Railway** (railway.app) — easiest, ~$5/mo usage-based
- **Render** (render.com) — ~$7/mo for a plan with enough RAM
- A small **DigitalOcean** droplet also works if you want more control

**Steps (Railway example):**
1. On your phone, go to github.com, sign in (or create a free account),
   tap **New repository**, name it `ego`, and use the "upload files" option
   to upload everything in this zip.
2. Go to railway.app, sign in with GitHub, tap **New Project → Deploy from
   GitHub repo**, pick your `ego` repo. Railway detects the `Dockerfile`
   automatically and builds it.
3. In Railway's dashboard, go to **Settings → Networking → Generate Domain**.
   That gives you your `https://` link.
4. Back in Google Cloud Console (same project as before), edit your OAuth
   client — this time create it as a **Web application** type (not Desktop),
   and add `https://your-railway-domain/auth/callback` as an authorized
   redirect URI. Download that JSON as `client_secret.json` and add it to
   your GitHub repo (or upload it as a Railway "volume"/secret file —
   check Railway's docs for mounting a file at runtime, since it shouldn't
   go into a public repo as plain text if your repo is public).
5. Open your Railway link on your phone. Tap **Connect YouTube**, log in,
   then upload a video and go.

That link is yours — bookmark it, and it works from any phone browser,
any time, without me or this chat in the loop.

## Notes on quota

Google gives every new API project 10,000 units/day free. Each upload costs
1,600 units, so ~6 uploads/day out of the box — plenty for personal use
spread across the week. If you ever want more, Google Cloud Console has a
quota increase request form; approval is a form + short review, not a
strict gate like TikTok/Instagram.
