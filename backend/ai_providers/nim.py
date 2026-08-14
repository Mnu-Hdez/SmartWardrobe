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
        """Ask NIM to suggest tags for a garment based on its metadata.
        Falls back to the local heuristic provider if NIM is unavailable
        or the response can't be parsed - suggestions are non-critical,
        so a broken NIM call should never block adding a garment."""
        from backend.ai_providers.local import LocalRulesProvider

        def fallback() -> list[str]:
            return LocalRulesProvider().suggest_tags(
                name, garment_type, color_name, material, pattern, brand, season, existing_tags
            )

        if not self.api_key:
            logger.warning("NIM API key not configured, falling back to local tag suggestions")
            return fallback()

        details = [f"name: {name}", f"type: {garment_type}"]
        if color_name:
            details.append(f"color: {color_name}")
        if material:
            details.append(f"material: {material}")
        if pattern:
            details.append(f"pattern: {pattern}")
        if brand:
            details.append(f"brand: {brand}")
        if season:
            details.append(f"season: {season}")
        if existing_tags:
            details.append(f"tags already applied (do not repeat these): {', '.join(existing_tags)}")

        prompt = (
            "Suggest up to 6 short, lowercase, single/double-word tags for this garment, "
            "useful for search and outfit matching (style, vibe, fabric feel, use-case, etc). "
            "Do not repeat the type or color verbatim unless genuinely useful. "
            "Respond ONLY with a JSON array of strings, nothing else.\n\n"
            + "\n".join(details)
        )

        try:
            response = self._call_nim(prompt)
            content = response["choices"][0]["message"]["content"]
            import json

            tags = json.loads(content)
            if not isinstance(tags, list):
                raise ValueError("NIM tag response was not a list")
            cleaned = []
            existing_lower = {t.lower() for t in (existing_tags or [])}
            for t in tags:
                t = str(t).strip().lower()
                if t and t not in existing_lower and t not in cleaned:
                    cleaned.append(t)
            return cleaned[:6] if cleaned else fallback()
        except Exception as e:
            logger.error(f"NIM tag suggestion failed: {e}, falling back to local")
            return fallback()

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """Ask a NIM vision-language model to guess garment metadata from the
        photo. Falls back to the local color-only heuristic on any failure
        (missing key, model unavailable, bad JSON) so a flaky vision call
        never blocks the manual form."""
        import base64
        import json

        from backend.ai_providers.local import LocalRulesProvider

        valid_types = {"top", "bottom", "dress", "outerwear", "shoes", "accessory"}
        valid_patterns = {
            "solid", "striped", "checked", "floral", "polka_dot",
            "geometric", "abstract", "animal_print", "paisley", "houndstooth",
        }
        empty = {
            "name": None, "type": None, "color_name": None, "color_hex": None,
            "material": None, "pattern": None, "formality": None, "tags": [],
        }

        if not self.api_key:
            logger.warning("NIM API key not configured, falling back to local color analysis")
            return LocalRulesProvider().analyze_image(image_bytes, mime_type)

        prompt = (
            "Look at this photo of a single clothing item and guess its attributes. "
            "Respond ONLY with a JSON object with these exact keys:\n"
            '- "name": short descriptive name\n'
            f'- "type": one of {sorted(valid_types)}\n'
            '- "color_name": dominant color in plain English\n'
            '- "color_hex": hex code approximating the dominant color\n'
            '- "material": best guess fabric/material, or null if unclear\n'
            f'- "pattern": one of {sorted(valid_patterns)}\n'
            '- "formality": integer 1-5 (1=very casual, 5=black tie)\n'
            '- "tags": up to 5 short lowercase style/use-case tags\n'
            "Use null for anything you can't tell confidently. No prose, JSON only."
        )

        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            payload = {
                "model": settings.NIM_VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            }
            response = requests.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)

            result = dict(empty)
            if data.get("name"):
                result["name"] = str(data["name"])[:200]
            if data.get("type") in valid_types:
                result["type"] = data["type"]
            if data.get("color_name"):
                result["color_name"] = str(data["color_name"])[:50]
            hex_val = data.get("color_hex")
            if isinstance(hex_val, str) and len(hex_val) == 7 and hex_val.startswith("#"):
                result["color_hex"] = hex_val
            if data.get("material"):
                result["material"] = str(data["material"])[:100]
            if data.get("pattern") in valid_patterns:
                result["pattern"] = data["pattern"]
            formality = data.get("formality")
            if isinstance(formality, int) and 1 <= formality <= 5:
                result["formality"] = formality
            tags = data.get("tags")
            if isinstance(tags, list):
                result["tags"] = [str(t).strip().lower() for t in tags if str(t).strip()][:5]
            return result
        except Exception as e:
            logger.error(f"NIM image analysis failed: {e}, falling back to local color analysis")
            return LocalRulesProvider().analyze_image(image_bytes, mime_type)

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
