from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.session import SessionLocal, init_db
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging("INFO" if settings.APP_ENV == "production" else "DEBUG")

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    with SessionLocal() as db:
        recovered = JobService(db).recover_interrupted_jobs()
        if recovered:
            logger.warning("Recovered %d interrupted job(s) from previous run.", recovered)

    logger.info(
        "Started %s v%s in %s mode (GENERATION_MODE=%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
        settings.GENERATION_MODE,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Range"],
        expose_headers=[
            "Content-Range",
            "Accept-Ranges",
            "Content-Length",
            "Content-Disposition",
        ],
    )

    @app.exception_handler(Exception)
    async def safe_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    app.include_router(router)
    return app


app = create_app()
