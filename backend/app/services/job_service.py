from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.job import VideoJob
from app.schemas.video import VideoCreateRequest


def generate_job_id() -> str:
    return f"ff_{uuid.uuid4().hex[:16]}"


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(self, payload: VideoCreateRequest) -> VideoJob:
        settings = get_settings()
        job = VideoJob(
            id=generate_job_id(),
            prompt=payload.prompt,
            style=payload.style,
            aspect_ratio=payload.aspect_ratio,
            duration=payload.duration,
            duration_seconds=payload.duration_seconds,
            generation_mode=settings.GENERATION_MODE,
            status="queued",
            progress=0,
            message="Video generation queued",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> Optional[VideoJob]:
        return self.db.query(VideoJob).filter(VideoJob.id == job_id).first()

    def update_progress(self, job_id: str, progress: int, message: str, status: str = "processing") -> None:
        job = self.get_job(job_id)
        if not job:
            return
        job.status = status
        job.progress = max(0, min(100, progress))
        job.message = message[:255]
        self.db.commit()

    def mark_completed(self, job_id: str, storage_key: str) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        job.status = "completed"
        job.progress = 100
        job.message = "Video generated successfully"
        job.storage_key = storage_key
        job.video_url = f"/videos/{job_id}"
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def mark_failed(self, job_id: str, error_message: str) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        job.status = "failed"
        job.message = "Video generation failed"
        job.error_message = error_message[:1000]
        self.db.commit()

    def increment_attempts(self, job_id: str) -> int:
        job = self.get_job(job_id)
        if not job:
            return 0
        job.attempts += 1
        self.db.commit()
        return job.attempts

    def cancel_job(self, job_id: str) -> tuple[Optional[VideoJob], bool]:
        """Cancels a queued job safely. Returns (job, cancelled_bool)."""
        job = self.get_job(job_id)
        if not job:
            return None, False
        if job.status != "queued":
            return job, False
        job.status = "cancelled"
        job.message = "Job cancelled by user"
        self.db.commit()
        self.db.refresh(job)
        return job, True

    def recover_interrupted_jobs(self) -> int:
        """Marks jobs stuck in 'processing' or 'queued' after an unexpected restart as failed."""
        stuck_jobs = (
            self.db.query(VideoJob)
            .filter(VideoJob.status.in_(["processing", "queued"]))
            .all()
        )
        for job in stuck_jobs:
            job.status = "failed"
            job.message = "Generation interrupted by server restart"
            job.error_message = (
                "The server restarted while this job was in progress. Please retry."
            )
        if stuck_jobs:
            self.db.commit()
        return len(stuck_jobs)
