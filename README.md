# VideoClipper AI

Automated YouTube highlight extractor — paste a YouTube link, get a highlight clip with AI-generated subtitles.

## Features

- **YouTube Download** — paste any public YouTube URL
- **AI Transcription** — Whisper-powered speech-to-text with word-level timestamps
- **Highlight Detection** — rule-based analysis using audio energy and silence detection
- **Auto Editing** — cuts, concatenates, and adds smooth transitions
- **Subtitles** — auto-generated SRT burned into video
- **Dark UI** — single-page workflow with real-time progress tracking

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Frontend | HTML + Tailwind CSS + vanilla JS |
| Video Download | yt-dlp |
| Transcription | OpenAI Whisper (local) |
| Video Processing | FFmpeg |
| Highlight Detection | NumPy + SciPy (audio energy analysis) |

## Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg installed and in PATH (or set `FFMPEG_PATH` env var)

### Install

```bash
cd backend
pip install -r requirements.txt
```

### Run

From the **project root**:

```bash
uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000`

### Docker

```bash
docker-compose up --build
```

Open `http://localhost:8000`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FFMPEG_PATH` | auto-detect | Path to ffmpeg binary |
| `PROJECT_DIR` | auto-detect | Project root directory |
| `WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/video-info?url=` | Fetch YouTube video metadata |
| `POST` | `/api/process` | Start highlight extraction pipeline |
| `GET` | `/api/status/{job_id}` | Poll processing progress |
| `GET` | `/api/preview/{job_id}` | Stream output video |
| `GET` | `/api/download/{job_id}` | Download final MP4 |

### POST /api/process

```json
{
  "url": "https://youtube.com/watch?v=...",
  "clip_duration": "short",
  "subtitle_lang": "id",
  "aspect_ratio": "16:9"
}
```

**Parameters:**
- `clip_duration`: `short` (30-60s), `medium` (2-5min), `long` (5-15min)
- `subtitle_lang`: `id` (Indonesian), `en` (English)
- `aspect_ratio`: `16:9` (standard), `9:16` (Shorts/Reels)

## Pipeline Flow

```
YouTube URL
    |
    v
[yt-dlp] Download video
    |
    v
[FFmpeg] Extract audio (16kHz WAV)
    |
    v
[Whisper] Transcribe with timestamps
    |
    v
[NumPy] Analyze audio energy + silence gaps
    |
    v
[Rule Engine] Select top highlight segments
    |
    v
[FFmpeg] Cut & concatenate segments
    |
    v
[FFmpeg] Generate SRT & burn subtitles
    |
    v
Final MP4 with subtitles
```

## Project Structure

```
shortez/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── models.py            # Pydantic schemas
│   │   ├── routes/pipeline.py   # API endpoints
│   │   ├── services/
│   │   │   ├── downloader.py    # yt-dlp wrapper
│   │   │   ├── transcriber.py   # Whisper transcription
│   │   │   ├── highlighter.py   # Highlight detection
│   │   │   ├── editor.py        # FFmpeg video editing
│   │   │   └── subtitle.py      # SRT generation
│   │   └── utils/
│   │       ├── audio.py         # Audio analysis
│   │       └── files.py         # File management
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── api.js               # API client
│       ├── components.js        # UI helpers
│       └── app.js               # App logic
├── docker-compose.yml
└── storage/                     # Temp files (gitignored)
```

## Highlight Detection Algorithm

1. **Audio Energy** — compute RMS energy per 1-second window
2. **Silence Detection** — find gaps below -30dB lasting > 0.5s
3. **Speech Segments** — identify continuous speech regions
4. **Scoring** — rank segments by energy level + speech density
5. **Selection** — pick top segments to fill target duration, snapped to silence boundaries

## Limitations (MVP)

- No video quality enhancement (upscaling, color correction)
- No LLM-based highlight detection (uses audio energy only)
- No translation (subtitles in source language only)
- No user accounts or rate limiting
- In-memory job storage (lost on restart)

## License

MIT
"# esther-clipper" 
