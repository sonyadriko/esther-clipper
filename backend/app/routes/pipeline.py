import asyncio
import traceback
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import get_token_from_query, verify_token
from app.config import settings
from app.models import (
    ClipDuration,
    JobStatus,
    OutputVideo,
    ProcessRequest,
    SubtitleLang,
    AspectRatio,
    PipelineStage,
)
from app.services import downloader, transcriber, highlighter, subtitle, editor
from app.utils.audio import extract_audio, load_audio
from app.utils.files import create_job_dir, get_output_path

router = APIRouter(prefix="/api")

jobs: dict[str, JobStatus] = {}


def _active_job_count() -> int:
    return sum(
        1 for j in jobs.values()
        if j.stage not in (PipelineStage.COMPLETE, PipelineStage.ERROR)
    )


@router.get("/video-info")
async def get_video_info(url: str, _: str = Depends(verify_token)):
    try:
        info = downloader.get_video_info(url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process")
async def start_process(
    request: ProcessRequest,
    bg: BackgroundTasks,
    _: str = Depends(verify_token),
):
    if _active_job_count() >= settings.MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=429,
            detail="Too many jobs running. Please wait.",
        )

    try:
        info = downloader.get_video_info(request.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id, job_dir = create_job_dir()

    jobs[job_id] = JobStatus(
        job_id=job_id,
        stage=PipelineStage.DOWNLOADING,
        progress=0,
        message="Starting pipeline...",
        video_info=info,
    )

    bg.add_task(
        run_pipeline,
        job_id,
        request.url,
        job_dir,
        request.clip_duration,
        request.subtitle_lang,
        request.aspect_ratio,
        request.num_highlights,
    )

    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def get_status(job_id: str, _: str = Depends(verify_token)):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/preview/{job_id}/{index}")
async def preview_video(job_id: str, index: int, _: str = Depends(get_token_from_query)):
    job = jobs.get(job_id)
    if not job or not job.output_ready:
        raise HTTPException(status_code=404, detail="Video not ready")

    output_dir = get_output_path(job_id)
    video_path = output_dir / f"highlight_{index:03d}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(video_path, media_type="video/mp4")


@router.get("/download/{job_id}/{index}")
async def download_video(job_id: str, index: int, _: str = Depends(get_token_from_query)):
    job = jobs.get(job_id)
    if not job or not job.output_ready:
        raise HTTPException(status_code=404, detail="Video not ready")

    output_dir = get_output_path(job_id)
    video_path = output_dir / f"highlight_{index:03d}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    title = job.video_info.title if job.video_info else "clip"
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
    filename = f"{safe_title}_highlight_{index + 1}.mp4"

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=filename,
    )


def _update_job(job_id: str, stage: PipelineStage, progress: int, message: str):
    if job_id in jobs:
        jobs[job_id].stage = stage
        jobs[job_id].progress = progress
        jobs[job_id].message = message


async def run_pipeline(
    job_id: str,
    url: str,
    job_dir: Path,
    clip_duration: ClipDuration,
    subtitle_lang: SubtitleLang,
    aspect_ratio: AspectRatio,
    num_highlights: int,
):
    try:
        output_dir = get_output_path(job_id)

        # Step 1: Download
        _update_job(job_id, PipelineStage.DOWNLOADING, 10, "Downloading video...")
        video_path = job_dir / "video.mp4"
        await asyncio.to_thread(downloader.download_video, url, str(video_path))

        # Step 2: Transcribe
        _update_job(job_id, PipelineStage.TRANSCRIBING, 30, "Transcribing audio...")
        audio_path = await asyncio.to_thread(extract_audio, video_path)
        transcript = await asyncio.to_thread(transcriber.transcribe, audio_path)

        # Step 3: Detect highlights
        _update_job(job_id, PipelineStage.ANALYZING, 50, "Analyzing highlights...")
        audio_data, sample_rate = await asyncio.to_thread(load_audio, audio_path)
        highlights = await asyncio.to_thread(
            highlighter.detect_highlights,
            audio_data,
            sample_rate,
            transcript,
            clip_duration.value,
            num_highlights,
        )
        jobs[job_id].highlights = highlights

        if not highlights:
            _update_job(job_id, PipelineStage.COMPLETE, 100, "No highlights detected in this video.")
            return

        # Step 4: Produce one video per highlight
        total = len(highlights)
        outputs = []

        for i, hl in enumerate(highlights):
            pct = 65 + int((i / total) * 30)
            _update_job(
                job_id, PipelineStage.EDITING, pct,
                f"Processing highlight {i + 1}/{total}...",
            )

            # Cut segment
            segment_paths = await asyncio.to_thread(
                editor.cut_segments, video_path, [hl], job_dir
            )

            # Generate SRT for this highlight
            srt_path = output_dir / f"highlight_{i:03d}.srt"
            await asyncio.to_thread(
                subtitle.generate_srt, [hl], transcript, srt_path
            )

            # Burn subtitles into segment
            final_path = output_dir / f"highlight_{i:03d}.mp4"
            await asyncio.to_thread(
                editor.burn_subtitles, segment_paths[0], srt_path, final_path
            )

            # Clean up temp segment
            for p in segment_paths:
                p.unlink(missing_ok=True)

            outputs.append(OutputVideo(
                index=i,
                filename=f"highlight_{i:03d}.mp4",
                highlight=hl,
            ))

        jobs[job_id].outputs = outputs
        _update_job(job_id, PipelineStage.COMPLETE, 100, f"Done! {total} highlight clips ready.")
        jobs[job_id].output_ready = True

    except Exception as e:
        tb = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"PIPELINE ERROR for job {job_id}")
        print(f"{'='*60}")
        print(tb)
        print(f"{'='*60}\n")
        _update_job(job_id, PipelineStage.ERROR, 0, f"Error: {str(e)}")
