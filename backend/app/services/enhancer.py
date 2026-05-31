import subprocess
from pathlib import Path

from app.config import settings


def enhance_video(
    input_path: Path,
    output_path: Path,
    upscale: bool = True,
    color_correct: bool = True,
    denoise: bool = True,
    audio_normalize: bool = True,
    aspect_ratio: str = "16:9",
) -> Path:
    """Enhance video using FFmpeg filters. Only processes enabled filters."""
    filters_v = []
    filters_a = []

    if upscale:
        if aspect_ratio == "9:16":
            filters_v.append("scale=1080:1920:flags=lanczos")
        else:
            filters_v.append("scale=-2:1080:flags=lanczos")

    if color_correct:
        filters_v.append("eq=brightness=0.04:contrast=1.1:saturation=1.15")

    if denoise:
        filters_v.append("hqdn3d=4:3:6:4")

    if audio_normalize:
        filters_a.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    if not filters_v and not filters_a:
        # Nothing to do, just copy
        import shutil
        shutil.copy2(input_path, output_path)
        return output_path

    args = [settings.FFMPEG_PATH, "-y", "-i", str(input_path)]

    if filters_v:
        args.extend(["-vf", ",".join(filters_v)])

    if filters_a:
        args.extend(["-af", ",".join(filters_a)])

    args.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ])

    try:
        subprocess.run(args, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        raise RuntimeError(f"Enhancement failed: {stderr[-500:]}") from e

    return output_path
