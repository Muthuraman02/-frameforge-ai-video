import asyncio
import logging
import shutil
from pathlib import Path

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.providers.base import ConfigurationError, GenerationContext, GenerationError
from app.services.job_service import JobService
from app.services.provider_factory import get_video_provider
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


class JobProcessor:
    """Bounded in-process async job processor.

    Limitation: Runs inside the web process using asyncio.Semaphore to cap
    concurrency (default MAX_CONCURRENT_JOBS=1). Ideal for single-instance
    free-tier demo workloads; for multi-instance production scaling, move
    execution to a dedicated worker queue (e.g. Redis + ARQ/Celery).
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._semaphore = asyncio.Semaphore(max(1, settings.MAX_CONCURRENT_JOBS))

    def _update_job_progress(self, job_id: str, progress: int, message: str) -> None:
        with SessionLocal() as db:
            JobService(db).update_progress(job_id, progress, message, status="processing")

    async def process_job(self, job_id: str) -> None:
        settings = get_settings()
        async with self._semaphore:
            with SessionLocal() as db:
                job_service = JobService(db)
                job = job_service.get_job(job_id)
                if not job:
                    logger.warning("Job %s not found before processing.", job_id)
                    return
                if job.status == "cancelled":
                    logger.info("Job %s was cancelled before starting.", job_id)
                    return

                prompt = job.prompt
                style = job.style
                aspect_ratio = job.aspect_ratio
                duration_seconds = job.duration_seconds

            max_attempts = 1 + max(0, settings.JOB_MAX_RETRIES)
            last_error = "Video generation failed."

            for attempt in range(1, max_attempts + 1):
                work_dir: Path = settings.temp_dir / f"{job_id}_attempt_{attempt}"
                try:
                    with SessionLocal() as db:
                        svc = JobService(db)
                        svc.increment_attempts(job_id)
                        svc.update_progress(job_id, 10, "Initializing video pipeline", status="processing")

                    provider = get_video_provider()
                    storage = get_storage_service()

                    ctx = GenerationContext(
                        job_id=job_id,
                        prompt=prompt,
                        style=style,
                        aspect_ratio=aspect_ratio,
                        duration_seconds=duration_seconds,
                        work_dir=work_dir,
                        progress_callback=lambda p, m: self._update_job_progress(job_id, p, m),
                    )

                    generated_path = await asyncio.wait_for(
                        provider.generate_video(ctx),
                        timeout=settings.JOB_TIMEOUT_SECONDS,
                    )

                    storage_key = f"{job_id}.mp4"
                    storage.save_video(generated_path, storage_key)

                    with SessionLocal() as db:
                        JobService(db).mark_completed(job_id, storage_key=storage_key)

                    logger.info("Job %s completed successfully on attempt %d.", job_id, attempt)
                    return

                except ConfigurationError as exc:
                    # Configuration errors are not transient; fail immediately without retrying.
                    last_error = str(exc)
                    logger.warning("Job %s configuration error: %s", job_id, last_error)
                    break
                except asyncio.TimeoutError:
                    last_error = "Video generation timed out. Please try a shorter duration or retry."
                    logger.error("Job %s timed out on attempt %d.", job_id, attempt)
                except GenerationError as exc:
                    last_error = str(exc)
                    logger.error("Job %s generation error on attempt %d: %s", job_id, attempt, exc)
                except Exception as exc:
                    last_error = "An unexpected error occurred while generating the video."
                    logger.exception("Job %s unexpected error on attempt %d: %s", job_id, attempt, exc)
                finally:
                    if work_dir.exists():
                        shutil.rmtree(work_dir, ignore_errors=True)

            with SessionLocal() as db:
                JobService(db).mark_failed(job_id, last_error)


job_processor = JobProcessor()
