"""Cut clips with ffmpeg, optionally reframe to 9:16 and burn in captions."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .highlight import Clip
from .transcribe import Segment


def _srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(segments: list[Segment], clip_start: float, clip_end: float, out_path: Path) -> None:
    """Build a per-clip .srt from word-level timestamps, short phrases at a time."""
    lines = []
    idx = 1
    words = []
    for seg in segments:
        if seg.end < clip_start or seg.start > clip_end:
            continue
        for w in seg.words:
            if w.start < clip_start or w.end > clip_end:
                continue
            words.append(w)

    # Group words into ~4-word caption chunks
    chunk = []
    for w in words:
        chunk.append(w)
        if len(chunk) >= 4:
            start = chunk[0].start - clip_start
            end = chunk[-1].end - clip_start
            text = " ".join(c.text for c in chunk)
            lines.append(f"{idx}\n{_srt_timestamp(max(start,0))} --> {_srt_timestamp(max(end,0))}\n{text}\n")
            idx += 1
            chunk = []
    if chunk:
        start = chunk[0].start - clip_start
        end = chunk[-1].end - clip_start
        text = " ".join(c.text for c in chunk)
        lines.append(f"{idx}\n{_srt_timestamp(max(start,0))} --> {_srt_timestamp(max(end,0))}\n{text}\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def cut_clip(
    source_video: str,
    clip: Clip,
    out_path: Path,
    segments: list[Segment],
    vertical: bool = True,
    captions: bool = True,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    duration = clip.end - clip.start

    vf_parts = []
    if vertical:
        # Crop to 9:16 centered, then scale to a standard Shorts resolution.
        # crop=ih*9/16:ih -> width based on height, centered horizontally.
        vf_parts.append("crop=ih*9/16:ih")
        vf_parts.append("scale=1080:1920")
    else:
        vf_parts.append("scale=1920:-2")

    srt_path = None
    if captions:
        srt_path = out_path.with_suffix(".srt")
        _write_srt(segments, clip.start, clip.end, srt_path)
        escaped = str(srt_path).replace("\\", "\\\\").replace(":", "\\:")
        vf_parts.append(
            f"subtitles='{escaped}':force_style="
            "'FontName=Arial,FontSize=16,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=80'"
        )

    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(clip.start),
        "-i", source_video,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def write_metadata(clips: list[Clip], out_dir: Path) -> None:
    """Write auto-generated titles/descriptions per clip for later upload."""
    meta = []
    for i, c in enumerate(clips, start=1):
        title = c.text.strip().split(".")[0][:90] or f"Clip {i}"
        meta.append({
            "index": i,
            "file": f"clip_{i:02d}.mp4",
            "title": title,
            "description": c.text.strip()[:1000],
            "start": c.start,
            "end": c.end,
        })
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
