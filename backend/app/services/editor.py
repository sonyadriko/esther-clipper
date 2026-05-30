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


def concat_segments(
    segment_paths: list[Path],
    output_path: Path,
    aspect_ratio: str = "16:9",
) -> Path:
    list_file = output_path.parent / "segments.txt"
    lines = []
    for p in segment_paths:
        safe_path = str(p).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")

    args = ["-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]
    vf = _get_aspect_filter(aspect_ratio)
    if vf:
        args.extend(["-vf", vf])
    args.extend(["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", str(output_path)])

    try:
        _run_ffmpeg(args)
    finally:
        list_file.unlink(missing_ok=True)

    return output_path


def burn_subtitles(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    font_size: int = 24,
) -> Path:
    # Copy to temp dir to avoid Windows path-with-colons issues in subtitle filter
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


def _get_aspect_filter(aspect_ratio: str) -> str:
    if aspect_ratio == "9:16":
        return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    return ""
