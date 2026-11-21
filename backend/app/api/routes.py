from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import enforce_rate_limit, validate_job_id
from app.database.session import get_db
from app.schemas.video import (
    HealthResponse,
    VideoCreateRequest,
    VideoCreateResponse,
    VideoStatusResponse,
)
from app.services.job_service import JobService
from app.services.storage_service import get_storage_service
from app.services.video_service import build_video_stream_response
from app.workers.processor import job_processor

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.post(
    "/api/videos",
    response_model=VideoCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Videos"],
    dependencies=[Depends(enforce_rate_limit)],
)
def create_video_job(
    payload: VideoCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> VideoCreateResponse:
    job = JobService(db).create_job(payload)
    background_tasks.add_task(job_processor.process_job, job.id)
    return VideoCreateResponse(
        job_id=job.id,
        status=job.status,  # type: ignore[arg-type]
        progress=job.progress,
        message=job.message,
    )


@router.get(
    "/api/videos/{job_id}",
    response_model=VideoStatusResponse,
    tags=["Videos"],
)
def get_video_status(
    job_id: str = Depends(validate_job_id),
    db: Session = Depends(get_db),
) -> VideoStatusResponse:
    job = JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video job not found.",
        )
    return VideoStatusResponse(
        job_id=job.id,
        status=job.status,  # type: ignore[arg-type]
        progress=job.progress,
        message=job.message,
        video_url=job.video_url,
        error=job.error_message,
    )


@router.get("/videos/{job_id}", tags=["Videos"])
def stream_or_download_video(
    request: Request,
    download: bool = Query(default=False),
    job_id: str = Depends(validate_job_id),
    db: Session = Depends(get_db),
):
    job = JobService(db).get_job(job_id)
    if not job or job.status != "completed" or not job.storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated video not found.",
        )

    storage = get_storage_service()
    video_path = storage.get_local_path(job.storage_key)
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file is no longer available on storage.",
        )

    return build_video_stream_response(
        file_path=video_path,
        request=request,
        download_filename=f"frameforge-{job.id}.mp4",
        as_attachment=download,
    )


@router.delete(
    "/api/videos/{job_id}",
    response_model=VideoStatusResponse,
    tags=["Videos"],
)
def cancel_video_job(
    job_id: str = Depends(validate_job_id),
    db: Session = Depends(get_db),
) -> VideoStatusResponse:
    job, cancelled = JobService(db).cancel_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video job not found.",
        )
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel job in '{job.status}' state.",
        )
    return VideoStatusResponse(
        job_id=job.id,
        status=job.status,  # type: ignore[arg-type]
        progress=job.progress,
        message=job.message,
        video_url=job.video_url,
        error=job.error_message,
    )
