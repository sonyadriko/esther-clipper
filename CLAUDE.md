# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Run

```bash
# From project root
uvicorn backend.app.main:app --reload
```

Dependencies: `cd backend && pip install -r requirements.txt`

System requirement: FFmpeg must be in PATH or set `FFMPEG_PATH` in `.env`.

## Architecture

**Two-phase pipeline** — the key design decision in this codebase.

Phase 1 (detection): download → transcribe → detect highlights → **pause at `ready_for_review`**
Phase 2 (processing): user confirms/edits highlights → cut → subtitle → enhance → output

This split is why there's `run_phase1` and `run_phase2` in `pipeline.py`, and `pipeline_context` dict stores state between phases.

**Detection modes** route differently in phase 1:
- Fast: `services/highlighter.py` — audio energy analysis via NumPy
- Smart: `services/llm_highlighter.py` — calls OpenAI/Anthropic API, validates key before downloading video

**Per-highlight output** — each highlight produces its own video file (`highlight_000.mp4`, `highlight_001.mp4`, etc.) rather than concatenating into one.

## Key Patterns

- All FFmpeg calls go through `editor._run_ffmpeg()` which wraps subprocess with error handling
- `editor.burn_subtitles()` and `editor.burn_ass_subtitles()` copy files to a temp dir to avoid Windows path-with-colons issues in FFmpeg's subtitle filter
- `editor._get_video_duration()` uses ffprobe via `Path.with_name()` to resolve the path (not string replace)
- Frontend is static HTML served by FastAPI's `StaticFiles` mount — no build step, no framework
- Auth: API routes use `verify_token` (Bearer header), streaming routes use `get_token_from_query` (query param) because `<video src>` can't set headers
- Token auto-loaded from `/api/config` on frontend init (localhost only)
- Subtitle style (font, size, color, position) flows from frontend → `EnhancementOptions.subtitle_style` → `editor.burn_subtitles()` params
- Jobs auto-cleanup after 24h (`_cleanup_old_jobs` in pipeline.py)
- Estimated processing time calculated in `downloader._estimate_processing_time()` based on video duration

## Config

`backend/app/config.py` — `Settings` class loads from env vars via `python-dotenv`. Key vars: `API_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `FFMPEG_PATH`, `WHISPER_MODEL`.

FFmpeg path resolution: `FFMPEG_PATH` env var → system PATH.

## Files

- `backend/app/routes/pipeline.py` — all API endpoints and both pipeline phases. This is the main orchestration file.
- `backend/app/models.py` — all Pydantic models. `ProcessRequest` is the main input, `JobStatus` is the main output.
- `backend/app/services/` — one service per concern (download, transcribe, detect, edit, subtitle, karaoke, enhance)
- `frontend/js/app.js` — state management, polling, editor logic
- `frontend/js/api.js` — all API calls with auth headers
- `frontend/js/components.js` — pure rendering functions (no state)

## RULE.md

When user has ideas or opinions: examine first, find weak spots, don't agree by default. Be direct. Point out flawed thinking early. For simple execution tasks, just do the task cleanly.
