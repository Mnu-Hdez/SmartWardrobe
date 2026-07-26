
from backend.ai_providers import AIProvider
from backend.ai_providers.local import LocalRulesProvider
from backend.ai_providers.nim import NVIDIANIMProvider
from backend.core.config import get_settings


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    _instance: AIProvider | None = None
    _provider_name: str | None = None

    @classmethod
    def get_provider(cls, provider_name: str | None = None) -> AIProvider:
        """Get or create an AI provider instance."""
        settings = get_settings()

        # Determine provider name
        name = provider_name or settings.ai_provider

        # Return cached instance if same provider
        if cls._instance is not None and cls._provider_name == name:
            return cls._instance

        # Create new instance
        if name == "nim":
            provider = NVIDIANIMProvider()
        else:
            provider = LocalRulesProvider()

        cls._instance = provider
        cls._provider_name = name
        return provider

    @classmethod
    async def get_available_provider(cls) -> AIProvider:
        """Get the best available provider, falling back to local."""
        settings = get_settings()

        if settings.ai_provider == "nim":
            nim_provider = NVIDIANIMProvider()
            if await nim_provider.is_available():
                cls._instance = nim_provider
                cls._provider_name = "nim"
                return nim_provider

        # Fallback to local
        provider = LocalRulesProvider()
        cls._instance = provider
        cls._provider_name = "local"
        return provider

    @classmethod
    def clear_cache(cls):
        """Clear the cached provider instance."""
        if cls._instance and hasattr(cls._instance, "close"):
            import asyncio

            try:
                asyncio.create_task(cls._instance.close())
            except Exception:
                pass
        cls._instance = None
        cls._provider_name = None
