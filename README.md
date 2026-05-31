# VideoClipper AI

Automated YouTube highlight extractor — paste a YouTube link, get highlight clips with subtitles.

## Features

- **YouTube Download** — paste any public YouTube URL
- **Two Detection Modes:**
  - **Fast** — rule-based audio energy analysis. Best for streams, reactions, debates.
  - **Smart** — LLM semantic analysis (OpenAI GPT-4o-mini / Anthropic Claude). Best for podcasts, interviews, tutorials.
- **Manual Highlight Editing** — review, add, remove, or adjust timestamps before processing
- **Per-Highlight Output** — each highlight becomes a separate video (configurable 1-10 clips)
- **Auto Subtitles** — SRT generation with word-level timestamps from Whisper
- **Karaoke Subtitles** — word-by-word ASS animation (toggle)
- **Video Enhancement** — upscale to 1080p, color correction, denoise, audio normalization (toggles)
- **Intro/Outro Overlays** — add text overlays at start/end of each clip
- **SRT Export** — download .srt file per highlight
- **Aspect Ratio** — 16:9 standard or 9:16 Shorts/Reels
- **Dark UI** — single-page workflow with real-time progress

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Frontend | HTML + Tailwind CSS + vanilla JS |
| YouTube | yt-dlp |
| Transcription | OpenAI Whisper (local) |
| Highlight Detection | NumPy (Fast) / OpenAI API or Anthropic API (Smart) |
| Video Processing | FFmpeg |

## Prerequisites

- Python 3.11+
- FFmpeg installed and in PATH
- ~2GB disk space (Whisper model + temp files)
- For Smart mode: OpenAI or Anthropic API key

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure

Edit `.env`:

```env
API_TOKEN=your-secret-token

# For Smart detection mode (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run

From the **project root**:

```bash
uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000`

### Docker

```bash
docker-compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/video-info?url=` | Fetch YouTube video metadata |
| `POST` | `/api/process` | Start pipeline (Phase 1: detect) |
| `POST` | `/api/confirm/{job_id}` | Confirm edited highlights (Phase 2: process) |
| `GET` | `/api/status/{job_id}` | Poll progress |
| `GET` | `/api/preview/{job_id}/{index}` | Stream video |
| `GET` | `/api/download/{job_id}/{index}` | Download MP4 |
| `GET` | `/api/download-srt/{job_id}/{index}` | Download SRT |

All endpoints require `Authorization: Bearer <token>` header (except video/download which use `?token=` query param).

### POST /api/process

```json
{
  "url": "https://youtube.com/watch?v=...",
  "clip_duration": "short",
  "subtitle_lang": "id",
  "aspect_ratio": "16:9",
  "num_highlights": 3,
  "detection_mode": "fast",
  "llm": {
    "provider": "openai",
    "api_key": "",
    "model": ""
  },
  "enhancement": {
    "upscale": true,
    "color_correct": true,
    "denoise": true,
    "audio_normalize": true,
    "karaoke_subs": false,
    "add_intro": false,
    "add_outro": false
  },
  "intro_outro": {
    "intro_text": "",
    "outro_text": ""
  }
}
```

### Pipeline Stages

```
downloading → transcribing → analyzing → ready_for_review → editing → complete
```

The pipeline pauses at `ready_for_review` for user to edit highlights via `POST /api/confirm/{job_id}`.

## Project Structure

```
shortez/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── models.py            # Pydantic schemas
│   │   ├── auth.py              # Bearer token auth
│   │   ├── routes/
│   │   │   ├── pipeline.py      # API endpoints + pipeline
│   │   │   └── config.py        # Config endpoint
│   │   ├── services/
│   │   │   ├── downloader.py    # YouTube download
│   │   │   ├── transcriber.py   # Whisper transcription
│   │   │   ├── highlighter.py   # Rule-based detection
│   │   │   ├── llm_highlighter.py # LLM detection
│   │   │   ├── editor.py        # FFmpeg video editing
│   │   │   ├── subtitle.py      # SRT generation
│   │   │   ├── karaoke.py       # ASS karaoke generation
│   │   │   └── enhancer.py      # Video enhancement
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
├── .env                         # Config (gitignored)
├── .env.example
├── docker-compose.yml
└── storage/                     # Temp files (gitignored)
```

## Detection Modes

### Fast (Rule-Based)
- Computes RMS audio energy per 1-second window
- Detects silence gaps for clean cut points
- Scores segments by energy + speech density
- Free, instant, no API key needed

### Smart (LLM)
- Sends full transcript to LLM
- AI identifies jokes, hot takes, emotional peaks, quotable moments
- Returns ranked segments with reasons
- Requires API key (OpenAI or Anthropic)
- Costs ~$0.03-0.10 per video

## Enhancement Options

| Toggle | Effect |
|--------|--------|
| Upscale 1080p | Sharp upscale via lanczos filter |
| Color Fix | Brightness +0.04, contrast 1.1, saturation 1.15 |
| Denoise | hqdn3d noise reduction |
| Audio Norm | EBU R128 loudness normalization (-16 LUFS) |
| Karaoke Subs | Word-by-word ASS subtitle animation |
| Intro/Outro | Text overlay at start/end of clip |

## Limitations

- In-memory job storage (lost on restart)
- No user accounts (single API token)
- No video quality enhancement beyond FFmpeg filters
- No subtitle translation (source language only)

## License

MIT
"# esther-clipper"
