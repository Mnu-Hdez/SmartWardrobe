from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.models.schemas import GarmentRead, OutfitRead


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
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
        pass

    @abstractmethod
    async def generate_outfit_description(
        self, garments: list[GarmentRead], occasion: str, context: str = ""
    ) -> str:
        """Generate a natural language description for an outfit."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""
        pass


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    _instance: AIProvider | None = None
    _provider_type: str | None = None

    @classmethod
    def create(
        cls, provider_type: str = None, config: dict[str, Any] | None = None
    ) -> AIProvider:
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
