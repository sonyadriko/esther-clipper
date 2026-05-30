from pathlib import Path

from app.models import HighlightSegment, TranscriptSegment


def generate_srt(
    highlights: list[HighlightSegment],
    transcript: list[TranscriptSegment],
    output_path: Path,
) -> Path:
    entries = []
    counter = 1

    for highlight in highlights:
        words = _get_words_in_range(transcript, highlight.start, highlight.end)
        if not words:
            continue

        srt_entries = _chunk_words_to_srt(words, counter)
        entries.extend(srt_entries)
        counter += len(srt_entries)

    srt_content = _format_srt(entries)
    output_path.write_text(srt_content, encoding="utf-8")
    return output_path


def _get_words_in_range(
    transcript: list[TranscriptSegment],
    start: float,
    end: float,
) -> list[tuple[str, float, float]]:
    words = []
    for seg in transcript:
        if seg.end < start or seg.start > end:
            continue
        for w in seg.words:
            if w.end >= start and w.start <= end:
                words.append((w.word, w.start, w.end))
    return words


def _chunk_words_to_srt(
    words: list[tuple[str, float, float]],
    start_counter: int,
    max_words: int = 8,
    max_duration: float = 3.0,
) -> list[dict]:
    entries = []
    chunk = []
    chunk_start = None

    for word, start, end in words:
        if chunk_start is None:
            chunk_start = start

        chunk.append(word)

        if len(chunk) >= max_words or (end - chunk_start) >= max_duration:
            entries.append({
                "index": start_counter + len(entries),
                "start": chunk_start,
                "end": end,
                "text": " ".join(chunk),
            })
            chunk = []
            chunk_start = None

    if chunk and chunk_start is not None:
        entries.append({
            "index": start_counter + len(entries),
            "start": chunk_start,
            "end": words[-1][2],
            "text": " ".join(chunk),
        })

    return entries


def _format_srt(entries: list[dict]) -> str:
    lines = []
    for entry in entries:
        lines.append(str(entry["index"]))
        lines.append(f"{_format_time(entry['start'])} --> {_format_time(entry['end'])}")
        lines.append(entry["text"])
        lines.append("")
    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
