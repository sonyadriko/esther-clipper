import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.models import HighlightSegment


def _run_ffmpeg(args: list[str], cwd: str | None = None):
    """Run ffmpeg with better error messages."""
    cmd = [settings.FFMPEG_PATH] + args
    try:
        subprocess.run(cmd, capture_output=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        raise RuntimeError(f"FFmpeg failed (exit {e.returncode}): {stderr[-500:]}") from e


def cut_segments(
    video_path: Path,
    highlights: list[HighlightSegment],
    output_dir: Path,
) -> list[Path]:
    segment_paths = []

    for i, seg in enumerate(highlights):
        output_path = output_dir / f"segment_{i:03d}.mp4"
        _run_ffmpeg([
            "-y", "-i", str(video_path),
            "-ss", str(seg.start), "-to", str(seg.end),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            str(output_path),
        ])
        segment_paths.append(output_path)

    return segment_paths


def burn_subtitles(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    font_size: int = 24,
) -> Path:
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_video = tmp_dir / "input.mp4"
    tmp_srt = tmp_dir / "sub.srt"
    tmp_output = tmp_dir / "output.mp4"

    shutil.copy2(video_path, tmp_video)
    shutil.copy2(srt_path, tmp_srt)

    subtitle_filter = (
        f"subtitles=sub.srt:force_style="
        f"'FontSize={font_size},PrimaryColour=&HFFFFFF,"
        f"OutlineColour=&H000000,Outline=2,Shadow=1,"
        f"MarginV=30'"
    )

    try:
        _run_ffmpeg([
            "-y", "-i", str(tmp_video),
            "-vf", subtitle_filter,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            str(tmp_output),
        ], cwd=str(tmp_dir))
        shutil.copy2(tmp_output, output_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_path


def burn_ass_subtitles(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
) -> Path:
    """Burn ASS subtitles (karaoke) into video."""
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_video = tmp_dir / "input.mp4"
    tmp_ass = tmp_dir / "sub.ass"
    tmp_output = tmp_dir / "output.mp4"

    shutil.copy2(video_path, tmp_video)
    shutil.copy2(ass_path, tmp_ass)

    try:
        _run_ffmpeg([
            "-y", "-i", str(tmp_video),
            "-vf", "ass=sub.ass",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            str(tmp_output),
        ], cwd=str(tmp_dir))
        shutil.copy2(tmp_output, output_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_path


def add_intro_outro(
    video_path: Path,
    output_path: Path,
    intro_text: str = "",
    outro_text: str = "",
    duration: float = 3.0,
) -> Path:
    """Add text intro and/or outro to video."""
    if not intro_text and not outro_text:
        import shutil as shutil_mod
        shutil_mod.copy2(video_path, output_path)
        return output_path

    filters = []

    if intro_text:
        escaped = _escape_drawtext(intro_text)
        filters.append(
            f"drawtext=text='{escaped}':"
            f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"enable='between(t,0.5,{duration - 0.5})'"
        )

    if outro_text:
        # Get video duration first, then use it for outro timing
        # For simplicity, outro appears at the end for 'duration' seconds
        escaped = _escape_drawtext(outro_text)
        filters.append(
            f"drawtext=text='{escaped}':"
            f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"enable='gte(t,0)'"
        )

    if not filters:
        import shutil as shutil_mod
        shutil_mod.copy2(video_path, output_path)
        return output_path

    _run_ffmpeg([
        "-y", "-i", str(video_path),
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        str(output_path),
    ])

    return output_path


def _escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    return text.replace("'", "'\\''").replace(":", "\\:").replace("%", "%%")
