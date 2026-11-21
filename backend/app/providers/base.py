from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


class ConfigurationError(Exception):
    """Raised when a required AI provider or credential is not configured."""


class GenerationError(Exception):
    """Raised when video generation fails in a provider or media pipeline."""


@dataclass
class GenerationContext:
    job_id: str
    prompt: str
    style: str
    aspect_ratio: str
    duration_seconds: int
    work_dir: Path
    progress_callback: Optional[Callable[[int, str], None]] = None

    def report_progress(self, progress: int, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(progress, message)


class ScriptProvider(ABC):
    @abstractmethod
    async def generate_script(self, ctx: GenerationContext) -> List[str]:
        """Return scene narration lines or shot descriptions for the prompt."""


class ImageProvider(ABC):
    @abstractmethod
    async def generate_scene_images(
        self, ctx: GenerationContext, scenes: List[str]
    ) -> List[Path]:
        """Generate or fetch still images for each scene."""


class VideoProvider(ABC):
    @abstractmethod
    async def generate_video(self, ctx: GenerationContext) -> Path:
        """Generate a complete MP4 video file and return its local path."""


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize_narration(
        self, text: str, output_path: Path
    ) -> Optional[Path]:
        """Synthesize narration audio to output_path, or return None if disabled."""
