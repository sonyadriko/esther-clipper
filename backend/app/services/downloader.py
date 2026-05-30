import yt_dlp

from app.config import settings
from app.models import VideoInfo


def get_video_info(url: str) -> VideoInfo:
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return VideoInfo(
            title=info.get("title") or "Unknown",
            thumbnail=info.get("thumbnail") or "",
            duration=info.get("duration") or 0,
            channel=info.get("uploader") or "Unknown",
            url=url,
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
