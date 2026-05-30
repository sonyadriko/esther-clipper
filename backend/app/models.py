import re
from enum import Enum

from pydantic import BaseModel, field_validator


YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w\-]+"
)


class ClipDuration(str, Enum):
    SHORT = "short"      # 30-60s
    MEDIUM = "medium"    # 2-5 min
    LONG = "long"        # 5-15 min


class SubtitleLang(str, Enum):
    INDONESIAN = "id"
    ENGLISH = "en"


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"


class PipelineStage(str, Enum):
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    EDITING = "editing"
    COMPLETE = "complete"
    ERROR = "error"


class ProcessRequest(BaseModel):
    url: str
    clip_duration: ClipDuration = ClipDuration.SHORT
    subtitle_lang: SubtitleLang = SubtitleLang.INDONESIAN
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE
    num_highlights: int = 3

    @field_validator("num_highlights")
    @classmethod
    def validate_num_highlights(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("Must be between 1 and 10")
        return v

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        v = v.strip()
        if not YOUTUBE_URL_PATTERN.match(v):
            raise ValueError("Must be a valid YouTube URL")
        return v


class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration: int
    channel: str
    url: str


class HighlightSegment(BaseModel):
    start: float
    end: float
    score: float
    text: str = ""


class OutputVideo(BaseModel):
    index: int
    filename: str
    highlight: HighlightSegment


class JobStatus(BaseModel):
    job_id: str
    stage: PipelineStage
    progress: int
    message: str
    video_info: VideoInfo | None = None
    highlights: list[HighlightSegment] = []
    outputs: list[OutputVideo] = []
    output_ready: bool = False


class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    text: str
    start: float
    end: float
    words: list[TranscriptWord] = []
