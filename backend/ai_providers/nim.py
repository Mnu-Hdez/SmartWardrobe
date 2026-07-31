import json
from typing import Any

import httpx

from backend.ai_providers import AIProviderProtocol
from backend.models.schemas import GarmentRead, OutfitRead


class NVIDIANIMProvider:
    """NVIDIA NIM API provider for AI-enhanced recommendations."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        from backend.core.config import get_settings

        settings = get_settings()

        self.api_url = self.config.get("api_url", settings.nim_api_url)
        self.api_key = self.config.get("api_key", settings.nim_api_key)
        self.model = self.config.get("model", settings.nim_model)
        self.name = "nim"

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=30.0)
        return self._client

    def get_provider_name(self) -> str:
        return "nim"

    async def health_check(self) -> bool:
        """Check if the provider is available."""
        if not self.api_key:
            return False
        try:
            client = await self._get_client()
            response = await client.get("/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def enhance_recommendation(
        self,
        outfit: OutfitRead,
        context: str = "",
        user_preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enhance recommendation using NVIDIA NIM LLM."""
        if not self.api_key:
            # Fallback to local provider
            from backend.ai_providers.local import LocalRulesProvider

            local = LocalRulesProvider()
            return await local.enhance_recommendation(outfit, context, user_preferences)

        garments = outfit.garments if hasattr(outfit, "garments") and outfit.garments else []

        # Build prompt
        prompt = self._build_enhancement_prompt(outfit, garments, context, user_preferences)

        try:
            client = await self._get_client()
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                },
            )

            if response.status_code != 200:
                raise Exception(f"NIM API error: {response.status_code} - {response.text}")

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)

            return {
                "enhanced_description": result.get(
                    "description", f"A stylish {outfit.occasion} outfit."
                ),
                "style_tips": result.get("tips", []),
                "confidence": result.get("confidence", 0.9),
            }

        except Exception:
            # Fallback to local
            from backend.ai_providers.local import LocalRulesProvider

            local = LocalRulesProvider()
            return await local.enhance_recommendation(outfit, context, user_preferences)

    async def generate_outfit_description(
        self, garments: list[GarmentRead], occasion: str, context: str = ""
    ) -> str:
        """Generate natural language description using NIM."""
        if not self.api_key:
            from backend.ai_providers.local import LocalRulesProvider

            local = LocalRulesProvider()
            return await local.generate_outfit_description(garments, occasion, context)

        prompt = self._build_description_prompt(garments, occasion, context)

        try:
            client = await self._get_client()
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a fashion stylist. Generate a concise, appealing outfit description in one paragraph.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200,
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()

        except Exception:
            pass

        # Fallback
        from backend.ai_providers.local import LocalRulesProvider

        local = LocalRulesProvider()
        return await local.generate_outfit_description(garments, occasion, context)

    def _get_system_prompt(self) -> str:
        return """You are an expert fashion stylist AI. Analyze outfits and provide:
1. An engaging, natural-language description (1-2 sentences)
2. 3-5 practical style tips
3. A confidence score (0-1)

Respond ONLY with valid JSON in this format:
{
  "description": "string",
  "tips": ["string", ...],
  "confidence": number
}"""

    def _build_enhancement_prompt(
        self,
        outfit: OutfitRead,
        garments: list[GarmentRead],
        context: str,
        user_preferences: dict[str, Any] | None,
    ) -> str:
        garment_details = []
        for g in garments:
            details = f"- {g.color_name} {g.type} ({g.pattern}, formality: {g.formality}/5"
            if g.material:
                details += f", {g.material}"
            if g.brand:
                details += f", {g.brand}"
            details += ")"
            garment_details.append(details)

        prefs_text = ""
        if user_preferences:
            prefs = []
            if user_preferences.get("preferred_colors"):
                prefs.append(f"preferred colors: {', '.join(user_preferences['preferred_colors'])}")
            if user_preferences.get("avoid_colors"):
                prefs.append(f"avoid colors: {', '.join(user_preferences['avoid_colors'])}")
            if user_preferences.get("style_keywords"):
                prefs.append(f"style: {', '.join(user_preferences['style_keywords'])}")
            prefs_text = f"User preferences: {'; '.join(prefs)}. " if prefs else ""

        context_text = f"Context: {context}. " if context else ""

        return f"""Outfit for: {outfit.occasion} (formality: {outfit.formality}/5)
Season: {outfit.season}
{context_text}{prefs_text}
Garments:
{chr(10).join(garment_details) if garment_details else "None provided"}

Score: {outfit.score}/100

Enhance this recommendation with an engaging description and practical styling tips."""

    def _build_description_prompt(
        self, garments: list[GarmentRead], occasion: str, context: str
    ) -> str:
        garment_desc = ", ".join([f"{g.color_name} {g.type} ({g.pattern})" for g in garments])
        context_text = f" for {context}" if context else ""
        return f"Describe this {occasion} outfit{context_text}: {garment_desc}. Make it appealing and specific."

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None