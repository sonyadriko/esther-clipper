import uuid
from pathlib import Path

from app.config import settings


def create_job_dir() -> tuple[str, Path]:
    job_id = uuid.uuid4().hex[:12]
    job_dir = settings.UPLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir


def get_output_path(job_id: str) -> Path:
    path = settings.OUTPUTS_DIR / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path
