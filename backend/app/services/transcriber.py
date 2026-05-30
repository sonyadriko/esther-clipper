from pathlib import Path

import numpy as np
import whisper

from app.config import settings
from app.models import TranscriptSegment, TranscriptWord


_model = None


def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model(settings.WHISPER_MODEL)
    return _model


def load_audio_for_whisper(audio_path: Path) -> np.ndarray:
    """Load audio as numpy array using our ffmpeg path (not system PATH)."""
    import subprocess

    cmd = [
        settings.FFMPEG_PATH,
        "-nostdin", "-threads", "1",
        "-i", str(audio_path),
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(whisper.audio.SAMPLE_RATE),
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    audio = np.frombuffer(result.stdout, np.int16).flatten().astype(np.float32) / 32768.0
    return audio


def transcribe(audio_path: Path) -> list[TranscriptSegment]:
    model = get_model()
    audio = load_audio_for_whisper(audio_path)
    result = model.transcribe(
        audio,
        language=None,
        word_timestamps=True,
        verbose=False,
    )

    segments = []
    for seg in result["segments"]:
        words = []
        for w in seg.get("words", []):
            words.append(TranscriptWord(
                word=w["word"].strip(),
                start=w["start"],
                end=w["end"],
            ))

        segments.append(TranscriptSegment(
            text=seg["text"].strip(),
            start=seg["start"],
            end=seg["end"],
            words=words,
        ))

    return segments
