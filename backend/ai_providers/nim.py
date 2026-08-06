# Smart Wardrobe - AI Providers
# NVIDIA NIM integration

import logging
from typing import Any

import requests

from backend.core.config import settings
from backend.models.garment import Garment, Outfit
from backend.models.schemas import OutfitRecommendationRequest, PackingPlanRequest

logger = logging.getLogger(__name__)


class NVIDIANIMProvider:
    """NVIDIA NIM integration for advanced AI recommendations"""

    def __init__(self):
        self.name = "nim"
        self.api_key = settings.NIM_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def recommend_outfits(
        self, request: OutfitRecommendationRequest, garments: list[Garment]
    ) -> list[Outfit]:
        """Generate outfit recommendations using NIM"""
        if not self.api_key:
            logger.warning("NIM API key not configured, falling back to local")
            from backend.ai_providers.local import LocalRulesProvider

            return LocalRulesProvider().recommend_outfits(request, garments)

        # Prepare context for NIM
        garment_context = self._prepare_garment_context(garments)
        prompt = self._build_recommendation_prompt(request, garment_context)

        try:
            response = self._call_nim(prompt)
            return self._parse_recommendations(response, request)
        except Exception as e:
            logger.error(f"NIM recommendation failed: {e}, falling back to local")
            from backend.ai_providers.local import LocalRulesProvider

            return LocalRulesProvider().recommend_outfits(request, garments)

    def create_packing_plan(
        self, request: PackingPlanRequest, garments: list[Garment]
    ) -> dict[str, Any]:
        """Create packing plan using NIM"""
        if not self.api_key:
            from backend.ai_providers.local import LocalRulesProvider

            return LocalRulesProvider().create_packing_plan(request, garments)

        garment_context = self._prepare_garment_context(garments)
        prompt = self._build_packing_prompt(request, garment_context)

        try:
            response = self._call_nim(prompt)
            return self._parse_packing_plan(response, request)
        except Exception as e:
            logger.error(f"NIM packing plan failed: {e}, falling back to local")
            from backend.ai_providers.local import LocalRulesProvider

            return LocalRulesProvider().create_packing_plan(request, garments)

    def _prepare_garment_context(self, garments: list[Garment]) -> str:
        """Prepare garment list as context for LLM"""
        lines = []
        for g in garments:
            lines.append(
                f"- {g.name} ({g.type}, {g.color_name}, formality: {g.formality}/5, season: {g.season}, pattern: {g.pattern})"
            )
        return "\n".join(lines)

    def _build_recommendation_prompt(
        self, request: OutfitRecommendationRequest, context: str
    ) -> str:
        return f"""You are a professional stylist. Recommend {request.top_n} outfit(s) for a {request.occasion} occasion in {request.season} season.

Available garments:
{context}

Requirements:
- Occasion: {request.occasion}
- Season: {request.season}
- Formality level: {request.formality or 'any'}/5
- Number of outfits: {request.top_n}

For each outfit, provide:
1. Name
2. List of garment names used
3. Score (0-100)
4. Score breakdown: color_harmony, formality_match, pattern_balance, seasonal
5. 1-2 style tips

Return as JSON array of outfits."""

    def _build_packing_prompt(self, request: PackingPlanRequest, context: str) -> str:
        return f"""You are a travel stylist. Create a {request.days}-day packing plan for {request.occasion} in {request.season} season.

Available garments:
{context}

Constraints:
- Max items: {request.max_items}
- Days: {request.days}
- Occasion: {request.occasion}
- Season: {request.season}

Provide:
1. Daily outfits (name, garments, score)
2. Packing list with versatility scores
3. Total items, days covered, mix-and-match ratio

Return as JSON."""

    def _call_nim(self, prompt: str) -> dict:
        """Call NIM API"""
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional fashion stylist. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        response = requests.post(
            f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def _parse_recommendations(
        self, response: dict, request: OutfitRecommendationRequest
    ) -> list[Outfit]:
        """Parse NIM response into Outfit objects"""
        import json

        try:
            content = response["choices"][0]["message"]["content"]
            outfits_data = json.loads(content)
            outfits = []
            for o in outfits_data:
                outfit = Outfit(
                    name=o.get("name", "Recommended Outfit"),
                    occasion=request.occasion,
                    season=request.season,
                    score=o.get("score", 75),
                    score_breakdown=o.get("score_breakdown", {}),
                    ai_tips=o.get("tips", []),
                )
                outfits.append(outfit)
            return outfits
        except Exception as e:
            logger.error(f"Failed to parse NIM response: {e}")
            return []

    def _parse_packing_plan(self, response: dict, request: PackingPlanRequest) -> dict[str, Any]:
        """Parse NIM packing plan response"""
        import json

        try:
            content = response["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse NIM packing response: {e}")
            return {
                "outfits": [],
                "packing_list": [],
                "total_items": 0,
                "days_covered": 0,
                "mix_and_match_ratio": 0,
            }
