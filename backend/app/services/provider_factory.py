from app.core.config import get_settings
from app.providers.base import ConfigurationError, TTSProvider, VideoProvider
from app.providers.demo_provider import DemoVideoProvider
from app.providers.tts_provider import EdgeTTSProvider, NoopTTSProvider
from app.providers.video_provider import UnconfiguredVideoProvider


def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    tts = settings.TTS_PROVIDER.strip().lower()
    if tts == "edge":
        return EdgeTTSProvider()
    return NoopTTSProvider()


def get_video_provider() -> VideoProvider:
    settings = get_settings()
    mode = settings.GENERATION_MODE.strip().lower()
    if mode == "demo":
        return DemoVideoProvider(tts_provider=get_tts_provider())

    if mode == "ai":
        if not settings.AI_API_KEY.strip() or settings.AI_PROVIDER.strip().lower() in {"", "none"}:
            raise ConfigurationError(
                "GENERATION_MODE is set to 'ai', but AI_PROVIDER or AI_API_KEY is not configured."
            )
        return UnconfiguredVideoProvider(provider_name=settings.AI_PROVIDER)

    raise ConfigurationError(f"Unsupported GENERATION_MODE: {settings.GENERATION_MODE}")
