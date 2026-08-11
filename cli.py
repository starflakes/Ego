from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from . import clipper, highlight, transcribe, youtube


def cmd_auth(_args):
    youtube.authorize()


def cmd_clip(args):
    print(f"Transcribing {args.video} (model={args.model})... this can take a few minutes.")
    segments = transcribe.transcribe(args.video, model_size=args.model)

    print(f"Selecting {args.num_clips} clips...")
    clips = highlight.pick_clips(
        segments, num_clips=args.num_clips, min_len=args.min_len, max_len=args.max_len
    )
    if not clips:
        print("No clips found.")
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, clip in enumerate(clips, start=1):
        out_path = out_dir / f"clip_{i:02d}.mp4"
        print(f"  Cutting clip {i}/{len(clips)}: {clip.start:.1f}s - {clip.end:.1f}s")
        clipper.cut_clip(
            args.video, clip, out_path, segments,
            vertical=args.vertical, captions=args.captions,
        )

    clipper.write_metadata(clips, out_dir)
    print(f"Done. {len(clips)} clips + metadata.json written to {out_dir}/")


def cmd_upload(args):
    times = [t.strip() for t in args.times.split(",")]
    start_date = dt.date.fromisoformat(args.start_date) if args.start_date else None
    youtube.upload_batch(
        Path(args.clips_dir),
        per_day=args.per_day,
        times=times,
        start_date=start_date,
        shorts=args.shorts,
    )


def main():
    parser = argparse.ArgumentParser(prog="ego", description="Clip long videos, auto-post to YouTube.")
    sub = parser.add_subparsers(required=True)

    p_auth = sub.add_parser("auth", help="One-time YouTube OAuth setup")
    p_auth.set_defaults(func=cmd_auth)

    p_clip = sub.add_parser("clip", help="Transcribe + cut clips from a video")
    p_clip.add_argument("video")
    p_clip.add_argument("--num-clips", type=int, default=10)
    p_clip.add_argument("--min-len", type=float, default=20.0)
    p_clip.add_argument("--max-len", type=float, default=90.0)
    p_clip.add_argument("--model", default="small", help="whisper model size")
    p_clip.add_argument("--vertical", dest="vertical", action="store_true", default=True)
    p_clip.add_argument("--no-vertical", dest="vertical", action="store_false")
    p_clip.add_argument("--captions", dest="captions", action="store_true", default=True)
    p_clip.add_argument("--no-captions", dest="captions", action="store_false")
    p_clip.add_argument("--out-dir", default="clips")
    p_clip.set_defaults(func=cmd_clip)

    p_upload = sub.add_parser("upload", help="Upload + schedule a clips folder to YouTube")
    p_upload.add_argument("clips_dir")
    p_upload.add_argument("--per-day", type=int, default=5)
    p_upload.add_argument("--times", default="09:00,17:00")
    p_upload.add_argument("--start-date", default=None, help="YYYY-MM-DD, defaults to tomorrow")
    p_upload.add_argument("--shorts", dest="shorts", action="store_true", default=True)
    p_upload.add_argument("--no-shorts", dest="shorts", action="store_false")
    p_upload.set_defaults(func=cmd_upload)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
