# backend/ai_providers/__init__.py
"""AI Provider Protocol.

Uses Protocol for structural subtyping (duck typing) instead of ABC
inheritance - any class with the right shape can be used as an AI provider
without inheriting from anything.

This reflects the interface the providers (LocalRulesProvider,
NVIDIANIMProvider, GeminiProvider) actually implement and that
backend/api/routers/wardrobe.py actually calls: `suggest_tags` (tag
suggestions for the add-garment form) and `analyze_image` (auto-fill from
photo). Provider instantiation lives in backend/ai_providers/factory.py.
"""

from typing import Protocol


class AIProviderProtocol(Protocol):
    """Structural interface every AI provider (local/nim/gemini) satisfies."""

    name: str

    def suggest_tags(
        self,
        name: str,
        garment_type: str,
        color_name: str | None = None,
        material: str | None = None,
        pattern: str | None = None,
        brand: str | None = None,
        season: str | None = None,
        existing_tags: list[str] | None = None,
    ) -> list[str]:
        """Suggest up to a handful of short lowercase tags for a garment."""
        ...

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """Best-effort field guesses from a garment photo, shaped like
        ImageAnalysisResponse (minus `provider`)."""
        ...
