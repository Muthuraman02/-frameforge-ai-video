from pathlib import Path
from typing import List

from app.providers.base import ConfigurationError, GenerationContext, ScriptProvider


class UnconfiguredScriptProvider(ScriptProvider):
    """Placeholder for real LLM script/storyboard generation."""

    async def generate_script(self, ctx: GenerationContext) -> List[str]:
        raise ConfigurationError(
            "AI script generation is not configured. Set GENERATION_MODE=demo or configure a supported AI_PROVIDER and AI_API_KEY."
        )
