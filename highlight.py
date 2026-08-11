"""Score transcript segments and pick non-overlapping clip windows."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .transcribe import Segment

FILLER_WORDS = {"um", "uh", "like", "you know", "sort of", "kind of", "i mean", "basically"}

HOOK_PATTERNS = [
    r"\b(never|always|secret|mistake|truth|wrong|nobody|everyone|worst|best|biggest)\b",
    r"\b(here's why|the reason|what nobody tells you|i realized|turns out)\b",
    r"\?\s*$",  # ends on a question
    r"!",  # exclamation / emphasis
]


@dataclass
class Clip:
    start: float
    end: float
    text: str
    score: float


def _segment_score(seg: Segment) -> float:
    text = seg.text.lower()
    words = text.split()
    if not words:
        return 0.0

    score = 0.0

    # Reward hook-like language
    for pattern in HOOK_PATTERNS:
        if re.search(pattern, text):
            score += 1.5

    # Penalize filler-heavy segments (usually low-energy rambling)
    filler_count = sum(1 for w in words if w.strip(".,!?") in FILLER_WORDS)
    score -= 0.5 * (filler_count / len(words))

    # Reward reasonably dense, information-carrying segments (not too short)
    if 8 <= len(words) <= 60:
        score += 0.5

    # Slight reward for numbers/specifics ("3 ways", "10x", stats) — concrete
    # claims tend to hook viewers better than vague statements.
    if re.search(r"\b\d+\b", text):
        score += 0.4

    return max(score, 0.0)


def _merge_into_windows(
    segments: list[Segment], min_len: float, max_len: float
) -> list[Clip]:
    """Slide over segments, building candidate windows within [min_len, max_len]
    that snap to segment boundaries so clips don't cut mid-sentence."""
    windows: list[Clip] = []
    n = len(segments)
    for i in range(n):
        start = segments[i].start
        text_parts = []
        total_score = 0.0
        for j in range(i, n):
            end = segments[j].end
            length = end - start
            text_parts.append(segments[j].text)
            total_score += _segment_score(segments[j])
            if length < min_len:
                continue
            if length > max_len:
                break
            windows.append(Clip(start=start, end=end, text=" ".join(text_parts), score=total_score))
    return windows


def _select_non_overlapping(
    candidates: list[Clip], num_clips: int, video_duration: float
) -> list[Clip]:
    """Greedily pick the highest-scoring windows, skipping overlaps and
    lightly penalizing windows that cluster near already-picked ones so
    clips spread across the whole video instead of bunching in one section."""
    candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
    chosen: list[Clip] = []

    def overlaps(a: Clip, b: Clip) -> bool:
        return a.start < b.end and b.start < a.end

    for cand in candidates:
        if len(chosen) >= num_clips:
            break
        if any(overlaps(cand, c) for c in chosen):
            continue
        chosen.append(cand)

    chosen.sort(key=lambda c: c.start)
    return chosen


def pick_clips(
    segments: list[Segment],
    num_clips: int = 10,
    min_len: float = 20.0,
    max_len: float = 90.0,
) -> list[Clip]:
    if not segments:
        return []
    video_duration = segments[-1].end
    candidates = _merge_into_windows(segments, min_len, max_len)
    if not candidates:
        raise ValueError(
            "No candidate clips found — video may be shorter than min_len, "
            "or try lowering --min-len."
        )
    return _select_non_overlapping(candidates, num_clips, video_duration)
