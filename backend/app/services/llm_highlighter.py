import json

from app.config import settings
from app.models import HighlightSegment, TranscriptSegment, LLMProvider, LLMOptions

CLIP_DURATIONS = {
    "short": (30, 60),
    "medium": (120, 300),
    "long": (300, 900),
}


def resolve_api_key(provider: LLMProvider, user_key: str = "") -> str:
    """Resolve API key: user-provided > env. Returns empty string if none."""
    if user_key:
        return user_key
    if provider == LLMProvider.OPENAI:
        return settings.OPENAI_API_KEY
    return settings.ANTHROPIC_API_KEY


def validate_api_key(provider: LLMProvider, api_key: str) -> None:
    """Test API key with a minimal request. Raises on failure."""
    if not api_key:
        raise ValueError("No API key provided")

    if provider == LLMProvider.OPENAI:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed")
        client = OpenAI(api_key=api_key)
        try:
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI key invalid: {str(e)[:150]}")
    else:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed")
        client = Anthropic(api_key=api_key)
        try:
            client.messages.create(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
        except Exception as e:
            raise RuntimeError(f"Anthropic key invalid: {str(e)[:150]}")


def detect_highlights(
    transcript: list[TranscriptSegment],
    clip_duration: str,
    num_highlights: int,
    llm_options: LLMOptions,
) -> list[HighlightSegment]:
    """Use LLM to find highlights based on semantic content. Key must be pre-resolved."""
    min_dur, max_dur = CLIP_DURATIONS.get(clip_duration, (30, 60))

    transcript_text = _format_transcript(transcript)
    prompt = _build_prompt(transcript_text, num_highlights, min_dur, max_dur)

    if llm_options.provider == LLMProvider.OPENAI:
        result_text = _call_openai(prompt, llm_options)
    else:
        result_text = _call_anthropic(prompt, llm_options)

    highlights = _parse_response(result_text, min_dur, max_dur, num_highlights)
    return highlights


def _format_transcript(segments: list[TranscriptSegment]) -> str:
    lines = []
    for seg in segments:
        start = _fmt(seg.start)
        end = _fmt(seg.end)
        lines.append(f"[{start} -> {end}] {seg.text}")
    return "\n".join(lines)


def _fmt(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def _build_prompt(transcript_text: str, num: int, min_dur: int, max_dur: int) -> str:
    return f"""You are a video highlight detector. Analyze this transcript and find the {num} most engaging, interesting, or viral-worthy moments.

Each highlight should be {min_dur}-{max_dur} seconds long.

Look for:
- Funny moments, jokes, punchlines
- Surprising statements or revelations
- Emotional peaks
- Key arguments or hot takes
- Quotable lines
- Topic transitions that are interesting

Transcript:
{transcript_text}

Return ONLY a JSON array. No explanation. Format:
[{{"start_mm:ss": "mm:ss", "end_mm:ss": "mm:ss", "reason": "why this is a highlight"}}]

Make sure timestamps are within the transcript range. Each highlight should be {min_dur}-{max_dur} seconds."""


def _call_openai(prompt: str, opts: LLMOptions) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    model = opts.model or "gpt-4o-mini"
    client = OpenAI(api_key=opts.api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {str(e)[:200]}")


def _call_anthropic(prompt: str, opts: LLMOptions) -> str:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    model = opts.model or "claude-sonnet-4-20250514"
    client = Anthropic(api_key=opts.api_key)

    try:
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )
        return response.content[0].text
    except Exception as e:
        raise RuntimeError(f"Anthropic API error: {str(e)[:200]}")


def _parse_response(
    text: str,
    min_dur: float,
    max_dur: float,
    num_highlights: int,
) -> list[HighlightSegment]:
    """Parse LLM JSON response into HighlightSegments."""
    # Extract JSON from response
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON array in text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            items = json.loads(text[start:end])
        else:
            return []

    highlights = []
    for item in items[:num_highlights]:
        start = _parse_timestamp(item.get("start_mm:ss", "0:00"))
        end = _parse_timestamp(item.get("end_mm:ss", "0:00"))
        reason = item.get("reason", "")

        duration = end - start
        if duration < min_dur * 0.3:
            continue
        if duration > max_dur * 2:
            # Clamp to max
            end = start + max_dur

        highlights.append(HighlightSegment(
            start=start,
            end=end,
            score=0.9,
            text=reason,
        ))

    highlights.sort(key=lambda h: h.start)
    return highlights


def _parse_timestamp(ts: str) -> float:
    """Parse 'mm:ss' or 'm:ss' to seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0
