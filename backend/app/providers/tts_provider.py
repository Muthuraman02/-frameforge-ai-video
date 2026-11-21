import logging
from pathlib import Path
from typing import Optional

from app.providers.base import TTSProvider

logger = logging.getLogger(__name__)


class NoopTTSProvider(TTSProvider):
    async def synthesize_narration(
        self, text: str, output_path: Path
    ) -> Optional[Path]:
        return None


class EdgeTTSProvider(TTSProvider):
    """Optional free narration adapter using Microsoft Edge TTS."""

    def __init__(self, voice: str = "en-US-AndrewNeural") -> None:
        self.voice = voice

    async def synthesize_narration(
        self, text: str, output_path: Path
    ) -> Optional[Path]:
        try:
            import edge_tts  # type: ignore
        except ImportError:
            logger.warning("edge-tts is not installed; skipping narration.")
            return None

        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except Exception as exc:
            logger.warning("Edge TTS narration failed (%s); continuing without narration.", exc)
        return None
