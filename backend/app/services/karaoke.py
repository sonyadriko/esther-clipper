from pathlib import Path

from app.models import HighlightSegment, TranscriptSegment


def generate_ass(
    highlights: list[HighlightSegment],
    transcript: list[TranscriptSegment],
    output_path: Path,
) -> Path:
    """Generate ASS subtitle file with karaoke word-by-word animation."""
    entries = []
    for highlight in highlights:
        words = _get_words_in_range(transcript, highlight.start, highlight.end)
        if not words:
            continue
        entries.extend(_words_to_ass_entries(words, highlight.start))

    content = _format_ass(entries)
    output_path.write_text(content, encoding="utf-8")
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
                words.append((w.word, w.start - start, w.end - start))
    return words


def _words_to_ass_entries(
    words: list[tuple[str, float, float]],
    offset: float,
) -> list[dict]:
    """Group words into lines and generate ASS karaoke tags."""
    entries = []
    line_words = []
    line_start = None

    for word, start, end in words:
        if line_start is None:
            line_start = start

        line_words.append((word, start, end))

        # New line after 4 seconds or 6 words
        if (end - line_start) >= 4.0 or len(line_words) >= 6:
            entries.append(_make_ass_entry(line_words, line_start, end, offset))
            line_words = []
            line_start = None

    if line_words:
        entries.append(_make_ass_entry(line_words, line_start, words[-1][2], offset))

    return entries


def _make_ass_entry(
    words: list[tuple[str, float, float]],
    line_start: float,
    line_end: float,
    offset: float,
) -> dict:
    """Create a single ASS dialogue line with karaoke tags."""
    # \k tag takes duration in centiseconds
    karaoke_parts = []
    prev_end = line_start

    for word, start, end in words:
        # Duration before this word (pause/transition)
        gap_cs = max(0, int((start - prev_end) * 100))
        if gap_cs > 0:
            karaoke_parts.append(f"\\kf{gap_cs}")

        # Duration of this word
        word_cs = max(1, int((end - start) * 100))
        karaoke_parts.append(f"\\kf{word_cs} {word}")
        prev_end = end

    text = "".join(karaoke_parts)

    return {
        "start": line_start + offset,
        "end": line_end + offset,
        "text": text,
    }


def _format_ass(entries: list[dict]) -> str:
    """Format ASS file with header and dialogue lines."""
    header = """[Script Info]
Title: VideoClipper AI Karaoke
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,60,1
Style: Karaoke,Arial,52,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = []
    for entry in entries:
        start_str = _format_ass_time(entry["start"])
        end_str = _format_ass_time(entry["end"])
        lines.append(f"Dialogue: 0,{start_str},{end_str},Karaoke,,0,0,0,,{entry['text']}")

    return header + "\n".join(lines) + "\n"


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
