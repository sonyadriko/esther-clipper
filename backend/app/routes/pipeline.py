import asyncio
import traceback
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import get_token_from_query, verify_token
from app.config import settings
from app.models import (
    ClipDuration,
    ConfirmHighlightsRequest,
    EnhancementOptions,
    HighlightSegment,
    IntroOutroOptions,
    JobStatus,
    OutputVideo,
    ProcessRequest,
    SubtitleLang,
    AspectRatio,
    PipelineStage,
)
from app.services import downloader, transcriber, highlighter, subtitle, editor, enhancer, karaoke
from app.utils.audio import extract_audio, load_audio
from app.utils.files import create_job_dir, get_output_path

router = APIRouter(prefix="/api")

jobs: dict[str, JobStatus] = {}
pipeline_context: dict[str, dict] = {}


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
        raise HTTPException(status_code=429, detail="Too many jobs running.")

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

    pipeline_context[job_id] = {
        "url": request.url,
        "job_dir": job_dir,
        "clip_duration": request.clip_duration,
        "subtitle_lang": request.subtitle_lang,
        "aspect_ratio": request.aspect_ratio,
        "enhancement": request.enhancement,
        "intro_outro": request.intro_outro,
    }

    bg.add_task(
        run_phase1,
        job_id,
        request.url,
        job_dir,
        request.clip_duration,
        request.num_highlights,
    )

    return {"job_id": job_id}


@router.post("/confirm/{job_id}")
async def confirm_highlights(
    job_id: str,
    request: ConfirmHighlightsRequest,
    bg: BackgroundTasks,
    _: str = Depends(verify_token),
):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.stage != PipelineStage.READY_FOR_REVIEW:
        raise HTTPException(status_code=400, detail="Job not ready for review")

    ctx = pipeline_context.get(job_id)
    if not ctx:
        raise HTTPException(status_code=400, detail="Pipeline context lost")

    job.highlights = request.highlights
    bg.add_task(run_phase2, job_id)

    return {"status": "confirmed", "highlights": len(request.highlights)}


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

    return FileResponse(video_path, media_type="video/mp4", filename=filename)


@router.get("/download-srt/{job_id}/{index}")
async def download_srt(job_id: str, index: int, _: str = Depends(get_token_from_query)):
    job = jobs.get(job_id)
    if not job or not job.output_ready:
        raise HTTPException(status_code=404, detail="Not ready")

    output_dir = get_output_path(job_id)
    srt_path = output_dir / f"highlight_{index:03d}.srt"
    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="SRT not found")

    title = job.video_info.title if job.video_info else "clip"
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
    filename = f"{safe_title}_highlight_{index + 1}.srt"

    return FileResponse(srt_path, media_type="text/plain", filename=filename)


def _update_job(job_id: str, stage: PipelineStage, progress: int, message: str):
    if job_id in jobs:
        jobs[job_id].stage = stage
        jobs[job_id].progress = progress
        jobs[job_id].message = message


# ── Phase 1: Download → Transcribe → Detect ──────────────────────

async def run_phase1(
    job_id: str,
    url: str,
    job_dir: Path,
    clip_duration: ClipDuration,
    num_highlights: int,
):
    try:
        _update_job(job_id, PipelineStage.DOWNLOADING, 10, "Downloading video...")
        video_path = job_dir / "video.mp4"
        await asyncio.to_thread(downloader.download_video, url, str(video_path))

        _update_job(job_id, PipelineStage.TRANSCRIBING, 30, "Transcribing audio...")
        audio_path = await asyncio.to_thread(extract_audio, video_path)
        transcript = await asyncio.to_thread(transcriber.transcribe, audio_path)

        pipeline_context[job_id]["video_path"] = video_path
        pipeline_context[job_id]["transcript"] = transcript

        _update_job(job_id, PipelineStage.ANALYZING, 60, "Analyzing highlights...")
        audio_data, sample_rate = await asyncio.to_thread(load_audio, audio_path)
        highlights = await asyncio.to_thread(
            highlighter.detect_highlights,
            audio_data, sample_rate, transcript,
            clip_duration.value, num_highlights,
        )
        jobs[job_id].highlights = highlights

        if not highlights:
            pipeline_context.pop(job_id, None)
            _update_job(job_id, PipelineStage.COMPLETE, 100, "No highlights detected.")
            return

        _update_job(job_id, PipelineStage.READY_FOR_REVIEW, 70, f"Found {len(highlights)} highlights. Review and confirm.")

    except Exception as e:
        tb = traceback.format_exc()
        print(f"\n{'='*60}\nPIPELINE PHASE 1 ERROR for job {job_id}\n{'='*60}\n{tb}\n{'='*60}\n")
        pipeline_context.pop(job_id, None)
        _update_job(job_id, PipelineStage.ERROR, 0, f"Error: {str(e)}")


