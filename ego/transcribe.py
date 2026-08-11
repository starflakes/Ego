"""Local transcription with word-level timestamps."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word]


def transcribe(video_path: str, model_size: str = "small") -> list[Segment]:
    """Transcribe a video/audio file, returning segments with word timestamps.

    model_size options (speed/accuracy tradeoff): tiny, base, small, medium, large-v3.
    "small" is a good default for a laptop CPU; use "medium" or "large-v3" if you
    have a GPU and want better accuracy.
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    raw_segments, _info = model.transcribe(
        video_path,
        word_timestamps=True,
        vad_filter=True,  # skip silence, tightens timestamps around speech
    )

    segments: list[Segment] = []
    for seg in raw_segments:
        words = [Word(w.start, w.end, w.word.strip()) for w in (seg.words or [])]
        segments.append(Segment(start=seg.start, end=seg.end, text=seg.text.strip(), words=words))
    return segments
