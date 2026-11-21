from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings

ALLOWED_STYLES = (
    "Cinematic",
    "Anime",
    "Realistic",
    "3D Animation",
    "Fantasy",
    "Documentary",
)

ALLOWED_ASPECT_RATIOS = ("16:9", "9:16", "1:1")

DURATION_MAP = {
    "8 seconds": 8,
    "12 seconds": 12,
    "20 seconds": 20,
    "8": 8,
    "12": 12,
    "20": 20,
}

JobStatusType = Literal["queued", "processing", "completed", "failed", "cancelled"]


class VideoCreateRequest(BaseModel):
    prompt: str = Field(..., description="Text description of the video to generate.")
    style: str = Field(..., description="Visual style preset.")
    aspect_ratio: str = Field(..., description="Output video aspect ratio (16:9, 9:16, 1:1).")
    duration: str = Field(..., description="Target duration (8 seconds, 12 seconds, 20 seconds).")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Prompt cannot be empty.")
        max_len = get_settings().MAX_PROMPT_LENGTH
        if len(cleaned) > max_len:
            raise ValueError(f"Prompt exceeds maximum length of {max_len} characters.")
        return cleaned

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in ALLOWED_STYLES:
            raise ValueError(
                f"Invalid style '{cleaned}'. Must be one of: {', '.join(ALLOWED_STYLES)}."
            )
        return cleaned

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in ALLOWED_ASPECT_RATIOS:
            raise ValueError(
                f"Invalid aspect_ratio '{cleaned}'. Must be one of: {', '.join(ALLOWED_ASPECT_RATIOS)}."
            )
        return cleaned

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: str) -> str:
        cleaned = str(value).strip().lower()
        if cleaned not in DURATION_MAP:
            raise ValueError(
                "Invalid duration. Must be '8 seconds', '12 seconds', or '20 seconds'."
            )
        seconds = DURATION_MAP[cleaned]
        return f"{seconds} seconds"

    @property
    def duration_seconds(self) -> int:
        return DURATION_MAP[self.duration.lower()]


class VideoCreateResponse(BaseModel):
    job_id: str
    status: JobStatusType
    progress: int = Field(ge=0, le=100)
    message: str


class VideoStatusResponse(BaseModel):
    job_id: str
    status: JobStatusType
    progress: int = Field(ge=0, le=100)
    message: str
    video_url: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