# ── Phase 2: Edit → Enhance → Output ─────────────────────────────

async def run_phase2(job_id: str):
    try:
        ctx = pipeline_context.get(job_id)
        if not ctx:
            _update_job(job_id, PipelineStage.ERROR, 0, "Pipeline context lost")
            return

        output_dir = get_output_path(job_id)
        video_path = ctx["video_path"]
        transcript = ctx["transcript"]
        enhancement: EnhancementOptions = ctx["enhancement"]
        intro_outro: IntroOutroOptions = ctx["intro_outro"]
        highlights = jobs[job_id].highlights

        total = len(highlights)
        outputs = []

        for i, hl in enumerate(highlights):
            pct = 75 + int((i / total) * 22)
            _update_job(job_id, PipelineStage.EDITING, pct, f"Processing highlight {i + 1}/{total}...")

            # Cut segment
            segment_paths = await asyncio.to_thread(editor.cut_segments, video_path, [hl], ctx["job_dir"])

            # Subtitles
            srt_path = output_dir / f"highlight_{i:03d}.srt"
            await asyncio.to_thread(subtitle.generate_srt, [hl], transcript, srt_path)

            if enhancement.karaoke_subs:
                ass_path = output_dir / f"highlight_{i:03d}.ass"
                await asyncio.to_thread(karaoke.generate_ass, [hl], transcript, ass_path)
                sub_path = output_dir / f"highlight_{i:03d}_sub.mp4"
                await asyncio.to_thread(editor.burn_ass_subtitles, segment_paths[0], ass_path, sub_path)
            else:
                sub_path = output_dir / f"highlight_{i:03d}_sub.mp4"
                await asyncio.to_thread(editor.burn_subtitles, segment_paths[0], srt_path, sub_path)

            # Intro/outro
            has_intro_outro = intro_outro.intro_text or intro_outro.outro_text
            if has_intro_outro:
                io_path = output_dir / f"highlight_{i:03d}_io.mp4"
                await asyncio.to_thread(
                    editor.add_intro_outro, sub_path, io_path,
                    intro_outro.intro_text, intro_outro.outro_text,
                )
                sub_path.unlink(missing_ok=True)
                sub_path = io_path

            # Enhance
            final_path = output_dir / f"highlight_{i:03d}.mp4"
            has_enhancement = any([
                enhancement.upscale, enhancement.color_correct,
                enhancement.denoise, enhancement.audio_normalize,
            ])
            if has_enhancement:
                _update_job(job_id, PipelineStage.EDITING, pct + 1, f"Enhancing highlight {i + 1}/{total}...")
                await asyncio.to_thread(
                    enhancer.enhance_video, sub_path, final_path,
                    enhancement.upscale, enhancement.color_correct,
                    enhancement.denoise, enhancement.audio_normalize,
                )
                sub_path.unlink(missing_ok=True)
            else:
                sub_path.rename(final_path)

            # Cleanup temp segments
            for p in segment_paths:
                p.unlink(missing_ok=True)

            outputs.append(OutputVideo(index=i, filename=f"highlight_{i:03d}.mp4", highlight=hl))

        jobs[job_id].outputs = outputs
        _update_job(job_id, PipelineStage.COMPLETE, 100, f"Done! {total} highlight clips ready.")
        jobs[job_id].output_ready = True
        pipeline_context.pop(job_id, None)

    except Exception as e:
        tb = traceback.format_exc()
        print(f"\n{'='*60}\nPIPELINE PHASE 2 ERROR for job {job_id}\n{'='*60}\n{tb}\n{'='*60}\n")
        pipeline_context.pop(job_id, None)
        _update_job(job_id, PipelineStage.ERROR, 0, f"Error: {str(e)}")
