# backend/ai_providers/__init__.py
"""AI Provider Protocol and Factory.

Uses Protocol for structural subtyping (duck typing) instead of ABC inheritance.
This allows any class with the right methods to be used as an AI provider
without inheritance — the "lazy" Ponytail way.
"""

from typing import Any, Protocol

from backend.models.schemas import GarmentRead, OutfitRead


class AIProviderProtocol(Protocol):
    """Protocol for AI providers — structural subtyping (duck typing)."""

    async def enhance_recommendation(
        self,
        outfit: OutfitRead,
        context: str = "",
        user_preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enhance an outfit recommendation with AI-generated content.

        Returns:
            Dict with keys: enhanced_description, style_tips, confidence
        """
        ...

    async def generate_outfit_description(
        self, garments: list[GarmentRead], occasion: str, context: str = ""
    ) -> str:
        """Generate a natural language description for an outfit."""
        ...

    def get_provider_name(self) -> str:
        """Return the provider name."""
        ...

    async def health_check(self) -> bool:
        """Check if the provider is available."""
        ...


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    _instance: Any = None
    _provider_type: str | None = None

    @classmethod
    def create(
        cls, provider_type: str | None = None, config: dict[str, Any] | None = None
    ) -> AIProviderProtocol:
        if provider_type is None:
            from backend.core.config import get_settings

            settings = get_settings()
            provider_type = settings.ai_provider

        if cls._instance and cls._provider_type == provider_type:
            return cls._instance

        if provider_type == "nim":
            from backend.ai_providers.nim import NVIDIANIMProvider

            cls._instance = NVIDIANIMProvider(config)
        else:
            from backend.ai_providers.local import LocalRulesProvider

            cls._instance = LocalRulesProvider(config)

        cls._provider_type = provider_type
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None
        cls._provider_type = None
