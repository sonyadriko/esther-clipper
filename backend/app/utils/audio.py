import subprocess
from pathlib import Path

import numpy as np

from app.config import settings


def extract_audio(video_path: Path) -> Path:
    audio_path = video_path.parent / "audio.wav"
    try:
        subprocess.run(
            [
                settings.FFMPEG_PATH, "-y", "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                str(audio_path),
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        raise RuntimeError(f"FFmpeg audio extraction failed: {stderr[-500:]}") from e
    return audio_path


def load_audio(audio_path: Path) -> tuple[np.ndarray, int]:
    import wave

    with wave.open(str(audio_path), "rb") as wf:
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0

    return audio, sample_rate


def compute_energy(audio: np.ndarray, sample_rate: int, window_sec: float = 1.0) -> np.ndarray:
    window_size = int(sample_rate * window_sec)
    n_windows = len(audio) // window_size
    energy = np.zeros(n_windows)

    for i in range(n_windows):
        start = i * window_size
        end = start + window_size
        chunk = audio[start:end]
        energy[i] = np.sqrt(np.mean(chunk ** 2))

    if energy.max() > 0:
        energy = energy / energy.max()

    return energy


def detect_silences(
    audio: np.ndarray,
    sample_rate: int,
    threshold: float = 0.01,
    min_duration: float = 0.5,
) -> list[tuple[float, float]]:
    window_size = int(sample_rate * 0.1)
    n_windows = len(audio) // window_size
    silences = []
    silence_start = None

    for i in range(n_windows):
        start = i * window_size
        end = start + window_size
        rms = np.sqrt(np.mean(audio[start:end] ** 2))

        if rms < threshold:
            if silence_start is None:
                silence_start = i * 0.1
        else:
            if silence_start is not None:
                silence_end = i * 0.1
                if silence_end - silence_start >= min_duration:
                    silences.append((silence_start, silence_end))
                silence_start = None

    if silence_start is not None:
        silence_end = n_windows * 0.1
        if silence_end - silence_start >= min_duration:
            silences.append((silence_start, silence_end))

    return silences


def find_speech_segments(
    audio: np.ndarray,
    sample_rate: int,
    energy_threshold: float = 0.02,
) -> list[tuple[float, float]]:
    window_size = int(sample_rate * 0.5)
    hop_size = int(sample_rate * 0.1)
    n_windows = (len(audio) - window_size) // hop_size

    is_speech = np.zeros(n_windows, dtype=bool)
    for i in range(n_windows):
        start = i * hop_size
        end = start + window_size
        rms = np.sqrt(np.mean(audio[start:end] ** 2))
        is_speech[i] = rms > energy_threshold

    segments = []
    in_segment = False
    seg_start = 0.0

    for i in range(n_windows):
        time = i * 0.1
        if is_speech[i] and not in_segment:
            seg_start = time
            in_segment = True
        elif not is_speech[i] and in_segment:
            if time - seg_start >= 1.0:
                segments.append((seg_start, time))
            in_segment = False

    if in_segment:
        time = n_windows * 0.1
        if time - seg_start >= 1.0:
            segments.append((seg_start, time))

    return segments
