import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def _find_project_root() -> Path:
    """Find project root by looking for docker-compose.yml or frontend/ dir."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "docker-compose.yml").exists() or (current / "frontend").is_dir():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent


def _resolve_ffmpeg() -> tuple[str, Path | None]:
    """Resolve ffmpeg path: env var > system PATH."""
    # 1. Check environment variable
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).exists():
        p = Path(env_path)
        return str(p), p.parent if p.is_file() else p

    # 2. Fallback to system PATH
    system = shutil.which("ffmpeg")
    if system:
        p = Path(system)
        return str(p), p.parent if p.is_file() else p

    return "ffmpeg", None


class Settings:
    APP_NAME: str = "VideoClipper AI"
    VERSION: str = "1.0.0"

    BASE_DIR: Path = Path(os.environ.get("PROJECT_DIR", str(_find_project_root())))
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOADS_DIR: Path = STORAGE_DIR / "uploads"
    OUTPUTS_DIR: Path = STORAGE_DIR / "outputs"

    WHISPER_MODEL: str = "base"
    MAX_VIDEO_DURATION: int = 10800  # 3 hours in seconds
    MAX_CONCURRENT_JOBS: int = 3

    HIGHLIGHT_ENERGY_THRESHOLD: float = 0.02
    SILENCE_THRESHOLD: float = 0.01
    SILENCE_MIN_DURATION: float = 0.5
    SEGMENT_MIN_DURATION: int = 10
    SEGMENT_MAX_DURATION: int = 60

    _ffmpeg_path, _ffmpeg_dir = _resolve_ffmpeg()
    FFMPEG_PATH: str = _ffmpeg_path
    FFMPEG_DIR: Path | None = _ffmpeg_dir

    API_TOKEN: str = os.environ.get("API_TOKEN", "videoclipper-local-token")

    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

    SUBTITLE_FONT: str = "Arial"
    SUBTITLE_FONTSIZE: int = 24
    SUBTITLE_COLOR: str = "&HFFFFFF"
    SUBTITLE_OUTLINE: int = 2

    def __init__(self):
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
