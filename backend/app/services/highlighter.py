import numpy as np

from app.config import settings
from app.models import HighlightSegment, TranscriptSegment
from app.utils.audio import compute_energy, detect_silences, find_speech_segments


CLIP_DURATIONS = {
    "short": (30, 60),
    "medium": (120, 300),
    "long": (300, 900),
}


def detect_highlights(
    audio: np.ndarray,
    sample_rate: int,
    transcript: list[TranscriptSegment],
    clip_duration: str,
    num_highlights: int = 3,
) -> list[HighlightSegment]:
    min_dur, max_dur = CLIP_DURATIONS.get(clip_duration, (30, 60))

    energy = compute_energy(audio, sample_rate)
    silences = detect_silences(
        audio, sample_rate,
        threshold=settings.SILENCE_THRESHOLD,
        min_duration=settings.SILENCE_MIN_DURATION,
    )
    speech_segments = find_speech_segments(
        audio, sample_rate,
        energy_threshold=settings.HIGHLIGHT_ENERGY_THRESHOLD,
    )

    scored_segments = _score_segments(
        speech_segments, energy, transcript, sample_rate,
    )

    selected = _select_segments(scored_segments, num_highlights, min_dur, max_dur)
    return selected


def _score_segments(
    speech_segments: list[tuple[float, float]],
    energy: np.ndarray,
    transcript: list[TranscriptSegment],
    sample_rate: int,
) -> list[HighlightSegment]:
    scored = []

    for seg_start, seg_end in speech_segments:
        duration = seg_end - seg_start
        if duration < settings.SEGMENT_MIN_DURATION:
            continue
        if duration > settings.SEGMENT_MAX_DURATION:
            continue

        start_idx = int(seg_start)
        end_idx = min(int(seg_end), len(energy))
        if start_idx >= len(energy) or end_idx <= start_idx:
            continue

        avg_energy = float(np.mean(energy[start_idx:end_idx]))

        text = _get_text_for_range(transcript, seg_start, seg_end)

        score = avg_energy
        if text and len(text.split()) > 3:
            score += 0.1

        scored.append(HighlightSegment(
            start=seg_start,
            end=seg_end,
            score=round(score, 4),
            text=text,
        ))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def _get_text_for_range(
    transcript: list[TranscriptSegment],
    start: float,
    end: float,
) -> str:
    words = []
    for seg in transcript:
        if seg.end < start or seg.start > end:
            continue
        for w in seg.words:
            if w.end >= start and w.start <= end:
                words.append(w.word)
    return " ".join(words)


def _select_segments(
    segments: list[HighlightSegment],
    num_highlights: int,
    min_duration: float,
    max_duration: float,
) -> list[HighlightSegment]:
    if not segments:
        return []

    selected = []
    for seg in segments:
        seg_duration = seg.end - seg.start
        if seg_duration < min_duration * 0.5:
            continue
        if seg_duration > max_duration * 1.5:
            continue
        selected.append(seg)
        if len(selected) >= num_highlights:
            break

    selected.sort(key=lambda s: s.start)
    return selected
