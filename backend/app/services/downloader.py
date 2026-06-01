import yt_dlp

from app.config import settings
from app.models import VideoInfo


def _estimate_processing_time(duration: int) -> int:
    """Estimate total processing time in seconds based on video duration."""
    # Download: ~2s per minute of video
    download = max(5, duration * 0.03)
    # Transcription: ~0.5x realtime
    transcription = duration * 0.5
    # Analysis + editing: ~15s per highlight (rough)
    editing = 30
    return int(download + transcription + editing)


def get_video_info(url: str) -> VideoInfo:
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        duration = info.get("duration") or 0
        return VideoInfo(
            title=info.get("title") or "Unknown",
            thumbnail=info.get("thumbnail") or "",
            duration=duration,
            channel=info.get("uploader") or "Unknown",
            url=url,
            estimated_seconds=_estimate_processing_time(duration),
        )


def download_video(url: str, output_path: str) -> str:
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
    }
    if settings.FFMPEG_DIR:
        ydl_opts["ffmpeg_location"] = str(settings.FFMPEG_DIR)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path
