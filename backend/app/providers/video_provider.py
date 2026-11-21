from pathlib import Path

from app.providers.base import ConfigurationError, GenerationContext, VideoProvider


class UnconfiguredVideoProvider(VideoProvider):
    """Adapter stub for real AI text-to-video providers.

    Never silently substitutes a demo slideshow when GENERATION_MODE=ai.
    """

    def __init__(self, provider_name: str = "none") -> None:
        self.provider_name = provider_name

    async def generate_video(self, ctx: GenerationContext) -> Path:
        raise ConfigurationError(
            f"Real AI video provider '{self.provider_name}' is not configured or missing credentials. "
            "Use GENERATION_MODE=demo for free demo rendering or configure a supported AI_PROVIDER and AI_API_KEY."
        )
