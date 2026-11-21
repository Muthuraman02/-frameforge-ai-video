from pathlib import Path
from typing import List

from app.providers.base import ConfigurationError, GenerationContext, ImageProvider


class UnconfiguredImageProvider(ImageProvider):
    """Placeholder for real AI image generation."""

    async def generate_scene_images(
        self, ctx: GenerationContext, scenes: List[str]
    ) -> List[Path]:
        raise ConfigurationError(
            "AI image generation is not configured. Set GENERATION_MODE=demo or configure a supported AI_PROVIDER and AI_API_KEY."
        )
