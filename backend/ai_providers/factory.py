from backend.ai_providers import AIProviderProtocol
from backend.ai_providers.gemini import GeminiProvider
from backend.ai_providers.local import LocalRulesProvider
from backend.ai_providers.nim import NVIDIANIMProvider
from backend.core.config import get_settings

# Registry of provider constructors (OCP): a new provider only needs a new
# entry here, not a new branch in get_ai_provider().
_PROVIDER_CLASSES = {
    "nim": NVIDIANIMProvider,
    "gemini": GeminiProvider,
}


def get_ai_provider() -> AIProviderProtocol:
    """FastAPI dependency (DIP): routers depend on this function via
    `Depends(get_ai_provider)` rather than importing a concrete factory
    class, so a test can override it (`app.dependency_overrides`) with a
    fake provider without touching any endpoint code.

    Builds a fresh provider instance from the *current* settings on every
    call - no class-level singleton, no manual cache invalidation. Every
    provider's __init__ is cheap (it just stores an api_key/base_url; the
    network call only happens in suggest_tags()/analyze_image()), so there's
    no real cost to skipping the cache - and it means update_ai_config()
    no longer needs to remember to invalidate anything when the provider
    or its keys change.
    """
    settings = get_settings()
    provider_class = _PROVIDER_CLASSES.get(settings.AI_PROVIDER, LocalRulesProvider)
    return provider_class()
